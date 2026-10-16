# Correlation - 明密文相关性泄漏定位

## 1. 算法原理

### 1.1 核心概念

Correlation 分析用于计算轨迹样本点与输入数据汉明重量之间的皮尔逊相关性。它不枚举密钥假设，而是直接使用已知的明文、密文、密钥或扩展数据，将这些数据转换为汉明重量矩阵，再与功耗轨迹逐采样点做相关性计算。

该方法适合回答两个问题：

- 哪些采样点与已知数据相关，可能存在侧信道泄漏
- 哪个字节或数据分组在某个时间点的相关性最强

### 1.2 泄漏模型

输入数据按 `data_type` 选择：

| `data_type` | 输入参数 | 说明 |
|-------------|----------|------|
| `plaintext` | `plaintext` | 使用明文字节 |
| `ciphertext` | `ciphertext` | 使用密文字节 |
| `key` | `key` | 使用密钥字节 |
| `extended` | `extended` | 使用调用方提供的扩展数据 |

每个输入值转换为汉明重量：

$$HW(x) = \sum_i bit_i(x)$$

当 `data_width=1` 时，每个字节独立计算 8-bit HW；当 `data_width` 为 2/4/8 时，会将多个字节合并为 16/32/64-bit 分组后计算 HW。

### 1.3 相关性公式

对第 `b` 个数据分组和第 `s` 个采样点：

$$corr(b, s) = \frac{E[(HW_b - E[HW_b])(T_s - E[T_s])]}{\sigma_{HW_b}\sigma_{T_s}}$$

其中：

- `HW_b` 是所有轨迹在第 `b` 个数据分组上的汉明重量向量
- `T_s` 是所有轨迹在采样点 `s` 上的功耗值向量
- 输出矩阵形状为 `(n_data_groups, n_samples)`

泄漏点判定：

$$leakage\_point_s = \max_b |corr(b, s)| > threshold$$

## 2. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── CorrelationAnalyzer
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `CorrelationAnalyzer` | correlation/correlation.py | 主相关性分析器类 |
| `CorrelationResult` | correlation/correlation.py | 相关性分析结果数据类 |
| `CorrelationVerificationResult` | correlation/correlation.py | 验证指标数据类 |

### 继承结构图

```
Analyzer (squirrel.base)
    │
    └── CorrelationAnalyzer
            ├── name = "correlation"
            ├── description = "Correlation Analysis for Leakage Detection"
            │
            ├── __init__(config: dict | None)
            │       ├── data_type: str = "plaintext"
            │       ├── data_width: int = 1
            │       ├── sample_range: tuple[int, int | None] = (0, None)
            │       └── correlation_threshold: float = 0.5
            │
            ├── hamming_weight(data, bit_width=8) -> np.ndarray
            ├── _compute_correlation_matrix(traces, hw_matrix) -> np.ndarray
            ├── analyze(traces, plaintext/ciphertext/key/extended, **kwargs) -> CorrelationResult
            └── detect_leakage_points(result, threshold=None) -> np.ndarray
```

## 3. API 接口说明

### 构造函数

```python
CorrelationAnalyzer(config: dict[str, Any] | None = None)
```

**配置参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `data_type` | "plaintext" | 输入数据类型："plaintext"、"ciphertext"、"key"、"extended" |
| `data_width` | 1 | 数据宽度，单位为字节；对应 8/16/32/64-bit HW |
| `sample_range` | (0, None) | 分析采样区间，结束为 `None` 时使用轨迹末尾 |
| `correlation_threshold` | 0.5 | 泄漏检测阈值，比较 `abs(correlation)` |

### 主要方法

#### `analyze(...) -> CorrelationResult`

运行相关性分析。

```python
from squirrel.analysis.correlation import CorrelationAnalyzer

analyzer = CorrelationAnalyzer(config={
    "data_type": "plaintext",
    "data_width": 1,
    "sample_range": (0, None),
    "correlation_threshold": 0.3
})

result = analyzer.analyze(
    traces=traces,
    plaintext=plaintext,
    input_path="/path/to/correlation_traces.zarr"
)

print(f"Max correlation: {result.max_correlation_value:.4f}")
print(f"Byte: {result.max_correlation_byte}")
print(f"Sample: {result.max_correlation_sample}")
```

#### `hamming_weight(data, bit_width=8) -> np.ndarray`

将 `uint8` 二维数组转换为汉明重量矩阵。支持：

| `bit_width` | 行为 |
|-------------|------|
| 1/2/4 | 将每个字节拆成多个低位宽分组后计算 HW |
| 8 | 对每个字节直接查表计算 HW |
| 16/32/64 | 将多个字节合并为宽分组后计算 HW |

#### `detect_leakage_points(result, threshold=None) -> np.ndarray`

返回所有超过阈值的采样点索引。判定方式为任意数据分组在该采样点满足 `abs(correlation) > threshold`。

#### `verify_correlation(input_path, correlation_result, threshold=0.5)`

验证最大绝对相关性是否超过阈值，返回 `CorrelationVerificationResult`。

### CorrelationResult 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `method` | str | "correlation" |
| `data_type` | str | 使用的数据类型 |
| `data_width` | int | 数据宽度，单位为字节 |
| `total_samples` | int | 原始轨迹采样点总数 |
| `trace_count` | int | 实际参与分析的轨迹数量 |
| `correlation_min` | float | 相关性矩阵最小值 |
| `correlation_max` | float | 相关性矩阵最大值 |
| `correlation_mean_abs` | float | 相关性绝对值均值 |
| `max_correlation_byte` | int | 最大绝对相关性对应的数据分组索引 |
| `max_correlation_sample` | int | 最大绝对相关性对应的采样点索引 |
| `max_correlation_value` | float | 最大绝对相关性位置的带符号相关系数 |
| `leakage_points` | list[int] | 超过阈值的采样点索引 |
| `correlation_matrix` | np.ndarray | 相关性矩阵，shape=(n_data_groups, n_samples) |

## 4. Makefile 用法

### 快速开始

```bash
make correlation
```

### 可用目标

| 目标 | 说明 |
|------|------|
| `correlation` | 兼容别名，等价于 `test-correlation` |
| `test-correlation` | 运行完整流程：生成 → 分析 → 验证 |

### 配置变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CORRELATION_NUM_TRACES` | 500 | 生成轨迹数量 |
| `CORRELATION_NUM_SAMPLES` | 2000 | 每条轨迹样本数 |
| `CORRELATION_NOISE_STD` | 0.3 | 噪声标准差 |
| `CORRELATION_LEAKAGE_START` | 400 | 泄漏区域起点 |
| `CORRELATION_LEAKAGE_END` | 600 | 泄漏区域终点 |
| `CORRELATION_LEAKAGE_AMP` | 12.0 | 泄漏幅度 |
| `CORRELATION_THRESHOLD` | 0.2 | 验证阈值 |
| `CORRELATION_BASE_SEED` | 42 | 随机种子 |

### 使用示例

```bash
# 默认运行
make correlation

# 提高噪声并调整阈值
make correlation CORRELATION_NOISE_STD=0.6 CORRELATION_THRESHOLD=0.15

# 自定义泄漏区间
make correlation CORRELATION_LEAKAGE_START=700 CORRELATION_LEAKAGE_END=900
```

### 输出文件

```
sim/analysis/Correlation/
├── traces/
│   ├── correlation_traces.zarr
│   └── correlation_metadata.json
├── result/
│   ├── correlation_report.json
│   ├── correlation_plot.png
│   ├── correlation_vs_sample.png
│   └── correlation_by_byte.png
└── log/
    ├── generate.log
    ├── analyze.log
    └── verify.log
```

## 5. 算法流程

```
1. 选择 data_type 对应的数据矩阵
   └─> plaintext / ciphertext / key / extended

2. 对轨迹和数据数量取交集
   └─> num_traces = min(traces.shape[0], data.shape[0])

3. 应用 sample_range
   └─> traces_slice = traces[:, start:end]

4. 计算汉明重量矩阵
   └─> hw_matrix = hamming_weight(data, bit_width=data_width * 8)

5. 向量化计算相关性矩阵
   └─> corr = centered(HW).T @ centered(traces) / (std(HW) * std(traces))

6. 提取最大绝对相关性和泄漏点
   └─> max(abs(corr)), abs(corr) > correlation_threshold
```

## 6. 应用场景

| 场景 | 说明 |
|------|------|
| 泄漏定位 | 找出与明文/密文/密钥相关的时间区域 |
| 数据依赖检查 | 检查轨迹是否随某类输入数据变化 |
| 攻击前评估 | 在 CPA 前快速观察可利用泄漏窗口 |
| 特征筛选 | 将强相关采样点作为后续分析或机器学习特征 |

## 7. 与 CPA 的区别

| 方法 | 是否枚举密钥 | 输入 | 输出重点 |
|------|--------------|------|----------|
| Correlation | 否 | 已知数据的 HW | 泄漏位置和相关性强度 |
| CPA | 是 | 明文 + 密钥假设 | 密钥猜测和 PGE |

Correlation 更像泄漏检测与定位工具；CPA 是密钥恢复攻击工具。

## 8. 局限性

- 依赖正确的数据对齐；若轨迹存在明显抖动，应先进行 Resync。
- 只使用 HW 模型，若真实泄漏更接近 HD 或非线性模型，相关性会降低。
- `max_correlation_sample` 是切片后的相对采样索引；使用非零 `sample_range` 时需要加上起始位置解释到原始轨迹。
- 当输入数据列方差为 0 时，该列相关性会退化为 0。
