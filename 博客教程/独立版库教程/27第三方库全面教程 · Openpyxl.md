# 第三方库全面教程 · Openpyxl

> 面向初学者：这是**零基础起步**的 Excel 读写库全套教程，假设你只会最基础 Python 语法（列表、字典、for）。术语第一次出现都有白话解释。
> 适用版本：Openpyxl 3.1 ｜ 配套知识：配合《Pandas》（数据分析后落盘）、配合《Matplotlib/Pillow》（图表与图片嵌入）、配合《Requests/Playwright》（自动化报表）。
> 学习目标：从"手动复制粘贴做表"到"代码自动生成带样式、带图表、带图片的专业 Excel 报表"。

## 第 1 章 这个库是什么

### 1.1 一句话认识 Openpyxl

**Openpyxl** 是 Python 读写 **Excel（.xlsx）文件**最主流的库：创建表格、写入数据、设置样式（字体/颜色/边框/合并）、插入图表、嵌入图片、读取已有 Excel，全部代码化。

```python
from openpyxl import Workbook

wb = Workbook()                 # 新建工作簿
ws = wb.active                  # 拿默认工作表
ws["A1"] = "姓名"               # 直接给单元格赋值
ws["A2"] = "张三"
wb.save("demo.xlsx")            # 保存
```

### 1.2 为什么需要它（什么时候该用）

| 场景 | 用 Pandas | 用 Openpyxl |
| --- | --- | --- |
| 快速读写数据 | ✅（一行搞定） | ✅ |
| 复杂样式（合并/边框/配色） | ❌ 弱 | ✅ **强项** |
| 图表（柱状/折线/饼图） | 配合 matplotlib | ✅ **原生图表** |
| 嵌入图片 | 弱 | ✅ |
| 公式 | 弱 | ✅ |
| 读取并修改已有复杂报表 | 会破坏样式 | ✅ |

**分工建议**：Pandas 管"数据计算"，Openpyxl 管"精美呈现"——先 pandas 算好，再 openpyxl 排版导出。

### 1.3 基本概念

- **Workbook（工作簿）**：一个 .xlsx 文件。
- **Worksheet（工作表）**：工作簿里的 Sheet。
- **Cell（单元格）**：一个格子，用 "A1" 坐标或 (行, 列) 定位。
- **行/列**：从 1 开始计数（A 列 = 第 1 列）。

## 第 2 章 核心概念与原理

### 2.1 单元格坐标两种写法

```python
ws["A1"] = "值"            # 字母数字坐标
ws.cell(row=1, column=1, value="值")   # 行列数字（循环写数据时用这个）
```

### 2.2 .xlsx 的本质

.xlsx 是 zip 压缩的 XML 文件集合，Openpyxl 负责把它变成好用的 Python 对象。**旧格式 .xls 不支持**（那是老库 xlrd/xlwt 的领域）。

### 2.3 三种创建方式

```python
from openpyxl import Workbook
from openpyxl import load_workbook

wb = Workbook()                     # 新建
ws = wb.active                      # 默认 Sheet（名为 "Sheet"）
ws2 = wb.create_sheet("数据")       # 新建命名 Sheet

# 打开已有文件
wb2 = load_workbook("report.xlsx")
ws3 = wb2["Sheet1"]                 # 按名字取 Sheet
```

## 第 3 章 安装与版本

```bash
pip install openpyxl
```

当前稳定版 3.1。**Pandas 读 Excel 也依赖它**（`pd.read_excel` / `to_excel` 需要 openpyxl）。导入：`from openpyxl import Workbook, load_workbook`。

## 第 4 章 API 全面讲解（✅ = 必会 ｜ ➕ = 推荐 ｜ 🧪 = 进阶）

### 4.1 写入数据（✅）

```python
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
ws.title = "销售数据"                # 重命名 Sheet

# 单个单元格
ws["A1"] = "姓名"
ws["B1"] = "销售额"
ws["A2"] = "张三"
ws["B2"] = 15000

# 一行一行追加（从当前最后一行往下）
ws.append(["李四", 12000])
ws.append(["王五", 18000])

# 用 cell() 循环写入（写表头）
headers = ["月份", "金额", "订单数"]
for col, h in enumerate(headers, start=1):
    ws.cell(row=1, column=col, value=h)

wb.save("sales.xlsx")
```

### 4.2 读取数据（✅）

```python
from openpyxl import load_workbook

wb = load_workbook("sales.xlsx", data_only=True)   # data_only=True 读公式计算结果
ws = wb.active

print(ws["A1"].value)              # 单个单元格的值
print(ws.max_row, ws.max_column)   # 最大行/列（数据范围）
print(ws["A2:B4"])                 # 切片区域（元组的元组）

# 遍历所有行
for row in ws.iter_rows(min_row=1, max_row=ws.max_row, values_only=True):
    print(row)                     # 每行是一个元组 (姓名, 销售额)

# 遍历所有列（转置视角）
for col in ws.iter_cols(min_col=1, max_col=2, values_only=True):
    print(col)
```

**⚠️ 公式读取**：文件里有公式（如 `=SUM(B2:B4)`）时，`load_workbook` 默认读到的**是公式字符串**不是结果。要读结果必须 `data_only=True`（且文件必须被 Excel 保存过，否则没有缓存结果）。

### 4.3 样式：字体、颜色、对齐、边框（✅ 报表美观核心）

```python
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl import Workbook

wb = Workbook()
ws = wb.active

# 字体
ws["A1"].font = Font(name="微软雅黑", size=12, bold=True, color="FFFFFF")

# 背景填充
ws["A1"].fill = PatternFill("solid", fgColor="3498DB")   # 实心填充，fgColor 是颜色

# 对齐
ws["A1"].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

# 边框（thin 细线；Side 定义一边）
thin = Side(style="thin", color="BDD7EE")
ws["A1"].border = Border(top=thin, bottom=thin, left=thin, right=thin)

# 行高列宽
ws.row_dimensions[1].height = 28
ws.column_dimensions["A"].width = 15
ws.column_dimensions["B"].width = 20

# 合并单元格
ws.merge_cells("A1:C1")
ws["A1"] = "2026 年销售报表"       # 合并后内容写在左上角
ws.unmerge_cells("A1:C1")          # 取消合并
```

**颜色对照**：`3498DB` 蓝、`E74C3C` 红、`2ECC71` 绿、`F1C40F` 黄、`95A5A6` 灰。格式是 6 位十六进制（无 #）。

### 4.4 条件格式（➕ 自动高亮）

```python
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import PatternFill
from openpyxl import Workbook

wb = Workbook()
ws = wb.active
for i, v in enumerate([100, 200, 150, 300, 250], start=1):
    ws.cell(row=i, column=1, value=v)

# 大于 200 的格子变红
red = PatternFill("solid", fgColor="E74C3C")
ws.conditional_formatting.add(
    "A1:A5",
    CellIsRule(operator="greaterThan", formula=["200"], fill=red))
wb.save("cond.xlsx")
```

### 4.5 图表（➕ 原生图表，比截图更专业）

```python
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference

wb = Workbook()
ws = wb.active
rows = [["月份", "销售额"], ["1月", 120], ["2月", 150], ["3月", 130], ["4月", 180]]
for r in rows:
    ws.append(r)

# 柱状图
chart = BarChart()
chart.title = "月度销售"
chart.x_axis.title = "月份"
chart.y_axis.title = "销售额"
data = Reference(ws, min_col=2, min_row=1, max_row=5)       # 数据区域（含表头）
cats = Reference(ws, min_col=1, min_row=2, max_row=5)       # 分类（X 轴标签）
chart.add_data(data, titles_from_data=True)
chart.set_categories(cats)
ws.add_chart(chart, "D2")          # 图表放在 D2 位置

# 其他图表类型：LineChart 折线、PieChart 饼图、ScatterChart 散点
from openpyxl.chart import LineChart, PieChart
wb.save("chart.xlsx")
```

### 4.6 插入图片（➕）

```python
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils.units import pixels_to_EMU

wb = Workbook()
ws = wb.active
ws["A1"] = "图表看板"

img = XLImage("chart.png")         # 打开图片文件
img.width = 600                    # 设置显示尺寸
img.height = 400
ws.add_image(img, "A2")            # 放到 A2 单元格

wb.save("with_image.xlsx")
```

### 4.7 公式（➕）

```python
ws["A1"] = 100
ws["A2"] = 200
ws["A3"] = "=SUM(A1:A2)"           # 写入公式字符串
# 注意：openpyxl 不计算公式，公式要 Excel/WPS 打开后才会计算
```

### 4.8 冻结窗格与筛选（➕ 大表友好）

```python
ws.freeze_panes = "A2"             # 冻结第 1 行（滚动时表头不动）
ws.auto_filter.ref = "A1:C100"     # 表头加筛选下拉
```

## 第 5 章 实战项目案例（从小白到大神）

### 案例 1（入门级）：自动生成带样式的成绩单

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

data = [
    ("张三", 85, 92, 78),
    ("李四", 66, 88, 95),
    ("王五", 90, 70, 60),
    ("赵六", 72, 84, 90),
]

wb = Workbook()
ws = wb.active
ws.title = "成绩单"

# 表头
headers = ["姓名", "语文", "数学", "英语", "总分"]
header_fill = PatternFill("solid", fgColor="3498DB")
header_font = Font(bold=True, color="FFFFFF", name="微软雅黑")
thin = Side(style="thin", color="BDD7EE")
for col, h in enumerate(headers, start=1):
    cell = ws.cell(row=1, column=col, value=h)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center")
    cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)

# 数据 + 总分
for r, (name, ch, ma, en) in enumerate(data, start=2):
    ws.cell(row=r, column=1, value=name)
    ws.cell(row=r, column=2, value=ch)
    ws.cell(row=r, column=3, value=ma)
    ws.cell(row=r, column=4, value=en)
    ws.cell(row=r, column=5, value=ch + ma + en)
    # 不及格标红
    for c in range(2, 6):
        cell = ws.cell(row=r, column=c)
        cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
        if isinstance(cell.value, (int, float)) and cell.value < 60:
            cell.fill = PatternFill("solid", fgColor="F5B7B1")

ws.freeze_panes = "A2"
for col, w in zip("ABCDE", [10, 10, 10, 10, 10]):
    ws.column_dimensions[col].width = w

wb.save("成绩单.xlsx")
print("已生成 成绩单.xlsx")
```

### 案例 2（进阶级）：数据采集 → Excel 报表（requests + bs4 + openpyxl）

```python
"""抓取公告列表 → 生成带样式的 Excel 报表"""
import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

# ① 采集
rows = []
for page in range(1, 4):
    resp = requests.get(f"https://example.com/notices?page={page}",
                        headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    for item in soup.select("tr.notice"):
        rows.append([
            item.select_one(".title").get_text(strip=True),
            item.select_one(".dept").get_text(strip=True),
            item.select_one(".date").get_text(strip=True),
        ])

# ② 生成报表
wb = Workbook()
ws = wb.active
ws.title = "公告列表"
headers = ["标题", "部门", "日期"]
for col, h in enumerate(headers, start=1):
    c = ws.cell(row=1, column=col, value=h)
    c.font = Font(bold=True, color="FFFFFF")
    c.fill = PatternFill("solid", fgColor="2C3E50")
    c.alignment = Alignment(horizontal="center")
for r, row in enumerate(rows, start=2):
    for c, v in enumerate(row, start=1):
        ws.cell(row=r, column=c, value=v)
ws.column_dimensions["A"].width = 40
ws.column_dimensions["B"].width = 15
ws.column_dimensions["C"].width = 15
ws.auto_filter.ref = f"A1:C{len(rows) + 1}"
ws.freeze_panes = "A2"
wb.save("公告列表.xlsx")
print("已生成 公告列表.xlsx，共", len(rows), "条")
```

### 案例 3（综合）：**自动化日报系统**（requests + pandas + openpyxl + matplotlib 图嵌入）

```python
"""每日经营日报：抓接口数据 → pandas 汇总 → openpyxl 多 Sheet + 图表 + 图片 一站式生成"""
import requests
import pandas as pd
import matplotlib.pyplot as plt
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Font, PatternFill, Alignment

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

# ① 抓数据（模拟）
resp = requests.get("https://example.com/api/daily",
                    params={"date": "2026-09-15"}, timeout=10)
resp.raise_for_status()
records = resp.json()["items"]          # [{城市, 金额, 订单数}, ...]

# ② pandas 汇总
df = pd.DataFrame(records)
df["金额"] = pd.to_numeric(df["金额"], errors="coerce").fillna(0)
city_sum = df.groupby("城市")["金额"].sum().sort_values(ascending=False)
total = df["金额"].sum()
avg_order = df["金额"].mean()

# ③ matplotlib 出图 → 稍后嵌入
fig, ax = plt.subplots(figsize=(6, 3))
ax.bar(city_sum.index, city_sum.values, color="#3498db")
ax.set_title("城市销售分布")
ax.bar_label(ax.containers[0], fmt="%.0f")
plt.tight_layout()
plt.savefig("city_chart.png", dpi=150)

# ④ openpyxl 组装
wb = Workbook()
# Sheet1 总览
ws = wb.active
ws.title = "总览"
ws.merge_cells("A1:C1")
ws["A1"] = "每日经营日报"
ws["A1"].font = Font(size=16, bold=True)
ws["A1"].alignment = Alignment(horizontal="center")
summary = [["总销售额", round(total, 2)], ["订单数", len(df)], ["平均订单额", round(avg_order, 2)]]
for r, (k, v) in enumerate(summary, start=3):
    ws.cell(row=r, column=1, value=k).font = Font(bold=True)
    ws.cell(row=r, column=2, value=v)
ws.add_image(XLImage("city_chart.png"), "D2")

# Sheet2 明细
ws2 = wb.create_sheet("明细")
for col, name in enumerate(df.columns, start=1):
    c = ws2.cell(row=1, column=col, value=name)
    c.font = Font(bold=True)
    c.fill = PatternFill("solid", fgColor="D6EAF8")
for r, row in df.iterrows():
    for c, name in enumerate(df.columns, start=1):
        ws2.cell(row=int(r) + 2, column=c, value=row[name])

# Sheet3 图表（原生 BarChart）
ws3 = wb.create_sheet("图表")
ws3.append(["城市", "金额"])
for k, v in city_sum.items():
    ws3.append([k, round(v, 2)])
chart = BarChart()
data = Reference(ws3, min_col=2, min_row=1, max_row=len(city_sum) + 1)
cats = Reference(ws3, min_col=1, min_row=2, max_row=len(city_sum) + 1)
chart.add_data(data, titles_from_data=True)
chart.set_categories(cats)
chart.title = "城市销售柱状图"
ws3.add_chart(chart, "D2")

wb.save("经营日报.xlsx")
print("日报已生成：经营日报.xlsx")
```

**这个案例演示了 Openpyxl 的完整能力**：合并单元格、样式、插入图片、原生图表、多 Sheet——一套代码每天自动出正式日报。

## 第 6 章 进阶内容（大神之路）

### 6.1 与 Pandas 双向转换

```python
import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

# pandas → openpyxl（保留 pandas 计算，用 openpyxl 排版）
df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
wb = Workbook()
ws = wb.active
for r in dataframe_to_rows(df, index=False, header=True):
    ws.append(r)

# openpyxl → pandas
wb2 = load_workbook("x.xlsx", data_only=True)
ws2 = wb2.active
data = ws2.iter_rows(values_only=True)
df2 = pd.DataFrame(list(data)[1:], columns=list(data)[0])
```

### 6.2 大数据量：只写模式（write_only）

```python
wb = Workbook(write_only=True)      # 百万行数据内存友好
ws = wb.create_sheet("big")
ws.append(["A", "B"])
for i in range(1000000):
    ws.append([i, i * 2])
wb.save("big.xlsx")
```

### 6.3 样式批量应用与命名样式

```python
from openpyxl.styles import NamedStyle, Font, PatternFill

title_style = NamedStyle(name="title_style")
title_style.font = Font(bold=True, size=14)
title_style.fill = PatternFill("solid", fgColor="3498DB")
wb.add_named_style(title_style)

ws["A1"].style = "title_style"     # 复用
```

### 6.4 保护工作表（只读分享）

```python
ws.protection.sheet = True
ws.protection.password = "123"     # 设密码保护（防修改）
```

## 第 7 章 高频坑与排查（新手必看）

| 坑 | 症状 | 解决 |
| --- | --- | --- |
| 读公式得到公式字符串 | `=SUM(A1:A2)` 不是结果 | `load_workbook(..., data_only=True)`（且文件被 Excel 存过） |
| .xls 打不开 | `InvalidFileException` | Openpyxl 只支持 .xlsx；.xls 用 pandas/xlrd 转 |
| 保存后 Excel 报"文件损坏" | 文件打不开 | 别用 .xls 扩展名存 .xlsx 内容；确认 wb.save 路径扩展名正确 |
| 合并单元格赋值报错 | `AttributeError: 'MergedCell'` | 合并区域只有左上角能写值 |
| 颜色不生效 | 填充没显示 | `PatternFill("solid", fgColor="3498DB")` 必须带 "solid" 和 6 位色 |
| 中文乱码 | Excel 里乱码 | xlsx 内部是 UTF-8，正常不会乱；乱码多半来源是 CSV 场景 |
| 图表不显示 | 打开没图 | 图表引用区域别写成整个列（如 A:A）；确认 Reference 范围 |
| 图片太大 | xlsx 文件暴涨 | 插入前用 Pillow 压缩图片 |
| 遍历时拿到公式值 | 结果不符 | 确认 data_only 参数 |
| 修改已有文件样式丢失 | 原样式没了 | openpyxl 加载后保存会保留大部分；复杂文件（宏、特殊图表）用 load_workbook 后检查 |

## 第 8 章 学习路径与自测

**学习路径**：
1. 新建工作簿 + 写数据 + 保存（半天）
2. 读取已有文件 + 遍历行（半天）
3. 字体/填充/对齐/边框（1 天）
4. 合并单元格 + 行列宽（半天）
5. 条件格式 + 冻结窗格（半天）
6. 原生图表 BarChart/LineChart/PieChart（1 天）
7. 插入图片（半天）
8. 案例 1→3 手写（2 天）
9. Pandas ↔ openpyxl 配合（1 天）
10. 自动化日报 + 定时任务（1-2 天）

**自测题**：
1. `ws["A1"]` 和 `ws.cell(row=1, column=1)` 有什么区别？
2. 读公式结果用什么参数？
3. 怎么把表头做蓝底白字加粗？
4. 合并单元格后给哪个格子赋值？
5. 怎么加原生柱状图？（三个关键步骤）
6. 怎么插入图片并控制大小？
7. 百万行数据怎么避免内存爆炸？
8. 冻结第一行用什么？
9. Openpyxl 和 Pandas 的分工是什么？
10. 综合：描述"抓数据 → pandas 统计 → openpyxl 多 Sheet 报表 → 嵌入图表和图片"流程。

**答案提示**：
1. 都定位单元格；字母坐标直观，cell(row,column) 适合循环变量。
2. `load_workbook(path, data_only=True)`。
3. `cell.fill = PatternFill("solid", fgColor="3498DB")` + `cell.font = Font(bold=True, color="FFFFFF")`。
4. 左上角那个单元格（如 A1:C1 合并 → 写 A1）。
5. `BarChart()` → `chart.add_data(Reference(...))` → `ws.add_chart(chart, "位置")`。
6. `img = XLImage("x.png"); img.width=600; img.height=400; ws.add_image(img, "A1")`。
7. `Workbook(write_only=True)` 只写模式。
8. `ws.freeze_panes = "A2"`。
9. Pandas 算数据，Openpyxl 做样式/图表/排版呈现。
10. 参考案例 3：requests → DataFrame/groupby → matplotlib savefig → openpyxl 多 Sheet + add_image + add_chart。

<hr>

> 下一篇：《PyAutoGUI》——桌面级自动化：控制鼠标键盘，和网页自动化双剑合璧。
