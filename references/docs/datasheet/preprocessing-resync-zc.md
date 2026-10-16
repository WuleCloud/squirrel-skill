# Resync_ZC - 零交叉点轨迹对齐

## 测试结果

**对齐前后对比图：**


| 指标 | 数值 |
|------|------|
| **标准差降低** | 89.9% ✓ |
| **相关性通过** | ✓ |
| **对齐精度** | 100% (上升沿 ±5) |
| **适用波形** | 方波(单脉冲)、陡峭边缘、有过零点的信号 |

> **验证方法**: 使用上升沿(rise-edge)检测验证对齐效果，而非峰值检测。因为方波脉冲的峰值区域是平坦的，峰值位置不确定。

## 1. 算法原理

### 1.1 核心思想

Resync_ZC（零交叉重采样）通过检测**零交叉点**并将相邻交叉点之间的每段重采样到统一长度来对齐轨迹。基于 ChipWhisperer 的 ResyncResampleZC 算法。

**核心思想**：方波或脉冲信号有清晰的上升沿/下降沿，这些边缘产生的零交叉点可以作为对齐的参考点。将相邻零交叉点之间的信号段标准化为相同长度，可以消除时间偏移的影响。

### 1.2 数学公式

**给定：**
- 轨迹：$T = (t_1, t_2, ..., t_N)$，长度 $N$（所有轨迹，包括第 0 条作为参考）
- 零交叉电平：$z$（通常为 0）

**零交叉点检测：**

找到满足以下条件的索引 $i$：

$$(t_i - z) \geq 0 \text{ 且 } (t_{i-1} - z) < 0$$

即信号从负侧穿越到正侧的第一个采样点。

**平均区间长度：**

$$L_{avg} = \frac{\sum_{j=2}^{M} (ZC_j - ZC_{j-1})}{M-1}$$

其中 $M$ = 零交叉点数量，$ZC_j$ = 第 $j$ 个零交叉点索引。

**重采样：**

对于 $ZC_{j-1}$ 和 $ZC_j$ 之间的区间：

$$segment_{resampled} = \text{resample}(segment, L_{avg})$$

将每个区间重采样到平均长度，实现对齐。

### 1.3 算法步骤

```
1. 检测ZC: 在参考轨迹中找出所有零交叉点
2. 计算区间长度: 计算相邻ZC间的平均距离
3. 重采样区间: 将ZC之间的每个区间重采样到 L_avg 长度
4. 拼接: 将所有重采样后的区间连接起来
```

## 2. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── ResyncZCAligner (继承自 Analyzer)
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `ResyncZCAligner` | resync_zc.py | 主对齐器类 |
| `ResyncZCResult` | resync_zc.py | 对齐结果数据类 |
| `ResyncZCVerificationResult` | resync_zc.py | 验证指标数据类 |
| `ShiftZCVerificationResult` | resync_zc.py | 平移验证数据类 |
| `ZCVerificationResult` | resync_zc.py | ZC专用验证数据类 |

### 继承结构图
```
Analyzer (squirrel.base)
    │
    └── ResyncZCAligner
            ├── name = "resync_zc"
            ├── description = "基于零交叉重采样对齐轨迹"
            │
            ├── __init__(config, ref_trace_idx, zc_level, bin_length)
            │       ├── ref_trace_idx: int = 0 (参考轨迹索引)
            │       ├── zc_level: float = 0.0 (ZC检测阈值)
            │       └── bin_length: int = 0 (目标区间长度，为0则自动计算)
            │
            ├── analyze(traces, labels=None, **kwargs) -> ResyncZCResult
            │
            ├── verify(original, aligned, ref_trace_idx) -> ResyncZCVerificationResult
            ├── verify_zc_variance(original, aligned, ref_trace_idx) -> ZCVerificationResult
            ├── detect_leakage_points(result, threshold) -> np.ndarray
            ├── load_traces(path, format="zarr") -> TraceDataset
            ├── save_traces(traces, path, format="zarr") -> Path
            └── print_verification(result)
```

## 3. API接口说明

### 构造函数

```python
ResyncZCAligner(
    config: dict | None = None,
    ref_trace_idx: int = 0,
    zc_level: float = 0.0,
    bin_length: int = 0
)
```

**配置参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ref_trace_idx` | 0 | 参考轨迹索引 |
| `zc_level` | 0.0 | 零交叉检测的阈值电平 |
| `bin_length` | 0 | 目标区间长度（0=从参考轨迹自动计算） |

### 核心方法

#### `_find_zerocrossing(a: np.ndarray) -> np.ndarray`
查找信号从负到正穿过zc_level的索引。

```python
indices = aligner._find_zerocrossing(trace)
# 返回交叉点索引数组
```

#### `_find_avg_length(indices: np.ndarray) -> int`
计算相邻零交叉点之间的平均距离。

#### `_resample_resize(data, indices, targlen) -> np.ndarray`
将ZC之间的每个区间重采样到目标长度。

#### `analyze(traces, **kwargs) -> ResyncZCResult`
对齐的主入口。

### 使用示例

```python
from squirrel.preprocessing import ResyncZCAligner
import numpy as np

# 加载轨迹
traces = np.random.randn(100, 2000)

# 创建对齐器
aligner = ResyncZCAligner(
    ref_trace_idx=0,
    zc_level=0.0,      # 在零点检测交叉
    bin_length=0        # 从参考轨迹自动计算
)

# 分析
result = aligner.analyze(traces)
aligned = result.metadata["aligned_traces"]

# 验证
verify_result = aligner.verify(traces, aligned)
print(f"标准差降低: {verify_result.std_reduction_percent:.1f}%")
```

## 4. Makefile用法

### 快速开始
```bash
make resync_zc
```

### 可用目标

| 目标 | 说明 |
|------|------|
| `resync_zc` | 运行完整流程：生成 → 对齐 → 验证 |
| `resync_zc-generate` | 仅生成测试数据 |
| `resync_zc-align` | 执行ZC对齐 |
| `resync_zc-verify` | 验证对齐结果 |
| `resync_zc-clean` | 清理输出文件 |

### 配置变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RESYNC_ZC_NUM_TRACES` | 300 | 生成轨迹数量 |
| `RESYNC_ZC_NUM_SAMPLES` | 2000 | 每条轨迹样本数 |
| `RESYNC_ZC_MAX_SHIFT` | 20 | 测试数据最大偏移 |
| `RESYNC_ZC_NOISE_STD` | 0.3 | 噪声标准差 |

### 使用示例

```bash
# 默认运行
make resync_zc

# 自定义配置
make resync_zc RESYNC_ZC_NOISE_STD=0.5

# 查看日志
cat sim/preprocessing/Resync_ZC/log/verify.log

# 清理
make resync_zc-clean
```

## 5. 测试波形

### 单脉冲方波

ZC 测试使用**单脉冲方波**（而非连续方波）：

```
        ┌────────────────┐
Signal  │                │
Level   └────────────────┘
        0    500        1000   2000
              ↑
           上升沿位置
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `edge_pos` | 500 | 上升沿位置 |
| `pulse_width` | 500 | 脉冲宽度 |
| `amplitude` | 5.0 | 信号幅度 |

### 验证方法

使用**上升沿检测**验证对齐效果：
- 检测信号从低电平穿越阈值到高电平的第一个位置
- 对齐后，所有轨迹的上升沿应与参考轨迹对齐

```python
def find_rise_edge(trace, threshold=0.0):
    idx = np.where((trace[:-1] < threshold) & (trace[1:] >= threshold))[0]
    return idx[0] if len(idx) > 0 else np.argmax(trace)
```

> **为什么不用峰值检测？** 方波脉冲的顶部是平坦的，峰值位置在 plateau 区域有多个，无法唯一确定。上升沿位置是唯一可靠的特征点。

## 6. 算法特性

### 优点
- 有物理依据（尖锐过渡产生ZC）
- 可处理非线性偏移
- 无需参考窗口
- 单脉冲方波提供清晰的上升沿特征

### 局限性
- 对噪声敏感（可能产生虚假ZC）
- 性能取决于信号质量
- 输出长度可能与输入不同

### 推荐的zc_level值
| 波形类型 | 推荐的zc_level |
|----------|---------------|
| 尖峰波形 | 0.0 或小偏移 |
| 正弦波形 | 0.0 |
| 噪声信号 | 较高阈值以避免虚假检测 |

## 7. 方法选择速查

| 波形特征 | 推荐方法 |
|---------|---------|
| 清晰单峰 | Peak |
| 双尖峰/多峰 | DTW |
| 高噪声 | CrossCorr |
| 非线性变形 | DTW |
| 有过零点的波形 | **ZC** ✓ |
| 有参考模板 | SAD |