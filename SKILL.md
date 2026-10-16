---
name: squirrel-analysis
description: 使用 Squirrel Python 工具箱设计、编写、修改或排查侧信道分析与轨迹预处理脚本。适用于 TVLA、CPA、DPA、MIA、模板攻击、相关性、SNR、信道估计、MixColumns CPA，以及滤波、归一化、降采样和轨迹对齐任务。
---

# Squirrel 分析脚本

为用户交付可运行的 Python 脚本，而不只是 API 片段。先根据任务选择方法，只读取对应链接中的文档；不要一次加载所有方法文档。

## 工作流

1. 明确输入数据的位置、数组含义和形状，以及用户期望的分析目标与输出。缺少非关键参数时采用文档默认值，并在脚本中集中配置。
2. 从下面的路由表选择方法，完整读取对应 datasheet。需要组合流程时，只读取涉及的方法文档；对齐方法尚未确定时先读对比文档。
3. 依据文档确认公开类、构造参数、`analyze()` 输入和结果字段。需要完整调用流程时，只读取对应的包内参考示例。若文档与用户安装的 Squirrel 版本不一致，再用 Python 签名检查或查看已安装包源码；以用户环境的当前公开 API 为准，并告知用户差异。
4. 编写端到端脚本：导入数据、校验维度/样本数、预处理、分析、保存数值结果，并按需要绘图。不要调用尚未实现的 `Analyzer.load_traces()`；根据用户文件格式显式使用 NumPy、Zarr 或相应库读取。
5. 优先从 `squirrel.analysis` 或 `squirrel.preprocessing` 的公共 API 导入，不使用测试目录或模块内部实现作为生产依赖。
6. 用用户项目的 Python 环境做最小运行验证；原 Squirrel 仓库环境可使用 `uv run --no-editable python <script>`。没有真实数据时，至少做导入/编译检查，或使用小型合成数组验证形状。不要擅自运行完整、耗时的攻击流程。

## 分析方法路由

- 泄漏存在性、固定组与随机组 Welch t 检验：读取 [TVLA](references/docs/datasheet/analysis-tvla.md)；需要流程参考时读取 [TVLA 示例](references/examples/tvla/verifier.py)。
- AES 字节密钥恢复、汉明重量/距离模型：读取 [CPA](references/docs/datasheet/analysis-cpa.md)；需要流程参考时读取 [CPA 示例](references/examples/cpa_test/analyzer.py)。
- 按选择函数分组并比较均值差：读取 [DPA](references/docs/datasheet/analysis-dpa.md)；需要流程参考时读取 [DPA 示例](references/examples/dpa/analyzer.py)。
- 用互信息评估密钥猜测：读取 [MIA](references/docs/datasheet/analysis-mia.md)；需要流程参考时读取 [MIA 示例](references/examples/mia/analyzer.py)。
- 建模集与攻击集、多变量高斯模板：读取 [Template Attack](references/docs/datasheet/analysis-template.md)；需要流程参考时读取 [Template 示例](references/examples/template/analyzer.py)。
- 明文/密文与轨迹的直接相关性和泄漏定位：读取 [Correlation](references/docs/datasheet/analysis-correlation.md)；需要流程参考时读取 [Correlation 示例](references/examples/correlation/analyzer.py)。
- 按中间值类别评估信号与噪声：读取 [SNR](references/docs/datasheet/analysis-snr.md)；需要流程参考时读取 [SNR 示例](references/examples/snr/analyzer.py)。
- 线性回归或信道系数估计攻击：读取 [Channel Estimate](references/docs/datasheet/analysis-channel-estimate.md)；需要流程参考时读取 [Channel Estimate 示例](references/examples/channel_estimate/analyzer.py)。
- 针对 AES MixColumns 输出或汉明距离：读取 [MixColumns CPA](references/docs/datasheet/analysis-mix-columns.md)；需要流程参考时读取 [MixColumns 示例](references/examples/mix_columns/analyzer.py)。

## 预处理方法路由

- 不确定如何处理时：先读 [轨迹对齐方法对比](references/docs/datasheet/preprocessing-resync-comparison.md)。
- 零均值或标准化：读取 [Normalize](references/docs/datasheet/preprocessing-normalize.md)；示例见 [Normalize](references/examples/normalize/align.py)。
- 低通、高通、带通或带阻滤波：读取 [DigitalFilter](references/docs/datasheet/preprocessing-digital-filter.md)；示例见 [DigitalFilter](references/examples/digital_filter/align.py)。
- 固定比例降采样：读取 [Decimation](references/docs/datasheet/preprocessing-decimation.md)；示例见 [Decimation](references/examples/decimation/align.py)。
- 清晰峰值定位：读取 [Peak](references/docs/datasheet/preprocessing-resync-peak.md)；示例见 [Peak](references/examples/resync_peak/align.py)。
- 特征窗口互相关：读取 [Cross-correlation](references/docs/datasheet/preprocessing-resync-crosscorr.md)；示例见 [Cross-correlation](references/examples/resync_crosscorr/align.py)。
- 非线性时间扭曲：读取 [DTW](references/docs/datasheet/preprocessing-resync-dtw.md)；示例见 [DTW](references/examples/resync_dtw/align.py)。
- 参考窗口绝对差：读取 [SAD](references/docs/datasheet/preprocessing-resync-sad.md)；示例见 [SAD](references/examples/resync_sad/align.py)。
- 周期边沿或零交叉重采样：读取 [Zero Crossing](references/docs/datasheet/preprocessing-resync-zc.md)；示例见 [Zero Crossing](references/examples/resync_zc/align.py)。

## 共同约束

- 轨迹通常为二维数组 `(num_traces, num_samples)`；明文、密文、标签和密钥材料的第一维必须与轨迹数匹配。根据所选 datasheet 检查更具体的形状和 dtype。
- 不臆造结果字段。只使用所选方法文档或当前实现中声明的结果属性与 `metadata` 键。
- 包内示例来自 Squirrel 验证流程，主要用于理解数据读取、调用和结果处理；它们可能包含原仓库路径或测试数据约定。生成用户脚本时应移除这些测试耦合，不要直接导入 `references/examples/`。
- 构造函数是否接收独立关键字参数或 `config={...}` 必须以当前签名为准；仓库不同文档可能展示不同风格。
- 随机流程设置固定 seed。大数组避免不必要复制；绘图和结果目录由脚本参数控制，不硬编码用户机器路径。
- 输出至少包括关键数值结果和可复用文件（如 `.npz`/`.npy`/`.csv`）；仅在用户需要时增加图形。对密钥恢复任务，报告猜测值、分数/秩和对应字节，不把测试数据中的已知密钥写死。

完整模块总览只在需要跨方法查询时读取 [API 索引](references/docs/api-index.md)。项目安装、环境和通用示例见 [使用说明](references/usage.md)。
