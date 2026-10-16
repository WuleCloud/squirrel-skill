# MixColumns CPA - AES MixColumns 输出相关性攻击

## 测试结果

**MixColumns CPA Correlation vs Time 曲线：**


| 指标 | 测试结果 |
|------|----------|
| **Key correct** | True |
| **PGE = 0** | 16/16 bytes |
| **Success rate** | 100.0% |
| **PGE total** | 0 |
| **Avg PGE** | 0.00 |
| **Max PGE** | 0 |
| **通过验证** | ✓ PASS |

## 1. 算法原理

### 1.1 核心概念

MixColumns CPA 攻击针对 AES 加密中 MixColumns 操作的输出，利用列混合变换后字节之间的相关性来恢复密钥字节。与标准 CPA 攻击不同，MixColumns 攻击利用的是多字节之间的线性关系。

**攻击背景**：参见 https://eprint.iacr.org/2016/249.pdf

### 1.2 MixColumns 变换

AES MixColumns 对状态的每一列（4 字节）进行以下线性变换：

```
[02 03 01 01]   [s0]
[01 02 03 01] × [s1]
[01 01 02 03]   [s2]
[03 01 01 02]   [s3]
```

在伽罗瓦域 GF(2^8) 上：
- 输出字节 0：`GAL2[s0] ⊕ GAL3[s1] ⊕ s2 ⊕ s3`
- 输出字节 1：`s0 ⊕ GAL2[s1] ⊕ GAL3[s2] ⊕ s3`
- 输出字节 2：`s0 ⊕ s1 ⊕ GAL2[s2] ⊕ GAL3[s3]`
- 输出字节 3：`GAL3[s0] ⊕ s1 ⊕ s2 ⊕ GAL2[s3]`

其中 `GAL2[x] = 2·x`，`GAL3[x] = 3·x`（GF(2^8) 乘法）。

### 1.3 泄漏模型

参考 ChipWhisperer MixColumns 攻击实现，泄漏模型为**汉明距离**：

$$L = HD(GAL[S[PT \oplus K]], PT) = HW(GAL[S[PT \oplus K]] \oplus PT)$$

即 S-Box 输出的伽罗瓦变换结果与明文字节之间的汉明距离。对于 campaign 0（column 0），使用 GAL2 变换：

```
result_byte[k] = GAL2[S[PT[k] ⊕ K[k]]] ⊕ PT[k]   (k = 0..3)
HD = HW(result_byte[0]) + HW(result_byte[1]) + HW(result_byte[2]) + HW(result_byte[3])
```

### 1.4 攻击策略

攻击将 16 字节分成 4 个 campaign，每个 campaign 处理一列（4 字节）：

| Campaign | 攻击字节 | 使用的 GAL 变换 |
|----------|---------|--------------|
| 0 | 字节 0, 1, 2, 3 | GAL2 |
| 1 | 字节 4, 5, 6, 7 | GAL3 |
| 2 | 字节 8, 9, 10, 11 | GAL1（恒等变换） |
| 3 | 字节 12, 13, 14, 15 | GAL1 |

每个字节运行 8 次单比特 CPA（bit 0-7），将绝对值相加以获得总相关性。

## 2. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── MixColumnsCPAAnalyzer
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `MixColumnsCPAAnalyzer` | mix_columns/mix_columns.py | 主分析器类 |
| `MixColumnsResult` | mix_columns/mix_columns.py | 分析结果数据类 |

### 继承结构图

```
Analyzer (squirrel.base)
    │
    └── MixColumnsCPAAnalyzer
            ├── name = "mix_columns_cpa"
            ├── description = "CPA attack on AES MixColumns output using Monobit leakage models"
            │
            ├── __init__(config: dict | None)
            │       ├── vec_type: str = "column"
            │       └── hamming_distance: bool = True
            │
            ├── analyze(traces, plaintext, key=None, **kwargs) -> MixColumnsResult
            │
            ├── _run_campaign_cpa(traces, plaintext, campaign) -> list[np.ndarray]
            │       └── 对单个 campaign（4 字节）运行 CPA
            │
            ├── _compute_bit_correlation(traces, plaintext, target_byte, lut_in, lut_out, gal_idx, bit) -> np.ndarray
            │       └── 核心：计算特定 bit 位置的 Pearson 相关性
            │
            ├── _get_byte_range(campaign) -> list[int]
            ├── _combine_correlations(all_campaign_correlations) -> list[np.ndarray]
            └── detect_leakage_points(result, threshold=None) -> np.ndarray
```

## 3. API 接口说明

### 构造函数

```python
MixColumnsCPAAnalyzer(config: dict[str, Any] | None = None)
```

**配置参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `vec_type` | "column" | 攻击向量类型："column" 或 "row" |
| `hamming_distance` | True | 是否使用汉明距离模型 |

### 主要方法

#### `analyze(traces, plaintext, key=None, **kwargs) -> MixColumnsResult`

运行 MixColumns CPA 分析。

```python
analyzer = MixColumnsCPAAnalyzer(config={
    "threshold": 0.5,
    "vec_type": "column",
})
result = analyzer.analyze(traces, plaintext=plaintext, key=known_key)
print(f"Key guess: {[hex(b) for b in result.key_guess]}")
print(f"PGE: {result.pge}")
```

### MixColumnsResult 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `method` | str | "mix_columns_cpa" |
| `num_subkeys` | int | 子密钥数量（16） |
| `num_campaigns` | int | Campaign 数量（4） |
| `threshold` | float | 使用的检测阈值 |
| `num_traces` | int | 使用的轨迹数量 |
| `total_samples` | int | 每条轨迹的样本数 |
| `best_guesses` | list[dict] | 每个字节的最佳猜测详情 |
| `key_guess` | list[int] | 猜测的完整密钥（16 字节） |
| `correlations` | list[np.ndarray] | 每个字节的 256×num_samples 相关系数矩阵 |
| `pge` | list[int] | 每个子密钥的排序误差 |
| `metadata` | dict | 附加元数据（vec_type, hamming_distance） |

## 4. 测试数据生成

### 数据生成器

```bash
python -m tests.data_generators.cli mix_columns \
    --output /path/to/output.zarr \
    --num-traces 500 \
    --num-samples 1000 \
    --noise-std 0.5 \
    --seed 42
```

**泄漏模型**：对每个 column，生成对应的汉明距离泄漏：

- Column 0（campaign 0）：`HW(GAL2[S[PT[k] ⊕ key[k]]] ⊕ PT[k])`，k=0..3
- Column 1（campaign 1）：`HW(GAL3[S[PT[k] ⊕ key[k]]] ⊕ PT[k])`，k=4..7
- Column 2（campaign 2）：`HW(S[PT[k] ⊕ key[k]] ⊕ PT[k])`，k=8..11
- Column 3（campaign 3）：`HW(S[PT[k] ⊕ key[k]] ⊕ PT[k])`，k=12..15

每个 column 的泄漏信号使用不同峰值位置的高斯脉冲叠加。

### 测试命令

```bash
make mix_columns              # 完整流程：生成 → 分析 → 验证
make test-mix_columns        # 仅运行测试
```

### 验证结果

| 指标 | 期望值 |
|------|--------|
| PGE = 0 字节数 | 16/16 |
| Success rate | 100% |
| Key correct | True |

## 5. 结果解读指南

### 5.1 PGE 解读

| PGE | 解读 |
|-----|------|
| 0 | 正确密钥排名第一 ✓ |
| 1-10 | 攻击成功，正确密钥排名前 10 |
| > 10 | 攻击效果差 |

### 5.2 相关性强度

由于 MixColumns 攻击涉及多字节汉明距离，相关性通常比标准 CPA 弱：

| |r| 值 | 解读 |
|---|------------------|
| > 0.5 | 强泄漏，攻击稳定 |
| 0.2 - 0.5 | 中等泄漏，500 轨迹可成功 |
| < 0.2 | 弱泄漏，需要更多轨迹或更低噪声 |

### 5.3 Campaign 结构

正确的 key guess 应在每个 campaign 的 4 个字节中均排名第一：

```
Campaign 0: Byte 0, 1, 2, 3  ← GAL2 变换
Campaign 1: Byte 4, 5, 6, 7  ← GAL3 变换
Campaign 2: Byte 8, 9, 10, 11 ← GAL1 变换
Campaign 3: Byte 12, 13, 14, 15 ← GAL1 变换
```

## 6. 局限性

### 6.1 数据模型要求

- **泄漏模型必须匹配**：数据生成器的泄漏模型必须与攻击期望的泄漏模型一致（`HD(GAL[S[PT⊕K]], PT)`）
- **轨迹对齐**：与标准 CPA 一样，需要良好对齐的轨迹
- **噪声水平**：噪声 std 过高会降低相关性

### 6.2 攻击局限性

- **多字节联合分析**：当前实现对每个 campaign 的 4 个字节分别攻击，未利用字节间相关性
- **抗对策敏感性**：掩码和随机延迟会显著降低攻击效果
- **数据量需求**：通常需要 500+ 轨迹才能稳定恢复密钥

## 7. 核心算法细节

### 7.1 Pearson 相关性计算

对每个 bit 位置 i（0-7）和每个 key guess g（0-255）：

```
intermediate = GAL[gal][S[PT[b] ⊕ g]] ⊕ PT[b]
bit_value = (intermediate >> (7 - i)) & 1

correlation[g, sample] = |Pearson(bit_value, traces[:, sample])|
```

总相关性 = Σ(bit 0..7 的 |correlation|)

### 7.2 LUT 查表

```python
_LUT_INPUT_COL = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11], [12, 13, 14, 15]]
_LUT_MIX_COLUMN_COL[campaign]  # 每个 campaign 的 MixColumns LUT
_GAL_LUT = [_GAL2, _GAL3, _GAL1, _GAL1]  # 伽罗瓦域乘法表
```

### 7.3 中间值公式

对于 campaign 0（GAL2）的第 k 个目标字节（k=0..3）：

```
sbox_out = S[PT[target_byte] ⊕ key_guess]
mc_result[k] = GAL2[sbox_out] ⊕ PT[k]   # k=0 时
mc_result[k] = PT[k]                     # k=1,2,3 时（参考实现公式）
HD = HW(mc_result[0]) + HW(mc_result[1]) + HW(mc_result[2]) + HW(mc_result[3])
```

## 8. 参考

- https://eprint.iacr.org/2016/249.pdf - MixColumns CPA 攻击原始论文
- ChipWhisperer `attack_mix_columns.py` - 参考实现
