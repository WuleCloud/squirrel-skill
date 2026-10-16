# SNR - Signal-to-Noise Ratio 分析

## 测试结果

**SNR vs Time 曲线：**


| 指标 | 测试结果 |
|------|----------|
| **Peak SNR** | 24.38 dB at sample 500 |
| **Leakage groups** | 9 |
| **Best group size** | 135 |
| **Expected SNR** | 21.50 dB |
| **SNR Diff** | 2.88 dB |
| **通过验证** | ✓ PASS |

## 1. 算法原理

### 1.1 核心概念

SNR（信噪比）分析用于量化侧信道轨迹中泄漏信号与噪声的比率。通过计算 `Var(signal) / Var(noise)`，可以识别轨迹中哪些采样点包含可检测的密钥相关信息。

SNR 越高表示该位置的信号越强，攻击者越容易从中提取密钥信息。

### 1.2 泄漏模型

SNR 分析的核心是**泄漏模型（Leakage Model）**：将轨迹按某个已知量（如明文的汉明重量）分组。如果存在泄漏，同一组内的轨迹应该具有相似的均值，而不同组之间的差异则反映了信号的存在。

Squirrel SNR 实现使用 `HW(pt[0])`（明文第 0 字节的汉明重量）作为泄漏模型，明文按 HW 值分为 9 个组（0-8）。

### 1.3 SNR 公式

参考 ChipWhisperer `attacks/snr.py` 实现：

```
hwarray[h] = [所有 leakage=h 的轨迹]
hwmean[h] = mean(hwarray[h], axis=0)              # 每组的平均波形

signal_var = Var(hwmean[valid_groups], axis=0)   # 组间方差
noise_var  = Var(hwarray[best_group], axis=0)    # 最大组的组内方差

SNR = signal_var / noise_var
SNR_dB = 20 * log10(SNR)
```

**best_group** 是轨迹数最多的那个 HW 组，用作噪声基准。

## 2. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── SNRAnalyzer
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `SNRAnalyzer` | snr/snr.py | 主分析器类 |
| `SNRResult` | snr/snr.py | 分析结果数据类 |

### 继承结构图

```
Analyzer (squirrel.base)
    │
    └── SNRAnalyzer
            ├── name = "snr"
            ├── description = "Signal-to-Noise Ratio analysis for leakage detection"
            │
            ├── __init__(config: dict | None)
            │       └── leakage_model: str = "HW"
            │
            ├── analyze(traces, plaintext, **kwargs) -> SNRResult
            │       └── 核心：按 HW 分组 → 计算 SNR vs 时间
            │
            └── detect_leakage_points(result, threshold=None) -> np.ndarray
                    └── 返回 SNR 超过阈值的采样点索引
```

## 3. API 接口说明

### 构造函数

```python
SNRAnalyzer(config: dict[str, Any] | None = None)
```

**配置参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `leakage_model` | "HW" | 泄漏模型，当前仅支持 "HW" |

### 主要方法

#### `analyze(traces, plaintext, **kwargs) -> SNRResult`

运行 SNR 分析。

```python
analyzer = SNRAnalyzer()
result = analyzer.analyze(traces, plaintext=plaintext)
print(f"Peak SNR: {result.peak_snr_db:.2f} dB at sample {result.peak_sample}")
```

### SNRResult 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `method` | str | "snr" |
| `snr` | np.ndarray | 原始 SNR 值（无 dB 转换），shape=(num_samples,) |
| `snr_db` | np.ndarray | SNR_dB = 20*log10(snr)，shape=(num_samples,) |
| `peak_snr_db` | float | SNR_dB 的最大值 |
| `peak_sample` | int | 峰值所在的采样点索引 |
| `num_leakage_groups` | int | 有效的 HW 分组数量（通常 9） |
| `best_group_size` | int | 最大 HW 组的轨迹数 |
| `metadata` | dict | 附加信息（num_traces, num_samples, group_sizes, leakage_model） |

## 4. 测试数据生成

### 数据生成器

```bash
python -m tests.data_generators.cli snr \
    --output /path/to/output.zarr \
    --num-traces 500 \
    --num-samples 1000 \
    --noise-std 0.5 \
    --seed 42
```

**泄漏模型**：`HW(pt[0])`

每个轨迹包含一个高斯脉冲，其幅度正比于 `HW(pt[0])`：

```
leakage = base_pulse * (HW(pt[0]) / 8.0) * 6.0
trace = leakage + noise
```

这使得 HW 值高的轨迹整体幅值更大，组间方差增大，SNR 升高。

### 测试命令

```bash
make snr              # 完整流程：生成 → 分析 → 验证
make test-snr        # 仅运行测试
```

### 验证结果

| 指标 | 期望值 |
|------|--------|
| Peak SNR | ~21.5 dB（实际测量 24.38 dB） |
| Peak sample | 应在脉冲中心附近（sample ~500 for 1000 samples） |
| Leakage groups | 9（HW 0-8 全部分组有轨迹） |
| SNR Diff | < 5.0 dB（与预设值对比） |

## 5. 结果解读指南

### 5.1 SNR 强度判断

| SNR_dB | 解读 |
|--------|------|
| < 0 dB | 无明显泄漏，噪声主导 |
| 0 - 3 dB | 边缘，可能存在弱泄漏 |
| 3 - 10 dB | 存在可检测泄漏 |
| > 10 dB | 强泄漏，攻击极易成功 |

### 5.2 峰值位置

SNR 峰值位置对应轨迹中泄漏信号最强的采样点。在合成数据中，这对应注入脉冲的中心位置。在真实设备上，这通常对应加密操作的特定阶段（如 S-Box 查表、MixColumns 等）。

### 5.3 分组数量与分布

理想情况下，9 个 HW 组（0-8）都应有足够轨迹覆盖。分组不均匀（如某些 HW 值缺失）会影响 SNR 估计准确性。

## 6. 局限性

### 6.1 泄漏模型依赖

SNR 分析需要预先知道泄漏模型（如 `HW(pt)`）。错误的泄漏模型会导致分组错误，SNR 估计不准确。

### 6.2 线性假设

SNR 假设信号在各 HW 组间的差异是线性的。对于非线性泄漏（如 S-Box 输出），需要更复杂的模型。

### 6.3 噪声估计

使用最大 HW 组的组内方差作为噪声基准。这假设最大组包含足够多的轨迹，且其内部确实只反映噪声。该假设在某些场景下可能不成立。

## 7. 核心算法细节

### 7.1 分组逻辑

```python
hwarray: list[list[np.ndarray]] = [[] for _ in range(9)]  # HW 0-8
for i in range(num_traces):
    hw = HW(pt[i, 0])
    hwarray[hw].append(traces[i])
```

### 7.2 方差计算

```python
hwmean_valid = hwmean[inc_list]  # shape: (num_valid_groups, num_samples)
signal_var = np.var(hwmean_valid, axis=0)  # 组间方差，shape: (num_samples,)
noise_var = np.var(hwarray[best_choice], axis=0)  # 组内方差，shape: (num_samples,)
```

### 7.3 dB 转换

```python
snr_db = 20 * np.log10(signal_var / noise_var)
```

使用 20 而不是 10，是因为 SNR 定义为功率比，而方差本身就是功率的度量。

## 8. 参考

- ChipWhisperer `attacks/snr.py` - SNR 分析参考实现
- Mangard et al. "Power Analysis Attacks" - SNR 理论基础
