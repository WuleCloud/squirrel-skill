# Resync_SAD - 绝对差值和轨迹对齐

## 测试结果

**对齐前后对比图：**


| 指标 | 数值 |
|------|------|
| **对齐前 MAE** | 10.20 samples |
| **对齐后 MAE** | 0.00 samples |
| **对齐精度 (±5)** | 100% ✓ |
| **相关系数改善** | +0.7911 |
| **适用波形** | 有参考模板的信号、逐点匹配 |

## 1. 算法原理

### 1.1 核心思想

Resync_SAD 使用 **绝对差值和（Sum of Absolute Difference, SAD）** 找到将测试轨迹与参考轨迹对齐的最佳平移量。它在测试轨迹上滑动参考窗口，找到 SAD 最小的位置。

**核心思想**：当两条轨迹完全对齐时，它们对应位置的绝对差值最小。因此，通过穷举搜索找到最小 SAD 对应的平移量，即为最优对齐位置。

### 1.2 数学公式

**给定：**
- 参考窗口：$W = (w_1, w_2, ..., w_L)$，长度 $L = end - start$（从第 0 条轨迹提取）
- 测试轨迹：$T = (t_1, t_2, ..., t_N)$，长度 $N$（第 1, 2, 3 ... 条轨迹）
- 搜索范围：$[-max\_shift, +max\_shift]$

**在平移 $s$ 处的 SAD：**

$$SAD(s) = \sum_{i=1}^{L} |t_{i+s} - w_i|$$

**最优平移：**

$$s_{opt} = \arg\min_{s \in [-max\_shift, max\_shift]} SAD(s)$$

**直观理解**：
- $s > 0$：测试轨迹偏右，需要左移 $|s|$ 个采样点
- $s < 0$：测试轨迹偏左，需要右移 $|s|$ 个采样点

### 1.3 关键特性

- SAD 在搜索窗口内的整数平移处计算
- SAD 越小 = 测试轨迹与参考窗口匹配越好
- 找到最优平移后通过零填充进行校正

## 2. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── SADAligner (继承自 Analyzer)
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `SADAligner` | sad.py | 主对齐器类 |
| `SADResult` | sad.py | 对齐结果数据类 |
| `SADVerificationResult` | sad.py | 验证指标数据类 |

### 继承结构图
```
Analyzer (squirrel.base)
    │
    └── SADAligner
            ├── name = "sad"
            ├── description = "使用绝对差值和对齐轨迹"
            │
            ├── __init__(config: dict | None)
            │       ├── ref_trace_idx: int = 0 (参考轨迹索引)
            │       ├── target_window: tuple[int, int] = (0, 0) (参考窗口范围)
            │       └── max_shift: int = 50 (最大搜索平移量)
            │
            ├── analyze(traces, labels=None, **kwargs) -> SADResult
            │       └── 返回对齐轨迹在 result.metadata["aligned_traces"]
            │
            ├── verify(original, aligned, ref_trace_idx) -> SADVerificationResult
            ├── verify_shifts(original, aligned, ground_truth_shifts) -> tuple[float, bool]
            ├── detect_leakage_points(result, threshold) -> np.ndarray
            ├── load_traces(path, format="zarr") -> TraceDataset
            ├── save_traces(traces, path, format="zarr") -> Path
            └── print_verification(result)
```

## 3. API接口说明

### 构造函数

```python
SADAligner(
    config: dict[str, Any] | None = None,
    ref_trace_idx: int = 0,
    target_window: tuple[int, int] = (0, 0),
    max_shift: int = 50
)
```

**配置参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ref_trace_idx` | 0 | 参考轨迹索引 |
| `target_window` | (0, 0) | (起始, 结束) 参考窗口范围；为(0,0)时使用前100个样本 |
| `max_shift` | 50 | 向两侧搜索的最大平移量 |

### 主要方法

#### `analyze(traces, labels=None, **kwargs) -> SADResult`
主入口，对齐轨迹并返回结果。

```python
result = aligner.analyze(traces)
aligned_traces = result.metadata["aligned_traces"]
shifts = result.metadata["shifts"]  # 每条轨迹的平移量
```

#### `verify(original, aligned, ref_trace_idx) -> SADVerificationResult`
验证对齐效果，计算：
- 标准差降低百分比
- 相关系数改善
- 方差降低百分比

#### `verify_shifts(original, aligned, ground_truth_shifts, ref_trace_idx) -> tuple[float, bool]`
返回 (MAE, passed)，MAE是估算偏移与真实偏移的平均绝对误差。

### 使用示例

```python
from squirrel.preprocessing import SADAligner
import numpy as np

# 加载轨迹
traces = np.random.randn(100, 2000)

# 创建对齐器
aligner = SADAligner(
    ref_trace_idx=0,
    target_window=(100, 200),  # 使用样本100-200作为参考
    max_shift=50
)

# 分析
result = aligner.analyze(traces)
aligned = result.metadata["aligned_traces"]

# 验证
verify_result = aligner.verify(traces, aligned)
print(f"标准差降低: {verify_result.std_reduction:.2f}%")
```

## 4. Makefile用法

### 快速开始
```bash
make resync_sad
```

### 可用目标

| 目标 | 说明 |
|------|------|
| `resync_sad` | 运行完整流程：生成 → 对齐 → 验证 |
| `resync_sad-generate` | 仅生成测试数据 |
| `resync_sad-align` | 执行SAD对齐 |
| `resync_sad-verify` | 验证对齐结果 |
| `resync_sad-clean` | 清理输出文件 |

### 配置变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RESYNC_SAD_NUM_TRACES` | 300 | 生成轨迹数量 |
| `RESYNC_SAD_NUM_SAMPLES` | 2000 | 每条轨迹样本数 |
| `RESYNC_SAD_MAX_SHIFT` | 20 | 测试数据最大偏移 |
| `RESYNC_SAD_NOISE_STD` | 0.1 | 噪声标准差 |

### 使用示例

```bash
# 默认运行
make resync_sad

# 自定义轨迹数
make resync_sad RESYNC_SAD_NUM_TRACES=500

# 仅生成并查看日志
make resync_sad-generate
cat sim/preprocessing/Resync_SAD/log/generate.log

# 仅验证
make resync_sad-verify

# 清理
make resync_sad-clean
```

### 输出文件

```
sim/preprocessing/Resync_SAD/
├── traces/
│   ├── sad_original.zarr        # 原始轨迹
│   └── sad_original_shifts.json  # 真实偏移量
├── result/
│   ├── sad_aligned.zarr         # 对齐后轨迹
│   └── sad_comparison.png        # 对比可视化
└── log/
    ├── generate.log              # 数据生成日志
    ├── align.log                  # 对齐日志
    └── verify.log                 # 验证结果
```

## 5. 算法流程

```
1. 计算参考窗口
   └─> 从ref_trace提取target_window范围的样本作为参考

2. 对每条轨迹：
   ├─> 在[-max_shift, +max_shift]范围内滑动参考窗口
   ├─> 计算每个位置的SAD: Σ|ref_window[i] - trace[pos+i]|
   ├─> 找到SAD最小的位置
   └─> 应用平移（用零填充）

3. 返回对齐后的轨迹

## 7. 方法选择速查

| 波形特征 | 推荐方法 |
|---------|---------|
| 清晰单峰 | Peak |
| 双尖峰/多峰 | DTW |
| 高噪声 | CrossCorr |
| 非线性变形 | DTW |
| 方波/过零点 | ZC |
| 有参考模板 | **SAD** |
```