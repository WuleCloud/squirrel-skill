# DTW 测试 - Makefile 使用说明

## 快速开始

```bash
cd /home/wuleler/.config/opencode/skills/squirrel-auto-testbench/verify/dtw-test

make help
```

## 目标详解

| 目标 | 功能 | 输出 |
|------|------|------|
| `make generate` | 仅生成测试数据 | `traces/dtw_original.zarr` + `traces/dtw_original_shifts.json` |
| `make align` | 读取 traces/ → DTW 对齐 | `result/dtw_aligned.zarr` + `result/dtw_comparison.png` |
| `make verify` | 验证对齐效果 | 验证报告 |
| `make all` | generate + align + verify | 完整流程 |
| `make clean` | 清理输出文件 | - |

## 环境变量

```bash
# 自定义输出目录
make all OUTPUT_DIR=/path/to/traces

# 自定义日志目录
make all LOG_DIR=/path/to/log
```

## 默认参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `BASE_SEED` | 888 | 随机种子 |
| `NUM_TRACES` | 300 | 轨迹数量 |
| `NUM_SAMPLES` | 2000 | 每条轨迹采样点数 |
| `MAX_SHIFT` | 50 | 最大偏移量 |
| `NOISE_STD` | 0.1 | 噪声标准差 |
| `DTW_RADIUS` | 3 | DTW 半径 |

## 输出文件

默认输出到 `sim/preprocessing/DWT/` 目录：

```
sim/preprocessing/DWT/
├── traces/
│   ├── dtw_original.zarr        # 原始轨迹
│   └── dtw_original_shifts.json # 真实偏移值（地面真值）
├── result/
│   ├── dtw_aligned.zarr          # 对齐后轨迹
│   └── dtw_comparison.png        # 对比图
└── log/
    ├── generate.log
    ├── align.log
    └── verify.log
```

## 接口函数

DTW 相关功能已封装为可复用模块：

```python
from verify.dtw_test import align, DTWVerifier

# 对齐
align(input_path, output_path, radius=3, plot_path=None)

# 验证
verifier = DTWVerifier(radius=3)
result = verifier.verify(input_path, aligned_path, shifts_json)
```

## 工作流示例

```bash
# 1. 仅生成数据
make generate

# 2. 生成 + 对齐
make align

# 3. 完整测试流程
make all

# 4. 清理并重新测试
make clean && make all

# 5. 仅运行验证（依赖已生成的轨迹）
make verify
```

## 生成原理

- **基准波形**：固定形状（两个尖峰），seed 决定初始噪声
- **随机偏移**：每条轨迹在 `[-MAX_SHIFT, +MAX_SHIFT]` 范围内随机平移
- **可复现**：相同 seed + 相同参数 → 完全相同的曲线集