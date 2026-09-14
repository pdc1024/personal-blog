# 第三方库全面教程 · Pandas

> 面向初学者：这是**零基础起步**的数据分析库全套教程，假设你只会最基础 Python 语法和列表/字典。术语第一次出现都有白话解释。
> 适用版本：Pandas 2.x ｜ 配套知识：配合《NumPy》（底层计算）、《Matplotlib》（画图）、《Openpyxl》（Excel 落盘）、配合《Requests/BeautifulSoup4/Playwright》（数据采集后分析）。
> 学习目标：从"只会用 Excel 手动统计"到"用代码完成 读取→清洗→筛选→统计→分组→导出 的完整数据分析流水线"。

## 第 1 章 这个库是什么

### 1.1 一句话认识 Pandas

**Pandas** 是 Python 的**数据分析第一库**。它的核心是 **DataFrame（数据表）**——一个像 Excel 表格一样、带行列标签的二维数据结构。有了它，"读 CSV/Excel、筛选数据、排序、分组统计、合并表格、导出结果"全部变成**几行代码**。

```python
import pandas as pd

df = pd.read_csv("销售数据.csv")        # 一行读 CSV
print(df.head())                        # 看前 5 行
print(df["销售额"].sum())               # 销售额总和
print(df.groupby("地区")["销售额"].sum())  # 按地区汇总
```

### 1.2 为什么需要它

- **数据处理是程序员的日常**：日志分析、报表生成、数据清洗、爬虫结果整理……都要和表格数据打交道。
- **Python 原生写法太累**：用列表+循环处理 10 万行数据，又慢又难写；Pandas 底层用 C 实现，**快几十倍**，且 API 极简。
- 它是整个 Python 数据生态的地基：数据科学、机器学习（sklearn）、绘图（matplotlib）都建立在 Pandas 之上。

### 1.3 和 Excel 的对应关系

| 概念 | Excel | Pandas |
| --- | --- | --- |
| 工作簿里的表 | Sheet | DataFrame |
| 一列数据 | 列 | Series（带名字的一列） |
| 单元格 | 单元格 | df.loc[行, 列] |
| 筛选 | 筛选/高级筛选 | df[条件] |
| 透视表 | 数据透视表 | groupby + agg |
| 公式 | =SUM(A:A) | df["列"].sum() |

## 第 2 章 核心概念与原理

### 2.1 DataFrame 和 Series：两件套

- **Series**：一列数据（带索引），像"带标签的一维数组"。
- **DataFrame**：多列组成的表格（二维），每列是一个 Series，共享行索引。

```
      姓名   年龄   城市
0    张三    25    广州     ← 行索引 0,1,2...
1    李四    30    北京
2    王五    28    上海
      ↑列名
```

### 2.2 索引（Index）：行的"标签"

每行有一个**索引**（默认 0,1,2…），可以理解为行的"名字"。按索引取行用 `.loc` / `.iloc`（见 4.3）。索引在合并、对齐数据时非常关键。

### 2.3 布尔索引：筛选的底层原理

`df[df["年龄"] > 28]` 这种写法叫**布尔索引**：`df["年龄"] > 28` 先生成一个 True/False 序列（每行是否满足），再把这个序列当作"行过滤器"传给 df。这是 Pandas 最核心、最高频的用法，务必吃透。

### 2.4 NaN：缺失值

表格里缺数据时显示 **NaN**（Not a Number）。NaN 会"传染"：任何数和 NaN 运算结果都是 NaN。所以分析前通常要处理缺失值（`dropna` 删 / `fillna` 填）。

## 第 3 章 安装与版本

```bash
pip install pandas
```

- 当前稳定版 2.x。导入约定：`import pandas as pd`（大家都这么写）。
- 读 Excel 需要额外装 `openpyxl`（`pip install openpyxl`）。
- 画图需要 `matplotlib`。

## 第 4 章 API 全面讲解（✅ = 必会 ｜ ➕ = 推荐 ｜ 🧪 = 进阶）

### 4.1 创建数据（✅）

```python
import pandas as pd

# ① 从字典（列名 → 列表）——最常用
df = pd.DataFrame({
    "姓名": ["张三", "李四", "王五"],
    "年龄": [25, 30, 28],
    "城市": ["广州", "北京", "上海"],
})

# ② 从列表的列表（自动 0,1,2 列名）
df2 = pd.DataFrame([[1, 2], [3, 4]], columns=["A", "B"])

# ③ 从 Series
s = pd.Series([10, 20, 30], name="价格")

# ④ 从文件（最常用入口，见 4.9）
# df = pd.read_csv("data.csv")
```

### 4.2 看数据：上手三件套（✅）

```python
df.head()              # 前 5 行（看数据长什么样）
df.head(10)            # 前 10 行
df.tail(3)             # 后 3 行
df.info()              # 总览：行数、每列类型、缺失值（分析前必看！）
df.describe()          # 数值列统计：均值/标准差/最小最大/四分位
df.shape               # (行数, 列数)
df.columns             # 列名列表
df.index               # 行索引
df.dtypes              # 每列类型
len(df)                # 行数
```

### 4.3 取数据：列、行、单元格（✅ 必须全掌握）

```python
# 取列
df["年龄"]                        # 一列 → Series
df[["姓名", "城市"]]              # 多列 → DataFrame
df.年龄                           # 简写（列名是合法标识符时可用，不推荐）

# 取行（用位置）
df.iloc[0]                        # 第 1 行（位置索引）
df.iloc[1:3]                      # 第 2-3 行（切片）
df.iloc[[0, 2]]                   # 第 1、3 行

# 取行（用索引标签）——loc 是按"行索引名"
df.loc[0]                         # 索引为 0 的行
df.loc[df["年龄"] > 28]           # 布尔索引筛选（见 2.3）

# 取单元格
df.iloc[0, 1]                     # 第 1 行第 2 列
df.loc[0, "年龄"]                 # 索引 0 行的"年龄"列
df.at[0, "年龄"]                  # 更快地取单个值
```

**记忆口诀**：`iloc` = 按位置（整数），`loc` = 按标签/条件。

### 4.4 筛选与排序（✅ 最高频操作）

```python
# 单条件
adults = df[df["年龄"] >= 18]

# 多条件（注意：用 & 和 |，不是 and/or；每个条件都要括号）
df[(df["年龄"] >= 18) & (df["城市"] == "广州")]
df[(df["城市"] == "广州") | (df["城市"] == "深圳")]

# 否定
df[~(df["城市"] == "广州")]

# 列值在某个集合里
df[df["城市"].isin(["广州", "上海"])]

# 字符串包含
df[df["姓名"].str.contains("张")]

# 排序
df.sort_values("年龄")                        # 升序
df.sort_values("年龄", ascending=False)       # 降序
df.sort_values(["城市", "年龄"], ascending=[True, False])  # 多列排序

# 去重
df.drop_duplicates(subset=["姓名"])           # 按姓名去重，保留第一个
```

### 4.5 新增/修改/删除列（✅）

```python
# 新列
df["是否成年"] = df["年龄"] >= 18
df["年薪"] = df["年龄"] * 10000
df["组合"] = df["姓名"] + "-" + df["城市"]

# 修改列（条件赋值——必须用 .loc，否则有 SettingWithCopyWarning）
df.loc[df["年龄"] < 28, "等级"] = "青年"
df.loc[df["年龄"] >= 28, "等级"] = "中年"

# 删除列/行
df.drop(columns=["组合"])               # 删列
df.drop(index=0)                        # 删行
```

**⚠️ 链式赋值警告（SettingWithCopyWarning）**：`df2 = df[条件]; df2["新列"] = x` 会警告且可能不生效。正确做法：要么用 `df.loc[条件, "新列"] = x` 直接在原表改，要么先 `.copy()`：

```python
df2 = df[df["年龄"] > 20].copy()   # copy 之后随便改
```

### 4.6 分组与聚合（✅ 数据分析的灵魂）

```python
# 按城市分组，统计每组的年龄均值
df.groupby("城市")["年龄"].mean()

# 多种统计一起算
df.groupby("城市")["年龄"].agg(["mean", "max", "min", "count"])

# 对多个列各算各的
df.groupby("城市").agg({"年龄": "mean", "姓名": "count"})

# 分组后排序取前 N（每组最大的）
df.groupby("城市").apply(lambda g: g.nlargest(1, "年龄"))

# 透视表（Excel 透视表的感觉）
pd.pivot_table(df, index="城市", columns="等级", values="年龄", aggfunc="mean")
```

### 4.7 缺失值处理（➕）

```python
df.isna()                    # 每个位置是否缺失（True/False 表）
df.isna().sum()              # 每列缺失数量（分析必查）
df.dropna()                  # 删掉有缺失的行
df.dropna(subset=["年龄"])    # 只按某列判断
df.fillna(0)                 # 缺失填 0
df.fillna(df["年龄"].mean())  # 缺失填均值
df["年龄"] = df["年龄"].fillna(method="ffill")   # 用上一个有效值填充（时间序列）
```

### 4.8 数据清洗常用（➕）

```python
# 类型转换
df["年龄"] = df["年龄"].astype(int)          # 转整数
df["日期"] = pd.to_datetime(df["日期"])       # 转日期
df["金额"] = pd.to_numeric(df["金额"], errors="coerce")  # 转数字，转不了的变 NaN

# 字符串清洗
df["姓名"] = df["姓名"].str.strip()            # 去首尾空格
df["电话"] = df["电话"].str.replace("-", "")   # 替换

# 重命名
df.rename(columns={"姓名": "name"}, inplace=True)

# 重置索引
df.reset_index(drop=True)      # 筛选/删除后索引变乱，重置回 0,1,2...
```

### 4.9 文件读写（✅ 最常用的入口和出口）

```python
# 读
df = pd.read_csv("data.csv")                      # CSV（默认 utf-8）
df = pd.read_csv("data.csv", encoding="gbk")      # 中文乱码时试 gbk
df = pd.read_csv("data.csv", encoding="utf-8-sig")  # 带 BOM 的 utf-8
df = pd.read_excel("data.xlsx")                   # Excel（需 openpyxl）
df = pd.read_excel("data.xlsx", sheet_name="Sheet2")
df = pd.read_json("data.json")
df = pd.read_sql("SELECT * FROM posts", engine)   # 数据库

# 写
df.to_csv("out.csv", index=False, encoding="utf-8-sig")  # Excel 打开不乱码
df.to_excel("out.xlsx", index=False)
df.to_json("out.json", orient="records", force_ascii=False)
```

> **编码三兄弟**：读中文 CSV 乱码 → 试 `encoding="gbk"`；写出给 Excel → 用 `utf-8-sig`（带 BOM，Excel 才不乱码）。

### 4.10 合并与连接（🧪 进阶）

```python
# 上下拼接（行方向，列结构相同）
pd.concat([df1, df2], ignore_index=True)

# 左右合并（像 SQL JOIN，按关键列对齐）
pd.merge(df_a, df_b, on="用户ID", how="inner")
# how: inner(交集)/left(左全)/right(右全)/outer(并集)
```

### 4.11 时间序列（🧪）

```python
df["日期"] = pd.to_datetime(df["日期"])
df.set_index("日期", inplace=True)
df["2026-09":]                       # 按日期切片
df.resample("M").sum()               # 按月汇总（M=月，D=天，H=小时）
df["月份"] = df.index.month          # 取月份列
```

## 第 5 章 实战项目案例（从小白到大神）

### 案例 1（入门级）：销售报表一键统计

```python
import pandas as pd

df = pd.read_csv("sales.csv", encoding="utf-8-sig")
print(df.info())

# 总销售额、订单数
print("总销售额：", df["金额"].sum())
print("订单数：", len(df))

# 按地区统计
by_region = df.groupby("地区")["金额"].agg(["sum", "count", "mean"]).round(2)
by_region.columns = ["总金额", "订单数", "平均单价"]
print(by_region.sort_values("总金额", ascending=False))

# 按月份趋势
df["日期"] = pd.to_datetime(df["日期"])
df["月份"] = df["日期"].dt.strftime("%Y-%m")
print(df.groupby("月份")["金额"].sum())

# 前 10 大客户
top = df.groupby("客户")["金额"].sum().nlargest(10)
print(top)
```

### 案例 2（进阶级）：爬虫数据清洗统计（requests + bs4 + pandas）

```python
import requests
import pandas as pd
from bs4 import BeautifulSoup

# ① 抓取
rows = []
for page in range(1, 4):
    resp = requests.get(f"https://example.com/jobs?page={page}",
                        headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    for item in soup.select("div.job"):
        rows.append({
            "职位": item.select_one(".name").get_text(strip=True),
            "薪资": item.select_one(".salary").get_text(strip=True),
            "城市": item.select_one(".city").get_text(strip=True),
            "经验": item.select_one(".exp").get_text(strip=True),
        })

# ② 清洗：把"15K-25K"拆成数值列
df = pd.DataFrame(rows)
def parse_salary(s):
    s = s.replace("K", "").replace("k", "")
    parts = s.split("-")
    return float(parts[0]) if parts else None
df["薪资下限"] = df["薪资"].apply(parse_salary)

# ③ 分析
print("岗位总数：", len(df))
print(df.groupby("城市")["薪资下限"].mean().round(1).sort_values(ascending=False))
print(df["经验"].value_counts())

# ④ 导出
df.to_csv("jobs_clean.csv", index=False, encoding="utf-8-sig")
```

### 案例 3（综合）：**多源数据合并 + 指标计算 + Excel 多表报告**（pandas + openpyxl + matplotlib 见 Matplotlib 教程）

```python
"""把 订单表 + 商品表 + 用户表 三份 CSV 合并分析，输出 Excel 多 Sheet 报告"""
import pandas as pd
from openpyxl import Workbook

# ① 读三张表
orders = pd.read_csv("orders.csv", encoding="utf-8-sig")
products = pd.read_csv("products.csv", encoding="utf-8-sig")
users = pd.read_csv("users.csv", encoding="utf-8-sig")

# ② 合并：订单关联商品（拿商品名/类目），关联用户（拿城市）
df = orders.merge(products, on="商品ID", how="left")
df = df.merge(users, on="用户ID", how="left")

# ③ 计算订单金额 = 数量 × 单价（处理缺失）
df["金额"] = df["数量"].fillna(0) * df["单价"].fillna(0)

# ④ 指标
total = df["金额"].sum()
by_cat = df.groupby("类目")["金额"].sum().sort_values(ascending=False)
by_city = df.groupby("城市")["金额"].sum().sort_values(ascending=False)
repurchase = df.groupby("用户ID")["订单ID"].count()
repeat_rate = (repurchase > 1).mean() * 100

# ⑤ openpyxl 输出多 Sheet 报告
wb = Workbook()
ws = wb.active
ws.title = "总览"
ws.append(["指标", "数值"])
ws.append(["总销售额", round(total, 2)])
ws.append(["重复购买率%", round(repeat_rate, 2)])

ws2 = wb.create_sheet("类目销售")
ws2.append(["类目", "金额"])
for k, v in by_cat.items():
    ws2.append([k, round(v, 2)])

ws3 = wb.create_sheet("城市销售")
ws3.append(["城市", "金额"])
for k, v in by_city.items():
    ws3.append([k, round(v, 2)])

wb.save("经营报告.xlsx")
print("报告已生成：总销售额", round(total, 2), "重复购买率", round(repeat_rate, 2), "%")
```

## 第 6 章 进阶内容（大神之路）

### 6.1 性能技巧：大数据量不卡

```python
# ① 只读需要的列
df = pd.read_csv("big.csv", usecols=["日期", "金额"])

# ② 用向量化代替循环（Pandas 精髓）
# 慢：for i in range(len(df)): df.loc[i,"x"] = df.loc[i,"a"]*2
# 快：df["x"] = df["a"] * 2

# ③ apply 也不要滥用，能用向量化就用向量化
# ④ 大文件分块读
chunks = pd.read_csv("big.csv", chunksize=100000)
total = sum(chunk["金额"].sum() for chunk in chunks)
```

### 6.2 apply 自定义函数（万金油）

```python
def 评分等级(score):
    if score >= 90: return "A"
    if score >= 60: return "B"
    return "C"

df["等级"] = df["分数"].apply(评分等级)
```

### 6.3 与 Matplotlib 无缝画图

```python
import matplotlib.pyplot as plt
df.groupby("月份")["金额"].sum().plot(kind="bar")
plt.title("月度销售趋势")
plt.savefig("趋势.png", dpi=150)
plt.show()
```

### 6.4 与机器学习接轨

Pandas 是 sklearn 的标准输入格式：`X = df[["特征列"]]`，`y = df["标签列"]`，直接 `model.fit(X, y)`。Pandas 学的就是"把数据准备好"这一半。

## 第 7 章 高频坑与排查（新手必看）

| 坑 | 症状 | 解决 |
| --- | --- | --- |
| 中文乱码 | 读 CSV 乱码 / Excel 打开乱码 | 读用 `encoding="gbk"` 试；写用 `utf-8-sig` |
| 链式赋值警告 | SettingWithCopyWarning | 用 `df.loc[条件, "列"] = 值` 或先 `.copy()` |
| 布尔条件写 and/or | `ValueError: truth value of a Series is ambiguous` | 用 `&` / `\|`，每个条件加括号 |
| NaN 参与计算 | 结果全是 NaN | 先 `dropna()` 或 `fillna()` |
| 筛选后索引错乱 | 行号不是 0,1,2 | `reset_index(drop=True)` |
| 列名有空格/中文 | `df.列名` 取不到 | 用 `df["列名"]`；先 `df.columns = [c.strip() for c in df.columns]` |
| inplace 失效 | 修改没生效 | inplace=True 或重新赋值 `df = df.sort_values(...)` |
| 类型不对 | 字符串当数字 | `pd.to_numeric(..., errors="coerce")` / `astype(int)` |
| read_excel 报错 | 缺库 | `pip install openpyxl` |
| 改了 df 原表也变 | 意外影响原数据 | 明确要独立副本时用 `.copy()` |

## 第 8 章 学习路径与自测

**学习路径**：
1. 创建 DataFrame + head/info/describe（半天）
2. 取列/取行 iloc/loc（1 天）
3. 布尔筛选 + 排序（1 天）
4. 新增/修改列 + 去重（半天）
5. groupby 分组统计（1 天，重点）
6. 缺失值 + 类型转换（半天）
7. 文件读写（半天）
8. 案例 1→3 手写（2 天）
9. 合并 concat/merge（1 天）
10. 时间序列 + 性能优化（1 天）

**自测题**：
1. DataFrame 和 Series 的区别？
2. `df.iloc[0]` 和 `df.loc[0]` 区别？
3. `df[df["年龄"] > 18]` 为什么能筛选？底层机制是什么？
4. groupby 之后怎么拿到多列统计？
5. 写 CSV 给 Excel 用，为什么用 utf-8-sig？
6. 怎么处理缺失值？（至少三种）
7. SettingWithCopyWarning 怎么消除？
8. 两个表怎么按某列合并？
9. 100 万行数据，怎么避免卡死？
10. 综合：描述 抓取→清洗→分组统计→导出 Excel 每步用 pandas 的哪些 API？

**答案提示**：
1. Series 是一列（一维带标签），DataFrame 是多列表格（二维），DataFrame 的每列是 Series。
2. iloc 按位置（整数 0,1,2）；loc 按索引标签或布尔条件。
3. 内部是先算布尔序列，再按 True/False 过滤行（布尔索引）。
4. `.groupby("列").agg({"列A": "mean", "列B": "count"})` 或 `.agg(["mean","max"])`。
5. utf-8-sig 带 BOM，Excel 识别为 UTF-8 不乱码。
6. dropna() 删行、fillna(0/均值/前值) 填充、subset 指定列判断。
7. 用 `df.loc[条件, "列"]=值` 或先 `.copy()` 再改。
8. `pd.merge(df1, df2, on="键", how="inner")`。
9. 只读需要列 usecols、向量化代替循环、分块 read_csv(chunksize)。
10. 见案例 2/3：read_csv → groupby/agg → merge → to_excel/to_csv。

<hr>

> 下一篇：《NumPy》——Pandas 的底层引擎，学会用数组批量算数，告别 for 循环。
