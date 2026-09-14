# 第三方库全面教程 · python-markdown（独立版）

> 面向初学者：本教程**独立成篇**，假设你会基础 Python。术语第一次出现都有白话解释。
> 适用版本：python-markdown 3.6 ｜ 配套知识：与《Flask》《Jinja2》配合（把 Markdown 渲染成网页）。
> 学习目标：从"没听过 Markdown"到"能用 python-markdown 把 Markdown 文档转成安全漂亮的 HTML，并熟练配置扩展"。

---

# 第 1 章 这个库是什么

## 1.1 一句话认识 python-markdown

**python-markdown** 是 Python 的 **Markdown → HTML 转换器**：你写 `# 标题`、`**加粗**`、`- 列表`，它转换成 `<h1>`、`<strong>`、`<ul>` 等 HTML 标签。

```python
import markdown

md_text = "# 我的博客\n\n这是一段**加粗**文字。"
html = markdown.markdown(md_text)
print(html)
# <h1>我的博客</h1>
# <p>这是一段<strong>加粗</strong>文字。</p>
```

## 1.2 Markdown 是什么

**Markdown** 是一种"轻量标记语言"：用简单的符号（`#`、`*`、`-`）标记格式，写起来像纯文本，渲染出来是排版好的网页。GitHub、飞书、公众号编辑器、博客系统都在用。

## 1.3 为什么用 python-markdown

- **用户友好**：写文章不用学 HTML，用 Markdown 就行。
- **安全可控**：相比直接让用户贴 HTML，Markdown 转换结果更可控（仍需配合转义防 XSS）。
- **扩展丰富**：代码高亮、目录（TOC）、表格、脚注都有官方扩展。

---

# 第 2 章 核心概念与原理

## 2.1 Markdown 语法速览（写文章的必会集）

| 语法 | 效果 |
|---|---|
| `# 一级标题` ~ `###### 六级标题` | h1 ~ h6 |
| `**加粗**` / `*斜体*` | 加粗 / 斜体 |
| `[文字](https://链接)` | 超链接 |
| `![描述](图片url)` | 图片 |
| `` `行内代码` `` | 行内代码 |
| ` ```python ... ``` ` | 代码块（可带语言） |
| `- 项目` / `1. 项目` | 无序/有序列表 |
| `> 引用` | 引用块 |
| `---` | 分割线 |
| `| 列1 | 列2 |` | 表格（需 tables 扩展） |
| `[TOC]` | 目录（需 toc 扩展） |

## 2.2 转换流程

```
Markdown 文本
   ↓ markdown.markdown(text, extensions=[...])
HTML 字符串
   ↓ 模板渲染 / 存库
网页
```

**注意**：python-markdown 输出的是**片段**（不含 `<html><body>` 完整骨架），要嵌进你的页面模板。

## 2.3 扩展（extensions）机制

扩展给转换器加能力：代码高亮（codehilite）、目录（toc）、表格（tables）、脚注（footnotes）、数学公式（数学）等。**想用哪个功能就加哪个扩展**。

---

# 第 3 章 安装与版本

```bash
pip install markdown
```

- 当前稳定版 3.6。
- 导入名是 `markdown`（包名也是 markdown，别和 Markdown 语言混淆）。
- 代码高亮需要额外装 Pygments（见《Pygments》教程）。

---

# 第 4 章 API 全面讲解

> 标注：✅ = 必会；➕ = 推荐；🧪 = 进阶

## 4.1 最简用法（✅）

```python
import markdown

html = markdown.markdown("# 标题")
# <h1>标题</h1>
```

## 4.2 带扩展转换（✅ 写博客的标准配置）

```python
import markdown

md_text = """# 文章标题

## 目录
[TOC]

## 第一节
正文内容，含 **加粗** 和 `代码`。

```python
print("hello")
```

| 列A | 列B |
| --- | --- |
| 1 | 2 |
"""

html = markdown.markdown(
    md_text,
    extensions=[
        "toc",            # 目录 [TOC] + 标题自动加 id
        "fenced_code",     # ``` 围栏代码块（不写这个三个反引号不生效！）
        "codehilite",      # 代码高亮（配合 Pygments）
        "tables",          # 表格
        "nl2br",           # 换行转 <br>
        "footnotes",       # 脚注
        "attr_list",       # 标题加自定义属性 {#id .class}
        "md_in_html",      # HTML 块内支持 Markdown
    ],
    extension_configs={
        "codehilite": {
            "guess_lang": False,      # 不猜语言（防误判）
            "css_class": "codehilite",
        },
        "toc": {
            "toc_depth": "1-3",       # 目录只到三级标题
        },
    },
)
```

## 4.3 codehilite 扩展配置（✅ 代码高亮）

```python
html = markdown.markdown(code, extensions=["fenced_code", "codehilite"],
    extension_configs={
        "codehilite": {
            "css_class": "codehilite",   # 外层 CSS 类
            "guess_lang": False,         # 关掉语言猜测
            "linenums": True,            # 显示行号
        }
    })
```

**输出结构**：`<div class="codehilite"><pre><span></span><code>...<span class="k">...</span></code></pre></div>`——每个语法 token 包了 `<span>`，配 Pygments 的 CSS 就彩色显示。

## 4.4 toc 扩展：自动生成目录（✅ 长文必备）

```python
import markdown

md = "# 第一章\n\n内容\n\n# 第二章\n\n内容"
md_instance = markdown.Markdown(extensions=["toc"])
html = md_instance.convert(md)
toc = md_instance.toc                # 目录 HTML 字符串！
print(toc)                           # <div class="toc"><ul>...
print(html)                          # 标题带 id（如 id="_1"）
```

**关键**：`toc` 属性只有用 `Markdown` 实例（不是 `markdown.markdown()` 快捷函数）才能拿到。标题自动生成 id，锚点跳转靠它。

## 4.5 Markdown 实例复用（➕ 性能）

```python
md = markdown.Markdown(extensions=["toc", "fenced_code", "codehilite"])
html1 = md.convert(text1)      # 复用同一实例
html2 = md.convert(text2)
md.reset()                     # 重要！复用前 reset，否则 toc 状态累积
```

**⚠️ 坑**：同一实例连续 convert，toc 会累积；`md.reset()` 清状态。

## 4.6 安全：转义与过滤（✅ 必须知道）

python-markdown 默认**不转义 HTML**（`<script>` 原样输出！）。用户投稿必须额外防护：

```python
from markupsafe import escape  # Flask 自带；或自己写转义

md_text = '<script>alert(1)</script>'
html = markdown.markdown(md_text)   # ⚠️ <script> 原样输出，危险！

# 方案一：先转义再转 Markdown（Markdown 符号也会被转，体验差）
# 方案二：用 bleach 白名单过滤（推荐）
import bleach
allowed = ["p", "h1", "h2", "h3", "ul", "ol", "li", "strong", "em",
           "a", "code", "pre", "blockquote", "table", "thead", "tbody",
           "tr", "th", "td", "img", "br", "hr"]
html = bleach.clean(markdown.markdown(md_text), tags=allowed,
                    attributes={"a": ["href"], "img": ["src", "alt"]})
```

---

# 第 5 章 实战项目案例

## 案例 1（入门级）：命令行 Markdown 转 HTML

```python
"""python md2html.py 文章.md 文章.html"""
import sys
import markdown

def md2html(src, dst):
    with open(src, "r", encoding="utf-8") as f:
        md_text = f.read()
    html_body = markdown.markdown(md_text, extensions=["toc", "fenced_code",
                                                        "codehilite", "tables"])
    full = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>{src}</title>
<style>
body {{ max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.7; }}
code {{ background: #f4f4f4; padding: 2px 5px; border-radius: 3px; }}
pre {{ background: #282c34; color: #abb2bf; padding: 15px; border-radius: 6px; overflow-x: auto; }}
table {{ border-collapse: collapse; }} td, th {{ border: 1px solid #ddd; padding: 6px 12px; }}
</style></head><body>{html_body}</body></html>"""
    with open(dst, "w", encoding="utf-8") as f:
        f.write(full)
    print(f"已生成 {dst}")

if __name__ == "__main__":
    md2html(sys.argv[1], sys.argv[2])
```

## 案例 2（进阶级）：Flask 博客的 Markdown 渲染

```python
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import markdown

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blog.db"
db = SQLAlchemy(app)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    body_md = db.Column(db.Text)          # 存 Markdown 原文

def render_md(text):
    """把 Markdown 转成安全 HTML（含目录）"""
    md = markdown.Markdown(extensions=[
        "toc", "fenced_code", "codehilite", "tables"],
        extension_configs={"toc": {"toc_depth": "1-3"}})
    html = md.convert(text or "")
    toc = md.toc
    return html, toc

@app.route("/post/<int:aid>")
def post(aid):
    article = db.session.get(Article, aid)
    html, toc = render_md(article.body_md)
    return render_template("post.html", article=article, html=html, toc=toc)

with app.app_context():
    db.create_all()
```

模板 `post.html`：

```jinja2
<div class="toc-sidebar">{{ toc | safe }}</div>
<article>{{ html | safe }}</article>
{# 注意：html 来自我们的转换器+bleach 过滤后才可 safe #}
```

## 案例 3（综合）：**带目录、代码高亮、表格的文档站渲染器**

```python
"""把整个 docs/ 目录的 .md 批量转成带导航的 HTML 文档站"""
import os
import markdown
from pygments.formatters import HtmlFormatter

def build_site(src_dir="docs", dst_dir="site"):
    os.makedirs(dst_dir, exist_ok=True)
    # Pygments 高亮 CSS（一次性生成）
    with open(os.path.join(dst_dir, "pygments.css"), "w", encoding="utf-8") as f:
        f.write(HtmlFormatter().get_style_defs(".codehilite"))

    md = markdown.Markdown(extensions=[
        "toc", "fenced_code", "codehilite", "tables",
    ], extension_configs={
        "codehilite": {"css_class": "codehilite"},
        "toc": {"toc_depth": "1-3"},
    })

    nav = []
    for name in sorted(os.listdir(src_dir)):
        if not name.endswith(".md"):
            continue
        md.reset()   # 关键：每篇重置，防 toc 累积
        with open(os.path.join(src_dir, name), encoding="utf-8") as f:
            body = md.convert(f.read())
        title = name[:-3]
        nav.append((title, f"{title}.html"))
        html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<title>{title}</title>
<link rel="stylesheet" href="pygments.css">
<style>
body {{ max-width: 900px; margin: 0 auto; display: flex; }}
nav {{ width: 200px; padding: 20px; }}
nav a {{ display: block; padding: 4px 0; color: #2c3e50; text-decoration: none; }}
main {{ flex: 1; padding: 20px; }}
pre {{ padding: 12px; overflow-x: auto; border-radius: 6px; }}
</style></head><body>
<nav>{"".join(f'<a href="{f}">{t}</a>' for t, f in nav)}</nav>
<main>{md.toc}<hr>{body}</main>
</body></html>"""
        with open(os.path.join(dst_dir, f"{title}.html"), "w", encoding="utf-8") as f:
            f.write(html)
    print(f"文档站已生成到 {dst_dir}/，共 {len(nav)} 篇")

if __name__ == "__main__":
    build_site()
```

**本案例组合**：toc 目录 + codehilite 高亮 + Pygments CSS + 多文件批量渲染——**一套代码把 Markdown 文档变成带导航的静态文档站**。

---

# 第 6 章 进阶内容（大神之路）

## 6.1 自定义扩展（🧪）

```python
import markdown
from markdown.inlinepatterns import InlineProcessor

class HighlightPattern(InlineProcessor):
    """==高亮== → <mark>高亮</mark>"""
    def handleMatch(self, m, data):
        el = markdown.util.etree.Element("mark")
        el.text = m.group(1)
        return el, m.start(0), m.end(0)

class HighlightExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(HighlightPattern(r"==(.+?)==", "hl"), "hl", 175)

html = markdown.markdown("==重点内容==", extensions=[HighlightExtension()])
# <p><mark>重点内容</mark></p>
```

## 6.2 数学公式（🧪）

```python
html = markdown.markdown(r"$E=mc^2$", extensions=["mdx_math"])
# 需要额外安装 mdx_math 或用第三方扩展
```

## 6.3 性能：大量文档

- 复用 Markdown 实例 + `reset()`。
- 缓存转换结果（文章保存时转一次存 HTML，不每次现转）。

---

# 第 7 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 三个反引号不生效 | 代码块原样显示 | 必须加 `fenced_code` 扩展 |
| 代码没颜色 | 输出只有 `<div class="codehilite">` | 装 Pygments + 引入 Pygments CSS |
| 表格不渲染 | 表格变纯文本 | 加 `tables` 扩展 |
| [TOC] 不出现 | 目录不显示 | 加 `toc` 扩展；用 Markdown 实例才能拿 `md.toc` |
| 多次 convert 目录累积 | toc 越来越多 | 复用实例前 `md.reset()` |
| 用户注入 `<script>` | 页面被攻击 | 用 bleach 白名单过滤（绝不直接 safe） |
| 标题 id 乱 | 锚点跳不对 | toc 扩展自动生成 id；自定义 id 用 attr_list |
| 中文乱码 | 转换结果乱 | 文件 UTF-8 读写；HTML 声明 charset |
| 行号不显示 | linenums 无效 | `extension_configs` 里配 `"linenums": True` |
| 嵌套引用/列表错乱 | 渲染结构怪 | Markdown 缩进规则严格：子级多缩进 4 空格 |

---

# 第 8 章 学习路径与自测

**学习路径**：
1. Markdown 语法（半天）
2. markdown() 最简转换（半天）
3. fenced_code + codehilite 代码高亮（1 天）
4. toc 目录 + 锚点（1 天）
5. tables 等扩展全家桶（半天）
6. 安全过滤 bleach（1 天，必配）
7. Flask 集成（1 天）
8. 批量文档站（2 天，案例 3）
9. 自定义扩展（进阶，1 天）

**自测题**：
1. python-markdown 输出的是什么？包含 `<html>` 骨架吗？
2. 三个反引号代码块不生效，缺什么扩展？
3. 代码高亮需要什么配合？CSS 从哪来？
4. 怎么拿到生成的目录 HTML？
5. 同一实例多次 convert 要注意什么？
6. 用户投稿的 Markdown 有什么风险？怎么防？
7. `toc_depth` 配置干什么？
8. 表格和脚注分别需要什么扩展？
9. 文章存库：存 Markdown 原文还是 HTML？为什么？
10. 综合：描述"用户写 Markdown → 转 HTML → 过滤 → 渲染进模板"的链路。

**答案提示**：
1. HTML 片段（`<h1>` 等），不含完整页面骨架，需嵌入模板。
2. `fenced_code` 扩展。
3. Pygments + `codehilite` 扩展；CSS 用 `HtmlFormatter().get_style_defs()` 生成。
4. 用 `md = markdown.Markdown(extensions=["toc"])` 实例，`md.toc` 属性。
5. 先 `md.reset()`，否则 toc/状态累积。
6. 可注入 `<script>`；用 bleach 白名单过滤后再 safe。
7. 目录包含哪些标题级别（如 "1-3" 只到三级）。
8. `tables` 扩展；`footnotes` 扩展。
9. 存原文 Markdown：改格式/主题可重新渲染；存 HTML 改版要重新转换。
10. 参考案例 2+3：Markdown() 实例 convert → bleach.clean → 模板 safe 输出。

---

> 下一篇：《Pygments（独立版）》——代码高亮引擎从零到精通。
