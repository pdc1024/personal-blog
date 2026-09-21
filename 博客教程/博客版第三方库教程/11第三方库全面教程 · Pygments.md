# 第三方库全面教程 · Pygments

> 面向初学者到进阶者：博客代码块五颜六色就是它。
> 学完这份教程，你会掌握 Lexer/Token/Formatter 三件套、主题、行号、命令行和自定义 Lexer。
>
> 适用版本：Pygments 2.x ｜ 博客项目：`app.py` 生成高亮 CSS + python-markdown codehilite

---

# 第 1 章 认识 Pygments

## 1.1 一句话定位

Pygments 是 Python 最强大的**通用语法高亮引擎**，识别 500+ 种语言：

```python
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

html = highlight('def hello(): return 1', PythonLexer(), HtmlFormatter())
```

一句话：**博客代码块的化妆师**。

---

# 第 2 章 三件套架构

```
原始代码
  ↓ Lexer 分词：按语言切成 Token
  ↓ Token 流
  ↓ Formatter：变成 HTML
高亮结果
```

- **Lexer**：认语言（PythonLexer、JavaScriptLexer）；
- **Formatter**：画输出（HtmlFormatter、TerminalFormatter）；
- 换主题只改 Formatter。

## 2.1 CSS 分离

HtmlFormatter 贴 class，颜色在 CSS：

```html
<span class="k">def</span>
```

```css
.codehilite .k { color: #f92672; }
```

一份 CSS 管全部代码块。

## 2.2 和 python-markdown 分工

markdown codehilite 负责"这是代码块"，Pygments 负责"代码长什么样"。

---

# 第 3 章 API

## 3.1 highlight

```python
highlight(code, PythonLexer(), HtmlFormatter())
```

## 3.2 自动识别

```python
from pygments.lexers import get_lexer_by_name, guess_lexer
lexer = get_lexer_by_name('python')
```

## 3.3 HtmlFormatter 参数

```python
HtmlFormatter(
    style='monokai',
    cssclass='codehilite',
    linenos='table',
)
```

## 3.4 命令行

```bash
pygmentize hello.py
pygmentize -f html -o out.html hello.py
pygmentize -L styles
```

---

# 第 4 章 项目实战

## 4.1 博客高亮 CSS（app.py 第 43 行）

```python
from pygments.formatters import HtmlFormatter
STYLE_CSS = HtmlFormatter(style='monokai').get_style_defs('.codehilite')
```

模板里 `<style>{{ STYLE_CSS|safe }}</style>`。

---

# 第 5 章 高频坑

| # | 坑 | 解决 |
|---|---|---|
| 1 | CSS 类名不匹配 | cssclass 一致 |
| 2 | CSS 显示成源码 | 模板加 \|safe |
| 3 | 代码全灰 | 写语言标记 ```python |
| 4 | 换主题没变 | 重新生成 CSS |
| 5 | 大文件高亮卡 | 缓存结果 |

---

# 第 6 章 自测

1. Lexer、Token、Formatter 各做什么？
2. 为什么颜色放 CSS？
3. 代码块没颜色前三个排查点？
4. 怎么列所有主题？

**答案**：
1. 认语言、中间产物、输出。
2. 一份 CSS 管全部、可缓存、换主题只换 CSS。
3. cssclass 一致、写语言标记、CSS 成功挂页面。
4. `get_all_styles()` 或 `pygmentize -L styles`。

---

> 下一篇：PyYAML —— YAML 解析全面教程
