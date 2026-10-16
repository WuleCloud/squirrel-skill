# Resync_CrossCorr - 互相关轨迹对齐 加一个range参数

## 测试结果

**对齐前后对比图：**


| 指标 | 数值 |
|------|------|
| **对齐前 MAE** | 10.20 samples |
| **对齐后 MAE** | 0.00 samples |
| **对齐精度 (±5)** | 100% ✓ |
| **相关系数改善** | +0.3627 |
| **适用波形** | 高斯峰等平滑特征 |

## 1. 算法原理

### 1.1 核心思想

Resync_CrossCorr 通过计算测试轨迹与参考轨迹之间的**互相关（cross-correlation）**来检测时间偏移，然后对轨迹进行对齐。基于 ChipWhisperer 的 ResyncCrossCorrelation 算法。

**核心思想**：当两条轨迹完全对齐时，它们的互相关峰值会出现在零偏移位置。通过找到互相关峰值的位置，可以计算出需要对齐的偏移量。

### 1.2 数学公式

**给定：**
- 参考轨迹：$R = (r_1, r_2, ..., r_N)$，长度 $N$（即第 0 条轨迹）
- 测试轨迹：$T = (t_1, t_2, ..., t_N)$，长度 $N$（第 1, 2, 3 ... 条轨迹）
- 参考窗口：$[start, end]$（从参考轨迹中提取的特征区域）

**步骤1：参考窗口提取**

$$W = R_{start:end}$$

**步骤2：互相关计算**

使用 `scipy.signal.correlate` 计算测试轨迹与参考窗口的互相关：

$$C = \text{correlate}(T, W, mode='valid')$$

互相关衡量的是 $T$ 和 $W$ 在不同相对位置下的相似程度。峰值位置表示最佳匹配位置。

**步骤3：计算平移量**

$$shift = peak_{ref} - peak_{test}$$

- $peak_{ref}$：参考轨迹与自身窗口的互相关峰值位置
- $peak_{test}$：测试轨迹与参考窗口的互相关峰值位置
- $shift > 0$：测试轨迹峰值偏右，需要左移
- $shift < 0$：测试轨迹峰值偏左，需要右移

**步骤4：零填充平移对齐**

$$aligned[i] = \begin{cases}
0 & \text{若 } i - shift < 0 \quad \text{（左侧越界，补零）}\\[4pt]
T_{i-shift} & \text{若 } 0 \leq i - shift < N \quad \text{（有效范围）}\\[4pt]
0 & \text{若 } i - shift \geq N \quad \text{（右侧越界，补零）}
\end{cases}$$

## 2. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── ResyncCrossCorrAligner (继承自 Analyzer)
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `ResyncCrossCorrAligner` | cross_corr.py | 主对齐器类 |
| `CrossCorrResult` | cross_corr.py | 对齐结果数据类 |
| `CrossCorrVerificationResult` | cross_corr.py | 验证指标数据类 |
| `ShiftVerificationResult` | cross_corr.py | 偏移验证数据类 |

### 继承结构图

```
Analyzer (squirrel.base)
    │
    └── ResyncCrossCorrAligner
            ├── name = "resync_crosscorr"
            ├── description = "通过互相关对齐轨迹"
            │
            ├── __init__(config, ref_trace_idx, window)
            │       ├── ref_trace_idx: int = 0 (参考轨迹索引)
            │       └── window: tuple[int, int] = (0, 0) (参考窗口范围)
            │
            ├── analyze(traces, labels=None, **kwargs) -> CrossCorrResult
            │
            ├── verify(original, aligned, ref_trace_idx) -> CrossCorrVerificationResult
            ├── verify_shifts(original, aligned, ground_truth_shifts) -> ShiftVerificationResult
            ├── detect_leakage_points(result, threshold) -> np.ndarray
            ├── load_traces(path, format="zarr") -> TraceDataset
            ├── save_traces(traces, path, format="zarr") -> Path
            ├── print_verification(result)
            └── print_shift_verification(result)
```

## 3. API接口说明

### 构造函数

```python
ResyncCrossCorrAligner(
    config: dict | None = None,
    ref_trace_idx: int = 0,
    window: tuple[int, int] = (0, 0)
)
```

**配置参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ref_trace_idx` | 0 | 参考轨迹索引 |
| `window` | (0, 0) | (起始, 结束) 参考窗口范围；为(0,0)时使用完整轨迹 |

### 主要方法

#### `analyze(traces, **kwargs) -> CrossCorrResult`

通过互相关对齐所有轨迹。

```python
result = aligner.analyze(traces)
aligned = result.metadata["aligned_traces"]
shifts = result.metadata["shifts"]
```

#### `verify(original, aligned, ref_trace_idx) -> CrossCorrVerificationResult`

计算：
- 峰值位置离散度降低百分比
- 相关系数改善

#### `verify_shifts(original, aligned, ground_truth_shifts) -> ShiftVerificationResult`

比较估算偏移与真实偏移。

### 使用示例

```python
from squirrel.preprocessing import ResyncCrossCorrAligner
import numpy as np

# 加载轨迹
traces = np.random.randn(100, 2000)

# 创建对齐器
aligner = ResyncCrossCorrAligner(
    ref_trace_idx=0,
    window=(500, 1100)  # 使用样本500-1100作为参考窗口
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
make resync_crosscorr
```

### 可用目标

| 目标 | 说明 |
|------|------|
| `resync_crosscorr` | 运行完整流程：生成 → 对齐 → 验证 |
| `resync_crosscorr-generate` | 仅生成测试数据 |
| `resync_crosscorr-align` | 执行互相关对齐 |
| `resync_crosscorr-verify` | 验证对齐结果 |
| `resync_crosscorr-clean` | 清理输出文件 |

### 配置变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RESYNC_CC_NUM_TRACES` | 300 | 生成轨迹数量 |
| `RESYNC_CC_NUM_SAMPLES` | 2000 | 每条轨迹样本数 |
| `RESYNC_CC_MAX_SHIFT` | 20 | 测试数据最大偏移 |
| `RESYNC_CC_NOISE_STD` | 0.1 | 噪声标准差 |

### 使用示例

```bash
# 默认运行
make resync_crosscorr

# 自定义配置
make resync_crosscorr RESYNC_CC_NUM_TRACES=500

# 查看日志
cat sim/preprocessing/Resync_CrossCorr/log/verify.log

# 清理
make resync_crosscorr-clean
```

## 5. 算法流程

```
1. 提取参考窗口
   └─> 从ref_trace的window范围内提取特征窗口W

2. 计算参考峰值位置
   └─> 对参考轨迹做互相关: C_ref = correlate(ref_trace, W, mode='valid')
   └─> 找峰值位置: peak_ref = argmax(C_ref)

3. 对每条轨迹：
   ├─> 计算互相关: C = correlate(trace, W, mode='valid')
   ├─> 找峰值位置: peak = argmax(C)
   ├─> 计算偏移: shift = peak_ref - peak
   └─> 通过零填充应用平移

4. 返回对齐后的轨迹
```

## 6. 局限性

### Resync_CrossCorr可能失效的情况

- **平坦信号区域**: 如果参考窗口内信号变化平缓，互相关峰值不明显
- **噪声信号**: 高噪声会掩盖真实的互相关峰值
- **重复模式**: 如果信号有周期性，可能产生多个相似的峰值
- **窗口选择不当**: 如果参考窗口没有包含足够的特征信息

### 建议

- 选择包含明显特征变化的区域作为参考窗口
- 确保参考窗口内有足够的信号能量（不是纯噪声）
- 对于高噪声数据，考虑先进行预处理或使用其他对齐方法

## 7. 与其他方法的比较

### 7.1 方法选择指南

| 波形特征 | 推荐方法 | 原因 |
|---------|---------|------|
| **清晰单峰** | Peak | 简单快速，argmax 精确定位 |
| **双尖峰/多峰** | DTW | 全局最优匹配，不依赖单一特征 |
| **高噪声 + 特征区域** | CrossCorr | 互相关抗噪声能力强 |
| **非线性变形** | DTW | 允许点对点最优对应 |
| **陡峭边缘/方波** | ZC | 过零点检测匹配边缘 |
| **有参考模板** | SAD | 逐点绝对差值最小化 |

### 7.2 实测性能对比

| 方法 | 精度 (±5) | 噪声敏感度 | 计算速度 | 推荐噪声水平 |
|------|----------|-----------|---------|------------|
| **Peak** | 100% | 高 | 最快 | < 0.01 |
| **CrossCorr** | 100% | 中 | 快 | < 0.1 |
| **DTW** | 100% | 低 | 慢 | 任意 |
| **ZC** | 部分通过 | 高 | 快 | < 0.05 |
| **SAD** | 待修复 | 中 | 中 | < 0.1 |

### 7.3 测试波形说明

| 方法 | 测试波形 | 特征 |
|------|---------|------|
| Peak | 单一尖锐正尖峰 | amplitude=10, width~4 samples |
| CrossCorr | 高斯峰 | sigma=8, amplitude=10 |
| DTW | 双尖峰（正负） | ±8 amplitude |
| ZC | 方波 | period=400, amplitude=5 |
| SAD | 双尖峰（正负） | ±8 amplitude |

### 7.4 通用优缺点

| 方法 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| Resync_Peak | 简单快速 | 对噪声敏感，多峰会混淆 | 干净的单峰信号 |
| Resync_SAD | 计算简单，模板匹配精确 | 计算量中等 | 有参考模板的信号 |
| Resync_DTW | 最灵活，适应性强 | 计算量大 | 复杂波形变形 |
| Resync_ZC | 快速 | 对噪声敏感，需过零点 | 方波、陡峭边缘 |
| **Resync_CrossCorr** | 抗噪声能力强 | 需要合适窗口 | 有明显特征区域的信号 |