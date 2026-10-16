# TVLA 测试 - Makefile 使用说明

## 快速开始

```bash
cd /home/wuleler/.config/opencode/skills/squirrel-auto-testbench/verify/tvla-test

make help
```

## 目标详解

| 目标 | 功能 | 输出 |
|------|------|------|
| `make generate` | 生成 TVLA 测试数据 | `traces/tvla_regions.zarr` |
| `make analyze` | 生成 + TVLA 分析 | `result/tvla_report.json` + `result/tvla_plot.png` |
| `make verify` | 验证 TVLA 结果 | 验证报告 |
| `make all` | generate + analyze + verify | 完整流程 |
| `make clean` | 清理输出文件 | - |

## 参数配置

### 基本参数

```bash
make all BASE_SEED=300 NUM_TRACES=2000 NUM_SAMPLES=3000 PROFILE=medium
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `BASE_SEED` | 300 | 随机种子 |
| `NUM_TRACES` | 2000 | 每组轨迹数量 |
| `NUM_SAMPLES` | 3000 | 每条轨迹采样点数 |
| `PROFILE` | medium | 泄露强度预设 |

### 泄露区域配置

```bash
# 指定额外泄露区域数量 (2-6)
make generate NUM_REGIONS=4

# 自定义区域配置 (格式: start,end,amplitude)
make generate NUM_REGIONS=3 REGION_CONFIG='500,700,1.5:1500,1800,2.0'
```

| 参数 | 说明 | 示例 |
|------|------|------|
| `NUM_REGIONS` | 额外泄露区域数量 (2-6) | `NUM_REGIONS=4` |
| `REGION_CONFIG` | 自定义区域配置，多个用冒号分隔 | `'500,700,1.5:1500,1800,2.0'` |

**区域配置格式**: `start,end,amplitude`
- `start`: 起始采样点
- `end`: 结束采样点
- `amplitude`: 泄露强度 (0.6=weak, 1.2=medium, 2.0=strong)

## 使用示例

### 1. 默认配置 (3 个随机区域)

```bash
make generate
# 输出: Region A [200,400] + 3 个随机区域 (B,C,D)
```

### 2. 指定区域数量

```bash
# 2 个额外区域
make generate NUM_REGIONS=2

# 4 个额外区域
make generate NUM_REGIONS=4

# 6 个额外区域
make generate NUM_REGIONS=6
```

### 3. 自定义区域配置

```bash
# 2 个自定义区域
make generate NUM_REGIONS=2 REGION_CONFIG='500,700,1.5'

# 3 个区域 (2 个自定义 + 1 个随机)
make generate NUM_REGIONS=3 REGION_CONFIG='500,700,1.5:1500,1800,2.0'

# 4 个区域 (全部自定义)
make generate NUM_REGIONS=4 REGION_CONFIG='300,400,1.0:800,900,1.5:1400,1600,2.0:2200,2400,1.2'
```

### 4. 完整测试流程

```bash
# 默认配置
make verify

# 自定义配置
make verify NUM_REGIONS=3 REGION_CONFIG='500,700,1.5:1500,1800,2.0'

# 清理后重新测试
make clean && make verify
```

## 输出文件

默认输出到 `sim/preprocessing/TVLA/` 目录：

```
sim/preprocessing/TVLA/
├── traces/
│   ├── tvla_regions.zarr       # 原始轨迹 (含泄露区域)
│   └── tvla_regions.meta.json  # 元数据
├── result/
│   ├── tvla_report.json         # TVLA 报告
│   └── tvla_plot.png            # TVLA 可视化
└── log/
    ├── generate.log
    ├── analyze.log
    └── verify.log
```

## TVLA 原理

TVLA (Test Vector Leakage Assessment) 用于检测侧信道泄露：

1. **固定/随机分组**：Fixed 组使用固定密钥，Random 组使用随机密钥
2. **t-test 计算**：$t = \frac{\mu_{fixed} - \mu_{random}}{\sqrt{\frac{\sigma_{fixed}^2}{n_{fixed}} + \frac{\sigma_{random}^2}{n_{random}}}}$
3. **泄露判断**：|t| > 4.5 则判定为泄露

## 直接使用 Python 脚本

```bash
cd /home/wuleler/.config/opencode/skills/squirrel-auto-testbench/test-data-generator

# 1. 生成基础数据
python3 generate_tvla_dataset.py --output test.zarr --leakage-start 200 --leakage-end 400

# 2. 添加泄露区域
python3 generate_tvla_dataset.py --add-regions test.zarr --num-regions 3

# 3. 添加自定义区域
python3 generate_tvla_dataset.py --add-regions test.zarr --num-regions 3 \
  --region-config 500,700,1.5:1500,1800,2.0
```