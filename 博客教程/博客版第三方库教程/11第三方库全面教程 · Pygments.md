# 第三方库全面教程 · Pygments

> 面向初学者：博客文章里的代码块五颜六色，就是 Pygments 的功劳。学完这份教程，你不仅能给代码上色，还能用命令行高亮文件、给代码加行号、换任意配色主题。
> 适用版本：Pygments 2.x ｜ 博客项目：`app.py` 生成高亮 CSS + python-markdown 的 codehilite 扩展

---

# 第 1 章 这个库是什么

Pygments 是 Python 世界最强大的**通用语法高亮引擎**——它能识别 500+ 种编程语言，把代码按"关键词/字符串/注释/函数名"等类别拆开，再渲染成带颜色的 HTML 或其他格式。

一句话：**Pygments 是博客代码块的"化妆师"**。它不认识博客的任何代码，但任何语言的代码它都能认出语法结构并上色。

**为什么需要它？** 没有高亮，代码块就是一堆灰色文字，读者分不清哪里是变量、哪里是注释、哪里是报错点。

---

# 第 2 章 核心概念与原理

## 2.1 三件套架构：Lexer → Token → Formatter

Pygments 把"代码 → 彩色文本"拆成三个阶段：

```
原始代码
  ↓ ① Lexer（词法分析器）：按语言规则把代码切成一个个 Token
      例如 Python 的 lexer 把 def 标成 Keyword、把 函数名 标成 Name.Function
  ↓ ② Token 流：一串带类型标签的片段
  ↓ ③ Formatter（格式化器）：把 Token 流变成输出
      HtmlFormatter → 带 class 的 HTML
      TerminalFormatter → 终端彩色文字
      RtfFormatter → Word 可用的 RTF
      SvgFormatter → SVG 图片
高亮结果
```

**关键认知**：Lexer 负责"认"，Formatter 负责"画"。换主题/换输出格式不用改认代码的部分。

## 2.2 HtmlFormatter 和 CSS 分离的奥秘

`HtmlFormatter` 默认不把颜色写进 HTML 标签里，而是给每类 Token 贴一个 **class**：

```html
<span class="k">def</span>   <!-- k = Keyword -->
```

颜色全部集中在它生成的 **CSS** 里：

```css
.codehilite .k { color: #f92672; }   /* 关键词红色 */
```

**好处**：一份 CSS 管全部代码块（浏览器缓存一份），想换主题只换 CSS。**坑**：CSS 的类名前缀必须和渲染代码块的外层类名一致——博客里 codehilite 插件输出 `<div class="codehilite">`，所以 CSS 用 `.codehilite .k { ... }` 前缀。

## 2.3 和 python-markdown 的分工

- **python-markdown 的 codehilite 扩展**：把 ```python 代码块转成带 class 的结构
- **Pygments**：提供 lexer（认语言）+ HtmlFormatter（生成 CSS）

记住协作流程：**markdown 负责"这是代码块"，Pygments 负责"代码块长什么样"**。markdown 内部其实调的就是 Pygments。

---

# 第 3 章 安装与版本

```bash
pip install pygments
pip show pygments    # 版本验证
```

装 python-markdown 不会自动带 Pygments，要单独装（博客 requirements.txt 里有）。

---

# 第 4 章 API 全面讲解

## 4.1 两个核心函数：highlight 与 lex

```python
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

code = 'def hello():\n    return "hi"'

# 完整渲染：代码 + lexer + formatter
html = highlight(code, PythonLexer(), HtmlFormatter())

# 只分词（拿到 Token 流，自己处理）
from pygments import lex
tokens = lex(code, PythonLexer())   # 生成器，产出 (Token类型, 文本)
for ttype, value in tokens:
    print(ttype, repr(value))
```

## 4.2 自动识别语言：get_lexer_by_name / guess_lexer

```python
from pygments.lexers import get_lexer_by_name, guess_lexer

# 按名字（codehilite 扩展就是这么干的）
lexer = get_lexer_by_name('python', stripall=False)

# 自动猜测（不知道语言时；慢且可能猜错）
lexer = guess_lexer('print("hello")')
```

**常用参数**：`stripnl`（去首尾空行）、`stripall`（去首尾空白）、`ensurenl`（末尾保证换行）。

## 4.3 HtmlFormatter：主题、行号、cssclass

```python
fmt = HtmlFormatter(
    style='monokai',          # 配色主题：monokai/vs/github/friendly/vim/one-dark 等
    cssclass='codehilite',    # 外层类名（必须和 markdown 的 css_class 一致！）
    linenos='table',          # 显示行号：'table' 单独一列 / 'inline' 内嵌 / False 关闭
    noclasses=False,          # True 则把颜色直接写进 style（不依赖 CSS）
    nowrap=False,             # True 则不包 <pre><code>（需自定义）
)
css = fmt.get_style_defs('.codehilite')   # 生成 CSS（前缀传进去）
```

**博客用法**：

```python
from pygments.formatters import HtmlFormatter
STYLE_CSS = HtmlFormatter(style='monokai').get_style_defs('.codehilite')
# 挂到 base.html 的 <style> 里，一次生成全站生效
```

**所有可用主题**：`from pygments.styles import get_all_styles; list(get_all_styles())`。

## 4.4 命令行工具 pygmentize（零代码高亮）

Pygments 装完自带命令行工具：

```bash
# 终端里直接高亮显示文件
pygmentize -l python -f terminal hello.py

# 生成带行号的 HTML 文件
pygmentize -l python -f html -O linenos=table -o hello.html hello.py

# 列出所有支持的语言
pygmentize -L lexers

# 列出所有主题
pygmentize -L styles
```

## 4.5 自定义 Lexer 与 Formatter（🧪 进阶）

给一种小众语言写高亮：

```python
from pygments.lexer import RegexLexer
from pygments.token import *

class MyLangLexer(RegexLexer):
    name = 'MyLang'
    tokens = {
        'root': [
            (r'#.*', Comment),
            (r'\b(if|else|for)\b', Keyword),
            (r'\d+', Number),
            (r'\w+', Name),
        ],
    }

from pygments import highlight
from pygments.formatters import HtmlFormatter
print(highlight('# 注释\nif x > 1', MyLangLexer(), HtmlFormatter()))
```

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客代码高亮完整链路

```python
# app.py 里，模块加载时生成一次 CSS（别放路由里，会重复生成）
PYGMENTS_CSS = HtmlFormatter(style='monokai').get_style_defs('.codehilite')

# 模板 base.html 里挂进 <style>
# <style>{{ PYGMENTS_CSS|safe }}</style>   ← 必须 safe，否则 CSS 变文字

# markdown 渲染时 codehilite 输出：
# <div class="codehilite"><pre><span class="k">def</span>...</pre></div>
# CSS 的 .codehilite .k 精确匹配上色
```

## 5.2 独立示例：把整个目录的代码高亮成一个 HTML 文档

```python
import glob
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

parts = ['<html><head><style>', 
         HtmlFormatter(style='github').get_style_defs('.hl'),
         '</style></head><body>']
for path in sorted(glob.glob('*.py')):
    with open(path, encoding='utf-8') as f:
        code = f.read()
    parts.append(f'<h2>{path}</h2>')
    parts.append(highlight(code, get_lexer_by_name('python'),
                           HtmlFormatter(cssclass='hl')))
parts.append('</body></html>')
open('all_code.html', 'w', encoding='utf-8').write('\n'.join(parts))
```

---

# 第 6 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| CSS 类名对不上 | 代码块没颜色 | markdown 的 css_class 与 formatter 的 cssclass 必须一致（博客都是 codehilite） |
| CSS 显示成源码 | 页面上是一堆 `{ color: ... }` | 模板输出 CSS 时加 `|safe` |
| 代码全一色 | 高亮没生效 | 代码块没写语言标记（要 ```python 而不是 ```） |
| 猜语言太慢/猜错 | 页面变慢、颜色错乱 | 代码块显式写语言；codehilite 关 guess_lang |
| 换了主题没变化 | 还是旧颜色 | CSS 是"生成一次"的，改主题要重新生成并强制刷新浏览器缓存 |
| 大文件高亮卡 | 渲染很久 | 别在路由里生成；缓存渲染结果；超大文件考虑分块 |

---

# 第 7 章 学习路径与自测

**学习路径**：先会用 `highlight` + HtmlFormatter 给一段代码上色（半天）→ 理解 cssclass 匹配机制（半天）→ 学会 get_style_defs 挂 CSS（半天）→ 试命令行 pygmentize（半天）→ 进阶自定义 lexer（1 天）。

**自测题**：

1. Lexer、Token、Formatter 各负责什么？
2. 为什么 HTML 里的颜色放在 CSS 而不是标签里？有什么好处？
3. 代码块"没颜色"时，前三个排查点是什么？
4. 怎么列出所有可用主题？
5. 博客为什么在模块加载时生成 CSS 而不是每次请求时？

**答案**：
1. Lexer 认语言切 Token；Token 是带类型的片段；Formatter 把 Token 变输出。
2. 一份 CSS 管全部代码块、可缓存、换主题只换 CSS。
3. ① cssclass/css_class 是否一致 ② 代码块是否写了语言标记 ③ CSS 是否成功挂到页面（|safe）。
4. `from pygments.styles import get_all_styles; list(get_all_styles())` 或 `pygmentize -L styles`。
5. 生成一次约 20ms 且结果不变；放路由里每次都重新生成浪费性能。

---

> 下一篇：PyYAML —— YAML 解析全面教程
