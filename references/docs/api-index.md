# Squirrel 模块索引

本文档提供 Squirrel 框架所有模块的一句话总结和 API 接口定义。

---

## Preprocessing（预处理模块）

### 1. Normalize - 轨迹归一化

**作用**: 将轨迹转换为零均值（和可选单位方差），消除均值偏移和标准化幅度。

**API 定义**:
```python
Normalize(
    config: dict[str, Any] | None = None,
    mode: str = "mean"  # "mean" | "mean_stddev"
)
```

| 模式 | 公式 | 效果 |
|------|------|------|
| `mean` | $T - \mu_T$ | 零均值化 |
| `mean_stddev` | $(T - \mu_T) / \sigma_T$ | 标准化（均值=0，std=1） |

**调用示例**:
```python
from squirrel.preprocessing import Normalize

# 零均值化
normalizer = Normalize(mode="mean")
result = normalizer.analyze(traces)
normalized = result.metadata["normalized_traces"]

# 标准化（均值=0，std=1）
normalizer_std = Normalize(mode="mean_stddev")
result_std = normalizer_std.analyze(traces)
normalized_std = result_std.metadata["normalized_traces"]
```

---

### 2. DigitalFilter - 数字频率滤波

**作用**: 使用 Butterworth 滤波器对轨迹进行频率选择性滤波（低通/高通/带通/带阻）。

**API 定义**:
```python
DigitalFilter(
    config: dict[str, Any] | None = None,
    filter_type: str = "low",  # "low" | "high" | "bandpass" | "bandstop"
    freq1: float = 0.1,        # 低通/高通截止频率，或带通/带阻下沿
    freq2: float = 0.8,        # 带通/带阻上沿（仅 bandpass/bandstop）
    order: int = 5             # 滤波器阶数 [1-32]
)
```

| 滤波器 | 保留频率 | 衰减频率 |
|--------|----------|----------|
| `low` | < freq1 | > freq1 |
| `high` | > freq1 | < freq1 |
| `bandpass` | freq1 ~ freq2 | < freq1, > freq2 |
| `bandstop` | < freq1, > freq2 | freq1 ~ freq2 |

**调用示例**:
```python
from squirrel.preprocessing import DigitalFilter

# 低通滤波（保留 < 0.2 的频率）
lpf = DigitalFilter(filter_type="low", freq1=0.2, order=5)
result = lpf.analyze(traces)
filtered = result.metadata["filtered_traces"]

# 高通滤波（保留 > 0.3 的频率）
hpf = DigitalFilter(filter_type="high", freq1=0.3, order=5)

# 带通滤波（保留 0.1-0.4 的频率）
bpf = DigitalFilter(filter_type="bandpass", freq1=0.1, freq2=0.4, order=5)

# 带阻滤波（衰减 0.1-0.4 的频率）
bsf = DigitalFilter(filter_type="bandstop", freq1=0.1, freq2=0.4, order=5)
```

---

### 3. Decimation - 轨迹降采样

**作用**: 通过固定间隔采样减少数据点数，降低采样率。

**API 定义**:
```python
Decimation(
    config: dict[str, Any] | None = None,
    dec_factor: int = 2  # 降采样因子，每隔 N 个点保留 1 个
)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `dec_factor` | 2 | 降采样因子，每隔 N 个点保留 1 个 |

**调用示例**:
```python
from squirrel.preprocessing import Decimation

# 降采样因子=4
decimator = Decimation(dec_factor=4)
result = decimator.analyze(traces)
decimated = result.metadata["decimated_traces"]

print(f"原始形状: {traces.shape}")      # (100, 2000)
print(f"降采样后: {decimated.shape}")   # (100, 500)
```

---

### 4. Resync_Peak - 峰值检测轨迹对齐

**作用**: 通过检测每条轨迹中的峰值（最大值/最小值）并与参考轨迹对齐来同步轨迹。

**API 定义**:
```python
ResyncPeakDetector(
    config: dict | None = None,
    ref_trace_idx: int = 0,              # 参考轨迹索引
    peak_type: str = "max",              # "max" | "min"
    peak_range: tuple[int, int] = (0, 0), # 搜索范围，为(0,0)时使用完整轨迹
    valid_limit: float = 0.0             # 幅度容差，0=跳过验证
)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ref_trace_idx` | 0 | 参考轨迹索引 |
| `peak_type` | "max" | "max" 或 "min" 峰值类型 |
| `peak_range` | (0, 0) | (起始, 结束) 搜索范围，为(0,0)时使用完整轨迹 |
| `valid_limit` | 0.0 | 幅度容差（0=跳过验证） |

**调用示例**:
```python
from squirrel.preprocessing import ResyncPeakDetector

# 默认配置（查找最大值）
aligner = ResyncPeakDetector()

# 自定义配置
aligner = ResyncPeakDetector(
    ref_trace_idx=0,
    peak_type="max",
    peak_range=(100, 500),  # 在样本100-500范围内搜索
    valid_limit=0.2          # 接受与参考幅度相差20%以内的峰值
)

# 执行对齐
result = aligner.analyze(traces)
aligned = result.metadata["aligned_traces"]
shifts = result.metadata["shifts"]  # 每条轨迹的平移量
```

---

### 5. Resync_CrossCorr - 互相关轨迹对齐

**作用**: 通过计算测试轨迹与参考窗口的互相关峰值来检测时间偏移并进行对齐。

**API 定义**:
```python
ResyncCrossCorrAligner(
    config: dict | None = None,
    ref_trace_idx: int = 0,              # 参考轨迹索引
    window: tuple[int, int] = (0, 0)     # (起始, 结束) 参考窗口范围
)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ref_trace_idx` | 0 | 参考轨迹索引 |
| `window` | (0, 0) | (起始, 结束) 参考窗口范围，为(0,0)时使用完整轨迹 |

**调用示例**:
```python
from squirrel.preprocessing import ResyncCrossCorrAligner

# 默认配置
aligner = ResyncCrossCorrAligner()

# 自定义配置
aligner = ResyncCrossCorrAligner(
    ref_trace_idx=0,
    window=(500, 1100)  # 使用样本500-1100作为参考窗口
)

# 执行对齐
result = aligner.analyze(traces)
aligned = result.metadata["aligned_traces"]
```

---

### 6. Resync_SAD - 绝对差值和轨迹对齐

**作用**: 在测试轨迹上滑动参考窗口，计算绝对差值和，找到 SAD 最小的位置作为最优对齐。

**API 定义**:
```python
SADAligner(
    config: dict[str, Any] | None = None,
    ref_trace_idx: int = 0,              # 参考轨迹索引
    target_window: tuple[int, int] = (0, 0), # 参考窗口范围，为(0,0)时使用前100个样本
    max_shift: int = 50                  # 向两侧搜索的最大平移量
)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ref_trace_idx` | 0 | 参考轨迹索引 |
| `target_window` | (0, 0) | (起始, 结束) 参考窗口范围，为(0,0)时使用前100个样本 |
| `max_shift` | 50 | 向两侧搜索的最大平移量 |

**调用示例**:
```python
from squirrel.preprocessing import SADAligner

# 默认配置
aligner = SADAligner()

# 自定义配置
aligner = SADAligner(
    ref_trace_idx=0,
    target_window=(100, 200),  # 使用样本100-200作为参考
    max_shift=50
)

# 执行对齐
result = aligner.analyze(traces)
aligned = result.metadata["aligned_traces"]
shifts = result.metadata["shifts"]  # 每条轨迹的平移量
```

---

### 7. Resync_DTW - 动态时间规整轨迹对齐

**作用**: 使用 FastDTW 算法通过动态规划找到两条轨迹间的最优对应关系，允许非线性形变对齐。

**API 定义**:
```python
DTWAligner(config: dict[str, Any] | None = None)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `radius` | 3 | FastDTW 搜索半径 |
| `ref_trace_idx` | 0 | 参考轨迹索引 |

**调用示例**:
```python
from squirrel.preprocessing import DTWAligner

# 默认配置
aligner = DTWAligner()

# 自定义配置
aligner = DTWAligner(config={
    "radius": 5,
    "ref_trace_idx": 0
})

# 执行对齐
aligned = aligner.align(traces)
# 或
result = aligner.analyze(traces)
aligned = result["aligned_traces"]
```

---

### 8. Resync_ZC - 零交叉轨迹对齐

**作用**: 通过检测零交叉点（信号从负穿过阈值电平到正）进行轨迹对齐。

**API 定义**:
```python
ResyncZCAligner(
    config: dict | None = None,
    ref_trace_idx: int = 0,
    zc_level: float = 0.0,
    bin_length: int = 0
)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `ref_trace_idx` | 0 | 参考轨迹索引 |
| `zc_level` | 0.0 | 零交叉检测的阈值电平 |
| `bin_length` | 0 | 目标区间长度，0=shift-based对齐，>0=resampling对齐（输出长度可变） |

**调用示例**:
```python
from squirrel.preprocessing import ResyncZCAligner

# 默认配置（shift-based对齐，输出长度不变）
aligner = ResyncZCAligner()

# Resampling模式（每段重采样到bin_length，输出长度可变）
aligner = ResyncZCAligner(
    ref_trace_idx=0,
    zc_level=0.0,
    bin_length=50
)

# 执行对齐
result = aligner.analyze(traces)
aligned = result.metadata["aligned_traces"]
```

---

### 9. Resync_Comparison - 轨迹对齐方法对比

**作用**: 对五种轨迹对齐方法（Peak、CrossCorr、SAD、DTW、ZC）进行综合对比，提供选择指南。

**曲线类型匹配表**:

| 方法 | 最适合的曲线类型 | 不适合的曲线类型 | 核心判断依据 |
|------|-----------------|-----------------|-------------|
| **Peak** | 峰很清楚、重复周期明显、每个周期有稳定主峰的曲线 | 峰不明显、噪声峰很多、一个周期内有多个相似峰 | 找最大峰或关键峰的位置 |
| **CrossCorr** | 整体形状相似、只有平移偏移的曲线 | 局部变形明显、周期内结构变化大、幅值漂移严重 | 找两段波形整体相似度最高的位置 |
| **SAD** | 有稳定模板、形状固定、幅值也比较一致的曲线 | 幅值变化大、局部拉伸压缩、噪声较强 | 找与模板差值最小的位置 |
| **DTW** | 形状相似但局部时间被拉伸/压缩的复杂波形 | 只需要简单平移对齐的大数据波形 | 允许局部非线性伸缩后匹配 |
| **ZC** | 方波、脉冲、边缘陡峭、过零点稳定的曲线 | 平滑峰、没有明显过零点、噪声导致频繁过零 | 根据零交叉点或边缘位置重新对齐 |

---

## Analysis（分析模块）

### 10. TVLA - 测试向量泄漏评估

**作用**: 使用 Welch's t 检验比较固定轨迹与随机轨迹的统计差异，检测侧信道泄漏。

**API 定义**:
```python
TVLAAnalyzer(config: dict[str, Any] | None = None)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `threshold` | 4.5 | t 值泄漏检测阈值（|t| > threshold 认为泄漏） |

**调用示例**:
```python
from squirrel.analysis import TVLAAnalyzer

# 创建分析器
analyzer = TVLAAnalyzer(config={"threshold": 4.5})

# 在zarr数据集上运行分析
result = analyzer.analyze("/path/to/tvla_data.zarr")

# 检查结果
print(f"T检验范围: [{result.ttest_min:.2f}, {result.ttest_max:.2f}]")
print(f"泄漏点数量: {result.total_leakage_points}")

if result.first_leakage_point:
    print(f"首个泄漏在样本 {result.first_leakage_point}")

# 获取所有泄漏点索引
leakage_idx = analyzer.detect_leakage_points(result)
```

---

### 11. Correlation - 明密文相关性泄漏定位

**作用**: 计算轨迹与明文、密文、密钥或扩展数据汉明重量之间的皮尔逊相关性，用于定位侧信道泄漏采样点。

**API 定义**:
```python
CorrelationAnalyzer(config: dict[str, Any] | None = None)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `data_type` | "plaintext" | 相关性输入数据类型："plaintext"、"ciphertext"、"key" 或 "extended" |
| `data_width` | 1 | 数据合并宽度，单位为字节；支持 1/2/4/8 字节映射到 8/16/32/64 bit HW |
| `sample_range` | (0, None) | 要分析的采样区间 |
| `correlation_threshold` | 0.5 | 泄漏检测阈值，使用相关系数绝对值判断 |

**调用示例**:
```python
from squirrel.analysis.correlation import CorrelationAnalyzer

# 明文汉明重量与轨迹相关性
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
print(f"Byte: {result.max_correlation_byte}, Sample: {result.max_correlation_sample}")
print(f"Leakage points: {len(result.leakage_points)}")

# 获取超过阈值的泄漏点
leakage_idx = analyzer.detect_leakage_points(result, threshold=0.3)
```

**测试命令**:
```bash
make correlation
make test-correlation
```

---

### 12. CPA - 相关功耗分析攻击

**作用**: 通过计算功耗假设（汉明重量）与实际轨迹的相关性，恢复 AES 密钥。

**API 定义**:
```python
CPAAnalyzer(config: dict[str, Any] | None = None)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `leakage_model` | "sbox_output" | 泄漏模型："sbox_output" 或 "pt_key_xor" |
| `num_subkeys` | 16 | 要分析的子密钥字节数（1-16） |

**调用示例**:
```python
from squirrel.analysis import CPAAnalyzer

# 创建分析器
analyzer = CPAAnalyzer(config={
    "leakage_model": "sbox_output",
    "num_subkeys": 16
})

# 运行CPA分析
result = analyzer.analyze(traces, plaintext=plaintext)

# 输出结果
print(f"猜测密钥: {[hex(b) for b in result.key_guess]}")
print(f"PGE: {result.pge}")
```

---

### 13. MixColumns CPA - AES MixColumns 输出相关性攻击

**作用**: 针对 AES MixColumns 操作的汉明距离泄漏模型，利用列混合变换后字节之间的相关性恢复密钥。

**API 定义**:
```python
MixColumnsCPAAnalyzer(config: dict[str, Any] | None = None)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `vec_type` | "column" | 攻击向量类型："column" 或 "row" |
| `hamming_distance` | True | 是否使用汉明距离模型 |

**调用示例**:
```python
from squirrel.analysis import MixColumnsCPAAnalyzer

# 创建分析器
analyzer = MixColumnsCPAAnalyzer(config={
    "vec_type": "column",
    "hamming_distance": True
})

# 运行分析
result = analyzer.analyze(traces, plaintext=plaintext)

# 输出结果
print(f"猜测密钥: {[hex(b) for b in result.key_guess]}")
print(f"PGE = 0 数量: {sum(1 for p in result.pge if p == 0)}/16")
```

---

### 14. SNR - 信噪比分析

**作用**: 通过分组方差比计算 SNR，量化侧信道轨迹中泄漏信号与噪声的比率。

**API 定义**:
```python
SNRAnalyzer(config: dict[str, Any] | None = None)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `leakage_model` | "HW" | 泄漏模型，当前仅支持 "HW" |

**调用示例**:
```python
from squirrel.analysis import SNRAnalyzer

# 创建分析器
analyzer = SNRAnalyzer()

# 运行分析
result = analyzer.analyze(traces, plaintext=plaintext)

# 输出结果
print(f"Peak SNR: {result.peak_snr_db:.2f} dB at sample {result.peak_sample}")
print(f"Leakage groups: {result.num_leakage_groups}")
```

---

### 15. Channel Estimate - 线性回归侧信道攻击

**作用**: 通过线性回归估计功耗"信道"，用 SSE 排序恢复 AES 密钥。

**API 定义**:
```python
ChannelEstimateAnalyzer(config: dict[str, Any] | None = None)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `num_subkeys` | 16 | 要分析的子密钥字节数（1-16） |
| `fit_ratio` | 0.8 | 轨迹分割比例（用于 fitting） |
| `use_svd` | True | 使用 SVD 伪逆加速求解 |
| `leakage_model` | "sbox_output" | 泄漏模型："sbox_output" 或 "pt_key_xor" |

**调用示例**:
```python
from squirrel.analysis import ChannelEstimateAnalyzer

# 创建分析器
analyzer = ChannelEstimateAnalyzer(config={
    "num_subkeys": 16,
    "fit_ratio": 0.8,
    "leakage_model": "sbox_output"
})

# 运行攻击
result = analyzer.analyze(traces, plaintext=plaintext)

# 输出结果
print(f"猜测密钥: {[hex(b) for b in result.key_guess]}")
print(f"PGE: {result.pge}")
```

---

### 16. MIA - 互信息分析攻击

**作用**: 衡量密钥相关泄漏假设与轨迹观测值的互信息，以恢复 AES 子密钥。

**API 定义**:
```python
MIAAnalyzer(config: dict[str, Any] | None = None)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `leakage_model` | `"hamming_weight"` | `"hamming_weight"` 或 `"sbox_output"` |
| `num_subkeys` | 16 | 分析的子密钥字节数（1–16） |
| `range_start` | 0 | 分析起始采样点 |
| `range_end` | None | 分析结束采样点，None 表示轨迹末尾 |

**调用示例**:
```python
from squirrel.analysis import MIAAnalyzer

analyzer = MIAAnalyzer(config={"num_subkeys": 1, "range_start": 100, "range_end": 200})
result = analyzer.analyze(traces, plaintext=plaintext)
print(result.key_guess)
print(result.best_guesses)
```

输入 `traces` 为 `(num_traces, num_samples)`，`plaintext` 为 `(num_traces, 16)`。运行 MIA 还需要安装 `pyitlib`。详见 [MIA 数据手册](datasheet/analysis-mia.md)。

---

### 17. DPA - 差分功耗分析攻击

**作用**: 按 AES 中间值的汉明重量阈值分组，利用两组轨迹均值差恢复密钥。

**API 定义**:
```python
DPAAnalyzer(config: dict[str, Any] | None = None)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `threshold` | 4.0 | 汉明重量分组阈值 |
| `byte_pos` | 0–15 | 要攻击的字节位置列表 |
| `direction` | `"enc"` | `"enc"` 或 `"dec"` |
| `sample_start`, `sample_end` | 0, None | 采样区间 |
| `multiple_thresholds` | None | 可选的多阈值列表 |

**调用示例**:
```python
from squirrel.analysis import DPAAnalyzer

analyzer = DPAAnalyzer(config={"threshold": 4.0, "byte_pos": [0]})
result = analyzer.analyze(traces, plaintext=plaintext, output_dir="./dpa_results")
print(result.best_keys)
print(result.top_candidates)
```

输入可为轨迹数组或符合项目布局的 Zarr 路径；当前实现会在 `output_dir` 中生成曲线文件。详见 [DPA 数据手册](datasheet/analysis-dpa.md)。

---

### 18. Template Attack - 多变量高斯模板攻击

**作用**: 用已知密钥的建模轨迹建立模板，再用攻击轨迹恢复密钥。

**API 定义**:
```python
TemplateAnalyzer(config: dict[str, Any] | None = None)
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `num_pois` | 5 | 每个字节选取的兴趣点数 |
| `poi_spacing` | 5 | 兴趣点间最小间隔 |
| `byte_pos` | 0–15 | 要攻击的字节位置列表 |
| `direction` | `"enc"` | `"enc"` 或 `"dec"` |
| `sample_start`, `sample_end` | 0, None | 采样区间 |

**调用示例**:
```python
from squirrel.analysis import TemplateAnalyzer

analyzer = TemplateAnalyzer(config={"num_pois": 5, "byte_pos": [0]})
result = analyzer.analyze(
    profile_traces=profile_traces,
    attack_traces=attack_traces,
    profile_plaintext=profile_plaintext,
    attack_plaintext=attack_plaintext,
    profile_key=profile_key,
    output_dir="./template_results",
)
print(result.best_keys)
print(result.top_candidates)
```

建模和攻击数据均需轨迹与对应明文；`profile_key` 为建模阶段已知密钥。当前实现会在 `output_dir` 中生成曲线文件。详见 [Template 数据手册](datasheet/analysis-template.md)。

---

## 快速参考表

| 模块 | 一句话总结 | 关键参数 |
|------|-----------|----------|
| **Normalize** | 将轨迹转为零均值/标准方差 | `mode` |
| **DigitalFilter** | Butterworth 频率滤波 | `filter_type`, `freq1`, `freq2`, `order` |
| **Decimation** | 固定间隔降采样 | `dec_factor` |
| **Resync_Peak** | 峰值检测对齐 | `peak_type`, `peak_range` |
| **Resync_CrossCorr** | 互相关峰值对齐 | `window` |
| **Resync_SAD** | 绝对差值和最小化对齐 | `target_window`, `max_shift` |
| **Resync_DTW** | 动态时间规整对齐（允许非线性形变） | `radius` |
| **Resync_ZC** | 零交叉重采样对齐 | `zc_level`, `bin_length` |
| **TVLA** | Welch's t 检验检测侧信道泄漏 | `threshold` |
| **Correlation** | 明密文/密钥 HW 与轨迹相关性泄漏定位 | `data_type`, `data_width`, `correlation_threshold` |
| **CPA** | 相关功耗分析恢复 AES 密钥 | `leakage_model`, `num_subkeys` |
| **MixColumns CPA** | MixColumns 汉明距离相关性攻击 | `vec_type` |
| **SNR** | 信噪比分析泄漏检测 | `leakage_model` |
| **Channel Estimate** | 线性回归信道估计攻击 | `num_subkeys`, `fit_ratio`, `leakage_model` |
| **MIA** | 互信息分析恢复 AES 密钥 | `leakage_model`, `num_subkeys`, `range_start`, `range_end` |
| **DPA** | 阈值分组的均值差攻击 | `threshold`, `byte_pos`, `direction` |
| **Template Attack** | 多变量高斯模板攻击 | `num_pois`, `poi_spacing`, `byte_pos` |
