# Resync_DTW - 动态时间规整轨迹对齐

## 测试结果

**对齐前后对比图：**


| 指标 | 数值 |
|------|------|
| **标准差降低** | 64.9% |
| **方差降低** | 通过 ✓ |
| **适用波形** | 复杂波形、非线性变形 |

## 1. 算法原理

### 1.1 核心思想

Resync_DTW 使用 **快速动态时间规整（FastDTW）** 算法对齐轨迹。与简单的平移对齐不同，DTW 能找到两条时间序列之间点的最优对应关系，允许**非线性形变**。

**核心假设**：轨迹中的相同物理现象会以相似但可能变形的形式出现，DTW 通过动态规划找到最优匹配。

### 1.2 数学公式

**给定：**
- 参考轨迹：$R = (r_1, r_2, ..., r_N)$，长度 $N$（即第 0 条轨迹）
- 测试轨迹：$T = (t_1, t_2, ..., t_N)$，长度 $N$（第 1, 2, 3 ... 条轨迹）

**DTW 距离递推：**

$$D(i, j) = |r_i - t_j| + \min(D(i-1, j), D(i, j-1), D(i-1, j-1))$$

其中 $D(i, j)$ 表示 $R[1:i]$ 和 $T[1:j]$ 之间的最优 DTW 距离。

**FastDTW 优化：**

- 使用滑动窗口半径 $r$ 限制搜索范围
- 半径 $r=3$ 表示只考虑距离对角线 $r$ 个单位内的点
- 时间复杂度从 $O(N^2)$ 降低到 $O(r \cdot N)$

**对齐输出：**

对于参考轨迹的每个索引 $i$，对齐值为该索引对应的所有匹配点的均值：

$$aligned[i] = \frac{\sum_{(x,y) \in path, x=i} T[y]}{count_i}$$

### 1.3 与平移对齐的区别

| 特性 | 平移对齐 | DTW |
|------|---------|-----|
| 形变类型 | 仅线性平移 | 非线性拉伸/压缩 |
| 计算复杂度 | $O(N)$ | $O(r \cdot N)$ |
| 适用场景 | 整体偏移 | 局部变形 |

### 1.4 直观理解：为什么需要 DTW？

#### 普通对齐 vs DTW 对齐

**普通对齐方法**（Peak、CrossCorr、SAD）假设：
> 整条波形只是**整体左移或右移一点**

但实际情况可能是：
> 某一小段"走得快一点"，另一小段"走得慢一点"

也就是，**不是整体平移，而是局部被拉伸或压缩了**。

#### 举个例子

```
参考轨迹 R:    A  B  C  D  E
测试轨迹 T:    A  B  B  C  D  E
               └──┘
              这里多了一个 B，被"拉长"了
```

如果强行一对一，长度都不一样，不好直接对。但 DTW 会这样想：

```
1↔1
2↔2,2    ← 参考里的 2 对应测试里的两个 2
3↔3
```

DTW 允许**一对多、多对一**，而不要求严格一对一。

#### D(i,j) 的物理意义

$D(i, j)$ 表示：**参考轨迹前 i 个点，和测试轨迹前 j 个点，对齐到当前位置为止的最小总代价。**

你可以把它理解成：
> "走到 $r_i$ 和 $t_j$ 这里时，历史上最便宜的匹配成本是多少。"

#### 递推公式的三种走法

$$D(i, j) = |r_i - t_j| + \min(D(i-1, j), D(i, j-1), D(i-1, j-1))$$

| 走法 | 含义 | 直观理解 |
|------|------|----------|
| $D(i-1, j)$ | 参考前进，测试停一下 | 测试轨迹这一段被"拉长"了一点 |
| $D(i, j-1)$ | 测试前进，参考停一下 | 参考轨迹这一段被"拉长"了一点 |
| $D(i-1, j-1)$ | 两边都前进 | 正常的一对一匹配 |

#### 走格子理解

把 DTW 想成"走格子"：

```
      T[1]  T[2]  T[3]  T[4]
R[1]   ○-----○-----○-----○
       | \   | \   |
       |  \  |  \  |
R[2]   ○---\-----○-----○
       |    \   |\   |
       |     \  | \  |
R[3]   ○------\--○---\─→  只能向下、向右、斜向右下走
       |        \ |   \ |
       ↓         ↓     ↓
```

- 一直沿对角线走 → 两条轨迹节奏完全一致
- 某段多走横向/纵向 → 某一边那一段被拉伸/压缩了

**这就是 DTW 能处理非线性形变的本质。**

#### FastDTW 半径 r

本来整张网格每个点都要算，太慢。但通常合理的匹配路径不会离主对角线太远，所以只在对角线附近一条窄带里搜索。

$r=3$：只允许路径在对角线附近偏 3 格左右

```
         r=3 窄带
    ╱───────────────────╲
   ╱                       ╲
  ╱   ═══════════════       ╲
 ╱          对角线            ╲
╱                               ╲
```

- 时间复杂度从 $O(N^2)$ 降低到 $O(r \cdot N)$

#### 四句话总结 DTW

1. 每个格子 $(i,j)$ 表示把 $r_i$ 和 $t_j$ 配一起
2. 当前代价是 $|r_i - t_j|$
3. 总代价 = 当前代价 + 之前最便宜路径
4. 最终找一条从左上到右下的最小代价路径

#### 与 CrossCorr 的本质区别

| | CrossCorr | DTW |
|--|-----------|-----|
| 找到的是 | 一个 shift（整体偏了多少） | 一条 path（每一小段怎么对应） |
| 匹配方式 | 整体对齐 | 局部最优匹配 |
| 形变处理 | 不支持 | 支持非线性拉伸/压缩 |

## 2. 类继承关系

```
squirrel.base.Analyzer (抽象基类)
    └── DTWAligner (继承自 Analyzer)
```

### 关键类

| 类名 | 文件 | 说明 |
|------|------|------|
| `DTWAligner` | dtw.py | 主对齐器类 |
| `DTWVerificationResult` | dtw.py | 对齐指标数据类 |
| `ShiftVerificationResult` | dtw.py | 平移估算指标数据类 |
| `PeakVerificationResult` | dtw.py | 峰值位置指标数据类 |

### 继承结构图
```
Analyzer (squirrel.base)
    │
    └── DTWAligner
            ├── name = "dtw"
            ├── description = "使用FastDTW算法对齐轨迹"
            │
            ├── __init__(config: dict | None)
            │       ├── radius: int = 3 (FastDTW搜索半径)
            │       ├── ref_trace_idx: int = 0 (参考轨迹索引)
            │       ├── std_threshold: float = 50.0 (通过标准差降低阈值)
            │       ├── var_threshold: float = 50.0 (通过方差降低阈值)
            │       └── corr_threshold: float = 0.5 (通过相关系数阈值)
            │
            ├── align(traces, ref_trace_idx) -> np.ndarray
            ├── verify(original, aligned, ref_trace_idx) -> DTWVerificationResult
            ├── verify_shifts(original, aligned, ground_truth_shifts, tolerance=2) -> ShiftVerificationResult
            ├── verify_peaks(original, aligned, ground_truth_shifts, tolerance=5) -> PeakVerificationResult
            ├── print_verification(result)
            ├── print_shift_verification(result, tolerance)
            └── print_peak_verification(result, tolerance)
```

## 3. API接口说明

### 构造函数

```python
DTWAligner(config: dict[str, Any] | None = None)
```

**配置参数：**
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `radius` | 3 | FastDTW搜索半径 |
| `ref_trace_idx` | 0 | 参考轨迹索引 |
| `std_threshold` | 50.0 | 标准差降低最小百分比 |
| `var_threshold` | 50.0 | 方差降低最小百分比 |
| `corr_threshold` | 0.5 | 最小相关系数 |

### 主要方法

#### `align(traces: np.ndarray, ref_trace_idx: int | None = None) -> np.ndarray`
使用FastDTW将所有轨迹对齐到参考轨迹。

#### `verify(original, aligned, ref_trace_idx) -> DTWVerificationResult`
验证对齐效果，计算：
- 标准差降低百分比
- 方差降低百分比
- 相关系数改善

#### `verify_shifts(original, aligned, ground_truth_shifts, tolerance=2) -> ShiftVerificationResult`
通过互相关估算平移量并与真实值比较。

#### `verify_peaks(original, aligned, ground_truth_shifts, tolerance=5) -> PeakVerificationResult`
查找峰值位置并计算对齐精度。

### 使用示例

```python
from squirrel.preprocessing import DTWAligner
import numpy as np

# 加载轨迹 (轨迹数, 样本数)
traces = np.random.randn(100, 2000)

# 创建对齐器
aligner = DTWAligner(config={
    "radius": 3,
    "ref_trace_idx": 0,
    "std_threshold": 50.0,
    "var_threshold": 50.0,
    "corr_threshold": 0.5
})

# 对齐轨迹
aligned = aligner.align(traces)

# 验证
result = aligner.verify(traces, aligned)
print(f"通过: {result.passed}")
print(f"标准差降低: {result.std_reduction_percent:.1f}%")
```

## 4. Makefile用法

### 快速开始
```bash
make resync_dtw
```

### 可用目标

| 目标 | 说明 |
|------|------|
| `resync_dtw` | 运行完整流程：生成 → 对齐 → 验证 |
| `resync_dtw-generate` | 仅生成测试数据 |
| `resync_dtw-align` | 执行DTW对齐 |
| `resync_dtw-verify` | 验证对齐结果 |
| `resync_dtw-clean` | 清理输出文件 |

### 配置变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RESYNC_DTW_NUM_TRACES` | 300 | 生成轨迹数量 |
| `RESYNC_DTW_NUM_SAMPLES` | 2000 | 每条轨迹样本数 |
| `RESYNC_DTW_MAX_SHIFT` | 20 | 测试数据最大偏移 |
| `RESYNC_DTW_NOISE_STD` | 0.1 | 噪声标准差 |
| `RESYNC_DTW_RADIUS` | 3 | FastDTW半径 |

### 使用示例

```bash
# 默认运行
make resync_dtw

# 自定义轨迹数
make resync_dtw RESYNC_DTW_NUM_TRACES=500

# 仅生成并查看日志
make resync_dtw-generate
cat sim/preprocessing/Resync_DTW/log/generate.log

# 仅验证
make resync_dtw-verify

# 清理
make resync_dtw-clean
```

### 输出文件

```
sim/preprocessing/Resync_DTW/
├── traces/
│   ├── dtw_original.zarr       # 原始轨迹
│   └── dtw_original_shifts.json # 真实偏移量
├── result/
│   ├── dtw_aligned.zarr        # 对齐后轨迹
│   └── dtw_comparison.png       # 对比可视化
└── log/
    ├── generate.log             # 数据生成日志
    ├── align.log                 # 对齐日志
    └── verify.log                # 验证结果

## 7. 方法选择速查

| 波形特征 | 推荐方法 |
|---------|---------|
| 清晰单峰 | Peak |
| 双尖峰/多峰 | **DTW** ✓ |
| 高噪声 | CrossCorr |
| 非线性变形 | **DTW** ✓ |
| 方波/过零点 | ZC |
| 有参考模板 | SAD |
```