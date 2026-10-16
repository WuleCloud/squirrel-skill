# Squirrel Auto Testbench

侧信道分析自动化测试框架，基于 CrackNuts，支持 **TVLA 测试** 和多种 **轨迹预处理算法**。

## 项目结构

```
squirrel-auto-testbench/
├── Makefile                      # 开发任务入口：test/build/clean
├── pyproject.toml                # 主包打包配置
├── AGENTS.md                     # 项目开发辅助说明
│
├── src/squirrel/                 # 【客户可见】核心库
│   ├── __init__.py
│   ├── base.py                   # 基类：Analyzer, AnalysisResult, TraceDataset
│   ├── preprocessing/            # 预处理模块
│   │   ├── Decimation/          # 降采样
│   │   ├── DigitalFilter/        # 数字滤波（Butterworth）
│   │   ├── Normalize/           # 归一化
│   │   ├── Resync_CrossCorr/    # 互相关对齐
│   │   ├── Resync_DTW/          # FastDTW 对齐
│   │   ├── Resync_Peak/         # 峰值检测对齐
│   │   ├── Resync_SAD/          # 绝对差值和对齐
│   │   └── Resync_ZC/           # 零交叉重采样对齐
│   └── analysis/                 # 分析模块
│       ├── tvla/                # TVLA 泄漏检测
│       ├── cpa/                  # CPA 分析
│       ├── mia/                  # MIA 分析
│       ├── dpa/                  # DPA 分析
│       ├── template/            # Template Attack 多变量高斯分析
│       ├── channel_estimate/    # Channel Estimate 线性回归攻击
│       ├── mix_columns/          # MixColumns CPA 分析
│       └── snr/                  # SNR 分析
│
├── tests/                        # 【内部使用】测试基础设施
│   ├── data_generators/          # 合成测试数据生成器
│   └── verify/                   # 验证脚本和回归测试流程
│
├── docs/                         # 详细文档
│   ├── api-index.md             # API 索引
│   ├── datasheet/              # 数据手册
│   └── img/                     # 图片资源
│
└── demo/
    └── jupyter/                  # Jupyter 示例
```

`sim/` 是测试运行时生成的输出目录，不作为源码提交。外部参考项目不再以源码快照放入仓库，后续仅在文档中保留链接引用。

## 支持的模块

### 预处理模块 (Preprocessing)

| 类名 | 算法 | 原理 | 状态 |
|------|------|------|------|
| `Decimation` | 降采样 | 固定间隔采样 | ✅ 完成 |
| `DigitalFilter` | 数字滤波 | Butterworth 滤波器 | ✅ 完成 |
| `Normalize` | 归一化 | 零均值/标准化 | ✅ 完成 |
| `ResyncPeakDetector` | Peak | 峰值检测对齐 | ✅ 完成 |
| `ResyncCrossCorrAligner` | CrossCorr | 互相关对齐 | ✅ 完成 |
| `DTWAligner` | DTW | 动态时间规整 | ✅ 完成 |
| `SADAligner` | SAD | 绝对差值和最小化 | ✅ 完成 |
| `ResyncZCAligner` | ZC | 零交叉重采样 | ✅ 完成 |

### 分析模块 (Analysis)

| 类名 | 算法 | 原理 | 状态 |
|------|------|------|------|
| `TVLAAnalyzer` | TVLA | Welch's t 检验 | ✅ 完成 |
| `CPAAnalyzer` | CPA | 相关性功耗分析 | ✅ 完成 |
| `MIAAnalyzer` | MIA | 互信息分析 | ✅ 完成 |
| `DPAAnalyzer` | DPA | 差分功耗分析（阈值分组） | ✅ 完成 |
| `TemplateAnalyzer` | Template Attack | 多变量高斯模板分析 | ✅ 完成 |
| `ChannelEstimateAnalyzer` | Channel Estimate | 线性回归信道估计 | ✅ 完成 |
| `MixColumnsCPAAnalyzer` | MixColumns CPA | MixColumns 汉明距离攻击 | ✅ 完成 |
| `SNRAnalyzer` | SNR | 信噪比分析 | ✅ 完成 |

## 快速开始

### 运行测试

```bash
make test                    # 运行所有验证流程
make test-tvla               # TVLA 泄漏检测测试
make test-cpa                # CPA 分析测试
make test-mia                # MIA 互信息分析测试
make test-dpa                # DPA 分析测试
make test-template           # Template Attack 多变量高斯分析测试
make test-channel_estimate   # Channel Estimate 攻击测试
make test-mix_columns        # MixColumns CPA 测试
make test-snr                # SNR 分析测试
make test-normalize           # 归一化测试
make test-decimation         # 降采样测试
make test-digital-filter     # 数字滤波测试（低通/高通/带通/带阻）
make test-resync-peak        # 峰值对齐测试
make test-resync-crosscorr   # 互相关对齐测试
make test-resync-dtw         # DTW 对齐测试
make test-resync-sad         # SAD 对齐测试
make test-resync-zc          # 零交叉对齐测试
```

兼容旧命令，例如 `make tvla`、`make decimation` 仍可使用。

### 打包

```bash
make build                   # 生成 wheel 和 sdist
```

### 清理输出

```bash
make clean                   # 清理所有测试输出
make clean-build             # 清理构建产物
make clean-all               # 清理测试输出和构建产物
```

## 方法选择指南

根据波形特征选择合适的方法：

### 轨迹对齐方法

| 波形特征 | 推荐方法 | 说明 |
|---------|---------|------|
| 清晰单峰 | Peak | 简单快速，argmax 精确定位 |
| 双尖峰/多峰 | DTW | 全局最优匹配，不依赖单一特征 |
| 高噪声 + 特征区域 | CrossCorr | 互相关抗噪声能力强 |
| 非线性变形 | DTW | 允许点对点最优对应 |
| 陡峭边缘/方波 | ZC | 过零点检测匹配边缘 |
| 有参考模板 | SAD | 逐点绝对差值最小化 |

### 数字滤波器选择

| 滤波器类型 | 适用场景 | 频率范围 | 测试验证 |
|-----------|---------|---------|---------|
| 低通 (Low) | 去除高频噪声 | 保留 < freq1 | 低频通过，高频衰减 >90% |
| 高通 (High) | 去除直流偏移/低频噪声 | 保留 > freq1 | 低频衰减 >99%，中高频通过 |
| 带通 (Bandpass) | 提取特定频段 | 保留 freq1 ~ freq2 | 通带通过，阻带衰减 >90% |
| 带阻 (Bandstop) | 去除工频干扰等 | 衰减 freq1 ~ freq2 | 阻带衰减 >99%，通带通过 |

测试数据频率分布：low=0.01, mid=0.1, high=0.48

### ZC 零交叉对齐模式

| bin_length | 模式 | 输出长度 | 适用场景 |
|-----------|------|---------|---------|
| 0 | Shift-based | 与输入相同 | 简单平移对齐 |
| >0 | Resampling | bin_length × (ZC点数-1) | 脉冲宽度不统一的方波对齐 |

## API 调用示例

### 分析器

```python
from squirrel.analysis import TVLAAnalyzer

analyzer = TVLAAnalyzer(config={"threshold": 4.5})
result = analyzer.analyze("/path/to/data.zarr")
print(f"T检验范围: [{result.ttest_min:.2f}, {result.ttest_max:.2f}]")
```

### 对齐器

```python
from squirrel.preprocessing import ResyncPeakDetector, ResyncCrossCorrAligner, DTWAligner

# 峰值对齐
aligner = ResyncPeakDetector(config={"peak_type": "max", "ref_trace_idx": 0})
result = aligner.analyze(traces)
aligned = result.metadata["aligned_traces"]

# 互相关对齐
aligner = ResyncCrossCorrAligner(config={"window": (500, 1100)})
result = aligner.analyze(traces)

# DTW 对齐
aligner = DTWAligner(config={"radius": 5})
result = aligner.analyze(traces)

# ZC 零交叉对齐
from squirrel.preprocessing import ResyncZCAligner

# Shift-based 模式（输出长度不变）
aligner = ResyncZCAligner(config={"ref_trace_idx": 0, "zc_level": 0.0, "bin_length": 0})
result = aligner.analyze(traces)

# Resampling 模式（输出长度可变）
aligner = ResyncZCAligner(config={"ref_trace_idx": 0, "zc_level": 0.0, "bin_length": 50})
result = aligner.analyze(traces)
aligned = result.metadata["aligned_traces"]  # 长度 = 50 × (ZC点数-1)
```

## 测试结果解读

### TVLA 测试

| |t| 值 | 解读 |
|---|------------------------|
| < 2 | 无泄漏 |
| 2 - 4 | 边缘 |
| 4 - 6 | 存在泄漏 |
| > 6 | 强泄漏 |

### 对齐算法

| 指标 | 阈值 | 说明 |
|------|------|------|
| 对齐精度 | >80% | 对齐后偏移在 ±5 内的比例 |
| 相关系数改善 | >0.1 | 对齐后与参考轨迹相关性提升 |

### 数字滤波器

| 指标 | 阈值 | 说明 |
|------|------|------|
| 阻带衰减 | >90% | 应被衰减的频率能量减少比例 |
| 通带增益 | <10% | 应被保留的频率能量变化 |

## 详细文档

完整 API 文档位于 `docs/api-index.md`（包含测试结果示例图片）。

各模块详细说明位于 `docs/datasheet/`：
- `preprocessing-decimation.md` - 降采样
- `preprocessing-digital-filter.md` - 数字滤波
- `preprocessing-normalize.md` - 归一化
- `preprocessing-resync-peak.md` - 峰值对齐
- `preprocessing-resync-crosscorr.md` - 互相关对齐
- `preprocessing-resync-dtw.md` - DTW 对齐
- `preprocessing-resync-sad.md` - SAD 对齐
- `preprocessing-resync-zc.md` - 零交叉对齐
- `preprocessing-resync-comparison.md` - 对齐方法对比
- `analysis-tvla.md` - TVLA 分析
- `analysis-cpa.md` - CPA 分析
- `analysis-mia.md` - MIA 分析
- `analysis-dpa.md` - DPA 分析
- `analysis-template.md` - Template Attack 多变量高斯分析
- `analysis-channel-estimate.md` - Channel Estimate 攻击
- `analysis-mix-columns.md` - MixColumns CPA 分析
- `analysis-snr.md` - SNR 分析

测试结果图片位于 `docs/img/`。

## 依赖

使用 `uv` 同步项目依赖：

```bash
uv sync
```
