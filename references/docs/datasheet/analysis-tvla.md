# TVLA - 测试向量泄漏评估

## 1. 算法原理

### 核心概念
TVLA（Test Vector Leakage Assessment，测试向量泄漏评估）是一种统计检验方法，用于检测密码学实现中的侧信道泄漏。它使用Welch's t检验比较两组轨迹：固定（确定性）vs 随机（概率性）明文。

### 数学公式

给定：
- 固定明文轨迹：$F = (f_1, f_2, ..., f_n) \in \mathbb{R}^{n \times N}$
- 随机明文轨迹：$R = (r_1, r_2, ..., r_m) \in \mathbb{R}^{m \times N}$

其中 $n$ = 固定轨迹数量，$m$ = 随机轨迹数量，$N$ = 每条轨迹的样本数。

**逐样本t检验：**
$$t_i = \frac{\bar{f}_i - \bar{r}_i}{\sqrt{\frac{var(f_i)}{n} + \frac{var(r_i)}{m}}}$$

其中：
- $\bar{f}_i = \frac{1}{n}\sum_{j=1}^{n} f_{j,i}$ （固定轨迹在样本 $i$ 处的均值）
- $\bar{r}_i = \frac{1}{m}\sum_{j=1}^{m} r_{j,i}$ （随机轨迹在样本 $i$ 处的均值）
- $var(f_i)$ = 固定轨迹在样本 $i$ 处的方差

**泄漏检测：**
$$leakage\_point\_i = |t_i| > threshold$$

常用阈值：$|t| > 4.5$ （对应双尾检验 p < 0.0001）

### 关键特性
- **固定轨迹**：相同明文/密钥，泄漏是确定性的
- **随机轨迹**：随机明文/密钥，平均泄漏≈0
- **差异**：若设备泄漏与数据相关的信息，t检验将显示显著性

## 2. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── TVLAAnalyzer (继承自 Analyzer)
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `TVLAAnalyzer` | tvla.py | 主分析器类 |
| `TVLAResult` | tvla.py | 分析结果数据类 |

### 继承结构图
```
Analyzer (squirrel.base)
    │
    └── TVLAAnalyzer
            ├── name = "tvla"
            ├── description = "TVLA测试向量泄漏评估"
            │
            ├── __init__(config: dict | None)
            │       └── threshold: float = 4.5 (泄漏检测阈值)
            │
            ├── analyze(traces, labels=None, **kwargs) -> TVLAResult
            │       └── 需要zarr数据集路径作为输入
            │
            ├── _analyze_zarr(zarr_path, output_dir) -> TVLAResult
            ├── _compute_ttest(fixed, random, input_path, output_dir) -> TVLAResult
            ├── _save_plot(t_values, num_samples, output_dir)
            ├── detect_leakage_points(result, threshold) -> np.ndarray
            ├── load_traces(path, format="zarr") -> TraceDataset
            └── save_traces(dataset, path, format="zarr") -> Path
```

## 3. API接口说明

### 构造函数

```python
TVLAAnalyzer(config: dict[str, Any] | None = None)
```

**配置参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `threshold` | 4.5 | t值泄漏检测阈值 |

### 主要方法

#### `analyze(traces, labels=None, **kwargs) -> TVLAResult`
运行TVLA分析。需要zarr数据集路径。

```python
result = analyzer.analyze(zarr_path="/path/to/dataset.zarr")
print(f"泄漏点数量: {result.total_leakage_points}")
print(f"首个泄漏: 样本 {result.first_leakage_point}")
```

#### `_compute_ttest(fixed, random, input_path, output_dir) -> TVLAResult`
执行t检验计算的内部方法。

#### `detect_leakage_points(result, threshold) -> np.ndarray`
返回检测到泄漏的样本索引数组。

### TVLAResult字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `method` | str | "tvla" |
| `threshold` | float | 使用的检测阈值 |
| `total_samples` | int | 样本点总数 |
| `trace_count_fixed` | int | 固定轨迹数量 |
| `trace_count_random` | int | 随机轨迹数量 |
| `ttest_min` | float | 最小t值 |
| `ttest_max` | float | 最大t值 |
| `ttest_mean_abs` | float | |t值|的平均值 |
| `total_leakage_points` | int | 超过阈值的泄漏点数量 |
| `leakage_points` | list[int] | 泄漏的样本索引 |
| `leakage_regions` | list[dict] | 泄漏区域 |
| `first_leakage_point` | int | 首个检测到的泄漏样本 |
| `first_leakage_tvalue` | float | 首个泄漏处的t值 |

### 使用示例

```python
from squirrel.analysis import TVLAAnalyzer
import zarr

# 创建分析器
analyzer = TVLAAnalyzer(config={"threshold": 4.5})

# 在zarr数据集上运行分析
result = analyzer.analyze("/path/to/tvla_data.zarr")

# 检查结果
print(f"T检验范围: [{result.ttest_min:.2f}, {result.ttest_max:.2f}]")
print(f"泄漏点数量: {result.total_leakage_points}")

if result.first_leakage_point:
    print(f"首个泄漏在样本 {result.first_leakage_point} (t={result.first_leakage_tvalue:.2f})")

# 获取所有泄漏点索引
leakage_idx = analyzer.detect_leakage_points(result)
```

## 4. Makefile用法

### 快速开始
```bash
make tvla
```

### 可用目标

| 目标 | 说明 |
|------|------|
| `tvla` | 运行完整TVLA流程：生成 → 分析 → 验证 |
| `tvla-generate` | 仅生成测试数据 |
| `tvla-analyze` | 运行TVLA分析 |
| `tvla-verify` | 验证TVLA结果 |
| `tvla-clean` | 清理输出文件 |

### 配置变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TVLA_NUM_TRACES` | 2000 | 每组轨迹数量 |
| `TVLA_NUM_SAMPLES` | 3000 | 每条轨迹样本数 |
| `TVLA_PROFILE` | medium | 泄漏配置（low/medium/high） |
| `TVLA_NUM_REGIONS` | 2 | 附加泄漏区域数量 |
| `TVLA_BASE_SEED` | 300 | 随机种子 |

### 使用示例

```bash
# 默认运行
make tvla

# 更多轨迹以获得更好的统计功效
make tvla TVLA_NUM_TRACES=5000

# 更多泄漏区域
make tvla TVLA_NUM_REGIONS=4

# 查看结果
cat sim/preprocessing/TVLA/log/verify.log

# 清理
make tvla-clean
```

### 输出文件

```
sim/preprocessing/TVLA/
├── traces/
│   └── tvla_regions.zarr       # TVLA数据集
├── result/
│   └── (分析输出)
└── log/
    ├── generate.log             # 数据生成日志
    ├── analyze.log              # 分析日志
    └── verify.log                # 验证结果
```

## 5. 结果解读指南

### T值解读

| |t| 值 | 解读 |
|---|------------------------|
| < 2 | 未检测到泄漏 |
| 2 - 4 | 边缘，可能需要更多轨迹 |
| 4 - 6 | 可能存在泄漏 |
| > 6 | 强泄漏 |

### TVLA测试类型
- **单变量**：对单个样本点进行t检验（已实现）
- **多变量**：对PCA变换或组合特征进行t检验（待实现）

### 局限性
- 需要平衡数据集（固定/随机轨迹数量相等）
- 对噪声敏感 - 轨迹越多检测越好
- 只能检测泄漏，不能定位泄漏源