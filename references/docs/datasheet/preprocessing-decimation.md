# Decimation - 轨迹降采样预处理

## 测试结果

**降采样前后对比图：**


| 指标 | 数值 |
|------|------|
| **输入采样数** | 2000 |
| **输出采样数** | 500 |
| **降采样因子** | 4 |
| **验证** | ✓ PASS |

## 1. 算法原理

### 1.1 核心思想

Decimation 通过固定间隔采样来减少数据点数，降低采样率。每隔 N 个点保留 1 个点。

**降采样因子 N:1** 表示：每 N 个输入样本输出 1 个样本。

### 1.2 数学公式

**输入轨迹：**
$$T = (t_1, t_2, t_3, ..., t_N)$$

**降采样后（因子 D）：**
$$T' = (t_1, t_{1+D}, t_{1+2D}, ..., t_{1+kD})$$

其中 $k = \lfloor (N-1)/D \rfloor$

**验证比例：**
$$\text{ratio} = \frac{\text{input\_samples}}{\text{output\_samples}}$$

### 1.3 关键特性

- 固定间隔采样，无插值
- 降低存储需求和计算复杂度
- 可能导致频谱混叠（奈奎斯特准则）
- 适合抗混叠预处理后的数据

## 2. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── Decimation (继承自 Analyzer)
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `Decimation` | decimation.py | 主降采样器类 |
| `DecimationResult` | decimation.py | 降采样结果数据类 |
| `DecimationVerificationResult` | decimation.py | 验证指标数据类 |

### 继承结构图

```
Analyzer (squirrel.base)
    │
    └── Decimation
            ├── name = "decimation"
            ├── description = "Decimate traces by a fixed factor"
            │
            ├── __init__(config: dict | None, dec_factor: int = 2)
            │       └── dec_factor: int (降采样因子)
            │
            ├── analyze(traces, labels=None, **kwargs) -> DecimationResult
            │       └── 返回降采样轨迹在 result.metadata["decimated_traces"]
            │
            ├── verify(original, decimated) -> DecimationVerificationResult
            └── detect_leakage_points(result, threshold) -> np.ndarray
```

## 3. API接口说明

### 构造函数

```python
Decimation(
    config: dict[str, Any] | None = None,
    dec_factor: int = 2
)
```

**配置参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `dec_factor` | 2 | 降采样因子，每隔 N 个点保留 1 个 |

### 主要方法

#### `analyze(traces, labels=None, **kwargs) -> DecimationResult`

主入口，降采样轨迹并返回结果。

```python
result = decimator.analyze(traces)
decimated_traces = result.metadata["decimated_traces"]
```

#### `verify(original, decimated) -> DecimationVerificationResult`

验证降采样效果，计算：
- 输入/输出采样数
- 降采样比例

### 使用示例

```python
from squirrel.preprocessing import Decimation
import numpy as np

# 加载轨迹
traces = np.random.randn(100, 2000)

# 创建降采样器 (因子=4)
decimator = Decimation(dec_factor=4)
result = decimator.analyze(traces)
decimated = result.metadata["decimated_traces"]

print(f"Original shape: {traces.shape}")      # (100, 2000)
print(f"Decimated shape: {decimated.shape}")  # (100, 500)
```

## 4. Makefile用法

### 快速开始

```bash
make decimation
```

### 可用目标

| 目标 | 说明 |
|------|------|
| `decimation` | 运行完整流程：生成 → 降采样 → 验证 |
| `decimation-generate` | 仅生成测试数据 |
| `decimation-decimate` | 执行降采样 |
| `decimation-verify` | 验证降采样结果 |
| `decimation-clean` | 清理输出文件 |

### 配置变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DECIMATION_NUM_TRACES` | 300 | 生成轨迹数量 |
| `DECIMATION_NUM_SAMPLES` | 2000 | 每条轨迹样本数 |
| `DECIMATION_NOISE_STD` | 0.5 | 噪声标准差 |
| `DECIMATION_FACTOR` | 4 | 降采样因子 |
| `DECIMATION_BASE_SEED` | 777 | 随机种子 |

### 使用示例

```bash
# 默认运行
make decimation

# 自定义降采样因子
make decimation DECIMATION_FACTOR=8

# 自定义轨迹数
make decimation DECIMATION_NUM_TRACES=500

# 仅生成并查看日志
make decimation-generate
cat sim/preprocessing/Decimation/log/generate.log

# 仅验证
make decimation-verify

# 清理
make decimation-clean
```

### 输出文件

```
sim/preprocessing/Decimation/
├── traces/
│   ├── decimation_original.zarr           # 原始轨迹
│   └── decimation_original_metadata.json  # 元数据
├── result/
│   ├── decimation_decimated.zarr          # 降采样后轨迹
│   └── decimation_comparison.png          # 对比可视化
└── log/
    ├── generate.log                       # 数据生成日志
    ├── decimation.log                     # 降采样日志
    └── verify.log                         # 验证结果
```

## 5. 算法流程

```
1. 初始化降采样器
   └─> 设置 dec_factor

2. 对所有轨迹降采样：
   └─> traces[:, ::dec_factor]  # 每隔 D 个点取 1 个

3. 返回降采样后的轨迹
```

## 6. 应用场景

| 场景 | 说明 |
|------|------|
| 数据压缩 | 减少存储和传输需求 |
| 预处理 | 降低后续处理计算量 |
| 抗混叠 | 配合低通滤波使用 |
| 多速率处理 | 降低采样率以匹配系统 |

## 7. 常见问题

**Q: 降采样后信号失真怎么办？**

A: 失真通常由频谱混叠引起。在降采样前使用低通滤波（DigitalFilter）截止频率设为 < 1/(2D)。

**Q: 如何选择降采样因子？**

A: 考虑奈奎斯特准则 - 原始信号最高频率 f_max，降采样因子 D 需满足 f_max < 采样率/(2D)。

**Q: 降采样和重采样的区别？**

A:
- **降采样 (Decimation)**: 直接丢弃点，计算快但可能失真
- **重采样 (Resampling)**: 插值后采样，保持信号完整性但计算量大

**Q: 什么时候用降采样？**

A:
- 数据量大，需要快速处理
- 已知信号频率远低于采样率
- 已经过抗混叠滤波
