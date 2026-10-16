# DigitalFilter - 数字频率滤波预处理

## 测试结果

**滤波前后对比图：**

### 低通滤波 (Low-Pass)

| 指标 | 原始数据 | 低通滤波后 |
|------|----------|------------|
| **低频 (0-0.1)** | 保留 | 0.18% 衰减 ✓ |
| **中频 (0.1-0.25)** | 保留 | 99.85% 衰减 |
| **高频 (0.25-0.5)** | 保留 | 99.80% 衰减 |
| **验证** | - | ✓ PASS |

### 高通滤波 (High-Pass)

| 指标 | 原始数据 | 高通滤波后 |
|------|----------|------------|
| **低频 (0-0.1)** | 保留 | 99.99% 衰减 |
| **高频 (0.25-0.5)** | 保留 | -0.37% 衰减 ✓ |
| **验证** | - | ✓ PASS |

### 带通滤波 (Band-Pass)

| 指标 | 原始数据 | 带通滤波后 |
|------|----------|------------|
| **低频 (0-0.1)** | 衰减 | 91.27% 衰减 ✓ |
| **中频 (0.1-0.25)** | 保留 | 36.26% 衰减 ✓ |
| **高频 (0.25-0.5)** | 衰减 | 99.25% 衰减 ✓ |
| **验证** | - | ✓ PASS |

### 带阻滤波 (Band-Stop)

| 指标 | 原始数据 | 带阻滤波后 |
|------|----------|------------|
| **低频 (0-0.1)** | 保留 | 3.85% 衰减 ✓ |
| **中频 (0.1-0.25)** | 衰减 | 99.73% 衰减 ✓ |
| **高频 (0.25-0.5)** | 保留 | -0.45% 衰减 ✓ |
| **验证** | - | ✓ PASS |

## 1. 算法原理

### 1.1 核心思想

DigitalFilter 使用 **Butterworth 数字滤波器** 对轨迹进行频率选择性滤波。Butterworth 滤波器具有平坦的通带响应和适度的过渡带。

**支持的滤波器类型：**
- **低通 (Low-Pass)**：保留低于 freq1 的频率
- **高通 (High-Pass)**：保留高于 freq1 的频率
- **带通 (Band-Pass)**：保留 freq1 到 freq2 之间的频率
- **带阻 (Band-Stop/Notch)**：衰减 freq1 到 freq2 之间的频率

### 1.2 数学公式

Butterworth 滤波器的传递函数：

$$|H(j\omega)| = \frac{1}{\sqrt{1 + (\omega / \omega_c)^{2n}}}$$

其中：
- $\omega_c$ 是截止频率
- $n$ 是滤波器阶数

滤波器系数通过 `scipy.signal.butter` 计算：

```python
b, a = signal.butter(order, freqs, filter_type)
filtered = signal.lfilter(b, a, trace)
```

### 1.3 关键特性

- 频率值归一化到 [0, 1]，其中 1 = 奈奎斯特频率
- 阶数越高，过渡带越陡峭（但可能出现数值不稳定）
- 使用 IIR 滤波，适合实时处理

### 1.4 测试数据频率成分

| 频率成分 | 归一化频率 | 说明 |
|----------|------------|------|
| 低频 | 0.03 | 在 [0, 0.1) 频段 |
| 中频 | 0.18 | 在 [0.1, 0.25) 频段 |
| 高频 | 0.45 | 在 [0.25, 0.5) 频段 |

## 2. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── DigitalFilter (继承自 Analyzer)
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `DigitalFilter` | digital_filter.py | 主滤波器类 |
| `FilterResult` | digital_filter.py | 滤波结果数据类 |
| `FilterVerificationResult` | digital_filter.py | 验证指标数据类 |

### 继承结构图

```
Analyzer (squirrel.base)
    │
    └── DigitalFilter
            ├── name = "digital_filter"
            ├── description = "Frequency-specific digital filter using Butterworth design"
            │
            ├── __init__(config: dict | None,
            │             filter_type: str = "low",
            │             freq1: float = 0.1,
            │             freq2: float = 0.8,
            │             order: int = 5)
            │
            ├── analyze(traces, labels=None, **kwargs) -> FilterResult
            │       └── 返回滤波轨迹在 result.metadata["filtered_traces"]
            │
            ├── verify(original, filtered) -> FilterVerificationResult
            ├── print_verification(result)
            ├── load_traces(path, format="zarr") -> np.ndarray
            └── save_traces(traces, path, format="zarr") -> Path
```

## 3. API接口说明

### 构造函数

```python
DigitalFilter(
    config: dict[str, Any] | None = None,
    filter_type: str = "low",
    freq1: float = 0.1,
    freq2: float = 0.8,
    order: int = 5
)
```

**配置参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `filter_type` | "low" | 滤波器类型：low, high, bandpass, bandstop |
| `freq1` | 0.1 | 低通/高通截止频率，或带通/带阻下沿 |
| `freq2` | 0.8 | 带通/带阻上沿（仅 bandpass/bandstop） |
| `order` | 5 | 滤波器阶数 [1-32]，越高过渡越陡 |

**频率范围：** 所有频率值归一化到 (0, 1)，其中 1 = 采样率/2 (Nyquist)

### 主要方法

#### `analyze(traces, labels=None, **kwargs) -> FilterResult`

主入口，应用滤波并返回结果。

```python
result = filter.analyze(traces)
filtered_traces = result.metadata["filtered_traces"]
```

#### `verify(original, filtered) -> FilterVerificationResult`

验证滤波效果。

#### `load_traces(path) / save_traces(traces, path)`

轨迹加载和保存。

### 使用示例

```python
from squirrel.preprocessing import DigitalFilter
import numpy as np

# 加载轨迹
traces = np.random.randn(100, 2000)

# 低通滤波 (保留 < 0.2 的频率)
lpf = DigitalFilter(filter_type="low", freq1=0.2, order=5)
result = lpf.analyze(traces)
filtered = result.metadata["filtered_traces"]

# 高通滤波 (保留 > 0.3 的频率)
hpf = DigitalFilter(filter_type="high", freq1=0.3, order=5)
result = hpf.analyze(traces)

# 带通滤波 (保留 0.1-0.4 的频率)
bpf = DigitalFilter(filter_type="bandpass", freq1=0.1, freq2=0.4, order=5)
result = bpf.analyze(traces)

# 带阻滤波 (衰减 0.1-0.4 的频率)
bsf = DigitalFilter(filter_type="bandstop", freq1=0.1, freq2=0.4, order=5)
result = bpf.analyze(traces)
```

## 4. Makefile用法

### 快速开始

```bash
make digital_filter        # 运行所有滤波器测试
make digital_filter_low    # 仅低通
make digital_filter_high    # 仅高通
make digital_filter_bandpass   # 仅带通
make digital_filter_bandstop    # 仅带阻
```

### 可用目标

| 目标 | 说明 |
|------|------|
| `digital_filter` | 运行所有四种滤波器测试 |
| `digital_filter_low` | 低通滤波测试 |
| `digital_filter_high` | 高通滤波测试 |
| `digital_filter_bandpass` | 带通滤波测试 |
| `digital_filter_bandstop` | 带阻滤波测试 |
| `digital_filter-clean` | 清理输出文件 |

### 配置变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DIGITAL_FILTER_NUM_TRACES` | 300 | 生成轨迹数量 |
| `DIGITAL_FILTER_NUM_SAMPLES` | 2000 | 每条轨迹样本数 |
| `DIGITAL_FILTER_NOISE_STD` | 0.5 | 噪声标准差 |
| `DIGITAL_FILTER_BASE_SEED` | 999 | 随机种子 |

### 测试参数

| 滤波器 | freq1 | freq2 | order |
|--------|--------|-------|-------|
| 低通 | 0.2 | - | 5 |
| 高通 | 0.33 | - | 9 |
| 带通 | 0.14 | 0.4 | 1 |
| 带阻 | 0.08 | 0.48 | 5 |

### 使用示例

```bash
# 运行所有滤波器测试
make digital_filter

# 仅运行低通测试
make digital_filter_low

# 清理
make digital_filter-clean
```

### 输出文件

```
sim/preprocessing/DigitalFilter/
├── traces/
│   └── digital_filter_original.zarr   # 原始轨迹
├── low/result/
│   ├── digital_filter_low.zarr         # 低通滤波结果
│   └── digital_filter_low_comparison.png
├── high/result/
│   ├── digital_filter_high.zarr        # 高通滤波结果
│   └── digital_filter_high_comparison.png
├── bandpass/result/
│   ├── digital_filter_bandpass.zarr    # 带通滤波结果
│   └── digital_filter_bandpass_comparison.png
└── bandstop/result/
    ├── digital_filter_bandstop.zarr    # 带阻滤波结果
    └── digital_filter_bandstop_comparison.png
```

## 5. 滤波器类型速查

| 滤波器 | 电路符号 | 作用 | 典型应用 |
|--------|----------|------|----------|
| **低通** | ○──┴──○ | 保留低频，衰减高频 | 去除高频噪声 |
| **高通** | ○──┬──○ | 保留高频，衰减低频 | 去除直流偏移 |
| **带通** | ○──┴┴──○ | 保留中间频段 | 提取特定信号 |
| **带阻** | ○──┬┬──○ | 衰减中间频段 | 去除工频干扰 |

## 6. 阶数选择指南

| 阶数 | 过渡带 | 稳定性 | 适用场景 |
|------|--------|--------|----------|
| 1-2 | 宽 | 非常稳定 | 快速滤波，精度要求不高 |
| 3-5 | 中等 | 稳定 | 一般用途（推荐） |
| 6-9 | 窄 | 可能不稳定 | 需要陡峭截止 |
| >9 | 非常窄 | 数值问题 | 慎用，考虑其他方法 |

## 7. 常见问题

**Q: 滤波后信号失真怎么办？**

A: 降低阶数 (order)。高阶 Butterworth 滤波器在过渡带会有 ringing 效应。

**Q: 频率成分没有被有效分离？**

A:
1. 确认频率成分在验证频段内（如 0.18 在 [0.1, 0.25)）
2. 增大阶数使截止更陡峭
3. 如果相邻频段太近，可能需要调整信号生成参数

**Q: bandpass 为什么不保留中频？**

A: 检查 freq1, freq2 设置。Butterworth 在截止频率处有 ~3dB 衰减，确保目标频率在通带内而非过渡带。
