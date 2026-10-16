# Resync_Peak - 峰值检测轨迹对齐

## 测试结果

**对齐前后对比图：**


| 指标 | 数值 |
|------|------|
| **对齐前 MAE** | 10.20 samples |
| **对齐后 MAE** | 0.00 samples |
| **对齐精度 (±5)** | 100% ✓ |
| **相关系数改善** | +0.7698 |
| **适用波形** | 尖锐单峰、无多峰干扰 |

## 1. 算法原理

### 1.1 核心思想

Resync_Peak 通过检测每条轨迹中的**峰值**（最大值或最小值），然后将峰值与参考轨迹对齐来对齐轨迹。基于 ChipWhisperer 的 ResyncPeakDetect 算法。

**核心假设**：同一操作在所有轨迹中都会产生相同形状的峰值，只是位置可能偏移。

### 1.2 几何图解

```
                    峰值位置          峰值位置
                  ◄──────►          ◄──────►
   参考轨迹 R:    ___/\___    测试轨迹 T:  __/\____
                      ↑                    ↑
                   peak_ref            peak_test

   shift > 0: 测试轨迹峰值在参考右侧，需要左移
   shift < 0: 测试轨迹峰值在参考左侧，需要右移
```

### 1.3 数学公式

**给定：**
- 参考轨迹：$R = (r_1, r_2, ..., r_N)$，长度 $N$（即第 0 条轨迹）
- 测试轨迹：$T = (t_1, t_2, ..., t_N)$，长度 $N$（第 1, 2, 3 ... 条轨迹）
- 峰值搜索范围：$[start, end]$（限定在可能感兴趣的区域搜索）

**步骤1：峰值检测**

找参考轨迹和测试轨迹在搜索范围内的峰值位置：

$$peak_{ref} = \arg\max_{i \in [start, end]} R_i$$

$$peak_{test} = \arg\max_{i \in [start, end]} T_i$$

这里 $\arg\max$ 返回的是**使 $R_i$ 最大化的索引 $i$**，即峰值所在位置。

**步骤2：计算平移量**

$$shift = peak_{ref} - peak_{test}$$

- 若 $shift > 0$：测试轨迹峰值在参考**右侧**，需要**左移** $shift$ 个采样点
- 若 $shift < 0$：测试轨迹峰值在参考**左侧**，需要**右移** $|shift|$ 个采样点

**步骤3：零填充平移对齐**

将测试轨迹按照 $shift$ 进行平移，溢出的部分丢弃，不足的部分补零：

$$aligned[i] = \begin{cases}
0 & \text{若 } i - shift < 0 \quad \text{（左侧越界，补零）}\\[4pt]
T_{i-shift} & \text{若 } 0 \leq i - shift < N \quad \text{（有效范围）}\\[4pt]
0 & \text{若 } i - shift \geq N \quad \text{（右侧越界，补零）}
\end{cases}$$

> **直观理解**：$shift$ 是参考峰值相对于测试峰值的位置差。
> - $shift = +2$：测试峰值偏右，需要左移 → aligned[i] = T[i-2]
> - $shift = -2$：测试峰值偏左，需要右移 → aligned[i] = T[i+2]

### 1.4 幅度验证（可选）

为防止错误峰值匹配，可以验证峰值幅度：

$$\frac{|peak_{test}|}{|peak_{ref}|} \in (1 - valid\_limit, 1 + valid\_limit)$$

- 若 $valid\_limit = 0$：跳过验证（默认）
- 若 $valid\_limit > 0$：例如 $0.2$ 表示接受幅度相差 ±20% 以内的峰值

## 2. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── ResyncPeakDetector (继承自 Analyzer)
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `ResyncPeakDetector` | peak_detect.py | 主对齐器类 |
| `ResyncResult` | peak_detect.py | 对齐结果数据类 |
| `ResyncVerificationResult` | peak_detect.py | 验证指标数据类 |
| `ShiftVerificationResult` | peak_detect.py | 平移指标数据类 |
| `PeakVerificationResult` | peak_detect.py | 峰值位置指标数据类 |

### 继承结构图
```
Analyzer (squirrel.base)
    │
    └── ResyncPeakDetector
            ├── name = "resync_peak"
            ├── description = "通过峰值检测对齐轨迹"
            │
            ├── __init__(config, ref_trace_idx, peak_type, peak_range, valid_limit)
            │       ├── ref_trace_idx: int = 0 (参考轨迹索引)
            │       ├── peak_type: str = "max" (或 "min")
            │       ├── peak_range: tuple[int, int] = (0, 0) (搜索范围)
            │       └── valid_limit: float = 0.0 (幅度容差)
            │
            ├── analyze(traces, labels=None, **kwargs) -> ResyncResult
            │
            ├── verify(original, aligned, ref_trace_idx) -> ResyncVerificationResult
            ├── verify_shifts(original, aligned, ground_truth_shifts) -> ShiftVerificationResult
            ├── verify_peaks(original, aligned, ground_truth_shifts) -> PeakVerificationResult
            ├── detect_leakage_points(result, threshold) -> np.ndarray
            ├── load_traces(path, format="zarr") -> TraceDataset
            ├── save_traces(traces, path, format="zarr") -> Path
            ├── print_verification(result)
            ├── print_shift_verification(result)
            └── print_peak_verification(result, tolerance)
```

## 3. API接口说明

### 构造函数

```python
ResyncPeakDetector(
    config: dict | None = None,
    ref_trace_idx: int = 0,
    peak_type: str = "max",
    peak_range: tuple[int, int] = (0, 0),
    valid_limit: float = 0.0
)
```

**配置参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ref_trace_idx` | 0 | 参考轨迹索引 |
| `peak_type` | "max" | "max" 或 "min" 峰值类型 |
| `peak_range` | (0, 0) | (起始, 结束) 搜索范围；为(0,0)时使用完整轨迹 |
| `valid_limit` | 0.0 | 幅度容差（0=跳过验证） |

### 主要方法

#### `analyze(traces, **kwargs) -> ResyncResult`
通过峰值检测对齐所有轨迹。

```python
result = aligner.analyze(traces)
aligned = result.metadata["aligned_traces"]
shifts = result.metadata["shifts"]
```

#### `verify(original, aligned, ref_trace_idx) -> ResyncVerificationResult`
计算：
- 标准差降低百分比
- 相关系数改善
- 方差降低百分比

#### `verify_shifts(original, aligned, ground_truth_shifts) -> ShiftVerificationResult`
比较估算偏移与真实偏移。

#### `verify_peaks(original, aligned, ground_truth_shifts) -> PeakVerificationResult`
计算峰值位置精度。

### 使用示例

```python
from squirrel.preprocessing import ResyncPeakDetector
import numpy as np

# 加载轨迹
traces = np.random.randn(100, 2000)

# 创建对齐器
aligner = ResyncPeakDetector(
    ref_trace_idx=0,
    peak_type="max",           # 查找最大值峰值
    peak_range=(100, 500),      # 在样本100-500范围内搜索
    valid_limit=0.2             # 接受与参考幅度相差20%以内的峰值
)

# 分析
result = aligner.analyze(traces)
aligned = result.metadata["aligned_traces"]

# 验证
verify_result = aligner.verify(traces, aligned)
print(f"相关系数改善: {verify_result.corr_improvement:.4f}")
```

## 4. Makefile用法

### 快速开始
```bash
make resync_peak
```

### 可用目标

| 目标 | 说明 |
|------|------|
| `resync_peak` | 运行完整流程：生成 → 对齐 → 验证 |
| `resync_peak-generate` | 仅生成测试数据 |
| `resync_peak-align` | 执行峰值对齐 |
| `resync_peak-verify` | 验证对齐结果 |
| `resync_peak-clean` | 清理输出文件 |

### 配置变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RESYNC_PEAK_NUM_TRACES` | 300 | 生成轨迹数量 |
| `RESYNC_PEAK_NUM_SAMPLES` | 2000 | 每条轨迹样本数 |
| `RESYNC_PEAK_MAX_SHIFT` | 20 | 测试数据最大偏移 |
| `RESYNC_PEAK_NOISE_STD` | 0.1 | 噪声标准差 |

### 使用示例

```bash
# 默认运行
make resync_peak

# 自定义配置
make resync_peak RESYNC_PEAK_NUM_TRACES=500

# 查看日志
cat sim/preprocessing/Resync_Peak/log/verify.log

# 清理
make resync_peak-clean
```

## 5. 算法流程

```
1. 计算参考峰值
   └─> 从ref_trace的peak_range范围内找出峰值(max或min)
   └─> 记录峰值位置和幅度

2. 对每条轨迹：
   ├─> 在peak_range范围内查找峰值
   ├─> 可选：验证峰值幅度（若valid_limit > 0）
   ├─> 计算 shift = ref_peak_loc - trace_peak_loc
   └─> 通过零填充应用平移

3. 返回对齐后的轨迹
```

## 5.1 具体计算示例

### 输入数据

假设有两条轨迹，每条长度 $N = 10$：

```
参考轨迹 R (ref_trace_idx=0):
R = [0.1, 0.3, 0.8, 1.5, 2.1, 1.8, 1.2, 0.6, 0.2, 0.1]
位置:    0    1    2    3    4    5    6    7    8    9

测试轨迹 T:
T = [0.1, 0.2, 0.4, 0.7, 1.2, 1.9, 2.3, 1.6, 0.8, 0.2]
位置:    0    1    2    3    4    5    6    7    8    9
```

### Step 1: 确定峰值搜索范围

假设设置 `peak_range = (2, 7)`，只在索引 2-7 范围内搜索峰值。

### Step 2: 检测参考轨迹峰值

在 R[2:8] = [0.8, 1.5, 2.1, 1.8, 1.2, 0.6] 中找最大值：

```
R[2] = 0.8
R[3] = 1.5
R[4] = 2.1  ← 最大值
R[5] = 1.8
R[6] = 1.2
R[7] = 0.6

peak_ref = argmax(R) = 4
peak_ref 的幅度 = 2.1
```

### Step 3: 检测测试轨迹峰值

在 T[2:8] = [0.4, 0.7, 1.2, 1.9, 2.3, 1.6] 中找最大值：

```
T[2] = 0.4
T[3] = 0.7
T[4] = 1.2
T[5] = 1.9
T[6] = 2.3  ← 最大值
T[7] = 1.6

peak_test = argmax(T) = 6
peak_test 的幅度 = 2.3
```

### Step 4: 计算平移量

$$shift = peak_{ref} - peak_{test} = 4 - 6 = -2$$

**含义**：测试轨迹的峰值在参考轨迹峰值**左侧** 2 个采样点，需要**右移 2 个采样点**。

### Step 5: 应用零填充平移

使用公式 $aligned[i] = T_{i-shift} = T_{i-(-2)} = T_{i+2}$：

```
i=0:  aligned[0] = T[0+2] = T[2] = 0.4
i=1:  aligned[1] = T[1+2] = T[3] = 0.7
i=2:  aligned[2] = T[2+2] = T[4] = 1.2
i=3:  aligned[3] = T[3+2] = T[5] = 1.9
i=4:  aligned[4] = T[4+2] = T[6] = 2.3  ← 峰值！位置4 = peak_ref ✓
i=5:  aligned[5] = T[5+2] = T[7] = 1.6
i=6:  aligned[6] = T[6+2] = T[8] = 0.8
i=7:  aligned[7] = T[7+2] = T[9] = 0.2
i=8:  aligned[8] = T[8+2] = T[10] = 越界 → 0
i=9:  aligned[9] = T[9+2] = T[11] = 越界 → 0

aligned = [0.4, 0.7, 1.2, 1.9, 2.3, 1.6, 0.8, 0.2, 0, 0]
```

### Step 6: 验证结果

```
对齐前：
  R peak@4 = 2.1
  T peak@6 = 2.3

对齐后：
  R peak@4 = 2.1
  aligned peak@4 = 2.3 ✓

峰值成功对齐到同一位置！
```

## 6. 局限性

### Resync_Peak可能失效的情况
- **多个峰值**: 如果波形每个尖峰有多个峰值，可能选错
- **噪声信号**: 噪声可能产生虚假峰值
- **低幅度峰值**: 小峰值难以精确定位
- **饱和信号**: 裁剪可能扭曲峰值位置

### 建议
- 用于干净、尖峰型波形
- 设置合适的 `peak_range` 聚焦相关区域
- 设置 `valid_limit` 拒绝异常轨迹

## 7. 方法选择速查

| 波形特征 | 推荐方法 |
|---------|---------|
| 清晰单峰 | **Peak** ✓ |
| 双尖峰/多峰 | DTW |
| 高噪声 | CrossCorr |
| 非线性变形 | DTW |
| 方波/过零点 | ZC |
| 有参考模板 | SAD |