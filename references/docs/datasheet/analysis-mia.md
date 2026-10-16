# MIA - 互信息分析攻击

## 测试结果

**MIA Mutual Information vs Time 曲线：**


**MIA MI vs Key Guess 曲线：**


| 指标 | 测试结果 |
|------|----------|
| **Key correct** | True |
| **Correct bytes** | 16/16 |
| **Max MI** | 1.7980 |
| **Avg MI** | 0.1887 |
| **通过验证** | ✓ PASS |

**测试条件：** 500 轨迹 × 500 样本，高斯噪声 σ=0.1

## 1. 算法原理

### 1.1 核心概念

MIA（Mutual Information Analysis，互信息分析）是一种基于信息论的侧信道攻击方法。与 CPA 使用相关性不同，MIA 直接计算侧信道观测值与密钥依赖泄漏之间的**互信息**。

**核心假设**：设备功耗与处理的中间值之间存在统计依赖关系，可以用互信息来量化。

### 1.2 数学公式

**互信息定义：**

给定两个离散随机变量 $X$ 和 $Y$，它们的互信息定义为：

$$I(X; Y) = H(X) + H(Y) - H(X, Y)$$

其中：
- $H(X) = -\sum_{x} P(x) \log_2 P(x)$ 是香农熵
- $H(X, Y) = -\sum_{x,y} P(x,y) \log_2 P(x,y)$ 是联合熵

**估计方法：**

使用直方图法估计概率分布：
1. 将连续轨迹值离散化（分箱）
2. 计算各离散值的频率作为概率估计
3. 计算边缘熵和联合熵
4. 得到互信息估计

### 1.3 MIA 攻击流程

```
1. 对每个时间点 t:
   ├── 获取观测值 O[t] = traces[:, t]
   ├── 离散化 O[t] → O_disc[t]
   │
   └── 对每个密钥猜测 k (0-255):
       ├── 计算泄漏假设 H[k] = HW[SBOX[pt ^ k]]
       ├── 计算互信息 MI = I(O_disc[t], H[k])
       └── 记录最大 MI 对应的密钥

2. 返回每个时间点最大 MI 对应的密钥
```

### 1.4 与 CPA 的区别

| 特性 | CPA | MIA |
|------|-----|-----|
| 度量方式 | 皮尔逊相关性 | 互信息（Shannon 熵） |
| 分布假设 | 假设线性关系 | 无分布假设 |
| 计算复杂度 | O(n×m×256) | O(n×m×256) + 熵估计 |
| 抗非线性对策 | 较弱 | 较强 |
| 对离散泄漏 | 不适用 | 适用 |

## 2. 泄漏模型

### 2.1 hamming_weight（默认）

**名称：** HW: AES SBox Output

**类型：** HW（汉明重量）

**计算公式：**

$$HW[SBox[P_i \oplus K_i]]$$

**物理意义：** AES 第一轮 S-Box 查找操作的输出包含了密钥信息。

### 2.2 sbox_output

**名称：** AES SBox Output (Direct)

**类型：** 直接输出

**计算公式：**

$$SBox[P_i \oplus K_i]$$

不使用汉明重量，直接使用 S-Box 输出值。

## 3. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── MIAAnalyzer (继承自 Analyzer)
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `MIAAnalyzer` | mia.py | 主分析器类 |
| `MIAResult` | mia.py | 分析结果数据类 |

### 继承结构图

```
Analyzer (squirrel.base)
    │
    └── MIAAnalyzer
            ├── name = "mia"
            ├── description = "MIA - Mutual Information Analysis"
            │
            ├── __init__(config: dict | None)
            │       ├── leakage_model: str = "hamming_weight"
            │       ├── num_subkeys: int = 16
            │       ├── range_start: int = 0
            │       └── range_end: int | None = None
            │
            └── analyze(traces, labels=None, plaintext, key=None, **kwargs) -> MIAResult
                    └── 返回包含最佳密钥猜测和 MI 值的 MIAResult
```

## 4. API 接口说明

### 构造函数

```python
MIAAnalyzer(config: dict[str, Any] | None = None)
```

**配置参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `leakage_model` | "hamming_weight" | 泄漏模型名称 |
| `num_subkeys` | 16 | 要分析的子密钥字节数（1-16） |
| `range_start` | 0 | 分析的起始时间点 |
| `range_end` | None | 分析的结束时间点（None 表示全部） |

### 主要方法

#### `analyze(traces, plaintext, key=None, **kwargs) -> MIAResult`

运行 MIA 分析。

**参数：**
- `traces`: np.ndarray，形状为 (num_traces, num_samples) 的功耗轨迹
- `plaintext`: np.ndarray，明文数据，形状为 (num_traces, 16)
- `key`: np.ndarray，可选，已知密钥用于验证
- `labels`: np.ndarray，可选，标签数据（MIA 不使用）

**返回：**
`MIAResult` 对象。

```python
result = analyzer.analyze(traces, plaintext=plaintext, key=known_key)
print(f"猜测密钥: {[hex(b) for b in result.key_guess]}")
print(f"最大 MI: {max(result.mutual_informations[0]):.4f}")
```

### MIAResult 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `method` | str | "mia" |
| `num_subkeys` | int | 分析的子密钥数量 |
| `num_traces` | int | 使用的轨迹数量 |
| `total_samples` | int | 每条轨迹的样本数 |
| `best_guesses` | list[dict] | 每个字节的最佳猜测详情 |
| `key_guess` | list[int] | 猜测的完整密钥（16字节） |
| `mutual_informations` | list[np.ndarray] | 每个字节的 MI vs 时间曲线 |
| `mi_matrix` | list[np.ndarray] | 每个字节的 (time × 256) MI 矩阵 |
| `leakage_model` | str | 使用的泄漏模型 |
| `metadata` | dict | 附加元数据 |

### best_guesses 条目结构

```python
{
    "byte": 0,           # 子密钥字节索引 (0-15)
    "guess": 0x88,       # 最佳密钥猜测值 (0-255)
    "known_key": 0x88,   # 已知密钥（如果提供）
    "correct": True,      # 猜测是否正确
}
```

### 使用示例

```python
from squirrel.analysis import MIAAnalyzer
import numpy as np

analyzer = MIAAnalyzer(config={
    "leakage_model": "hamming_weight",
    "num_subkeys": 16,
    "range_start": 0,
    "range_end": 500,
})

traces = np.random.randn(500, 500)
plaintext = np.random.randint(0, 256, size=(500, 16), dtype=np.uint8)

result = analyzer.analyze(traces, plaintext=plaintext)

print(f"猜测密钥: {[hex(b) for b in result.key_guess]}")
print(f"正确字节数: {sum(g['correct'] for g in result.best_guesses)}")
```

## 5. 性能优化

### 5.1 计算复杂度

MIA 的计算复杂度为：

$$O(n_{subkeys} \times n_{samples} \times 256)$$

其中：
- $n_{subkeys}$ = 子密钥字节数（默认 16）
- $n_{samples}$ = 分析的时间点数量
- 256 = 密钥猜测空间

### 5.2 优化策略

| 策略 | 效果 | 实现 |
|------|------|------|
| **多进程并行** | ~8x 加速（8核） | multiprocessing.Pool |
| **预计算泄漏表** | 减少重复计算 | all_leakages 矩阵 |
| **时间窗口限制** | 减少分析范围 | range_start/end |

### 5.3 进一步优化选项

1. **Numba JIT**：使用 `@numba.jit` 加速熵计算
2. **GPU 加速**：使用 CuPy 在 GPU 上计算
3. **近似算法**：使用快速近似熵估计

## 6. 结果解读指南

### 6.1 MI 值解读

| MI 值 | 解读 |
|-------|------|
| > 1.0 | 强泄漏，密钥易恢复 |
| 0.5 - 1.0 | 中等泄漏 |
| 0.1 - 0.5 | 弱泄漏，需要更多轨迹 |
| < 0.1 | 无明显泄漏 |

### 6.2 成功标准

- 正确恢复至少 12/16 字节（阈值可调）
- 最大 MI 值在泄漏点位置显著高于其他位置

## 7. 合成测试数据泄漏模型

### 7.1 多字节泄漏模型

MIA 测试数据采用**多字节独立泄漏模型**：

```
每个字节在不同时间窗口泄漏：
Byte 0 → samples [0, 31]
Byte 1 → samples [31, 62]
...
Byte 15 → samples [469, 500]
```

### 7.2 生成公式

```python
segment_size = num_samples // 16
sigma = 3.0

for b in range(16):
    center = (b + 0.5) * segment_size
    pulse = exp(-((t - center)^2) / (2 * sigma^2))
    leakage_hw = HW[SBOX[pt[b] ^ key[b]]]
    leakage = pulse * (leakage_hw / 8.0) * 6.0
    traces[i] += leakage
```

### 7.3 时间窗口示意

```
样本:  |----0----|----1----|----2----|...|----15---|
      ↑         ↑         ↑                  ↑
    Byte 0    Byte 1    Byte 2            Byte 15
   泄漏中心  泄漏中心  泄漏中心            泄漏中心
```

## 8. 与 CPA 对比

| 特性 | CPA | MIA |
|------|-----|-----|
| 核心度量 | 相关性 | 互信息 |
| 统计假设 | 线性关系 | 无 |
| 分布假设 | 假设正态 | 无 |
| 计算效率 | 较快 | 较慢（熵计算） |
| 适用场景 | 汉明重量泄漏 | 任意离散泄漏 |
| 抗对策能力 | 较弱 | 较强 |

## 9. 参考

- Gierlichs, B., et al. (2008). Mutual Information Analysis. CHES 2008.
- Standaert, F.-X., & Malkin, T. (2009). On the Conservation of Mutual Information in Side-Channel Attacks.