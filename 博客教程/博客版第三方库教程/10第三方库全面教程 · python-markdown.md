# 第三方库全面教程 · python-markdown

> 面向初学者：博客的文章正文从 Markdown 变成网页，就是它干的。学完这份教程，你能掌握 python-markdown 的全部常用扩展、插件机制和性能优化，而不只是会 `markdown.markdown(text)` 一句。
> 适用版本：Markdown 3.x ｜ 博客项目：`app.py` 的 `render_markdown` 函数

---

# 第 1 章 这个库是什么

python-markdown 是一个纯 Python 写的** Markdown 转 HTML 引擎**。你把 Markdown 原文丢给它，它吐回 HTML 字符串：

```python
import markdown
html = markdown.markdown('# 你好')
# → '<h1>你好</h1>'
```

Markdown 是"用简单符号写格式"的纯文本写法（`#` 标题、`**加粗**`、`- 列表`），但浏览器只认 HTML——python-markdown 就是两者之间的翻译官。

一句话：**python-markdown 是博客的"文章加工厂"**：作者写 Markdown，读者看 HTML。

---

# 第 2 章 核心概念与原理

## 2.1 渲染流水线：插件往哪塞

python-markdown 把"Markdown → HTML"拆成三个阶段，插件可以在任意阶段介入：

```
原始文本
  ↓ ① 预处理（Preprocessor）：按行加工，如围栏代码块识别
  ↓ ② 块解析（BlockParser）：切分段落/标题/列表
  ↓ ③ 行内解析（InlineParser）：处理 **加粗**、`代码`、[链接]()
  ↓ ④ 后处理（Postprocessor）：整体再加工，如生成目录
HTML 输出
```

**理解流水线**是玩转插件的钥匙：比如"表格"插件在块解析阶段加语法，"目录"插件在后处理阶段收集标题。

## 2.2 一次性 vs 可复用实例（性能关键）

```python
# 方式 A：一次性（每次新建实例，慢）
html = markdown.markdown(text, extensions=['fenced_code'])

# 方式 B：可复用实例（实例缓存已编译的解析器，快得多！）
md = markdown.Markdown(extensions=['fenced_code'])
html = md.convert(text)
md.reset()          # 用完后重置（否则目录等状态会残留）
```

**为什么复用更快？** 新建实例要重新加载扩展、重新编译内部解析器；复用实例只跑解析。博客把渲染器做成模块级单例 + 结果缓存到 `rendered_html` 列——高频访问也不会反复渲染。

## 2.3 安全边界：它不做 HTML 过滤

**python-markdown 默认不清理 HTML**——用户写 `<script>alert(1)</script>` 会原样进 HTML。单用户博客（只有自己发文章）风险可控；**多用户投稿必须加 bleach 等过滤库**清洗输出。

---

# 第 3 章 安装与版本

```bash
pip install markdown
pip show markdown   # 版本验证
```

Markdown 3.x 要求 Python 3.8+。

---

# 第 4 章 API 全面讲解

## 4.1 两个入口：markdown.markdown() 与 markdown.Markdown()

```python
# 入口一：函数式（简单场景）
markdown.markdown(text, extensions=['tables'], extension_configs={...})

# 入口二：类式（复用/性能场景，推荐）
md = markdown.Markdown(extensions=[...], extension_configs={...})
html = md.convert(text)
md.reset()   # 关键：复用前重置，清掉目录等实例状态
```

## 4.2 内置扩展大全（✅ 项目用到的 / ➕ 推荐 / 🧪 进阶）

| 扩展 | 做什么 | 状态 |
|---|---|---|
| `fenced_code` | 三个反引号包裹的代码块（```python） | ✅ 项目用 |
| `tables` | 表格语法 `\| a \| b \|` | ✅ 项目用 |
| `sane_lists` | 更严格的列表嵌套规则 | ✅ 项目用 |
| `nl2br` | 换行自动转 `<br>` | ✅ 项目用 |
| `toc` | 自动生成目录锚点 | ✅ 项目用 |
| `codehilite` | 代码高亮（配合 Pygments） | ✅ 项目用 |
| `footnotes` | 脚注语法 `[^1]` | ➕ 推荐 |
| `attr_list` | 给元素加 class/id/属性 | ➕ 推荐 |
| `md_in_html` | 在 HTML 块内继续渲染 Markdown | ➕ 推荐 |
| `admonition` | 提示框语法（!!! note） | 🧪 进阶 |
| `meta` | 解析文章头部元数据 | 🧪 进阶 |
| `smarty` | 智能引号/破折号美化 | 🧪 进阶 |
| `wikilinks` | `[[链接]]` 语法 | 🧪 进阶 |

**最常用的组合**（博客就是这个）：

```python
extensions = ['fenced_code', 'tables', 'sane_lists', 'nl2br',
              'toc', 'codehilite']
```

## 4.3 extension_configs：给扩展喂配置

```python
from markdown.extensions.toc import TocExtension

md = markdown.Markdown(extensions=['toc', 'codehilite'], extension_configs={
    'codehilite': {
        'css_class': 'codehilite',   # 代码块外层类名（要和 Pygments CSS 对上）
        'guess_lang': False,         # 不猜语言（避免误判，也更快）
    },
})
```

> 💡 **博客的实际写法**：不用 extension_configs 配 toc，而是直接把参数传给 `TocExtension` 类：
> `TocExtension(permalink=True, toc_depth='2-4')` ——两种方式效果一样，看哪个顺手。

## 4.4 从 Markdown 实例拿目录：md.toc

用 `toc` 扩展后，转换完可以拿到目录 HTML：

```python
md = markdown.Markdown(extensions=['toc'])
body = md.convert(long_article_md)
toc_html = md.toc          # 生成好的 <div class="toc">...</div>
md.reset()                 # 用完重置！
```

博客的"文章目录侧边栏"就是这么来的。

## 4.5 自定义扩展（🧪 进阶但很酷）

写一个自己的扩展 = 写一个 `extendMarkdown` 注册钩子：

```python
import markdown
from markdown.inlinepatterns import Pattern

class HighlightPattern(Pattern):
    """把 ==文字== 变成 <mark>高亮</mark>"""
    def handleMatch(self, m):
        el = markdown.util.etree.Element('mark')
        el.text = m.group(2)
        return el

class HighlightExtension(markdown.extensions.Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(
            HighlightPattern(r'==(.+?)==', md), 'highlight', 175)

# 使用
md = markdown.Markdown(extensions=[HighlightExtension()])
print(md.convert('这是 ==重点== 内容'))
# → <p>这是 <mark>重点</mark> 内容</p>
```

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客的 render_markdown（对照真实代码）

```python
from markdown.extensions.toc import TocExtension

# FencedCodeExtension 是项目自定义的围栏代码块扩展（增强 ``` 语法）
# TocExtension(permalink=True, toc_depth='2-4')：标题自动加锚点链接，只收 2~4 级标题进目录
def render_markdown(text):
    extensions = [
        FencedCodeExtension(),
        'tables',          # 表格语法
        'sane_lists',      # 更严格的列表嵌套
        TocExtension(permalink=True, toc_depth='2-4'),  # 目录 + 锚点
        'codehilite',      # 代码高亮（配合 Pygments）
        'nl2br',           # 换行转 <br>
    ]
    extension_configs = {
        'codehilite': {
            'css_class': 'codehilite',  # 类名必须和 Pygments 生成的 CSS 前缀一致
            'linenums': False,          # 不显示行号
            'guess_lang': False,        # 不猜语言
        }
    }
    md = markdown.Markdown(extensions=extensions,
                           extension_configs=extension_configs,
                           output_format='html5')
    return md.convert(text)
```

配合数据库缓存：文章首次访问渲染一次存进 `rendered_html`，之后直接读缓存。

## 5.2 独立示例：博客文章页"标题自动加锚点"

用 `toc` 扩展的 permalink 功能，让每个标题后面带一个可点击的链接图标：

```python
md = markdown.Markdown(extensions=['toc'], extension_configs={
    'toc': {'permalink': True, 'permalink_class': 'headerlink',
            'toc_depth': '1-3'}})
html = md.convert('''# 第一章\n内容\n\n## 1.1 小节\n内容''')
print(md.toc)   # 目录：<div class="toc"><ul><li><a href="#di-yi-zhang">第一章</a>...
```

---

# 第 6 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 代码块里还渲染 Markdown | ```python 块内 `# 标题` 变成了标题 | 必须开 `fenced_code` 扩展 |
| 换行全挤在一起 | 单换行不生效 | 开 `nl2br`，或 Markdown 里留空行 |
| 代码没有颜色 | 页面代码块是纯文本 | `codehilite` 只贴 class，还需 Pygments 生成 CSS（下篇讲） |
| 每次访问都重渲染 | 页面慢 | 复用 Markdown 实例 + `rendered_html` 缓存 |
| 目录重复/串内容 | 转换后 toc 带着上一篇文章的 | 复用实例必须 `md.reset()` |
| 用户写 `<script>` 被执 | XSS | 多用户投稿加 bleach 过滤 |
| 表格不显示 | 表格语法没生效 | 加 `tables` 扩展 |

---

# 第 7 章 学习路径与自测

**学习路径**：先跑通基本转换 + 常用扩展（半天）→ 理解流水线和实例复用（半天）→ 配 toc/codehilite（1 天）→ 自定义扩展（1 天，可选）。

**自测题**：

1. `markdown.markdown(text)` 和 `Markdown(extensions=...).convert(text)` 的区别？
2. 为什么复用 Markdown 实例后要调 `reset()`？
3. 代码高亮为什么需要 python-markdown 和 Pygments 两个库配合？
4. `md.toc` 里有什么？什么时候拿？
5. 多用户博客为什么还要额外做安全过滤？

**答案**：
1. 前者每次新建临时实例；后者可复用（性能好）并支持复杂配置。
2. reset 清掉 toc 目录、状态残留，防止上一篇的内容混进下一篇。
3. python-markdown 的 codehilite 只负责给代码块贴语言 class；Pygments 负责按 class 上色（生成 CSS）。
4. 转换后自动生成的目录 HTML；在 `convert()` 之后、`reset()` 之前读取。
5. python-markdown 不清理 HTML，用户可注入 `<script>`，需 bleach 等清洗。

---

> 下一篇：Pygments —— 代码高亮引擎全面教程
