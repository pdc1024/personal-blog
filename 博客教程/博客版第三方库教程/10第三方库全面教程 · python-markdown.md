# 第三方库全面教程 · python-markdown

> 面向初学者：博客文章正文从 Markdown 变成网页，就是它干的。
> 学完这份教程，你能掌握 python-markdown 的全部常用扩展、插件机制、自定义扩展和性能优化。
> 适用版本：Markdown 3.x ｜ 博客项目：`app.py` 的 `render_markdown` 函数（第 613 行）

---

# 第 1 章 这个库是什么

## 1.1 一句话定位

python-markdown 是一个纯 Python 写的 **Markdown 转 HTML 引擎**：

```python
import markdown
html = markdown.markdown('# 你好')
# → '<h1>你好</h1>'
```

Markdown 是"用简单符号写格式"的纯文本写法（`#` 标题、`**加粗**`、`- 列表`），但浏览器只认 HTML——python-markdown 就是两者之间的翻译官。

一句话：**python-markdown 是博客的"文章加工厂"**：作者写 Markdown，读者看 HTML。

## 1.2 它和同类工具的对比

| 工具 | 特点 |
|---|---|
| **python-markdown** | 纯 Python、扩展多、稳定 |
| markdown2 | 另一个 Python 实现，速度快 |
| mistune | 用正则，快但扩展少 |
| markdown-it-py | Rust 核心，速度最快 |
| marked (Node) | JavaScript 生态 |

博客选 python-markdown 是因为扩展生态全（FencedCode、Toc、Codehilite 都有）、稳定、文档好。

## 1.3 一个最小例子

```python
import markdown
md = '''# 标题

这是一段**加粗**文字。

- 列表项 1
- 列表项 2
'''
print(markdown.markdown(md))
# <h1>标题</h1>
# <p>这是一段<strong>加粗</strong>文字。</p>
# <ul><li>列表项 1</li>...</ul>
```

---

# 第 2 章 核心概念与原理

## 2.1 渲染流水线

python-markdown 把"Markdown → HTML"拆成四个阶段，扩展可以在任意阶段介入：

```
原始文本
  ↓ ① 预处理 Preprocessor：按行加工（如围栏代码块识别）
  ↓ ② 块解析 BlockParser：切分段落/标题/列表
  ↓ ③ 行内解析 InlineParser：处理 **加粗**、`代码`、[链接]()
  ↓ ④ 后处理 Postprocessor：整体再加工（如生成目录）
HTML 输出
```

**理解流水线**是玩转插件的钥匙：表格插件在块解析阶段加语法，目录插件在后处理阶段收集标题。

## 2.2 一次性 vs 可复用实例

```python
# 方式 A：一次性（每次新建实例，慢）
html = markdown.markdown(text, extensions=['fenced_code'])

# 方式 B：可复用实例（实例缓存已编译解析器，快得多）
md = markdown.Markdown(extensions=['fenced_code'])
html = md.convert(text)
md.reset()          # 用完后重置（否则目录等状态会残留）
```

**为什么复用更快？** 新建实例要重新加载扩展、重新编译内部解析器；复用实例只跑解析。博客把渲染器做成模块级单例 + 结果缓存到 `rendered_html` 列。

## 2.3 安全边界：它不做 HTML 过滤

python-markdown **默认不清理 HTML**——用户写 `<script>alert(1)</script>` 会原样进 HTML。

- **单用户博客**（只有自己发文章）：风险可控；
- **多用户投稿**：必须加 `bleach` 等过滤库清洗输出。

博客是单用户，作者本人的 Markdown 信任，直接 `|safe` 输出。

---

# 第 3 章 安装与版本

```bash
pip install markdown
pip show markdown
```

Markdown 3.x 要求 Python 3.8+。

---

# 第 4 章 API 全面讲解

## 4.1 两个入口

```python
# 函数式（简单场景）
html = markdown.markdown(text, extensions=['tables'])

# 类式（复用/性能）
md = markdown.Markdown(extensions=['tables'], extension_configs={...})
html = md.convert(text)
md.reset()
```

## 4.2 内置扩展大全

| 扩展 | 做什么 | 博客用 |
|---|---|---|
| `fenced_code` | 三反引号代码块 | ✅ |
| `tables` | 表格语法 | ✅ |
| `sane_lists` | 更严格的列表嵌套 | ✅ |
| `nl2br` | 换行转 `<br>` | ✅ |
| `toc` | 自动目录锚点 | ✅ |
| `codehilite` | 代码高亮（配合 Pygments） | ✅ |
| `footnotes` | 脚注 | ➕ |
| `attr_list` | 元素加 class/id | ➕ |
| `md_in_html` | 在 HTML 块内继续渲染 Markdown | ➕ |
| `admonition` | 提示框语法 | 🧪 |
| `meta` | 头部元数据 | 🧪 |
| `smarty` | 智能引号美化 | 🧪 |
| `wikilinks` | `[[链接]]` | 🧪 |

**博客的组合**（app.py 第 613 行附近）：

```python
extensions = [
    FencedCodeExtension(),          # 自定义围栏扩展
    'tables',
    'sane_lists',
    TocExtension(permalink=True, toc_depth='2-4'),
    'codehilite',
    'nl2br',
]
```

## 4.3 extension_configs

```python
md = markdown.Markdown(
    extensions=['toc', 'codehilite'],
    extension_configs={
        'codehilite': {
            'css_class': 'codehilite',
            'guess_lang': False,
        },
    })
```

## 4.4 从实例拿目录：md.toc

```python
md = markdown.Markdown(extensions=['toc'])
body = md.convert(long_article_md)
toc_html = md.toc          # 生成的目录 HTML
md.reset()
```

博客的"文章目录侧边栏"就是这么来的。

## 4.5 自定义扩展（进阶）

写一个 `==文字==` 变 `<mark>高亮</mark>` 的扩展：

```python
import markdown
from markdown.inlinepatterns import Pattern
from markdown.extensions import Extension
from markdown.util import etree

class HighlightPattern(Pattern):
    def handleMatch(self, m):
        el = etree.Element('mark')
        el.text = m.group(2)
        return el

class HighlightExtension(Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(
            HighlightPattern(r'==(.+?)==', md), 'highlight', 175)

md = markdown.Markdown(extensions=[HighlightExtension()])
print(md.convert('这是 ==重点== 内容'))
# <p>这是 <mark>重点</mark> 内容</p>
```

## 4.6 输出格式

```python
markdown.markdown(text, output_format='html5')
```

- `html4`：兼容旧浏览器；
- `html5`：现代（推荐）。

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客的 render_markdown（app.py 第 613 行）

```python
def render_markdown(text):
    extensions = [
        FencedCodeExtension(),
        'tables',
        'sane_lists',
        TocExtension(permalink=True, toc_depth='2-4'),
        'codehilite',
        'nl2br',
    ]
    extension_configs = {
        'codehilite': {
            'css_class': 'codehilite',
            'linenums': False,
            'guess_lang': False,
        }
    }
    md = markdown.Markdown(extensions=extensions,
                           extension_configs=extension_configs,
                           output_format='html5')
    return md.convert(text)
```

**缓存**：首次渲染后存进 `rendered_html` 列，之后直接读缓存——高频访问不重复渲染。

## 5.2 独立示例：文章目录侧边栏

```python
from markdown.extensions.toc import TocExtension

md = markdown.Markdown(extensions=[
    TocExtension(permalink=True, toc_depth='2-4')
])
body = md.convert(article_md)
toc = md.toc
md.reset()

# 模板里：
# <aside class="toc">{{ toc|safe }}</aside>
# <article>{{ body|safe }}</article>
```

---

# 第 6 章 高频坑与排查

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | 代码块还渲染 Markdown | ```python 里 # 标题 变标题 | 开 fenced_code |
| 2 | 换行全挤一起 | 单换行不生效 | 开 nl2br，或留空行 |
| 3 | 代码没颜色 | 纯文本 | codehilite + Pygments CSS |
| 4 | 每次访问重渲染 | 页面慢 | 复用实例 + rendered_html 缓存 |
| 5 | 目录重复 | 上一篇的目录混进来 | 复用实例必须 reset() |
| 6 | XSS | 用户写 script 被执行 | 多用户加 bleach |
| 7 | 表格不显示 | 语法没生效 | 加 tables 扩展 |
| 8 | 标题锚点重复 | 多个同标题锚点冲突 | TocExtension slugify |
| 9 | 代码高亮 CSS 类对不上 | 没颜色 | codehilite css_class 和 Pygments cssclass 一致 |
| 10 | 中文标题锚点乱码 | URL 里乱码 | 配置 slugify 或保持原文 |

---

# 第 7 章 学习路径与自测

## 7.1 学习路径

- 第 1 天：基本转换 + 常用扩展；
- 第 2 天：理解流水线和实例复用；
- 第 3 天：配 toc/codehilite；
- 第 4 天：自定义扩展（可选）。

## 7.2 自测题

1. `markdown.markdown(text)` 和 `Markdown(...).convert(text)` 区别？
2. 为什么复用实例后要 `reset()`？
3. 代码高亮为什么需要 python-markdown 和 Pygments 两个库？
4. `md.toc` 什么时候拿？
5. 多用户博客为什么要加安全过滤？
6. fenced_code 扩展做什么？
7. nl2br 解决什么问题？
8. 为什么博客要把 rendered_html 缓存到数据库？

## 7.3 答案

1. 前者每次新建临时实例；后者可复用（性能好）并支持复杂配置。
2. reset 清掉 toc 等状态，防上一篇内容混进下一篇。
3. python-markdown 的 codehilite 只贴 class；Pygments 负责按 class 上色。
4. convert() 之后、reset() 之前。
5. python-markdown 不清理 HTML，用户可注入 `<script>`。
6. 识别三反引号代码块，不在其中渲染 Markdown。
7. 单换行自动转 `<br>`，否则 Markdown 段落间单换行不生效。
8. 渲染是 CPU 密集操作，缓存避免每次访问都重渲染。

## 7.4 进一步学习

- 官方文档：https://python-markdown.github.io/
- 扩展列表：https://python-markdown.github.io/extensions/

---

> 下一篇：Pygments —— 代码高亮引擎全面教程
