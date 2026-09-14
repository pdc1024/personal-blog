# 第三方库全面教程 · Pygments（独立版）

> 面向初学者：本教程**独立成篇**，假设你会基础 Python。术语第一次出现都有白话解释。
> 适用版本：Pygments 2.x ｜ 配套知识：与《python-markdown》配合（codehilite 扩展底层就是 Pygments）。
> 学习目标：从"代码还是黑白的"到"能用 Pygments 给任何语言的代码上色高亮，生成网页/终端/HTML 样式"。

---

# 第 1 章 这个库是什么

## 1.1 一句话认识 Pygments

**Pygments** 是 Python 的**语法高亮引擎**：把代码字符串拆成"关键字、字符串、注释、数字、变量"等 token，再按配色方案渲染成彩色 HTML、终端 ANSI 色或图片。

```python
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

code = "def hello():\n    print('world')"
html = highlight(code, PythonLexer(), HtmlFormatter())
print(html)   # <div class="highlight"><pre>...<span class="k">def</span>...
```

## 1.2 三个核心对象

| 对象 | 作用 | 例子 |
|---|---|---|
| **Lexer（词法分析器）** | 识别语言、拆 token | `PythonLexer()`、`get_lexer_by_name("python")` |
| **Formatter（格式化器）** | 把 token 变成输出格式 | `HtmlFormatter()`、`TerminalFormatter()` |
| **Style（样式）** | 配色方案 | `'monokai'`、`'friendly'`、`'vs'` |

## 1.3 能干嘛

- 网页代码高亮（博客、文档站、教程站）。
- 终端彩色代码。
- 生成高亮图片。
- python-markdown 的 `codehilite` 扩展**底层就是它**。

---

# 第 2 章 核心概念与原理

## 2.1 高亮流程

```
代码字符串
  ↓ Lexer 分析（按语言规则拆成 token）
Token 流（类型 + 文本）
  ↓ Formatter 渲染（按 Style 配色）
彩色输出（HTML/终端色/图片）
```

## 2.2 Token 类型

Pygments 把代码分成几百种 token 类型，常用：

| Token 类型 | 含义 | 例 |
|---|---|---|
| `Token.Keyword` | 关键字 | `def`、`if`、`import` |
| `Token.String` | 字符串 | `"abc"`、`'x'` |
| `Token.Comment` | 注释 | `# 注释` |
| `Token.Number` | 数字 | `123`、`3.14` |
| `Token.Name` | 变量/函数名 | `hello` |
| `Token.Operator` | 运算符 | `+`、`==` |
| `Token.Punctuation` | 标点 | `(`、`)`、`,` |

## 2.3 Lexer 的选择

- 精确指定：`PythonLexer()`（快）。
- 按文件名/语言名自动：`get_lexer_by_name("python")`、`get_lexer_for_filename("app.py")`。
- 智能猜测：`guess_lexer(code)`（慢，可能猜错）。

---

# 第 3 章 安装与版本

```bash
pip install pygments
```

- 当前稳定版 2.x。
- python-markdown 的 codehilite 会自动调用（需安装）。
- 验证：`python -c "from pygments import highlight; print('ok')"`。

---

# 第 4 章 API 全面讲解

> 标注：✅ = 必会；➕ = 推荐；🧪 = 进阶

## 4.1 最简高亮（✅）

```python
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

code = "x = 1 + 2  # 计算"
html = highlight(code, PythonLexer(), HtmlFormatter())
# <div class="highlight"><pre>...<span class="k">x</span> ...
```

## 4.2 按语言名/文件名选择 Lexer（✅）

```python
from pygments import highlight
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.formatters import HtmlFormatter

# 按语言名
lexer = get_lexer_by_name("python")
lexer = get_lexer_by_name("javascript")
lexer = get_lexer_by_name("bash")
lexer = get_lexer_by_name("html")

# 按文件名（自动识别扩展名）
lexer = get_lexer_for_filename("app.py")

# 支持的语言列表
from pygments.lexers import get_all_lexers
print([name for name, _, _, _ in get_all_lexers()][:20])
```

## 4.3 HtmlFormatter 配置（✅ 网页高亮）

```python
from pygments.formatters import HtmlFormatter

# 常用参数
fmt = HtmlFormatter(
    style="monokai",          # 配色：friendly/vs/monokai/...（上百种）
    cssclass="codehilite",    # 外层 CSS 类名
    linenos=True,             # 显示行号
    nowrap=False,
    full=False,               # True = 输出完整 HTML 文档
)

html = highlight(code, lexer, fmt)
```

## 4.4 生成配套 CSS（✅ 关键一步）

HTML 里只有 `<span class="k">` 等类名，**颜色在 CSS 里**——必须生成 CSS：

```python
from pygments.formatters import HtmlFormatter

css = HtmlFormatter(style="monokai", cssclass="codehilite").get_style_defs()
with open("pygments.css", "w", encoding="utf-8") as f:
    f.write(css)

# HTML 里引入：
# <link rel="stylesheet" href="pygments.css">
```

**⚠️ 新手最大坑**：光 highlight 没引 CSS，代码全是默认色（但 span 结构在）。

## 4.5 终端彩色输出（➕）

```python
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter

highlight(code, PythonLexer(), TerminalFormatter())
# 终端直接显示彩色代码
```

## 4.6 行号与行内高亮（➕）

```python
# 行号
fmt = HtmlFormatter(linenos=True)
# 高亮某几行（diff 场景）
fmt = HtmlFormatter(hl_lines=[2, 5])     # 第 2、5 行加背景色
```

## 4.7 图片输出（🧪）

```bash
pip install pygments pillow
```

```python
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import ImageFormatter

highlight(code, PythonLexer(), ImageFormatter(style="monokai"),
          outfile="code.png")   # 生成代码图片（分享用）
```

## 4.8 自定义样式（🧪）

```python
from pygments.style import Style
from pygments.token import Keyword, String, Comment, Name

class MyStyle(Style):
    default_style = ""
    styles = {
        Keyword: "bold #e74c3c",      # 关键字红色加粗
        String: "#27ae60",            # 字符串绿色
        Comment: "italic #95a5a6",    # 注释灰色斜体
        Name: "#2c3e50",
    }

fmt = HtmlFormatter(style=MyStyle)
```

---

# 第 5 章 实战项目案例

## 案例 1（入门级）：多语言代码高亮工具

```python
"""按扩展名自动识别语言并生成带 CSS 的高亮 HTML"""
import sys
from pygments import highlight
from pygments.lexers import get_lexer_for_filename
from pygments.formatters import HtmlFormatter

def highlight_file(path):
    with open(path, encoding="utf-8") as f:
        code = f.read()
    lexer = get_lexer_for_filename(path)          # 自动识别
    fmt = HtmlFormatter(style="friendly", cssclass="codehilite")
    html = highlight(code, lexer, fmt)
    css = fmt.get_style_defs()
    full = f"""<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>{css}</style></head><body>{html}</body></html>"""
    out = path + ".html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(full)
    print(f"已生成 {out}")

if __name__ == "__main__":
    highlight_file(sys.argv[1])
```

## 案例 2（进阶级）：python-markdown + Pygments 高亮博客

```python
import markdown
from pygments.formatters import HtmlFormatter

# ① 生成高亮 CSS
css = HtmlFormatter(style="monokai", cssclass="codehilite").get_style_defs()
with open("static/pygments.css", "w", encoding="utf-8") as f:
    f.write(css)

# ② Markdown 转 HTML（codehilite 底层用 Pygments）
md_text = """```python
def greet(name):
    return f"你好，{name}！"
```"""
html = markdown.markdown(md_text, extensions=["fenced_code", "codehilite"],
    extension_configs={"codehilite": {"css_class": "codehilite"}})
print(html)
# <div class="codehilite"><pre><span></span><code>
# <span class="k">def</span> <span class="n">greet</span>...
```

**注意**：`css_class` 必须和生成 CSS 时的 `cssclass` 一致，颜色才对得上。

## 案例 3（综合）：**教程站代码高亮渲染器**

```python
"""批量把 .md 教程转成带代码高亮 + 目录的 HTML"""
import os
import markdown
from pygments.formatters import HtmlFormatter

def build(src_dir, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    # 一次性 CSS
    css = HtmlFormatter(style="monokai", cssclass="codehilite").get_style_defs()
    with open(os.path.join(dst_dir, "pygments.css"), "w", encoding="utf-8") as f:
        f.write(css)

    md = markdown.Markdown(extensions=[
        "toc", "fenced_code", "codehilite", "tables"],
        extension_configs={
            "codehilite": {"css_class": "codehilite"},
            "toc": {"toc_depth": "1-3"},
        })

    for name in sorted(os.listdir(src_dir)):
        if not name.endswith(".md"):
            continue
        md.reset()
        with open(os.path.join(src_dir, name), encoding="utf-8") as f:
            body = md.convert(f.read())
        title = name[:-3]
        html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<title>{title}</title>
<link rel="stylesheet" href="pygments.css">
<style>
body {{ max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.7; }}
pre {{ border-radius: 8px; padding: 12px; overflow-x: auto; }}
</style></head><body>
{md.toc}
<hr>
{body}
</body></html>"""
        with open(os.path.join(dst_dir, name[:-3] + ".html"), "w", encoding="utf-8") as f:
            f.write(html)
    print(f"完成：{len(os.listdir(dst_dir))} 个文件")

if __name__ == "__main__":
    build("docs", "site")
```

**本案例是"教程网站"的雏形**：Markdown 写作 → 自动高亮 + 目录 → 静态 HTML 站。

---

# 第 6 章 进阶内容（大神之路）

## 6.1 性能与缓存

- 每次 highlight 都有词法分析成本；**文章保存时转好存 HTML**，别每次请求现转。
- 大文件分段处理（Pygments 一次处理整个文件，超大文件注意内存）。

## 6.2 行号与折叠（大代码块友好）

```python
fmt = HtmlFormatter(linenos="table", lineanchors="line", anchorlinenos=True)
# 每行带锚点，可做"点击行号跳转/折叠"交互
```

## 6.3 与 Jinja2 结合

```jinja2
{% macro highlight_code(code, lang) %}
  <div class="codehilite">{{ highlight(code, get_lexer_by_name(lang), html_fmt) | safe }}</div>
{% endmacro %}
```

Python 侧把 `highlight` 函数、lexer 选择器、formatter 传给模板即可。

---

# 第 7 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 高亮没颜色 | span 有但全黑 | 没引 Pygments CSS！生成 cssclass 一致的 CSS |
| cssclass 对不上 | 样式不生效 | HtmlFormatter(cssclass=...) 与 CSS 的 cssclass 必须一致 |
| 语言识别错 | Python 代码按别的语言高亮 | 显式 `get_lexer_by_name` 或 `get_lexer_for_filename` |
| guess_lexer 慢/错 | 大文件卡 | 别用 guess，显式指定 lexer |
| codehilite 里没高亮 | Markdown 代码块黑白 | 装 Pygments + 配 codehilite 扩展 + 引 CSS |
| 行号没显示 | linenos 无效 | `HtmlFormatter(linenos=True)`；"table" 模式更稳 |
| 中文注释乱码 | 高亮后中文乱 | 文件 UTF-8；HTML charset UTF-8 |
| 特殊语言不支持 | LexerError | `get_all_lexers()` 查支持列表；用 guess_lexer 兜底 |
| 图片输出报错 | ImageFormatter 失败 | `pip install pillow` |
| 输出有转义问题 | HTML 标签被当代码 | Pygments 自动转义代码内容，正常现象 |

---

# 第 8 章 学习路径与自测

**学习路径**：
1. highlight + PythonLexer + HtmlFormatter（半天）
2. get_lexer_by_name / for_filename（半天）
3. 生成 CSS（半天，必配）
4. 多配色 style（半天）
5. 行号/行高亮（半天）
6. 与 python-markdown 集成（1 天）
7. 终端彩色输出（半天）
8. 自定义样式（1 天）
9. 批量文档站（2 天，案例 3）

**自测题**：
1. Pygments 的三个核心对象是什么？
2. 高亮输出为什么没颜色？两步解决？
3. 怎么按文件名自动选 Lexer？
4. `cssclass` 和 `get_style_defs()` 的关系？
5. codehilite 和 Pygments 是什么关系？
6. 终端彩色输出用什么 Formatter？
7. 生成代码图片需要什么？
8. 自定义配色怎么搞？
9. 高亮性能上要注意什么？
10. 综合：描述"Markdown 代码块 → 高亮 → 引入 CSS → 页面显示彩色代码"链路。

**答案提示**：
1. Lexer（拆 token）、Formatter（渲染）、Style（配色）。
2. ① 生成 CSS `HtmlFormatter().get_style_defs()`；② 页面引入且 cssclass 一致。
3. `get_lexer_for_filename("app.py")`。
4. HTML 类名由 cssclass 决定，CSS 选择器也要用同一 cssclass 才匹配。
5. codehilite 扩展内部调用 Pygments 做高亮（markdown → pygments）。
6. `TerminalFormatter()`。
7. `ImageFormatter()` + 安装 Pillow。
8. 继承 `Style` 类，写 `styles` 字典（Token 类型 → 颜色样式）。
9. 别每次请求现转；文章保存时缓存 HTML。
10. 参考案例 2：fenced_code+codehilite 扩展 → highlight → pygments.css 引入。

---

> 下一篇：《PyYAML（独立版）》——配置文件解析从零到精通。
