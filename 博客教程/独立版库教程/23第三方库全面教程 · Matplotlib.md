# 第三方库全面教程 · Matplotlib

> 面向初学者：这是**零基础起步**的绘图库全套教程，假设你只会最基础 Python 语法。术语第一次出现都有白话解释。
> 适用版本：Matplotlib 3.8+ ｜ 配套知识：配合《NumPy》《Pandas》生成数据、配合《Pillow》处理图像、配合《Requests/Playwright》采集数据后可视化。
> 学习目标：从"只会 print 数字"到"把任何数据变成折线图、柱状图、饼图、散点图，并自定义样式导出高清图片"。

## 第 1 章 这个库是什么

### 1.1 一句话认识 Matplotlib

**Matplotlib** 是 Python 最老牌、最通用的**数据可视化（画图）库**——把数据列表/数组/表格变成折线图、柱状图、饼图、散点图等，还能完全自定义颜色、标签、图例，导出 PNG/PDF。

```python
import matplotlib.pyplot as plt

x = [1, 2, 3, 4, 5]
y = [10, 15, 13, 18, 20]
plt.plot(x, y)          # 画折线图
plt.title("我的第一张图")
plt.savefig("chart.png", dpi=150)   # 保存图片
plt.show()              # 弹出窗口显示
```

### 1.2 为什么需要它

- **一图胜千言**：给数据配图，趋势、对比、分布一眼看懂；写报告、做演示、发文章都离不开。
- 和 Pandas/NumPy 无缝衔接：`df.plot()` 一行出图。
- 它是 Python 可视化的**地基**：很多高级库（seaborn、pandas.plot）都建立在它之上。

### 1.3 和 Excel 图表的对应

| 需求 | Excel | Matplotlib |
| --- | --- | --- |
| 趋势 | 折线图 | `plt.plot()` |
| 对比 | 柱状图 | `plt.bar()` |
| 占比 | 饼图 | `plt.pie()` |
| 分布/相关性 | 散点图 | `plt.scatter()` |
| 数值分布 | 直方图 | `plt.hist()` |

## 第 2 章 核心概念与原理

### 2.1 三层结构：Figure → Axes → Artist

```
Figure（画布/窗口）——整个图片
  └── Axes（坐标系/子图）——画图区域（一张图可以有多个子图）
        └── Artist（元素）——折线、柱体、标题、坐标轴标签……
```

- `plt.figure()` 创建画布；`plt.subplots()` 一次建画布+坐标系。
- 绝大多数操作是在 **Axes** 上画的（`ax.plot(...)`）。

### 2.2 pyplot（plt）和面向对象（ax）两种写法

```python
# 写法一：pyplot 风格（简单，教学/脚本用）
plt.plot([1, 2, 3], [1, 4, 9])
plt.xlabel("x")
plt.show()

# 写法二：面向对象风格（正式项目/多子图用，推荐掌握）
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 9])
ax.set_xlabel("x")
plt.show()
```

两种等价。**推荐主学面向对象**（`fig, ax = plt.subplots()`），画多子图、精细控制都靠它；pyplot 写法用于快速出图。

### 2.3 中文乱码问题（中国开发者第一坑）

Matplotlib 默认字体不含中文，直接写中文标题会显示成方块。两种解决：

```python
# 方案 A（推荐）：指定支持中文的字体
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "PingFang SC"]
plt.rcParams["axes.unicode_minus"] = False    # 解决负号显示成方块

# 方案 B：用英文标题（最省事，但中文场景不友好）
```

**每个脚本开头都加上方案 A 的两行**，形成肌肉记忆。

### 2.4 显示与保存

- `plt.show()`：弹出窗口显示（脚本运行到这才看到图）。
- `plt.savefig("name.png", dpi=150)`：保存图片（**记得在 show 之前调用**，且关掉窗口后 savefig 可能保存空白）。
- 服务器/无界面环境：用 `matplotlib.use("Agg")` 或直接只 savefig 不 show。

## 第 3 章 安装与版本

```bash
pip install matplotlib
```

Matplotlib 会自动安装 NumPy（依赖）。当前稳定版 3.8+。导入约定：`import matplotlib.pyplot as plt`。中文字体方案见 2.3。

## 第 4 章 API 全面讲解（✅ = 必会 ｜ ➕ = 推荐 ｜ 🧪 = 进阶）

### 4.1 折线图：趋势（✅）

```python
import matplotlib.pyplot as plt

x = [1, 2, 3, 4, 5, 6]
y1 = [10, 12, 11, 14, 13, 18]
y2 = [8, 9, 12, 10, 15, 16]

fig, ax = plt.subplots(figsize=(8, 4))       # 画布大小（英寸）
ax.plot(x, y1, label="产品A", color="#e74c3c", marker="o")   # 折线+数据点
ax.plot(x, y2, label="产品B", color="#3498db", linestyle="--", marker="s")
ax.set_title("月度销售趋势")
ax.set_xlabel("月份")
ax.set_ylabel("销售额（万）")
ax.legend()                                  # 显示图例
ax.grid(True, alpha=0.3)                     # 网格（半透明）
plt.tight_layout()
plt.savefig("trend.png", dpi=150)
plt.show()
```

**常用参数**：`color` 颜色、`linestyle` 线型（`-`实线 `--`虚线 `-.`点划线 `:`点线）、`marker` 点形（`o`圆 `s`方 `^`三角）、`linewidth` 线宽、`alpha` 透明度。

### 4.2 柱状图：对比（✅）

```python
import matplotlib.pyplot as plt

categories = ["A", "B", "C", "D"]
values = [25, 40, 18, 33]

fig, ax = plt.subplots()
bars = ax.bar(categories, values, color=["#e74c3c", "#3498db", "#27ae60", "#f39c12"])
ax.set_title("各品类销量")
ax.set_ylabel("销量")
ax.bar_label(bars)                           # 在柱顶标数值（3.4+ 支持）
plt.tight_layout()
plt.savefig("bar.png", dpi=150)
plt.show()

# 横向柱状图（品类名很长时用）
fig, ax = plt.subplots()
ax.barh(categories, values, color="#3498db")
ax.set_xlabel("销量")
plt.tight_layout()
plt.show()

# 分组柱状图（多系列对比）
import numpy as np
x = np.arange(4)
fig, ax = plt.subplots()
ax.bar(x - 0.2, [20, 30, 15, 25], width=0.4, label="上半年", color="#3498db")
ax.bar(x + 0.2, [25, 28, 22, 30], width=0.4, label="下半年", color="#e74c3c")
ax.set_xticks(x); ax.set_xticklabels(categories)
ax.legend()
plt.tight_layout(); plt.show()
```

### 4.3 饼图：占比（✅）

```python
import matplotlib.pyplot as plt

sizes = [40, 30, 20, 10]
labels = ["Python", "JavaScript", "Java", "Go"]
colors = ["#3498db", "#f1c40f", "#e74c3c", "#2ecc71"]

fig, ax = plt.subplots()
ax.pie(sizes, labels=labels, colors=colors, autopct="%1.1f%%",   # 显示百分比
       startangle=90, explode=[0.05, 0, 0, 0])                    # 第一块突出
ax.set_title("编程语言占比")
plt.tight_layout(); plt.show()
```

**注意**：饼图超过 5 块就不直观，优先用柱状图。

### 4.4 散点图：分布与相关性（➕）

```python
import matplotlib.pyplot as plt
import numpy as np

rng = np.random.default_rng(42)
x = rng.normal(50, 15, 200)       # 200 个正态分布数据
y = x * 0.8 + rng.normal(0, 8, 200)

fig, ax = plt.subplots()
scatter = ax.scatter(x, y, c=y, cmap="viridis", alpha=0.7, s=30)   # c 颜色按值，cmap 色带
ax.set_title("身高与体重关系")
fig.colorbar(scatter)             # 颜色条
plt.tight_layout(); plt.show()
```

### 4.5 直方图：数值分布（➕）

```python
import matplotlib.pyplot as plt
import numpy as np

data = np.random.default_rng(7).normal(100, 15, 1000)   # 1000 个数据

fig, ax = plt.subplots()
ax.hist(data, bins=30, color="#3498db", edgecolor="white", alpha=0.8)
ax.axvline(data.mean(), color="#e74c3c", linestyle="--", label=f"均值 {data.mean():.1f}")
ax.set_title("成绩分布")
ax.legend()
plt.tight_layout(); plt.show()
```

### 4.6 子图：一图多画（➕）

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 2, figsize=(10, 8))    # 2 行 2 列
x = range(1, 6)
axes[0, 0].plot(x, [1, 4, 9, 16, 25]); axes[0, 0].set_title("平方")
axes[0, 1].bar(["A", "B"], [10, 20]); axes[0, 1].set_title("柱状")
axes[1, 0].pie([30, 70], labels=["a", "b"]); axes[1, 0].set_title("饼图")
axes[1, 1].scatter([1, 2, 3], [3, 1, 2]); axes[1, 1].set_title("散点")
plt.tight_layout()
plt.savefig("subplots.png", dpi=150)
plt.show()
```

### 4.7 Pandas 直接画图（✅ 数据分析标配）

```python
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]

df = pd.read_csv("sales.csv", encoding="utf-8-sig")
df["日期"] = pd.to_datetime(df["日期"])

# 一行出图
df.groupby("月份")["金额"].sum().plot(kind="line", title="月度趋势", figsize=(8, 4))
df.groupby("地区")["金额"].sum().plot(kind="bar", title="地区对比")
df["金额"].plot(kind="hist", bins=20, title="金额分布")

plt.tight_layout()
plt.savefig("pandas_chart.png", dpi=150)
plt.show()
```

**kind 可选**：`line` 折线、`bar` 柱状、`barh` 横柱、`pie` 饼、`hist` 直方、`scatter` 散点（需 x/y 参数）、`box` 箱线。

### 4.8 样式与保存细节（➕）

```python
# 内置样式（一键换风格）
plt.style.use("ggplot")        # 好看的手绘风格
plt.style.use("seaborn-v0_8")  # 统计风格
plt.style.use("dark_background")  # 深色

# 常用全局设置
plt.rcParams["figure.figsize"] = (8, 4)      # 默认画布
plt.rcParams["font.size"] = 11
plt.rcParams["axes.grid"] = True

# 保存细节
plt.savefig("chart.png", dpi=200)            # 高清（论文/打印用 300）
plt.savefig("chart.pdf")                     # 矢量图（缩放不模糊）
plt.savefig("chart.jpg", quality=90)         # JPG
```

### 4.9 箱线图与面积图（🧪）

```python
# 箱线图：一组数据的分布（中位数/四分位/异常值）
data = [list(rng.normal(60, 10, 100)) for _ in range(3)]
fig, ax = plt.subplots()
ax.boxplot(data, labels=["班级A", "班级B", "班级C"])
plt.show()

# 面积图：累计趋势
fig, ax = plt.subplots()
ax.fill_between(x, y, alpha=0.4, color="#3498db")
ax.plot(x, y, color="#2980b9")
plt.show()
```

## 第 5 章 实战项目案例（从小白到大神）

### 案例 1（入门级）：自动生成月度报表图

```python
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

months = ["1月", "2月", "3月", "4月", "5月", "6月"]
sales = [12, 15, 13, 18, 16, 22]
costs = [8, 9, 9, 11, 10, 13]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
ax1.plot(months, sales, marker="o", label="销售额", color="#e74c3c")
ax1.plot(months, costs, marker="s", label="成本", color="#3498db")
ax1.set_title("销售额与成本趋势")
ax1.legend(); ax1.grid(True, alpha=0.3)

ax2.bar(months, [s - c for s, c in zip(sales, costs)], color="#27ae60")
ax2.set_title("每月利润")
ax2.bar_label(ax2.containers[0])

plt.tight_layout()
plt.savefig("月度报表.png", dpi=150)
plt.show()
```

### 案例 2（进阶级）：爬虫数据可视化（requests + bs4 + pandas + matplotlib）

```python
"""抓取岗位数据 → 按城市薪资分析 → 画柱状图 + 饼图"""
import requests
import pandas as pd
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ① 抓取
rows = []
for page in range(1, 4):
    resp = requests.get(f"https://example.com/jobs?page={page}",
                        headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    for item in soup.select("div.job"):
        rows.append({
            "城市": item.select_one(".city").get_text(strip=True),
            "薪资下限": float(item.select_one(".salary").get_text(strip=True).replace("K", "").split("-")[0]),
        })

# ② 分析
df = pd.DataFrame(rows)
city_avg = df.groupby("城市")["薪资下限"].mean().sort_values(ascending=False)
counts = df["城市"].value_counts()

# ③ 图一：各城市平均薪资（柱状）
fig, ax = plt.subplots(figsize=(9, 4))
bars = ax.bar(city_avg.index, city_avg.values, color="#3498db")
ax.bar_label(bars, fmt="%.1fK")
ax.set_title("各城市平均薪资下限")
ax.set_ylabel("K / 月")
plt.tight_layout(); plt.savefig("城市薪资.png", dpi=150)

# ④ 图二：岗位数占比（饼图）
fig, ax = plt.subplots()
ax.pie(counts.values, labels=counts.index, autopct="%1.0f%%")
ax.set_title("岗位城市分布")
plt.tight_layout(); plt.savefig("城市分布.png", dpi=150)
plt.show()
```

### 案例 3（综合）：**经营看板**（pandas + matplotlib + openpyxl 出带图 Excel 报告）

```python
"""销售数据 → 4 张子图看板 → 保存 PNG → 嵌入 Excel 报告"""
import pandas as pd
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ① 数据准备
df = pd.read_csv("sales.csv", encoding="utf-8-sig")
df["日期"] = pd.to_datetime(df["日期"])
df["月份"] = df["日期"].dt.strftime("%Y-%m")
df["金额"] = pd.to_numeric(df["金额"], errors="coerce").fillna(0)

# ② 2x2 看板
fig, axes = plt.subplots(2, 2, figsize=(12, 8))
axes[0, 0].plot(df.groupby("月份")["金额"].sum(), marker="o", color="#e74c3c")
axes[0, 0].set_title("月度销售趋势")
axes[0, 1].bar(df.groupby("地区")["金额"].sum().index,
               df.groupby("地区")["金额"].sum().values, color="#3498db")
axes[0, 1].set_title("地区销售对比")
axes[1, 0].pie(df.groupby("类目")["金额"].sum().values,
               labels=df.groupby("类目")["金额"].sum().index, autopct="%1.0f%%")
axes[1, 0].set_title("类目占比")
axes[1, 1].hist(df["金额"], bins=30, color="#27ae60", alpha=0.8)
axes[1, 1].set_title("订单金额分布")
plt.tight_layout()
plt.savefig("看板.png", dpi=150)

# ③ 嵌入 Excel
wb = Workbook()
ws = wb.active
ws.title = "看板"
ws.add_image(XLImage("看板.png"), "A1")
ws2 = wb.create_sheet("明细")
for col, name in enumerate(df.columns, start=1):
    ws2.cell(row=1, column=col, value=name)
for r, row in df.iterrows():
    for c, name in enumerate(df.columns, start=1):
        ws2.cell(row=int(r) + 2, column=c, value=str(row[name]))
wb.save("经营看板.xlsx")
print("已生成：经营看板.xlsx + 看板.png")
```

## 第 6 章 进阶内容（大神之路）

### 6.1 风格统一：写一个"画图配置函数"

```python
def setup_style():
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.sans-serif": ["Microsoft YaHei", "SimHei"],
        "axes.unicode_minus": False,
        "figure.figsize": (8, 4),
        "axes.grid": True,
        "grid.alpha": 0.3,
        "font.size": 11,
    })
# 每个脚本开头调用 setup_style()
```

### 6.2 交互与动画（🧪）

```python
# 鼠标悬停显示数值等交互（需要 mpld3/plotly 等，Matplotlib 原生交互有限）
# 简易动画
import matplotlib.animation as animation
import numpy as np

fig, ax = plt.subplots()
x = np.linspace(0, 2 * np.pi, 100)
line, = ax.plot(x, np.sin(x))

def update(frame):
    line.set_ydata(np.sin(x + frame / 10))
    return line,

ani = animation.FuncAnimation(fig, update, frames=100, interval=50)
ani.save("anim.gif", writer="pillow")
plt.show()
```

### 6.3 双 Y 轴（两组不同量纲的数据）

```python
fig, ax1 = plt.subplots()
ax1.plot(months, sales, color="#e74c3c", label="销售额")
ax1.set_ylabel("销售额（万）")
ax2 = ax1.twinx()                          # 共享 X 轴的第二个 Y 轴
ax2.plot(months, rate, color="#3498db", label="增长率%")
ax2.set_ylabel("增长率（%）")
plt.show()
```

### 6.4 与 Pillow 配合：在图片上叠加图表

Matplotlib 输出 PNG → Pillow 打开后和其他图片拼接、加水印、贴到背景上（见《Pillow》教程）。

## 第 7 章 高频坑与排查（新手必看）

| 坑 | 症状 | 解决 |
| --- | --- | --- |
| 中文显示方块 | 标题/标签是□□□ | `plt.rcParams["font.sans-serif"]=["Microsoft YaHei","SimHei"]` + `axes.unicode_minus=False` |
| savefig 保存空白 | 图片是白的 | savefig 要在 show() 之前；或关窗口后重新生成 |
| 图例不显示 | 没有 legend | `plot(..., label="xx")` 后必须 `plt.legend()` |
| 柱子上没数值 | 看不到具体值 | `ax.bar_label(bars)` |
| 多张图叠在一起 | 子图互相挤 | 每张图之间 `plt.figure()` 或 `fig, ax = subplots()`；最后 `tight_layout()` |
| 不弹窗口 | show 没效果（服务器） | 服务器用 savefig；本地检查后端：`plt.get_backend()` |
| 坐标轴刻度太密 | 挤成一团 | `plt.xticks(rotation=45)` 旋转；`ax.tick_params(axis="x", rotation=45)` |
| 折线图看着像乱码线 | x 不是数值 | 把 x 转成数值/日期类型 |
| 保存的图模糊 | 分辨率低 | `savefig(..., dpi=200/300)` |
| 负号显示方块 | -5 显示成方块 | `axes.unicode_minus=False` |
| 中文标签重叠 | 柱状图 x 轴文字叠 | `plt.tight_layout()` + `rotation=45` |

## 第 8 章 学习路径与自测

**学习路径**：
1. 折线图 + title/label/legend（半天）
2. 柱状图 + bar_label + 分组柱状（半天）
3. 饼图 + 散点图（半天）
4. 直方图 + 箱线图（半天）
5. 子图 subplots（半天）
6. 中文字体与全局样式（半天，必配）
7. Pandas 直接画图（半天）
8. 案例 1→3 手写（2 天）
9. 双 Y 轴 + 动画 + 高清导出（1 天）
10. 把图表嵌入 Excel/报告（1 天）

**自测题**：
1. `plt.plot` 和 `ax.plot` 有什么区别？为什么推荐后者？
2. 中文显示成方块怎么解决？（两行代码）
3. 怎么在柱子上显示数值？
4. 一图多画用哪个 API？
5. savefig 空白是什么原因？
6. Pandas 的 `df.plot(kind="bar")` 里的 kind 都有哪些？
7. 怎么让 X 轴标签不重叠？
8. 散点图怎么按值着色？
9. 导出高清图片用什么参数？
10. 综合：描述"抓数据 → pandas 统计 → 4 子图看板 → 嵌入 Excel"的流程。

**答案提示**：
1. pyplot 是全局式快捷入口；ax 是坐标系对象，多子图/精细控制更清晰。正式项目用 `fig, ax = plt.subplots()`。
2. `plt.rcParams["font.sans-serif"]=["Microsoft YaHei","SimHei"]` 和 `plt.rcParams["axes.unicode_minus"]=False`。
3. `bars = ax.bar(...); ax.bar_label(bars)`。
4. `fig, axes = plt.subplots(2, 2)`。
5. 在 `plt.show()` 之后才 savefig，窗口关闭导致画布清空；先 savefig 再 show。
6. line/bar/barh/pie/hist/scatter/box。
7. `plt.xticks(rotation=45)` 或 `ax.tick_params(axis="x", rotation=45)`，配合 `tight_layout()`。
8. `ax.scatter(x, y, c=y, cmap="viridis")`。
9. `plt.savefig("x.png", dpi=300)`。
10. 参考案例 3：read_csv → groupby/agg → subplots 画 4 图 → savefig → openpyxl add_image。

<hr>

> 下一篇：《Selenium》——传统浏览器自动化王者，和 Playwright 对比着学，一通百通。
