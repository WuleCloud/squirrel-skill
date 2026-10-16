# DPA - 差分功耗分析攻击

## 测试结果


| 指标 | 测试结果 |
|------|----------|
| **Key correct** | 16/16 bytes |
| **Throughput** | 5000 traces × 3000 samples |
| **Leakage window** | 500:700 |
| **Algorithm** | Threshold DPA (HW model) |
| **通过验证** | ✅ PASS |

## 1. 算法原理

### 1.1 核心概念

DPA（Differential Power Analysis，差分功耗分析）是一种通过统计分析功耗轨迹差异来恢复密钥的方法。与 CPA 不同，DPA 将轨迹按功耗假设值分组，比对两组均值差异。

**核心假设**：设备功耗与处理数据的汉明重量（HW）相关。

### 1.2 AES S-Box 泄漏模型

AES 第一轮加密中，S-Box 输出是常见泄漏点：

```
明文 P → [AddRoundKey] → S-Box[P ⊕ K] → 输出
```

攻击者已知 $P$，尝试所有 $256$ 个可能的 $K$ 值，计算汉明重量 $HW[S\text{-}Box[P ⊕ K]]$。

### 1.3 数学公式

**汉明重量计算：**

```python
HW = [bin(x).count("1") for x in range(256)]
# HW[0]=0, HW[1]=1, HW[255]=8
```

**阈值分组：**

给定汉明重量矩阵 $HW \in \mathbb{R}^{N \times 16}$（$N$ = 轨迹数，16 = 密钥字节数）和阈值 $\tau$：

$$M_{high} = \{ i \mid HW[i,b] > \tau \} \quad \text{(高组)}$$
$$M_{low} = \{ i \mid HW[i,b] \leq \tau \} \quad \text{(低组)}$$

**功耗差异：**

$$DPA\_diff[b,t] = \bar{T}_{high}[t] - \bar{T}_{low}[t]$$

其中 $\bar{T}_{high}[t]$ 是高组轨迹在时间点 $t$ 处的平均功耗。

**密钥排序：**

对于每个密钥字节 $b$，对 256 个候选密钥的差异曲线计算最大绝对值：

$$best\_key[b] = \arg\max_{k \in [0,255]} \max_t |DPA\_diff[k,b,t]|$$

## 2. 支持的参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `threshold` | 4.0 | HW 阈值，用于高低组划分 |
| `byte_pos` | [0..15] | 攻击的字节位置 |
| `direction` | "enc" | 加密方向（enc/dec） |
| `sample_start` | 0 | 分析样本起始位置 |
| `sample_end` | 3000 | 分析样本结束位置 |
| `multiple_thresholds` | None | 多阈值模式，e.g. [2.0, 3.0, 4.0, 5.0, 6.0] |

## 3. 数据格式

### Zarr 数据集结构

```
zarr_file/
└── /0/0/
    ├── traces     (num_traces, num_samples) float32  - 功耗轨迹
    ├── plaintext  (num_traces, 16) uint8            - 明文
    ├── key         (16,) uint8                        - 密钥
    └── labels     (num_traces,) int8                 - 标签
```

## 4. 使用方法

### 命令行

```bash
# 数据生成
uv run --no-editable python -m tests.data_generators.cli dpa \
    --output sim/DPA/traces/dpa_traces.zarr \
    --num-traces 5000 \
    --num-samples 3000 \
    --noise-std 0.1 \
    --seed 42 \
    --known-key 00112233445566778899aabbccddeeff \
    --leakage-start 500 \
    --leakage-end 700 \
    --leakage-amplitude 1.0

# 分析
uv run --no-editable python tests/verify/dpa/analyzer.py \
    sim/DPA/traces/dpa_traces.zarr \
    sim/DPA/result/dpa_results.json \
    --output-dir sim/DPA/result \
    --threshold 4.0 \
    --direction enc

# 验证
uv run --no-editable python tests/verify/dpa/verifier.py \
    sim/DPA/traces/dpa_traces.zarr \
    --results-json sim/DPA/result/dpa_results.json \
    --all-bytes
```

### Python API

```python
from squirrel.analysis.dpa import DPAAnalyzer

analyzer = DPAAnalyzer(config={
    "threshold": 4.0,
    "direction": "enc",
    "byte_pos": list(range(16)),
})

result = analyzer.analyze(
    "sim/DPA/traces/dpa_traces.zarr",
    input_path="sim/DPA/traces/dpa_traces.zarr",
    output_dir="sim/DPA/result",
)

print(f"Recovered key: {result.recovered_key}")
print(f"Expected key:  {result.known_key}")
```

## 5. 结果解读

### DPA 曲线图

生成的 `dpa_all_bytes.png` 包含 4×4 网格，每张子图显示：
- **X 轴**：采样点（时间）
- **Y 轴**：高低组均值差异（DPA 差值）
- **峰值位置**：对应 POI（泄漏点）

### 正确密钥特征

当猜测密钥正确时，其 DPA 曲线在泄漏窗口（500:700）内应显示明显峰值。

## 6. 与 CPA 的对比

| 特征 | DPA | CPA |
|------|-----|-----|
| **分组方式** | 阈值分割（high/low 两组） | 线性相关（皮尔逊相关系数） |
| **统计量** | 仅均值差 | 相关系数 |
| **信息利用率** | 低（仅用高低两组） | 高（利用 HW 线性关系） |
| **适用场景** | 噪声较低环境 | 高噪声环境 |
| **计算复杂度** | O(N × 256 × 16) | O(N × 256 × 16) |

## 7. 测试数据生成

数据生成器在 `tests/data_generators/generate_dpa_dataset.py`，核心参数：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--num-traces` | 5000 | 轨迹数量 |
| `--num-samples` | 3000 | 每条轨迹采样点数 |
| `--noise-std` | 0.1 | 噪声标准差 |
| `--known-key` | 001122... | 16 字节密钥（hex） |
| `--leakage-start` | 500 | 泄漏窗口起始 |
| `--leakage-end` | 700 | 泄漏窗口结束 |
| `--leakage-amplitude` | 1.0 | 泄漏信号幅度 |

**注意**：当前实现对所有 16 字节注入相同幅度的 HW 泄漏信号。