# Normalize - 轨迹归一化预处理

## 测试结果

**归一化前后对比图：**


| 指标 | 归一化前 | 归一化后 |
|------|----------|----------|
| **Mean** | 100.09 | 0.00 |
| **Std** | 2.11 | 1.00 |
| **通过验证** | - | ✓ PASS |

## 1. 算法原理

### 1.1 核心思想

Normalize 通过数学变换将轨迹转换为具有标准统计特性的形式，消除均值偏移和（可选地）标准化方差。这是侧信道分析中常用的预处理步骤。

**两种模式：**
- **mean**：仅减去均值，使轨迹变为零均值
- **mean_stddev**：减去均值并除以标准差，使轨迹变为零均值、单位方差

### 1.2 数学公式

**Mean 模式（零均值化）：**

$$T'_{norm}(i) = T(i) - \mu_T$$

其中 $\mu_T = \frac{1}{N}\sum_{i=1}^{N}T(i)$ 是轨迹的均值。

**Mean-Stddev 模式（标准化）：**

$$T'_{norm}(i) = \frac{T(i) - \mu_T}{\sigma_T}$$

其中 $\sigma_T = \sqrt{\frac{1}{N}\sum_{i=1}^{N}(T(i) - \mu_T)^2}$ 是轨迹的标准差。

### 1.3 关键特性

- 逐条轨迹独立处理
- 不改变波形形状，只改变位置和尺度
- Mean-Stddev 模式输出的标准差严格为 1

## 2. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── Normalize (继承自 Analyzer)
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `Normalize` | normalize.py | 主归一化器类 |
| `NormalizeResult` | normalize.py | 归一化结果数据类 |
| `NormalizeVerificationResult` | normalize.py | 验证指标数据类 |
| `NormMean` | normalize.py | Mean 模式实现 |
| `NormMeanStd` | normalize.py | Mean-Stddev 模式实现 |

### 继承结构图

```
Analyzer (squirrel.base)
    │
    └── Normalize
            ├── name = "normalize"
            ├── description = "Normalize traces by mean and/or standard deviation"
            │
            ├── __init__(config: dict | None, mode: str = "mean")
            │       └── mode: "mean" | "mean_stddev"
            │
            ├── analyze(traces, labels=None, **kwargs) -> NormalizeResult
            │       └── 返回归一化轨迹在 result.metadata["normalized_traces"]
            │
            ├── verify(original, normalized) -> NormalizeVerificationResult
            └── detect_leakage_points(result, threshold) -> np.ndarray
```

## 3. API接口说明

### 构造函数

```python
Normalize(
    config: dict[str, Any] | None = None,
    mode: str = "mean"
)
```

**配置参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `mode` | "mean" | 归一化模式：<br>"mean" - 零均值化<br>"mean_stddev" - 标准化 |

### 主要方法

#### `analyze(traces, labels=None, **kwargs) -> NormalizeResult`

主入口，归一化轨迹并返回结果。

```python
result = normalizer.analyze(traces)
normalized_traces = result.metadata["normalized_traces"]
```

#### `verify(original, normalized) -> NormalizeVerificationResult`

验证归一化效果，计算：
- 输入/输出均值
- 输入/输出标准差
- 验证是否通过

### 使用示例

```python
from squirrel.preprocessing import Normalize
import numpy as np

# 加载轨迹
traces = np.random.randn(100, 2000) + 100  # 非零均值轨迹

# 创建归一化器 (Mean 模式)
normalizer = Normalize(mode="mean")
result = normalizer.analyze(traces)
normalized = result.metadata["normalized_traces"]

print(f"Original mean: {np.mean(traces):.4f}")
print(f"Normalized mean: {np.mean(normalized):.4f}")  # 接近 0

# 创建归一化器 (Mean-Stddev 模式)
normalizer_std = Normalize(mode="mean_stddev")
result_std = normalizer_std.analyze(traces)
normalized_std = result_std.metadata["normalized_traces"]

print(f"Normalized mean: {np.mean(normalized_std):.4f}")  # 接近 0
print(f"Normalized std: {np.std(normalized_std):.4f}")    # 接近 1
```

## 4. Makefile用法

### 快速开始

```bash
make normalize
```

### 可用目标

| 目标 | 说明 |
|------|------|
| `normalize` | 运行完整流程：生成 → 归一化 → 验证 |
| `normalize-generate` | 仅生成测试数据 |
| `normalize-normalize` | 执行归一化 |
| `normalize-verify` | 验证归一化结果 |
| `normalize-clean` | 清理输出文件 |

### 配置变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `NORMALIZE_NUM_TRACES` | 300 | 生成轨迹数量 |
| `NORMALIZE_NUM_SAMPLES` | 2000 | 每条轨迹样本数 |
| `NORMALIZE_NOISE_STD` | 0.5 | 噪声标准差 |
| `NORMALIZE_BASE_SEED` | 888 | 随机种子 |

### 使用示例

```bash
# 默认运行
make normalize

# 自定义轨迹数
make normalize NORMALIZE_NUM_TRACES=500

# 仅生成并查看日志
make normalize-generate
cat sim/preprocessing/Normalize/log/generate.log

# 仅验证
make normalize-verify

# 清理
make normalize-clean
```

### 输出文件

```
sim/preprocessing/Normalize/
├── traces/
│   ├── normalize_original.zarr     # 原始轨迹
│   └── normalize_original_metadata.json  # 元数据
├── result/
│   ├── normalize_normalized.zarr   # 归一化后轨迹
│   └── normalize_comparison.png   # 对比可视化
└── log/
    ├── generate.log                # 数据生成日志
    ├── normalize.log               # 归一化日志
    └── verify.log                  # 验证结果
```

## 5. 算法流程

```
1. 初始化归一化器
   └─> 根据 mode 选择 NormMean 或 NormMeanStd

2. 对每条轨迹独立处理：
   ├─> Mean 模式: T' = T - mean(T)
   └─> Mean-Stddev 模式: T' = (T - mean(T)) / std(T)

3. 返回归一化后的轨迹
```

## 6. 模式对比

| 模式 | 公式 | Mean | Std | 适用场景 |
|------|------|------|-----|----------|
| `mean` | $T - \mu_T$ | 0 | 不变 | 消除直流偏移 |
| `mean_stddev` | $(T - \mu_T) / \sigma_T$ | 0 | 1 | 标准化功耗分析 |

## 7. 常见问题

**Q: 为什么归一化后迹线看起来"差不多"？**

A: `mean` 模式只平移数据，不改变形状。如果想要更明显的变化，使用 `mean_stddev` 模式。

**Q: 如何选择归一化模式？**

A:
- 使用固定硬件/采集设置 → `mean` 足够
- 比较不同条件下的迹线 → `mean_stddev` 更好
- 深度学习训练 → 推荐 `mean_stddev`（收敛更快）
