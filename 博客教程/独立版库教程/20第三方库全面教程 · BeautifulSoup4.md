# 第三方库全面教程 · BeautifulSoup4

> 面向初学者：这是**零基础起步**的 HTML 解析库全套教程，假设你只会最基础 Python 语法。术语第一次出现都有白话解释。
> 适用版本：BeautifulSoup4 4.12+（import 时写成 bs4）｜ 配套知识：配合《Requests》抓源码、配合《Pandas》清洗数据、配合《Playwright》解析动态页面。
> 学习目标：从"拿到网页源码不知道怎么看"到"熟练用选择器把网页里的标题、链接、表格数据精准拆出来"。

## 第 1 章 这个库是什么

### 1.1 一句话认识 BeautifulSoup4

**BeautifulSoup4**（简称 bs4）是 Python 的 **HTML/XML 解析库**：把一段网页源码（HTML 字符串）变成一棵"可查找的树"，然后用 `find` / `select` 等语法**精准摘出你想要的任何数据**。

```python
from bs4 import BeautifulSoup

html = "<html><body><h1>你好</h1><a href='/a/1'>链接一</a></body></html>"
soup = BeautifulSoup(html, "html.parser")   # 解析成树
print(soup.find("h1").text)                 # 输出：你好
print(soup.find("a")["href"])               # 输出：/a/1
```

### 1.2 为什么需要它

网页本质是 HTML 字符串。你可以用正则表达式去抠数据（`re.findall(r'<h1>(.*?)</h1>')`），但 HTML 嵌套复杂、写法多变，正则写起来又脆又难维护。**bs4 把 HTML 变成对象树，用语义化语法取数**，代码又好写又抗页面小变动。

### 1.3 与 Requests / Playwright 的分工

| 库 | 负责 | 类比 |
| --- | --- | --- |
| Requests | 把网页源码"拿"回来 | 快递员 |
| **BeautifulSoup4** | 从源码里"拆"出数据 | 拆包裹的人 |
| Playwright | 打开真浏览器拿"渲染后"的源码 | 亲自去店里拿货 |

## 第 2 章 核心概念与原理

### 2.1 HTML 是一棵树

HTML 的标签是**层层嵌套**的：

```html
<html>
  <body>
    <div class="article">
      <h2>标题</h2>
      <p>正文……</p>
    </div>
    <div class="article">
      <h2>标题2</h2>
      <p>正文2……</p>
    </div>
  </body>
</html>
```

bs4 把它变成一棵树：

```
soup (整棵树)
└── html
    └── body
        └── div.article (第 1 篇)
        │   ├── h2 → "标题"
        │   └── p  → "正文……"
        └── div.article (第 2 篇)
            ├── h2 → "标题2"
            └── p  → "正文2……"
```

**术语**：每个标签是一个 **Tag（节点）**，`h2` 的文本是 `.text`，`a` 的链接是 `["href"]`。

### 2.2 解析器：bs4 的"引擎"

`BeautifulSoup(html, "解析器")` 的第二个参数是解析器（底层引擎）：

| 解析器 | 速度 | 依赖 | 说明 |
| --- | --- | --- | --- |
| `"html.parser"` | 中 | Python 自带 | **零依赖，新手首选** |
| `"lxml"` | 快 | pip install lxml | 性能好，爬虫常配 |
| `"html5lib"` | 慢 | pip install html5lib | 最符合浏览器解析，慢 |

> 新手用 `"html.parser"` 起步；跑大量页面再换 `"lxml"`（见《Lxml》教程）。

### 2.3 常见误区：find 与 find_all

- `soup.find(...)`：找**第一个**匹配，没有返回 `None`。
- `soup.find_all(...)`：找**所有**匹配，返回**列表**。
- 对 `find_all` 的**结果继续 find**：`tag.find("span")` 在 tag 内部找。

## 第 3 章 安装与版本

```bash
pip install beautifulsoup4
```

注意：**导入名是 `bs4`**（不是 beautifulsoup4）：

```python
from bs4 import BeautifulSoup   # ✅ 正确
# import beautifulsoup4        # ❌ 不存在这个名字
```

当前稳定版 4.12+。可选装 lxml 提速：`pip install lxml`。

## 第 4 章 API 全面讲解（✅ = 必会 ｜ ➕ = 推荐 ｜ 🧪 = 进阶）

### 4.1 创建对象：三种数据来源（✅）

```python
from bs4 import BeautifulSoup

# ① 从字符串
soup = BeautifulSoup("<html><h1>hi</h1></html>", "html.parser")

# ② 从文件
with open("page.html", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# ③ 从 Requests 拿到的网页（爬虫标配）
import requests
resp = requests.get("https://example.com", timeout=10)
soup = BeautifulSoup(resp.text, "html.parser")
```

### 4.2 find / find_all（✅ 最核心）

```python
soup.find("h1")                          # 第一个 h1 标签
soup.find_all("a")                       # 所有 a 标签（列表）
soup.find_all("a", limit=5)              # 最多 5 个

# 按属性过滤（class 是 Python 关键字，要写成 class_！）
soup.find_all("div", class_="card")      # 所有 class="card" 的 div
soup.find("a", id="next")                # id 为 next 的 a
soup.find_all("a", href=True)            # 带 href 属性的 a

# 组合：class 里含多个值时，传列表表示"同时包含"
soup.find_all("div", class_=["card", "hot"])

# 用字典过滤任意属性
soup.find_all("input", attrs={"type": "checkbox", "name": "agree"})
```

**⚠️ class 陷阱**：HTML 属性 `class` 与 Python 关键字同名，bs4 规定写成 `class_="card"`（带下划线）。写成 `class="card"` 直接语法错误。

### 4.3 CSS 选择器：select（➕ 最灵活）

`select()` 用 CSS 选择器语法，和网页 CSS/jQuery 一样：

```python
soup.select("h1")                       # 所有 h1
soup.select("div.card")                 # class 含 card 的 div（. 是 class）
soup.select("#main")                    # id 为 main（# 是 id）
soup.select("div.card h2 a")            # 后代选择：card 里的 h2 里的 a
soup.select("div.card > h2")            # 直接子元素
soup.select("ul li:nth-of-type(2)")     # 第 2 个 li
soup.select("a[href^='/post/']")        # href 以 /post/ 开头的 a（属性选择器）
soup.select(".price, .old-price")       # 逗号 = 或
soup.select_one("div.card h2")          # 只取第一个（没有返回 None）
```

**什么时候用哪个**：`find` 简单直观；`select` 一行表达复杂路径，**大部分场景 select 更省事**。两个都会，看哪个顺眼用哪个。

### 4.4 取数据：文本、属性、子节点（✅）

```python
tag = soup.find("div", class_="card")

tag.text                                   # 所有子孙文本拼起来
tag.get_text(strip=True)                   # 去掉首尾空白（最常用！）
tag.get_text(separator=" ")                # 用空格分隔各段文本

tag["href"]                                # 取属性（不存在会 KeyError）
tag.get("href")                            # 取属性（不存在返回 None，推荐）
tag.get("href", "/")                       # 不存在给默认值

tag.name                                   # 标签名（如 'div'）
tag.attrs                                  # 所有属性字典
tag.parent                                 # 父节点
tag.children                               # 子节点（生成器）
tag.find_all("a")                          # 在 tag 内部继续找
```

### 4.5 遍历与定位（➕）

```python
soup.find_all("a")[2]                      # 第 3 个 a（配合列表索引）
rows = soup.find_all("tr")
for row in rows:                           # 遍历表格行
    cells = row.find_all("td")
    print([c.get_text(strip=True) for c in cells])

# 找"下一个兄弟"（表格/列表常用）
tag.find_next_sibling()                    # 下一个兄弟标签
tag.find_previous_sibling()                # 上一个兄弟标签

# 全局搜索任意位置（列表里嵌套最方便）
soup.find_all(string="首页")               # 找文本内容（返回字符串节点）
```

### 4.6 修改与输出（🧪 少用但要知道）

```python
tag["class"].append("hot")                 # 加 class
tag.string = "新文本"                      # 改文本
tag.decompose()                            # 从树中删除该节点
new_div = soup.new_tag("div")              # 新建标签
print(soup.prettify())                     # 缩进格式化输出（调试看结构）
print(str(soup))                           # 输出完整 HTML
```

### 4.7 与 lxml 解析器的配合（➕）

```python
soup = BeautifulSoup(html, "lxml")         # 只需换解析器名，其他代码全一样
```

## 第 5 章 实战项目案例（从小白到大神）

### 案例 1（入门级）：提取文章列表

```python
from bs4 import BeautifulSoup

html = """
<div class="article">
  <h2 class="title"><a href="/post/1">Python 入门</a></h2>
  <span class="date">2026-09-01</span>
</div>
<div class="article">
  <h2 class="title"><a href="/post/2">Requests 教程</a></h2>
  <span class="date">2026-09-10</span>
</div>
"""
soup = BeautifulSoup(html, "html.parser")

for art in soup.select("div.article"):
    title = art.select_one("h2.title a").get_text(strip=True)
    link = art.select_one("h2.title a")["href"]
    date = art.select_one("span.date").get_text(strip=True)
    print(title, "|", link, "|", date)
```

### 案例 2（进阶级）：Requests + bs4 爬取整站列表页并翻页

```python
import requests
from bs4 import BeautifulSoup

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

all_items = []
for page_no in range(1, 4):                     # 爬前 3 页
    resp = session.get(f"https://example.com/list?page={page_no}", timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for card in soup.select("div.item"):
        all_items.append({
            "标题": card.select_one("h3").get_text(strip=True),
            "链接": card.select_one("a")["href"],
            "价格": card.select_one(".price").get_text(strip=True),
        })
    print(f"第 {page_no} 页完成")

import json
with open("items.json", "w", encoding="utf-8") as f:
    json.dump(all_items, f, ensure_ascii=False, indent=2)
print("共抓取", len(all_items), "条")
```

### 案例 3（综合）：**抓取 + 清洗 + 分析 + 报表**（requests + bs4 + pandas + openpyxl）

```python
"""抓取某公告列表 → bs4 解析 → pandas 按部门统计 → openpyxl 出 Excel"""
import requests
import pandas as pd
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Font

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

records = []
for page in range(1, 4):
    resp = session.get(f"https://example.com/notices?page={page}", timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for row in soup.select("table tbody tr"):
        tds = row.find_all("td")
        records.append({
            "标题": tds[0].get_text(strip=True),
            "部门": tds[1].get_text(strip=True),
            "日期": tds[2].get_text(strip=True),
        })

# pandas 清洗统计
df = pd.DataFrame(records)
df = df.dropna()
df["日期"] = pd.to_datetime(df["日期"], errors="coerce")
df = df.dropna(subset=["日期"])
stats = df.groupby("部门").size().sort_values(ascending=False)

# openpyxl 导出
wb = Workbook()
ws = wb.active
ws.title = "原始数据"
for col, name in enumerate(df.columns, start=1):
    c = ws.cell(row=1, column=col, value=name); c.font = Font(bold=True)
for r, row in df.iterrows():
    for c, name in enumerate(df.columns, start=1):
        ws.cell(row=int(r) + 2, column=c, value=str(row[name]))
ws2 = wb.create_sheet("按部门统计")
ws2.cell(row=1, column=1, value="部门").font = Font(bold=True)
ws2.cell(row=1, column=2, value="公告数").font = Font(bold=True)
for i, (dept, cnt) in enumerate(stats.items(), start=2):
    ws2.cell(row=i, column=1, value=dept)
    ws2.cell(row=i, column=2, value=int(cnt))
wb.save("公告统计.xlsx")
print("完成，共", len(df), "条公告，", len(stats), "个部门")
```

## 第 6 章 进阶内容（大神之路）

### 6.1 解析 Playwright 渲染后的页面（重要组合）

Playwright 拿到动态页面的 `page.content()`（完整渲染后的 HTML），交给 bs4 解析——**动态网站的"浏览器 + 解析"黄金组合**：

```python
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://example.com/products")
    page.wait_for_selector(".product-card")
    html = page.content()                      # 渲染完成的完整 HTML
    browser.close()

soup = BeautifulSoup(html, "html.parser")      # 接下来纯 bs4 干活
for card in soup.select(".product-card"):
    print(card.select_one(".name").get_text(strip=True))
```

### 6.2 性能：只解析需要的部分 + 缓存

- 用 `soup.select_one` 而不是反复 `find_all` 再遍历。
- 大批量抓取时，把 HTML 存本地文件，解析失败可重跑解析而不重新请求。
- 需要极致性能时换 `"lxml"` 解析器（几倍提速，一行改动）。

### 6.3 处理"网页结构经常变"：写健壮的选择器

- 优先用**稳定的锚点**：`id`（唯一）> `class`（语义）> 标签路径。
- 对可能缺失的元素，先 `tag is not None` 判断再取 `.text`，避免 `AttributeError`。
- 把"取单个字段"封装成函数，页面结构变了只改一处。

### 6.4 合规提醒

爬虫请遵守目标网站 robots.txt 与使用条款，控制频率，只采集合法授权的数据。

## 第 7 章 高频坑与排查（新手必看）

| 坑 | 症状 | 解决 |
| --- | --- | --- |
| `class_` 写成 `class` | 语法错误 | 用 `class_=`；或改用 `select(".类名")` |
| find 返回 None 还取 .text | `AttributeError: 'NoneType' object has no attribute 'text'` | 先 `if tag is not None:` 再取值 |
| select 选不中 | 结果空列表（不报错！） | 先 `print(soup)[:500]` 看真实结构；用 `prettify()` 缩进检查 |
| 页面是 JS 渲染的 | 解析出来是空的 | 改用 Playwright 拿渲染后 HTML（见 6.1） |
| 中文乱码 | 解析出来乱码 | `resp.encoding="utf-8"`；文件打开带 `encoding="utf-8"` |
| get_text 带一堆空白 | 文本挤在一起 | `get_text(strip=True)` |
| 属性不存在报错 | `KeyError: 'href'` | 用 `tag.get("href")` |
| 嵌套结构取不到 | 用 find 只找到外层 | 用 `find_all` + 循环，或 `select("div.card h2 a")` 后代选择 |
| 解析速度慢 | 大批量卡 | 换 `"lxml"` 解析器 |
| 用正则抠 HTML | 写起来痛苦还容易错 | 一律用 bs4 |

## 第 8 章 学习路径与自测

**学习路径**：
1. 解析字符串 + find/find_all（半天）
2. select CSS 选择器（1 天）
3. 取文本/属性 + 遍历表格（半天）
4. 配合 Requests 爬列表页（1 天）
5. 翻页 + 保存 JSON/CSV（半天）
6. 配合 Pandas/Openpyxl 出报表（1 天）
7. 配合 Playwright 爬动态页（1 天）
8. 写健壮解析 + 异常兜底（半天）

**自测题**：
1. `find` 和 `find_all` 区别？查不到分别返回什么？
2. 为什么 class 要写成 `class_`？
3. `select("div.card h2 a")` 和 `select("div.card > h2")` 区别？
4. `tag["href"]` 和 `tag.get("href")` 区别？
5. 页面是 JS 动态渲染的，bs4 解析为空怎么办？
6. 解析出来文本带一堆空格换行怎么办？
7. 网页结构变了导致解析失败，怎么降低影响？
8. 解析器 `html.parser` 和 `lxml` 怎么选？
9. 怎么拿到 Playwright 渲染后的 HTML 给 bs4 用？
10. 综合：描述"requests 抓 5 页 → bs4 解析 → pandas 统计 → Excel 导出"每步用什么？

**答案提示**：
1. find 返回第一个 Tag（没有返回 None）；find_all 返回列表（没有返回空列表）。
2. class 是 Python 关键字，不能当参数名；`class_` 是 bs4 的约定写法。
3. `h2 a` 是任意层级后代；`> h2` 是直接子元素（中间隔层就匹配不到）。
4. `["href"]` 没有会抛 KeyError；`.get("href")` 没有返回 None（可给默认值）。
5. 改用 Playwright 等渲染完成拿 `page.content()` 再交给 bs4（见 6.1）。
6. `get_text(strip=True)`。
7. 选择器选稳定锚点、封装取值函数、对可能缺失元素判 None；页面变只改函数。
8. 新手/小规模用 `html.parser`（零依赖）；大批量用 `lxml`（快几倍）。
9. `page.content()` 返回完整渲染 HTML 字符串，直接 `BeautifulSoup(html, "html.parser")`。
10. 见案例 3：requests.get → BeautifulSoup(resp.text) → pandas DataFrame → openpyxl Workbook。

<hr>

> 下一篇：《Pandas》——把抓回来的数据变成表格，筛选、统计、分组一键搞定。
