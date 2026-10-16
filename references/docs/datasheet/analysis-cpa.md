# CPA - 相关功耗分析攻击

## 测试结果

**CPA Correlation vs Time 曲线：**


| 指标 | 测试结果 |
|------|----------|
| **Key correct** | True |
| **PGE total** | 0 |
| **Avg PGE** | 0.00 |
| **Max PGE** | 0 |
| **通过验证** | ✓ PASS |

## 1. 算法原理

### 1.1 核心概念

CPA（Correlation Power Analysis，相关功耗分析）是一种高效的侧信道攻击方法，通过计算密码学实现中间值的汉明重量（Hamming Weight）与实际功耗轨迹之间的相关性来恢复密钥。

**核心假设**：设备在处理不同数据时消耗的功率与该数据的汉明重量成正比。

### 1.2 AES S-Box 泄漏模型

AES 第一轮加密中，S-Box 输出是常见的泄漏点：

```
明文 P → [AddRoundKey] → S-Box[P ⊕ K] → 输出
```

其中 $K$ 是密钥字节，$P$ 是明文字节。攻击者已知 $P$，尝试所有 $256$ 个可能的 $K$ 值，计算汉明重量 $HW[S-Box[P ⊕ K]]$。

### 1.3 数学公式

**皮尔逊相关系数：**

给定：
- 轨迹样本：$T = (t_1, t_2, ..., t_n)$，第 $i$ 条轨迹在所有时间点的功耗值
- 功耗假设：$H = (h_1, h_2, ..., h_n)$，基于泄漏模型计算的汉明重量

**相关系数：**

$$r = \frac{n \sum_{i=1}^{n} t_i h_i - \sum_{i=1}^{n} t_i \sum_{i=1}^{n} h_i}{\sqrt{\left(n \sum_{i=1}^{n} t_i^2 - \left(\sum_{i=1}^{n} t_i\right)^2\right) \left(n \sum_{i=1}^{n} h_i^2 - \left(\sum_{i=1}^{n} h_i\right)^2\right)}}$$

**逐步计算优化：**

为避免重复计算，采用增量更新：

$$\sum t_i h_i^{new} = \sum t_i h_i^{old} + \sum_{j=1}^{m} T_j \cdot H_j$$

其中 $m$ 为新添加的轨迹数量。

### 1.4 密钥排序（PGE）

对于每个子密钥字节，根据相关系数对 $256$ 个密钥猜测排序：

$$PGE = \text{正确密钥在排序中的位置}$$

- $PGE = 0$：正确密钥排名最高
- $PGE = 255$：正确密钥排名最后

## 2. 支持的泄漏模型

CPA 分析器支持 **11 种泄漏模型**，涵盖 AES 加密不同阶段的功耗特征：

| 模型名称 | 类型 | 说明 |
|----------|------|------|
| `sbox_output` | HW | AES S-Box 输出（第一轮加密） |
| `pt_key_xor` | HW | 明文与密钥 XOR 输出 |
| `inv_sbox_output` | HW | 逆 S-Box 输出（第一轮解密） |
| `lastround_hw` | HW | 最后一轮状态汉明重量 |
| `lastround_state_diff` | HD | 最后一轮状态差异 |
| `lastround_state_diff_alt` | HD | 最后一轮状态差异（变体） |
| `pipeline_diff` | HD | 流水线相邻加密状态差异 |
| `half_pipeline_diff` | HD | 半流水线状态差异 |
| `sbox_in_out_diff` | HD | S-Box 输入到输出差异 |
| `sbox_input_successive` | HD | 相邻字节 S-Box 输入差异 |
| `sbox_output_successive` | HD | 相邻字节 S-Box 输出差异 |

### 2.1 HW 模型（汉明重量）

**原理**：功耗与数据值的汉明重量成正比。

$$Power \propto HW(data)$$

适用于数据直接体现在总线或寄存器状态的场景。

### 2.2 HD 模型（汉明距离）

**原理**：功耗与状态变化位数成正比。

$$Power \propto HD(state_{old}, state_{new})$$

适用于数据通过总线传输或状态变化的场景。

## 3. 泄漏模型详解

### 3.1 sbox_output（默认）

**名称：** HW: AES SBox Output, First Round (Enc)

**类型：** HW（汉明重量）

**计算公式：**

$$HW[SBox[P_i \oplus K_i]]$$

**参数说明：**
- $P_i$：明文字节的第 $i$ 个字节
- $K_i$：密钥字节猜测
- $SBox$：AES 替换盒
- $HW$：汉明重量函数

**物理意义：** AES 第一轮 S-Box 查找操作的输出包含了密钥信息，当数据从 S-Box 输出时，功耗与输出值的汉明重量相关。

**适用场景：** AES 加密硬件/软件实现中 S-Box 操作有显著泄漏的最常见模型。

**测试配置：**
```python
analyzer = CPAAnalyzer(config={"leakage_model": "sbox_output"})
```

---

### 3.2 pt_key_xor

**名称：** HW: AddRoundKey Output, First Round (Enc)

**类型：** HW（汉明重量）

**计算公式：**

$$HW[P_i \oplus K_i]$$

**参数说明：**
- $P_i$：明文字节的第 $i$ 个字节
- $K_i$：密钥字节猜测

**物理意义：** AddRoundKey 操作将明文与密钥 XOR，输出直接反映密钥比特信息。

**适用场景：** 某些硬件实现中 AddRoundKey 操作比 S-Box 操作更明显泄漏。

---

### 3.3 inv_sbox_output

**名称：** HW: AES Inv SBox Output, First Round (Dec)

**类型：** HW（汉明重量）

**计算公式：**

$$HW[InvSBox[P_i \oplus K_i]]$$

**参数说明：**
- $InvSBox$：AES 逆替换盒

**物理意义：** 用于 AES 解密方向的 CPA 攻击，攻击者持有密文时可推断最后一轮密钥。

**适用场景：** AES 解密操作有泄漏的场景，或已知密文的最后一轮攻击。

---

### 3.4 lastround_hw

**名称：** HW: AES Last-Round State

**类型：** HW（汉明重量）

**计算公式：**

$$HW[InvSBox[C_i \oplus K_i]]$$

其中 $C_i$ 是密文字节，$K_i$ 是最后一轮密钥字节猜测。

**物理意义：** 最后一轮（Round 10）解密时，InvSBox 输出在时钟边沿切换时产生功耗泄漏。

**适用场景：** 密文已知时的最后一轮攻击，无需知道完整密钥。

---

### 3.5 lastround_state_diff

**名称：** HD: AES Last-Round State

**类型：** HD（汉明距离）

**计算公式：**

$$HD(st_9, st_{10}) = HW[InvSBox[C_i \oplus K_i] \oplus C_{INVSHIFT\_UNDO[i]}]$$

**参数说明：**
- $st_9$：第 9 轮状态（InvSBox 输出）
- $st_{10}$：第 10 轮状态（密文字节经逆 ShiftRows）
- $INVSHIFT\_UNDO$：逆 ShiftRows 映射

**物理意义：** 最后一轮状态变化的功耗泄漏，HD 模型比 HW 模型更能反映数据变化。

**适用场景：** SASEBO-GII 或 SAKURA-G 等硬件平台。

---

### 3.6 lastround_state_diff_alt

**名称：** HD: AES Last-Round State Alternate

**类型：** HD（汉明距离）

**计算公式：**

$$HD(st_9, st_{10}) = HW[InvSBox[C_i \oplus K_i] \oplus C_i]$$

**与 lastround_state_diff 的区别：** 使用直接密文字节而非逆 ShiftRows 后的字节。

**适用场景：** 与 lastround_state_diff 类似的硬件平台。

---

### 3.7 pipeline_diff

**名称：** HD: AES round 9 between previous and current encryptions

**类型：** HD（汉明距离）

**计算公式：**

$$HD(InvSBox[C_i \oplus K_i], InvSBox[prev\_CT_i \oplus K_i])$$

**物理意义：** 连续两次加密之间，第 9 轮状态的变化产生的功耗泄漏。用于流水线加密场景。

**参数说明：**
- $C_i$：当前密文字节
- $prev\_CT_i$：前一次加密的密文字节

**适用场景：** 流水线架构的 AES 加密硬件。

---

### 3.8 half_pipeline_diff

**名称：** HD: AES previous round 10 and current round 9

**类型：** HD（汉明距离）

**计算公式：**

$$HD(InvSBox[C_i \oplus K_i], prev\_CT_{INVSHIFT\_UNDO[i]})$$

**物理意义：** 当前第 9 轮状态与前一次加密第 10 轮状态之间的差异。

**适用场景：** 半流水线架构的 AES 实现。

---

### 3.9 sbox_in_out_diff

**名称：** HD: AES SBox Input to Output

**类型：** HD（汉明距离）

**计算公式：**

$$HD(SBox\_input, SBox\_output) = HW[(P_i \oplus K_i) \oplus SBox[P_i \oplus K_i]]$$

**物理意义：** S-Box 输入与输出之间的位变化，反映 S-Box 查找操作的数据变化。

**适用场景：** S-Box 操作本身有泄漏的硬件实现。

---

### 3.10 sbox_input_successive

**名称：** HD: AES SBox Input i to i+1

**类型：** HD（汉明距离）

**计算公式：**

$$HD(SBox\_input_i, SBox\_input_{i-1}) = HW[(P_i \oplus K_i) \oplus (P_{i-1} \oplus K_{i-1})]$$

当 $i = 0$ 时，$SBox\_input_{i-1} = 0$。

**物理意义：** 相邻字节的 S-Box 输入之间的差异，用于多字节联合攻击。

**适用场景：** 字节之间有时序相关的功耗泄漏。

---

### 3.11 sbox_output_successive

**名称：** HD: AES SBox Output i to i+1

**类型：** HD（汉明距离）

**计算公式：**

$$HD(SBox\_output_i, SBox\_output_{i-1}) = HW[SBox[P_i \oplus K_i] \oplus SBox[P_{i-1} \oplus K_{i-1}]]$$

当 $i = 0$ 时，$SBox\_output_{i-1} = 0$。

**物理意义：** 相邻字节的 S-Box 输出之间的差异。

**适用场景：** 多字节联合分析场景。

---

## 4. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── CPAAnalyzer (继承自 Analyzer)
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `CPAAnalyzer` | cpa.py | 主分析器类 |
| `CPAResult` | cpa.py | 分析结果数据类 |
| `CPAProgressiveOneSubkey` | cpa.py | 单子密钥逐步CPA计算 |
| `AESLeakageHelper` | cpa.py | 泄漏模型基类 |

### 继承结构图

```
Analyzer (squirrel.base)
    │
    └── CPAAnalyzer
            ├── name = "cpa"
            ├── description = "CPA - Correlation Power Analysis"
            │
            ├── __init__(config: dict | None)
            │       ├── leakage_model: str = "sbox_output"
            │       └── num_subkeys: int = 16
            │
            ├── analyze(traces, labels=None, plaintext, key=None, **kwargs) -> CPAResult
            │       └── 返回包含最佳密钥猜测和相关系数的CPAResult
            │
            ├── detect_leakage_points(result, threshold) -> np.ndarray
            ├── load_traces(path, format="zarr") -> TraceDataset
            └── save_traces(dataset, path, format="zarr") -> Path
```

### 泄漏模型类

```
AESLeakageHelper (基类)
    │
    ├── SBoxOutput
    │       └── name = "HW: AES SBox Output, First Round (Enc)"
    │
    ├── PtKeyXOR
    │       └── name = "HW: AddRoundKey Output, First Round (Enc)"
    │
    ├── InvSBoxOutput
    │       └── name = "HW: AES Inv SBox Output, First Round (Dec)"
    │
    ├── LastroundHW
    │       └── name = "HW: AES Last-Round State"
    │
    ├── LastroundStateDiff
    │       └── name = "HD: AES Last-Round State"
    │
    ├── LastroundStateDiffAlternate
    │       └── name = "HD: AES Last-Round State Alternate"
    │
    ├── PipelineDiff
    │       └── name = "HD: AES round 9 between previous and current encryptions"
    │
    ├── HalfPipelineDiff
    │       └── name = "HD: AES previous round 10 and current round 9"
    │
    ├── SBoxInOutDiff
    │       └── name = "HD: AES SBox Input to Output"
    │
    ├── SBoxInputSuccessive
    │       └── name = "HD: AES SBox Input i to i+1"
    │
    └── SBoxOutputSuccessive
            └── name = "HD: AES SBox Output i to i+1"
```

## 5. API接口说明

### 构造函数

```python
CPAAnalyzer(config: dict[str, Any] | None = None)
```

**配置参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `leakage_model` | "sbox_output" | 泄漏模型名称 |
| `num_subkeys` | 16 | 要分析的子密钥字节数（1-16） |
| `threshold` | 0.5 | 检测阈值 |

**支持的泄漏模型：**

```python
LEAKAGE_MODELS = {
    "sbox_output": SBoxOutput,
    "pt_key_xor": PtKeyXOR,
    "inv_sbox_output": InvSBoxOutput,
    "lastround_hw": LastroundHW,
    "lastround_state_diff": LastroundStateDiff,
    "lastround_state_diff_alt": LastroundStateDiffAlternate,
    "pipeline_diff": PipelineDiff,
    "half_pipeline_diff": HalfPipelineDiff,
    "sbox_in_out_diff": SBoxInOutDiff,
    "sbox_input_successive": SBoxInputSuccessive,
    "sbox_output_successive": SBoxOutputSuccessive,
}
```

### 主要方法

#### `analyze(traces, plaintext, key=None, **kwargs) -> CPAResult`

运行CPA分析。

**参数：**
- `traces`: np.ndarray，形状为 (num_traces, num_samples) 的功耗轨迹
- `plaintext`: np.ndarray，明文数据，形状为 (num_traces, 16)
- `ciphertext`: np.ndarray，可选，密文数据
- `key`: np.ndarray，可选，已知密钥用于计算PGE
- `labels`: np.ndarray，可选，标签数据

**返回：**
`CPAResult` 对象，包含最佳密钥猜测和相关统计信息。

```python
result = analyzer.analyze(traces, plaintext=plaintext, key=known_key)
print(f"猜测密钥: {[hex(b) for b in result.key_guess]}")
print(f"PGE: {result.pge}")
```

#### `detect_leakage_points(result, threshold=None) -> np.ndarray`

检测超过阈值的泄漏点索引。

```python
leakage_idx = analyzer.detect_leakage_points(result, threshold=0.7)
print(f"强泄漏点数量: {len(leakage_idx)}")
```

### CPAResult字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `method` | str | "cpa" |
| `num_subkeys` | int | 分析的子密钥数量 |
| `num_perms` | int | 每个子密钥的可能值数量（256） |
| `threshold` | float | 使用的检测阈值 |
| `num_traces` | int | 使用的轨迹数量 |
| `total_samples` | int | 每条轨迹的样本数 |
| `best_guesses` | list[dict] | 每个字节的最佳猜测详情 |
| `key_guess` | list[int] | 猜测的完整密钥（16字节） |
| `correlations` | list[np.ndarray] | 每个字节的256×num_samples相关系数矩阵 |
| `pge` | list[int] | 每个子密钥的排序误差 |
| `metadata` | dict | 附加元数据（泄漏模型名称等） |

### best_guesses 条目结构

```python
{
    "byte": 0,           # 子密钥字节索引 (0-15)
    "guess": 42,         # 最佳密钥猜测值 (0-255)
    "correlation": 0.87, # 对应的最大相关系数
    "pge": 0             # 排序-guess误差（如果key已知）
}
```

### 使用示例

```python
from squirrel.analysis import CPAAnalyzer
import numpy as np

# 创建分析器 - 使用 S-Box 输出模型
analyzer = CPAAnalyzer(config={
    "leakage_model": "sbox_output",
    "num_subkeys": 16,
    "threshold": 0.5
})

# 假设有轨迹和明文数据
traces = np.random.randn(1000, 3000)
plaintext = np.random.randint(0, 256, size=(1000, 16), dtype=np.uint8)

# 运行 CPA 分析
result = analyzer.analyze(traces, plaintext=plaintext)

# 输出结果
print(f"猜测密钥: {result.key_guess}")
print(f"PGE: {result.pge}")

# 使用最后一轮模型（密文攻击）
analyzer_lastround = CPAAnalyzer(config={"leakage_model": "lastround_hw"})
result = analyzer_lastround.analyze(traces, plaintext=plaintext, ciphertext=ciphertext)
```

### 选择泄漏模型的指南

| 场景 | 推荐模型 | 说明 |
|------|---------|------|
| 标准 AES 加密攻击 | `sbox_output` | 最常用的模型 |
| 密文攻击（最后一轮） | `lastround_hw` | 使用密文无需解密 |
| 汉明距离模型 | `sbox_in_out_diff` | 反映状态变化 |
| 流水线架构 | `pipeline_diff` | 连续加密状态变化 |
| 多字节联合攻击 | `sbox_output_successive` | 相邻字节相关性 |

## 6. 结果解读指南

### 6.1 PGE 解读

| PGE | 解读 |
|-----|------|
| 0 | 正确密钥排名第一 ✓ |
| 1-5 | 正确密钥排名前5，攻击成功 |
| 6-50 | 中等效果，可能需要更多轨迹 |
| > 50 | 攻击效果差，可能存在对策 |

### 6.2 相关系数解读

| |r| 值 | 解读 |
|---|------------------|
| > 0.8 | 强泄漏，密钥易恢复 |
| 0.5 - 0.8 | 中等泄漏 |
| 0.2 - 0.5 | 弱泄漏，可能需要更多轨迹 |
| < 0.2 | 无明显泄漏 |

### 6.3 泄漏点位置

- CPA 相关系数在时间轴上的峰值位置对应实际的泄漏操作时间点
- 可通过 `detect_leakage_points()` 定位泄漏区域

## 7. 局限性

### CPA 攻击的局限性

- **对齐要求**：轨迹需要良好对齐，噪声和偏移会显著降低相关性
- **泄漏模型依赖**：假设汉明重量/汉明距离模型适用于目标设备
- **抗对策敏感性**：掩码、随机延迟等对策会大幅降低攻击效果
- **数据依赖性**：需要足够多的轨迹来建立统计显著性

### 建议

- 攻击前确保轨迹已对齐（使用 `ResyncCrossCorrAligner` 等）
- 选择合适的泄漏模型（S-Box 输出最常用）
- 使用逐步 CPA 增量添加轨迹，观察相关性收敛
- 对于 pipeline 模型，确保轨迹来自连续加密操作

## 8. 与其他分析方法对比

| 方法 | 适用场景 | 复杂度 | 抗对策能力 |
|------|---------|--------|-----------|
| CPA | 已知明文/密文，汉明重量泄漏 | O(n×m×256) | 较弱 |
| DPA | 已知明文/密文，1-bit 泄漏模型 | O(n×m×256) | 较弱 |
| TVLA | 泄漏检测，无需密钥假设 | O(n×m) | 中等 |
| LSTM | 深度学习，自动特征提取 | 高 | 较强 |

## 9. 合成测试数据泄露模型

### 9.1 汉明重量泄露模型

CPA 分析的合成测试数据采用 **汉明重量泄露模型（Hamming Weight Leakage Model）**：

```
泄露值 = 高斯脉冲 × (汉明重量 / 128) × 幅值系数
```

其中：
- **高斯脉冲**：模拟 S-Box 操作的时间轮廓，只在操作时刻有值
- **汉明重量 / 128**：归一化系数，将 HW 映射到 [0, 1]
- **幅值系数**：将泄露放大到实际噪声水平

### 9.2 生成公式

```python
# 高斯脉冲构造
t = np.arange(num_samples)
sigma = 4.24  # ~10 samples FWHM (2.355 * sigma ≈ 10)
peak_center = num_samples // 2
pulse = np.exp(-((t - peak_center) ** 2) / (2 * sigma**2))

# 每条轨迹的泄露
total_hw = sum(bin(_SBOX[pt[b] ^ key[b]]).count("1") for b in range(16))
leakage = pulse * (total_hw / 128.0) * 8.0
```

### 9.3 物理意义

| 组件 | 含义 |
|------|------|
| `_SBOX[pt ^ key]` | AES 第一轮 S-Box 替换输出 |
| `bin(x).count("1")` | 计算汉明重量（数据中 "1" 的位数） |
| 高斯脉冲 | S-Box 操作的**时间位置** |
| `total_hw / 128` | 归一化，最大可能汉明重量为 128（16字节×8） |
| `× 8.0` | 幅值缩放，使泄露峰值达到 8.0 |

### 9.4 泄露幅值范围

当 `noise_std=0.1` 时：

| total_hw | 泄露峰值 | SNR (dB) |
|----------|----------|----------|
| 0 | 0.0 | - |
| 64 | 4.0 | ~12 |
| 128 | 8.0 | ~19 |

### 9.5 时间轮廓示意

```
pulse:      ███▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒███   ← 高斯轮廓（峰值1.0）
                                          ↑
                                     S-Box操作时刻

最终泄露:    ███▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒███   ← 数据依赖的幅值调制
            └─── 峰值 0~8.0 (由 total_hw 决定) ────┘
```

### 9.6 数据生成器

合成 CPA 测试数据由 `tests/data_generators/generate_cpa_dataset.py` 生成：

```bash
python generate_cpa_dataset.py \
    --output ./cpa_test.zarr \
    --num-traces 500 \
    --num-samples 1000 \
    --noise-std 0.1 \
    --seed 42 \
    --leakage-model sbox_output
```

**参数说明：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--num-traces` | 500 | 轨迹数量 |
| `--num-samples` | 1000 | 每条轨迹采样点数 |
| `--noise-std` | 0.1 | 噪声标准差 |
| `--seed` | 42 | 随机种子 |
| `--leakage-model` | sbox_output | 泄漏模型名称 |

### 9.7 与 TVLA 测试数据的区别

| 特性 | CPA 数据 | TVLA 数据 |
|------|----------|-----------|
| 泄露位置 | S-Box 输出 | 可配置（step/gaussian） |
| 泄露幅度 | 随 HW 连续变化 | 固定幅度（profile 控制） |
| 轨迹分组 | 单一分组 | Fixed/Random 分组 |
| 适用测试 | 密钥恢复验证 | 泄漏检测验证 |

## 10. 参考

- Brier, E., Clavier, C., & Olivier, F. (2004). Correlation Power Analysis with a Leakage Model. CHES 2004.
- Mangard, S., Oswald, E., & Popp, T. (2008). Power Analysis Attacks: Revealing the Secrets of Smart Cards.