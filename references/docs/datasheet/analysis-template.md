# Template Attack - 模板攻击（多变量高斯分析）

## 测试结果


| 指标 | 测试结果 |
|------|----------|
| **Key correct** | 16/16 bytes |
| **Profile traces** | 5000 |
| **Attack traces** | 200 |
| **POIs per byte** | 5 |
| **Algorithm** | Multivariate Gaussian Template |
| **通过验证** | ✅ PASS |

## 1. 算法原理

### 1.1 核心概念

模板攻击（Template Attack）是一种**分析型侧信道攻击**，属于 profiling attack 的一种。它分为两个阶段：

1. **建模板阶段（Profiling）**：在受控设备上使用已知密钥采集大量轨迹，按中间值分类构建模板
2. **攻击阶段（Attack）**：使用构建好的模板对目标设备进行攻击，恢复密钥

**核心优势**：利用多变量高斯分布建模，比 DPA/CPA 利用更多信息。

### 1.2 AES S-Box 汉明重量模型

与 DPA/CPA 类似，使用 S-Box 输出作为泄漏点：

```
明文 P → [AddRoundKey] → S-Box[P ⊕ K] → 输出
```

泄漏值为输出的汉明重量 $HW \in \{0, 1, ..., 8\}$。

### 1.3 数学公式

**步骤 1：按 HW 分组**

对于每个字节 $b$，已知密钥 $K_b$，计算中间值：

$$M_i = S\text{-}Box[P_i[b] \oplus K_b]$$

按汉明重量分为 9 组（HW = 0 ~ 8）：

$$T_{b,hw} = \{ T_i \mid HW(M_i) = hw \}$$

**步骤 2：计算每组均值**

$$\bar{T}_{b,hw}[t] = \frac{1}{|T_{b,hw}|} \sum_{i \in T_{b,hw}} T_i[t]$$

**步骤 3：计算 POI（峰值点选择）**

在泄漏窗口内，两两组间均值差的绝对值求和得到峰值曲线：

$$Peak[t] = \sum_{i=0}^{8} \sum_{j=0}^{i-1} |\bar{T}_{b,i}[t] - \bar{T}_{b,j}[t]|$$

选择 Peak 曲线上 $n$ 个最大值作为 POI。

**步骤 4：构建协方差矩阵**

对每个 HW 类 $hw$，在 POI 点上构建协方差矩阵：

$$\Sigma_{b,hw} = Cov(T_{b,hw}[POI])$$

均值向量：$\mu_{b,hw} = \bar{T}_{b,hw}[POI]$

**步骤 5：攻击阶段（多变量高斯对数似然）**

对于每条攻击轨迹 $a$ 和每个候选密钥 $k$：

$$p(a | k) = \prod_{t} \frac{1}{\sqrt{(2\pi)^d |\Sigma|}} \exp\left(-\frac{1}{2}(\mathbf{a} - \mu_{k})^T \Sigma^{-1}(\mathbf{a} - \mu_{k})\right)$$

对数形式：

$$\log p(a | k) = -\frac{1}{2} \left[ d\ln(2\pi) + \ln|\Sigma| + (\mathbf{a} - \mu_{k})^T \Sigma^{-1}(\mathbf{a} - \mu_{k}) \right]$$

其中 $d$ = POI 数量，$\mathbf{a}$ = 轨迹在 POI 点上的值。

**步骤 6：累积并排序**

$$P[k] = \sum_{\text{attack traces}} \log p(a | k)$$

最大 $P[k]$ 对应的 $k$ 即为猜测密钥。

## 2. 支持的参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `num_pois` | 5 | 每个字节的 POI 数量 |
| `poi_spacing` | 5 | POI 之间最小间隔（防止选择相邻点） |
| `byte_pos` | [0..15] | 攻击的字节位置 |
| `direction` | "enc" | 加密方向（enc/dec） |
| `sample_start` | 0 | 分析样本起始位置 |
| `sample_end` | 3000 | 分析样本结束位置 |

## 3. 数据格式

### Zarr 数据集结构

模板攻击需要两组数据：建模板数据和攻击数据。

```
zarr_file/
├── /0/0/                    # 模板（建模板）轨迹
│   ├── traces     (num_profile, num_samples) float32
│   ├── plaintext  (num_profile, 16) uint8
│   ├── key         (num_profile, 16) uint8
│   └── labels     (num_profile,) int8
└── /1/0/                    # 攻击轨迹
    ├── traces     (num_attack, num_samples) float32
    ├── plaintext  (num_attack, 16) uint8
    ├── key         (num_attack, 16) uint8
    └── labels     (num_attack,) int8
```

## 4. 使用方法

### 命令行

```bash
# 数据生成（模板 + 攻击）
uv run --no-editable python -m tests.data_generators.cli template \
    --output sim/TemplateAttack/traces/template_traces.zarr \
    --num-traces 5000 \
    --num-attack-traces 200 \
    --num-samples 3000 \
    --noise-std 0.1 \
    --seed 42 \
    --known-key 00112233445566778899aabbccddeeff \
    --leakage-start 500 \
    --leakage-end 700 \
    --leakage-amplitude 3.0

# 分析
uv run --no-editable python tests/verify/template/analyzer.py \
    sim/TemplateAttack/traces/template_traces.zarr \
    sim/TemplateAttack/result/template_results.json \
    --output-dir sim/TemplateAttack/result \
    --num-pois 5 \
    --poi-spacing 5 \
    --direction enc

# 验证
uv run --no-editable python tests/verify/template/verifier.py \
    sim/TemplateAttack/traces/template_traces.zarr \
    --results-json sim/TemplateAttack/result/template_results.json \
    --all-bytes
```

### Python API

```python
from squirrel.analysis.template import TemplateAnalyzer

analyzer = TemplateAnalyzer(config={
    "num_pois": 5,
    "poi_spacing": 5,
    "direction": "enc",
})

result = analyzer.analyze(
    "sim/TemplateAttack/traces/template_traces.zarr",
    input_path="sim/TemplateAttack/traces/template_traces.zarr",
    output_dir="sim/TemplateAttack/result",
)

print(f"Recovered key: {result.recovered_key}")
print(f"Expected key:  {result.known_key}")
```

## 5. 结果解读

### 模板曲线图

生成的 `template_all_bytes.png` 包含 4×4 网格，每张子图显示：
- **X 轴**：采样点（时间）
- **Y 轴**：功耗值
- **9 条曲线**：9 种 HW 类（0~8）的平均功耗曲线
- **红色虚线**：5 个 POI 位置

### 正确密钥特征

当攻击成功时，正确密钥对应的 HW 模板应与实际轨迹的 POI 值高度吻合，对数似然值最大。

## 6. 与 DPA/CPA 的对比

| 特征 | DPA | CPA | Template Attack |
|------|-----|-----|-----------------|
| **类型** | 差分 | 相关性 | 分析型/模板 |
| **分组方式** | 阈值（2组） | 连续相关 | 9 类 HW |
| **统计模型** | 仅均值 | 相关系数 | 多变量高斯分布 |
| **利用信息** | 均值差 | 线性关系 | 全分布（均值+方差+协方差） |
| **攻击效率** | 低 | 中 | 高 |
| **模板数量** | 无需 | 无需 | 需大量建模板轨迹 |
| **适用场景** | 噪声低 | 噪声中 | 高噪声、复杂泄漏 |

## 7. 性能优化

攻击阶段采用向量化实现：

1. **预计算**：协方差矩阵求逆、Cholesky 分解计算 $\ln|\Sigma|$ 在建模板阶段一次性完成
2. **批量处理**：按 HW 类批量计算马氏距离，避免逐个调用 `scipy.stats.multivariate_normal.logpdf`
3. **进度显示**：实时打印每个字节、每个时间点的进度

典型性能：
- 200 attack traces：约 10 秒
- 500 attack traces：约 30 秒
- 1000 attack traces：约 1 分钟

## 8. 测试数据生成

数据生成器在 `tests/data_generators/generate_template_dataset.py`。

**注意**：当前实现建模板和攻击使用**相同密钥**，都是固定密钥。这是模板攻击的标准设置——建模板阶段使用已知密钥，攻击阶段也使用已知密钥验证。