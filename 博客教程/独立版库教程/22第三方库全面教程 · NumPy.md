# 第三方库全面教程 · NumPy

> 面向初学者：这是**零基础起步**的数值计算库全套教程，假设你只会最基础 Python 语法（列表、循环、函数）。术语第一次出现都有白话解释。
> 适用版本：NumPy 1.26 / 2.x ｜ 配套知识：配合《Pandas》（它底层就是 NumPy）、配合《Matplotlib》（画图坐标）、配合《Pillow》（图像本质是 NumPy 数组）。
> 学习目标：从"只会用 for 循环一个个算数"到"用数组向量化计算，几行代码搞定百万级数据运算"。

## 第 1 章 这个库是什么

### 1.1 一句话认识 NumPy

**NumPy** 是 Python 的**数值计算底层引擎**。它的核心是 **ndarray（N 维数组）**——一个比 Python 列表快几十倍、支持"整组一起算"的高性能数组。

```python
import numpy as np

scores = np.array([85, 92, 78, 96])   # 列表 → 数组
print(scores + 5)                     # 每个元素 +5 → [90 97 83 101]（不用循环！）
print(scores.mean())                  # 平均分 87.75
```

### 1.2 为什么需要它

1. **速度**：NumPy 底层是 C 语言实现，向量化运算比 Python for 循环快几十到几百倍。
2. **向量化（Vectorization）**：对**整组数据**一次性做运算，不用写循环——代码又短又快。
3. **它是地基**：Pandas 的数据结构底层就是 NumPy 数组；Matplotlib 画图数据、Pillow 图像、scikit-learn 机器学习、深度学习框架全部建立在 NumPy 之上。**学数据分析/科学计算，NumPy 是绕不开的第一块砖。**

### 1.3 NumPy vs Python 列表

| 对比 | Python 列表 | NumPy 数组 |
| --- | --- | --- |
| 元素类型 | 任意（混合也行） | **同一类型**（快的前提） |
| 运算 | 只能循环 | **整组一起算** |
| 速度 | 慢 | 快几十倍 |
| 内存 | 大 | 紧凑 |
| 适用 | 通用容器 | 数值计算 |

## 第 2 章 核心概念与原理

### 2.1 数组的"形状"（shape）：几维、每维多长

```
一维数组：   [1, 2, 3]                  shape = (3,)
二维数组：   [[1, 2],                    shape = (2, 3)   ← 2 行 3 列
              [3, 4]]
三维数组：   形状如 (2, 3, 4)             ← 2 个"3行4列"的块
```

**shape** 是 NumPy 的灵魂属性：几乎所有操作（变形、广播、索引）都围绕它。

### 2.2 向量化（Vectorization）：不用 for 循环的秘密

Python 的 `[x*2 for x in arr]` 是一个一个算；NumPy 的 `arr * 2` 是**一整块同时算**（底层 C 循环）。这就是快几十倍的原因。

**训练直觉**：看到"对数组的每个元素做同样操作"，第一反应应该是"能不能用 NumPy 一行搞定"，而不是写循环。

### 2.3 广播（Broadcasting）：不同形状也能一起算

**广播**是 NumPy 自动把形状"对齐"的规则：

```python
arr = np.array([[1, 2, 3],
                [4, 5, 6]])
arr + 10            # 标量 10 自动"扩展"成 2x3 → 每个元素 +10
arr + np.array([10, 20, 30])   # 一维自动广播到每一行
```

规则：从尾部维度开始比较，相等或其中一个为 1 就能广播。**不用记规则，遇到报错看 shape 即可**。

### 2.4 视图 vs 副本（关键陷阱）

- **切片是视图（view）**：`sub = arr[0:2]`，改 `sub` 会**影响原数组**（没有复制数据）。
- **需要独立副本用 `.copy()`**。
- 这和 Python 列表切片"复制一份"完全不同，新手必踩。

## 第 3 章 安装与版本

```bash
pip install numpy
```

导入约定：`import numpy as np`。当前主流版本 1.26 / 2.x（API 基本一致，教程代码都可用）。查看版本：`np.__version__`。

## 第 4 章 API 全面讲解（✅ = 必会 ｜ ➕ = 推荐 ｜ 🧪 = 进阶）

### 4.1 创建数组（✅）

```python
import numpy as np

# 从列表
np.array([1, 2, 3])                        # 一维
np.array([[1, 2], [3, 4]])                 # 二维（嵌套列表）
np.array([1, 2], dtype=float)              # 指定类型

# 常用快捷创建
np.zeros((3, 3))                           # 3x3 全 0
np.ones((2, 4))                            # 2x4 全 1
np.full((2, 2), 7)                         # 2x2 全 7
np.arange(10)                              # 0..9（同 range）
np.arange(0, 1, 0.2)                       # 0, 0.2, 0.4, 0.6, 0.8
np.linspace(0, 1, 5)                       # 0 到 1 等分 5 个点：[0, 0.25, 0.5, 0.75, 1]
np.eye(3)                                  # 3x3 单位矩阵
np.random.rand(5)                          # 5 个 0~1 均匀随机数
np.random.randint(1, 10, size=(3, 3))      # 3x3 整数随机（1~9）
np.random.randn(100)                       # 100 个标准正态随机数
```

### 4.2 数组属性（✅）

```python
arr = np.array([[1, 2, 3], [4, 5, 6]])
arr.shape          # (2, 3)
arr.ndim           # 2（几维）
arr.size           # 6（元素总数）
arr.dtype          # dtype('int64')（元素类型）
arr.itemsize       # 每个元素字节数
arr.T              # 转置（2x3 → 3x2）
```

### 4.3 索引与切片（✅）

```python
arr = np.arange(10)            # [0 1 2 3 4 5 6 7 8 9]

arr[0]                         # 0
arr[-1]                        # 9
arr[2:6]                       # [2 3 4 5]
arr[::2]                       # 隔一个取：[0 2 4 6 8]

m = np.array([[1, 2, 3],
              [4, 5, 6],
              [7, 8, 9]])
m[0, 1]                        # 第 1 行第 2 列 → 2
m[1]                           # 第 2 行
m[:, 0]                        # 所有行的第 1 列 → [1 4 7]
m[1:, :2]                      # 从第 2 行起、前 2 列
```

**关键**：逗号分隔"行, 列"；`:` 表示"这一维全要"。

### 4.4 布尔索引与条件筛选（✅ 高频）

```python
arr = np.array([10, 25, 30, 45, 60])
arr > 30                       # [False False False  True  True]
arr[arr > 30]                  # [45 60]  ← 只取满足条件的
arr[(arr > 20) & (arr < 50)]   # [25 30 45]  （& 且 / | 或，都要括号）
arr[arr % 2 == 0]              # 偶数
arr[arr == 25] = 99            # 把等于 25 的改成 99
```

### 4.5 向量化运算（✅ 核心中的核心）

```python
a = np.array([1, 2, 3])
b = np.array([10, 20, 30])

a + b              # [11 22 33]（逐元素加）
a - b              # 逐元素减
a * 2              # 逐元素乘（不是矩阵乘法）
a / 2
a ** 2             # 平方
np.sqrt(a)         # 开方
np.abs(a - 5)      # 绝对值
np.round(np.array([1.234, 5.678]), 2)   # 四舍五入

# 比较运算返回布尔数组
a > 2              # [False False  True]

# 逻辑
np.logical_and(a > 1, a < 3)
```

**⚠️ 注意**：`a * b` 是逐元素相乘（对应位置相乘）。矩阵乘法是 `a @ b` 或 `np.dot(a, b)`（高等数学的矩阵乘），别混了。

### 4.6 统计函数（✅）

```python
arr = np.array([85, 92, 78, 96, 88])

np.mean(arr)        # 均值 87.8
np.sum(arr)         # 总和
np.max(arr) / np.min(arr)   # 最大/最小
np.std(arr)         # 标准差（数据波动程度）
np.var(arr)         # 方差
np.median(arr)      # 中位数
np.percentile(arr, 90)      # 90 分位（比 90% 数据小）
np.argmax(arr)      # 最大值的下标
np.argmin(arr)      # 最小值的下标
arr.cumsum()        # 累加和
np.unique(arr)      # 去重后的值

# 按轴统计（二维）：axis=0 沿列，axis=1 沿行
m = np.array([[1, 2], [3, 4]])
m.sum(axis=0)       # [4 6]（每列求和）
m.sum(axis=1)       # [3 7]（每行求和）
```

### 4.7 变形与拼接（➕）

```python
arr = np.arange(12)

arr.reshape(3, 4)               # 变成 3 行 4 列（元素总数必须一致）
arr.reshape(2, -1)              # -1 自动算：2 行，列自动 = 6
arr.reshape(-1)                 # 拉平成一维
arr.flatten()                   # 拉平（返回副本）

np.concatenate([a, b])          # 拼接一维
np.vstack([a, b])               # 上下堆叠（变两行）
np.hstack([a, b])               # 左右拼接（变两列）

np.where(arr > 5, 1, 0)         # 条件替换：大于 5 的变 1，否则 0（超常用！）
```

### 4.8 随机数与高级索引（🧪）

```python
rng = np.random.default_rng(42)     # 带种子的随机（42 固定，结果可复现）
rng.random((3, 3))
rng.integers(1, 100, 10)
rng.choice(["A", "B", "C"], size=5) # 随机抽样

# 花式索引（用数组取多行/多列）
m[[0, 2]]                          # 取第 1、3 行
m[np.array([True, False, True])]   # 布尔行筛选
```

## 第 5 章 实战项目案例（从小白到大神）

### 案例 1（入门级）：成绩单统计

```python
import numpy as np

scores = np.array([[85, 92, 78],
                   [66, 88, 95],
                   [90, 70, 60],
                   [72, 84, 90]])

print("各科平均分：", scores.mean(axis=0).round(1))    # 每列 = 每科
print("每个学生总分：", scores.sum(axis=1))             # 每行 = 每个学生
print("全班最高分：", scores.max())
print("及格率：", (scores >= 60).mean() * 100, "%")     # 布尔数组 mean = 比例
print("90 分以上人数：", (scores >= 90).sum())
```

**亮点**：`(scores >= 60).mean()` 一行算出"及格率"——布尔数组的 mean 就是 True 的占比。

### 案例 2（进阶级）：数据标准化 + 异常值检测

```python
import numpy as np

# 某系统每天的响应耗时（毫秒），个别值异常大
latency = np.array([120, 135, 118, 900, 122, 128, 110, 500, 131, 125])

# ① 基础统计
print("均值：", latency.mean().round(1), "标准差：", latency.std().round(1))

# ② Z-score 标准化（机器学习常用：变成均值为 0、标准差为 1）
z = (latency - latency.mean()) / latency.std()
print("标准化后：", z.round(2))

# ③ 异常值检测：超过均值 + 3 倍标准差视为异常
threshold = latency.mean() + 3 * latency.std()
outliers = latency[latency > threshold]
print("异常耗时：", outliers)

# ④ 用中位数替代异常值（稳健处理）
clean = latency.copy()
clean[clean > threshold] = np.median(latency)
print("清洗后：", clean)
```

### 案例 3（综合）：图像数据 + 性能基准（NumPy + Pillow + Matplotlib）

```python
"""把一张图片当作 NumPy 数组处理：灰度化、裁剪、反色、统计，再画分布直方图"""
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

# ① 读图 → NumPy 数组（形状 H x W x 3，RGB）
img = np.array(Image.open("photo.jpg").convert("RGB"))
print("图像形状：", img.shape, "像素值范围：", img.min(), "~", img.max())

# ② 灰度化：加权平均（人眼对绿最敏感）
gray = (0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]).astype(np.uint8)

# ③ 反色
inverted = 255 - gray

# ④ 裁剪中心区域（用切片！）
h, w = gray.shape
center = gray[h // 4: h // 4 * 3, w // 4: w // 4 * 3]

# ⑤ 统计与直方图
print("亮度均值：", gray.mean().round(1), "标准差：", gray.std().round(1))
plt.figure(figsize=(12, 4))
plt.subplot(1, 3, 1); plt.imshow(gray, cmap="gray"); plt.title("灰度")
plt.subplot(1, 3, 2); plt.imshow(inverted, cmap="gray"); plt.title("反色")
plt.subplot(1, 3, 3); plt.hist(gray.ravel(), bins=50, color="#3498db"); plt.title("亮度分布")
plt.tight_layout()
plt.savefig("analysis.png", dpi=120)
plt.show()
```

**这个案例让你看到**：图像在计算机里就是 NumPy 数组，所有"图像处理"本质是数组运算——这就是 OpenCV/Pillow 背后的原理。

## 第 6 章 进阶内容（大神之路）

### 6.1 性能优化：向量化思维

```python
# 反面（慢，1 万次 Python 循环）
result = [x * 2 + 1 for x in data]

# 正面（快，C 语言批量算）
result = data * 2 + 1

# 需要条件逻辑时用 np.where 代替循环
result = np.where(data > 50, data * 2, data / 2)
```

### 6.2 内存：视图与 copy 的正确使用

- 切片操作（视图）不复制数据 → 大数组切来切去几乎不耗内存。
- 需要独立数据时 `.copy()`，避免无意改原数组。
- `arr.astype(float)` 会复制（类型变了必须新数组）。

### 6.3 与 Pandas / Matplotlib 配合

- Pandas 的 `df.values` / `df.to_numpy()` 拿到底层 NumPy 数组直接算。
- Matplotlib 的 `plt.plot(np_array)` 直接接受 NumPy 数组。

### 6.4 线性代数（机器学习预科）

```python
A = np.array([[1, 2], [3, 4]])
B = np.array([[5, 6], [7, 8]])
A @ B              # 矩阵乘法
np.linalg.inv(A)   # 矩阵求逆
np.linalg.det(A)   # 行列式
np.linalg.eig(A)   # 特征值特征向量
```

### 6.5 安全与复现

- 随机数用 `np.random.default_rng(seed)` 固定种子，结果可复现（写报告/调试必需）。
- 涉及浮点比较用 `np.isclose(a, b)` 而不是 `==`。

## 第 7 章 高频坑与排查（新手必看）

| 坑 | 症状 | 解决 |
| --- | --- | --- |
| 列表和数组混用 | 报错或结果不对 | 先 `np.array()` 转换；两边统一 |
| 忘了向量化 | 慢 | 能写 `arr + 1` 就别写 `[x+1 for x in arr]` |
| 广播报错 | `operands could not be broadcast together` | 看两边 `.shape`，用 reshape 对齐 |
| 整数除法 | `np.array([1,2]) / 2` 得 [0, 1] | 用 float 数组或 `dtype=float` |
| 切片改了原数组 | 原数据被意外修改 | 切片是视图；要独立用 `.copy()` |
| `*` 不是矩阵乘法 | 结果和数学预期不符 | 矩阵乘法用 `@` 或 `np.dot` |
| 形状不对 | reshape 报错 | 元素总数必须一致；用 `-1` 自动算 |
| 浮点比较失败 | `0.1+0.2 != 0.3` | 用 `np.isclose()` |
| 索引越界 | IndexError | 先看 `.shape`；用 `-1` 取最后一个 |
| 中文字符串进数组 | 类型变成 U 且运算报错 | 数值计算前确认 dtype 是数值型 |

## 第 8 章 学习路径与自测

**学习路径**：
1. 创建数组 + shape/属性（半天）
2. 索引与切片（1 天，二维要熟）
3. 向量化运算（半天）
4. 布尔索引（1 天）
5. 统计函数 + 轴 axis（1 天）
6. reshape/拼接/where（半天）
7. 案例 1→3 手写（2 天）
8. 随机数与种子（半天）
9. 广播规则深入（1 天）
10. 图像/线性代数实战（1-2 天）

**自测题**：
1. `np.array([1,2,3])` 的 shape 是什么？二维数组 shape 怎么读？
2. 切片为什么可能"改坏"原数组？
3. `a * b` 和 `a @ b` 的区别？
4. 布尔数组的 `.mean()` 和 `.sum()` 分别算出什么？
5. `axis=0` 和 `axis=1` 分别沿哪个方向？
6. 为什么说向量化快？for 循环慢在哪？
7. `arr[arr > 10]` 是什么操作？
8. reshape(2, -1) 的 -1 是什么？
9. 怎么让随机结果可复现？
10. 综合：用 NumPy 实现"标准化 + 异常值检测 + 阈值替换"（提示：参考案例 2）。

**答案提示**：
1. (3,)；二维如 (2,3) 表示 2 行 3 列。
2. NumPy 切片是视图（共享内存），改视图会改原数组；要独立用 .copy()。
3. `*` 逐元素相乘；`@` 是数学矩阵乘法。
4. mean = True 的占比（比例），sum = True 的个数。
5. axis=0 沿"行方向"压缩（每列计算）；axis=1 沿"列方向"压缩（每行计算）。
6. for 循环是 Python 解释器逐元素执行；NumPy 底层 C 一次处理整块数据。
7. 布尔索引筛选：只保留满足条件的元素。
8. -1 表示"该维度自动计算"（元素总数 ÷ 其他维度乘积）。
9. `np.random.default_rng(seed)`，如 `np.random.default_rng(42)`。
10. 参考案例 2：z-score → mean+3*std 阈值 → 布尔索引替换。

<hr>

> 下一篇：《Matplotlib》——把 NumPy/Pandas 的数据变成图表，一图胜千言。
