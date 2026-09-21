# 第三方库全面教程 · python-markdown

> 面向初学者到进阶者：博客文章正文从 Markdown 变成网页，就是它。
> 学完这份教程，你会掌握 python-markdown 的渲染流水线、扩展生态、实例复用、自定义扩展和 md.toc。
>
> 适用版本：Markdown 3.x ｜ 博客项目：`app.py` 第 613 行 `render_markdown`

---

# 第 1 章 认识 python-markdown

## 1.1 一句话定位

python-markdown 是纯 Python 写的 **Markdown 转 HTML 引擎**：

```python
import markdown
markdown.markdown('# 你好')
# '<h1>你好</h1>'
```

一句话：**它是博客的文章加工厂**——作者写 Markdown，读者看 HTML。

## 1.2 同类对比

| 工具 | 特点 |
|---|---|
| **python-markdown** | 纯 Python、扩展多、稳定 |
| markdown2 | 快 |
| mistune | 正则快、扩展少 |
| markdown-it-py | Rust 核心、最快 |

博客选它是因为扩展生态全。

---

# 第 2 章 渲染流水线

## 2.1 四阶段

```
原始文本
  ↓ Preprocessor：按行加工
  ↓ BlockParser：切段落/标题/列表
  ↓ InlineParser：处理 **加粗**、`代码`
  ↓ Postprocessor：整体再加工（目录）
HTML
```

扩展在任意阶段介入。

## 2.2 一次性 vs 可复用

```python
# 一次性（每次新建，慢）
markdown.markdown(text, extensions=['fenced_code'])

# 可复用（实例缓存解析器，快）
md = markdown.Markdown(extensions=['fenced_code'])
html = md.convert(text)
md.reset()
```

博客把渲染器做成模块级单例 + 结果缓存到 `rendered_html` 列。

## 2.3 安全边界

python-markdown **不清理 HTML**——用户写 `<script>` 原样进 HTML。单用户博客风险可控；多用户必须加 `bleach`。

---

# 第 3 章 API

## 3.1 两个入口

```python
markdown.markdown(text, extensions=[...])
# 或
md = markdown.Markdown(extensions=[...], extension_configs={...})
md.convert(text)
md.reset()
```

## 3.2 内置扩展

| 扩展 | 作用 |
|---|---|
| `fenced_code` | 三反引号代码块 |
| `tables` | 表格 |
| `sane_lists` | 严格列表 |
| `nl2br` | 换行转 br |
| `toc` | 目录 |
| `codehilite` | 代码高亮 |
| `footnotes` | 脚注 |
| `attr_list` | 元素加 class |
| `admonition` | 提示框 |
| `meta` | 头部元数据 |

## 3.3 md.toc 拿目录

```python
md = markdown.Markdown(extensions=['toc'])
body = md.convert(text)
toc = md.toc    # 目录 HTML
md.reset()
```

## 3.4 自定义扩展

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
```

---

# 第 4 章 项目实战

## 4.1 博客 render_markdown（app.py 第 613 行）

```python
def render_markdown(text):
    extensions = [
        FencedCodeExtension(),
        'tables', 'sane_lists',
        TocExtension(permalink=True, toc_depth='2-4'),
        'codehilite', 'nl2br',
    ]
    md = markdown.Markdown(extensions=extensions,
                           output_format='html5')
    return md.convert(text)
```

渲染结果存 `rendered_html` 列，下次直接读缓存。

---

# 第 5 章 高频坑

| # | 坑 | 解决 |
|---|---|---|
| 1 | 代码块还渲染 Markdown | 开 fenced_code |
| 2 | 换行挤一起 | nl2br 或空行 |
| 3 | 代码没颜色 | codehilite + Pygments CSS |
| 4 | 每次访问重渲染 | 复用实例 + 缓存 |
| 5 | 目录残留 | 复用后 reset() |
| 6 | XSS | 多用户加 bleach |
| 7 | 表格不显示 | 加 tables |

---

# 第 6 章 学习路径与自测

1. `markdown.markdown()` 和 `Markdown().convert()` 区别？
2. 为什么复用后要 reset()？
3. codehilite 和 Pygments 关系？
4. md.toc 什么时候拿？
5. 博客为什么缓存 rendered_html？

**答案**：
1. 前者每次新建实例；后者可复用性能好。
2. 清 toc 等状态。
3. codehilite 贴 class，Pygments 上色。
4. convert 之后、reset 之前。
5. 渲染是 CPU 密集，缓存避免重复。

---

> 下一篇：Pygments —— 代码高亮引擎全面教程
