# 第三方库全面教程 · Pygments

> 面向初学者：博客文章里代码块五颜六色，就是 Pygments 的功劳。
> 学完这份教程，你不仅能给代码上色，还能用命令行高亮文件、加行号、换任意配色主题、自定义 Lexer。
> 适用版本：Pygments 2.x ｜ 博客项目：`app.py` 生成高亮 CSS + python-markdown codehilite

---

# 第 1 章 这个库是什么

## 1.1 一句话定位

Pygments 是 Python 世界最强大的**通用语法高亮引擎**——识别 500+ 种编程语言，把代码按"关键词/字符串/注释/函数名"拆开，渲染成带颜色的 HTML。

一句话：**Pygments 是博客代码块的"化妆师"**。它不认识博客的任何代码，但任何语言的代码它都能认出语法结构并上色。

## 1.2 为什么需要它

没有高亮，代码块就是一堆灰色文字，读者分不清变量、注释、报错点。Pygments 让代码：

- 关键词变蓝；
- 字符串变绿；
- 注释变灰斜体；
- 函数名变黄。

阅读体验提升一个档次。

## 1.3 一个最小例子

```python
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

code = 'def hello():\n    return "hi"'
html = highlight(code, PythonLexer(), HtmlFormatter())
print(html)
# <div class="highlight"><pre><span class="k">def</span> ...
```

---

# 第 2 章 核心概念与原理

## 2.1 三件套架构

```
原始代码
  ↓ ① Lexer（词法分析器）：按语言规则把代码切成 Token
  ↓ ② Token 流：一串带类型标签的片段
  ↓ ③ Formatter（格式化器）：把 Token 流变成输出
高亮结果
```

- **Lexer 负责"认"**：PythonLexer、JavaScriptLexer；
- **Formatter 负责"画"**：HtmlFormatter、TerminalFormatter；
- 换主题/换格式不用改认代码的部分。

## 2.2 HtmlFormatter 和 CSS 分离

HtmlFormatter 默认不把颜色写进 HTML 标签，而是贴 class：

```html
<span class="k">def</span>   <!-- k = Keyword -->
```

颜色全部集中在 CSS：

```css
.codehilite .k { color: #f92672; }
```

**好处**：一份 CSS 管全部代码块，浏览器缓存一份；换主题只换 CSS。
**坑**：CSS 类名前缀必须和 markdown codehilite 输出的外层 class 一致——博客都是 `codehilite`。

## 2.3 和 python-markdown 的分工

- python-markdown 的 codehilite 扩展：把 ```python 代码块转成带 class 的结构；
- Pygments：提供 lexer + HtmlFormatter（生成 CSS）。

**markdown 负责"这是代码块"，Pygments 负责"代码长什么样"**。

---

# 第 3 章 安装与版本

```bash
pip install pygments
pip show pygments
```

装 python-markdown 不会自动带 Pygments，要单独装。

---

# 第 4 章 API 全面讲解

## 4.1 核心函数

```python
from pygments import highlight, lex
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

# 完整渲染
html = highlight(code, PythonLexer(), HtmlFormatter())

# 只分词（拿 Token 流）
tokens = lex(code, PythonLexer())
for ttype, value in tokens:
    print(ttype, repr(value))
```

## 4.2 自动识别语言

```python
from pygments.lexers import get_lexer_by_name, guess_lexer

lexer = get_lexer_by_name('python', stripall=False)   # 按名字
lexer = guess_lexer('print("hello")')                 # 自动猜
```

## 4.3 HtmlFormatter 常用参数

```python
fmt = HtmlFormatter(
    style='monokai',          # 配色主题
    cssclass='codehilite',    # 外层类名
    linenos='table',          # 行号：'table'/'inline'/False
    noclasses=False,          # True 则颜色直接写进 style
    nowrap=False,
)
css = fmt.get_style_defs('.codehilite')
```

**所有主题**：

```python
from pygments.styles import get_all_styles
print(list(get_all_styles()))
# ['monokai', 'github', 'friendly', 'vim', 'vs', ...]
```

## 4.4 命令行工具 pygmentize

```bash
pygmentize -l python -f terminal hello.py          # 终端高亮
pygmentize -l python -f html -O linenos=table -o out.html hello.py
pygmentize -L lexers                                # 列出所有语言
pygmentize -L styles                                # 列出所有主题
```

## 4.5 自定义 Lexer（进阶）

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
```

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客代码高亮完整链路（app.py 第 42~52 行）

```python
from pygments.formatters import HtmlFormatter

# 模块加载时生成一次 CSS（别放路由里）
_STYLE_CSS = HtmlFormatter(style='monokai').get_style_defs('.codehilite')

# 模板 base.html：
# <style>{{ _STYLE_CSS|safe }}</style>
```

codehilite 输出 `<div class="codehilite">...<span class="k">def</span>...</div>`，CSS 的 `.codehilite .k` 精确匹配上色。

## 5.2 独立示例：整个目录高亮成一个 HTML

```python
import glob
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

parts = ['<html><head><style>',
         HtmlFormatter(style='github').get_style_defs('.hl'),
         '</style></head><body>']
for path in sorted(glob.glob('*.py')):
    code = open(path, encoding='utf-8').read()
    parts.append(f'<h2>{path}</h2>')
    parts.append(highlight(code, get_lexer_by_name('python'),
                           HtmlFormatter(cssclass='hl')))
parts.append('</body></html>')
open('all_code.html', 'w', encoding='utf-8').write('\n'.join(parts))
```

---

# 第 6 章 高频坑与排查

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | CSS 类名对不上 | 代码块没颜色 | cssclass 和 codehilite css_class 一致 |
| 2 | CSS 显示成源码 | 页面一堆 `{ color: ... }` | 模板输出 CSS 加 `|safe` |
| 3 | 代码全一色 | 高亮没生效 | 代码块写语言标记 ```python |
| 4 | 猜语言慢/错 | 页面慢 | 显式写语言；guess_lang=False |
| 5 | 换主题没变化 | 还是旧颜色 | CSS 生成一次，改主题要重新生成 + 清缓存 |
| 6 | 大文件高亮卡 | 渲染久 | 别在路由里生成；缓存结果 |
| 7 | 深色主题下浅色 CSS | 代码块白底 | 选和博客主题匹配的 style |
| 8 | linenums 错位 | 行号对不上代码 | 用 'table' 而不是 'inline' |

---

# 第 7 章 学习路径与自测

## 7.1 学习路径

- 半天：highlight + HtmlFormatter 上色；
- 半天：理解 cssclass 匹配；
- 半天：get_style_defs 挂 CSS；
- 半天：pygmentize 命令行；
- 1 天：自定义 lexer（可选）。

## 7.2 自测题

1. Lexer、Token、Formatter 各负责什么？
2. 为什么颜色放 CSS 而不是标签里？
3. 代码块没颜色时前三个排查点？
4. 怎么列出所有可用主题？
5. 博客为什么在模块加载时生成 CSS？
6. noclasses=True 是什么效果？
7. linenos='table' 和 'inline' 区别？

## 7.3 答案

1. Lexer 认语言切 Token；Token 是带类型的片段；Formatter 把 Token 变输出。
2. 一份 CSS 管全部代码块、可缓存、换主题只换 CSS。
3. ① cssclass 一致 ② 代码块写语言标记 ③ CSS 成功挂到页面（|safe）。
4. `from pygments.styles import get_all_styles; list(get_all_styles())` 或 `pygmentize -L styles`。
5. 生成一次约 20ms 且结果不变；放路由每次都重新生成浪费。
6. 颜色直接写进 style 属性，不依赖外部 CSS。
7. table 是单独一列行号（对齐好）；inline 行号内嵌在代码行里。

## 7.4 进一步学习

- 官方文档：https://pygments.org/
- 主题预览：https://pygments.org/demo/

---

> 下一篇：PyYAML —— YAML 解析全面教程
