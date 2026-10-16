# Channel Estimate - 线性回归侧信道攻击

## 测试结果

**Channel Estimate SSE vs Key Guess 曲线：**


| 指标 | 测试结果 |
|------|----------|
| **Key correct** | True |
| **PGE total** | 0 |
| **Avg PGE** | 0.00 |
| **Max PGE** | 0 |
| **通过验证** | ✓ PASS |

## 1. 算法原理

### 1.1 核心概念

Channel Estimate（信道估计）攻击是一种基于线性回归的侧信道攻击方法。该方法将功耗轨迹视为"信道"，通过线性回归建立功耗与假设功耗之间的关系。

**核心假设**：设备功耗可以建模为假设功耗值的线性组合。

### 1.2 数学模型

给定：
- 轨迹样本矩阵：$T \in \mathbb{R}^{n \times m}$（$n$ 条轨迹，$m$ 个时间点）
- 假设功耗向量：$H \in \mathbb{R}^n$（基于泄漏模型计算）

**信道估计**：

$$T \cdot c \approx H$$

通过伪逆求解：

$$c = (T^T T)^{-1} T^T H = T^+ H$$

其中 $T^+$ 是 $T$ 的伪逆（SVD 分解实现）。

### 1.3 攻击流程

1. **数据分割**：将轨迹分为 fitting set 和 test set
2. **假设计算**：对每个密钥猜测 $k$，计算汉明重量假设 $HW[S-Box[P \oplus k]]$
3. **信道估计**：使用 fitting set 通过伪逆估计信道系数 $c$
4. **预测验证**：用 test set 验证预测误差 SSE
5. **密钥排序**：SSE 最小的猜测为最可能密钥

### 1.4 密钥排序（PGE）

对于每个子密钥字节，根据 SSE 对 256 个密钥猜测排序：

$$PGE = \text{正确密钥在排序中的位置}$$

- $PGE = 0$：正确密钥排名最高
- $PGE = 255$：正确密钥排名最后

## 2. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── ChannelEstimateAnalyzer (继承自 Analyzer)
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `ChannelEstimateAnalyzer` | channel_estimate.py | 主分析器类 |
| `ChannelEstimateResult` | channel_estimate.py | 分析结果数据类 |

### 继承结构图

```
Analyzer (squirrel.base)
    │
    └── ChannelEstimateAnalyzer
            ├── name = "channel_estimate"
            ├── description = "Channel Estimate Attack - Linear Regression"
            │
            ├── __init__(config: dict | None)
            │       ├── num_subkeys: int = 16
            │       ├── fit_ratio: float = 0.8
            │       ├── use_svd: bool = True
            │       └── leakage_model: str = "sbox_output"
            │
            ├── analyze(traces, labels=None, plaintext, key=None, **kwargs) -> ChannelEstimateResult
            │       └── 返回包含最佳密钥猜测和SSE的ChannelEstimateResult
            │
            └── detect_leakage_points(result, threshold) -> np.ndarray
```

## 3. API接口说明

### 构造函数

```python
ChannelEstimateAnalyzer(config: dict[str, Any] | None = None)
```

**配置参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `num_subkeys` | 16 | 要分析的子密钥字节数（1-16） |
| `fit_ratio` | 0.8 | 轨迹分割比例（用于 fitting） |
| `use_svd` | True | 使用 SVD 伪逆加速求解 |
| `leakage_model` | "sbox_output" | 泄漏模型："sbox_output" 或 "pt_key_xor" |

### 主要方法

#### `analyze(traces, plaintext, key=None, **kwargs) -> ChannelEstimateResult`

运行 Channel Estimate 攻击。

**参数：**
- `traces`: np.ndarray，形状为 (num_traces, num_samples) 的功耗轨迹
- `plaintext`: np.ndarray，明文数据，形状为 (num_traces, 16)
- `key`: np.ndarray，可选，已知密钥用于计算 PGE
- `labels`: np.ndarray，可选，标签数据

**返回：**
`ChannelEstimateResult` 对象，包含最佳密钥猜测和 SSE。

```python
result = analyzer.analyze(traces, plaintext=plaintext, key=known_key)
print(f"猜测密钥: {[hex(b) for b in result.key_guess]}")
print(f"PGE: {result.pge}")
```

### ChannelEstimateResult 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `method` | str | "channel_estimate" |
| `num_subkeys` | int | 分析的子密钥数量 |
| `num_traces_fit` | int | 用于拟合的轨迹数 |
| `num_traces_test` | int | 用于测试的轨迹数 |
| `total_samples` | int | 每条轨迹的样本数 |
| `best_guesses` | list[list[dict]] | 每个字节的最佳猜测列表 |
| `key_guess` | list[int] | 猜测的完整密钥（16字节） |
| `all_sses` | list[np.ndarray] | 每个字节的 256 维 SSE 数组 |
| `pge` | list[int] | 每个子密钥的排序误差 |
| `metadata` | dict | 附加元数据 |

### best_guesses 条目结构

```python
[
    [{"guess": 42, "sse": 0.123}, {"guess": 87, "sse": 0.456}, ...],  # Byte 0
    [{"guess": 33, "sse": 0.234}, ...],  # Byte 1
    ...
]
```

### 使用示例

```python
from squirrel.analysis import ChannelEstimateAnalyzer
import numpy as np

analyzer = ChannelEstimateAnalyzer(config={
    "num_subkeys": 16,
    "fit_ratio": 0.8,
    "use_svd": True,
    "leakage_model": "sbox_output"
})

traces = np.random.randn(1000, 3000)
plaintext = np.random.randint(0, 256, size=(1000, 16), dtype=np.uint8)

result = analyzer.analyze(traces, plaintext=plaintext)

print(f"猜测密钥: {result.key_guess}")
print(f"PGE: {result.pge}")
```

## 4. 与 CPA 对比

| 特性 | CPA | Channel Estimate |
|------|-----|------------------|
| 原理 | 相关性分析 | 线性回归 |
| 数学工具 | Pearson 相关系数 | SVD 伪逆 |
| 数据需求 | 单组轨迹 | fitting + test 分割 |
| 计算复杂度 | O(n×m×256) | O(n×m×256) |
| 抗噪声 | 较强 | 中等 |

## 5. 合成测试数据泄漏模型

### 5.1 独立字节泄漏模型

与 CPA 的累积泄漏不同，Channel Estimate 使用独立字节泄漏模型：

```
泄露值(字节b) = 高斯脉冲(位置b) × (HW[S-Box[P_b ⊕ K_b]] / 8) × 幅值
```

每个字节的脉冲位置不同，避免重叠：

| 字节 | 脉冲位置偏移 |
|------|-------------|
| Byte 0 | -160 samples |
| Byte 1 | -120 samples |
| ... | ... |
| Byte 15 | +160 samples |

### 5.2 生成公式

```python
for b in range(16):
    pulse_b = np.roll(pulse, (b - 8) * 20)
    leakage_b = pulse_b * (hw_per_byte[b] / 8.0) * 2.0
    traces_row += leakage_b
```

### 5.3 数据生成器

合成 Channel Estimate 测试数据由 `tests/data_generators/generate_channel_estimate_dataset.py` 生成：

```bash
python -m tests.data_generators.cli channel_estimate \
    --output ./ce_test.zarr \
    --num-traces 500 \
    --num-samples 500 \
    --noise-std 0.01 \
    --seed 42
```

## 6. 参考

- O'Flynn, C. (2014). Channel Estimation Attack. ChipWhisperer Documentation.
- Mangard, S., Oswald, E., & Popp, T. (2008). Power Analysis Attacks: Revealing the Secrets of Smart Cards.
