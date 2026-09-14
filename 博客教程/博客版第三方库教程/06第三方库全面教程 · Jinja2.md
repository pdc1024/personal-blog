# 第三方库全面教程 · Jinja2

> 面向初学者：每个概念都从零解释。学完你能全面掌控 Jinja2 模板引擎，而不只是会博客里 `{{ }}` 那点皮毛。
> 适用版本：Jinja2 3.x ｜ 博客项目：`templates/` 目录全部页面

---

# 第 1 章 这个库是什么

Jinja2 是 Python 最流行的**模板引擎**。模板（template）就是"HTML 骨架 + 留好的空位"，引擎把数据填进空位，拼出最终网页。

没有它，你要在 Python 代码里手写 `'<div>' + title + '</div>'` 字符串拼接——又丑又容易出错（引号、转义、XSS 全是坑）。

一句话：**Jinja2 是博客的"皮肤工厂"**：`base.html` 是公共骨架，每个页面往里填自己的内容。

Jinja2 是 Flask 的默认模板引擎，装 Flask 就自动带上了，不需要单独安装。

---

# 第 2 章 核心概念与原理

## 2.1 三种定界符

| 符号 | 名字 | 作用 | 例子 |
|---|---|---|---|
| `{{ 变量 }}` | 表达式定界符 | 输出一个值 | `{{ post.title }}` |
| `{% 语句 %}` | 语句定界符 | 执行逻辑（循环、判断、继承） | `{% if post.published %}` |
| `{# 注释 #}` | 注释定界符 | 注释，不输出 | `{# 这段不会出现在网页里 #}` |

**记住**：`{{ }}` 是"给数据"，`{% %}` 是"写逻辑"。

## 2.2 渲染流程

```
Python 代码传数据（render_template('index.html', posts=posts)）
  ↓
Jinja2 把模板编译成 Python 函数（只编译一次，之后很快）
  ↓
执行时把数据填进空位 → 输出 HTML 字符串
```

**为什么很快？** 模板只在第一次访问时"编译"成 Python 代码，后续直接跑编译结果——所以博客里每个页面访问都很快。

## 2.3 自动转义（安全的第一道防线）

Jinja2 默认把 `{{ 变量 }}` 输出前做 **HTML 转义**：`<script>` 会变成 `&lt;script&gt;`，浏览器按普通文字显示，不会执行。**这就是防 XSS（跨站脚本攻击）的默认保险**。

**什么时候用 `|safe`？** 只有当你确定内容是自己生成的信任 HTML（比如 Markdown 渲染结果），才加 `|safe` 告诉 Jinja2"不用转义，直接输出"。**用户输入的内容永远别加 safe**。

---

# 第 3 章 安装与版本

```bash
pip install jinja2        # 独立安装（用 Flask 的话已自带）
pip show jinja2           # 查看版本
```

Jinja2 3.x 要求 Python 3.7+。

---

# 第 4 章 API 全面讲解

## 4.1 变量与属性访问

```jinja
{{ post.title }}          {# 属性访问 #}
{{ post['title'] }}       {# 字典访问，效果一样 #}
{{ posts|length }}        {# 过滤器：| 后面跟过滤器名 #}
{{ post.created_at|strftime('%Y-%m-%d') }}   {# 自定义过滤器（见 4.5） #}
```

**未定义变量不报错**：Jinja2 把不存在的变量当作"未定义"，输出空字符串（可配 `|default('缺省值')` 排查）。

## 4.2 过滤器（Filter）：数据处理的小工具

`{{ 值|过滤器名 }}`，可叠加：`{{ name|trim|upper }}`。

| 常用过滤器 | 作用 |
|---|---|
| `default('x')` | 变量为空时用缺省值（排查神器） |
| `length` | 长度（列表/字符串） |
| `upper` / `lower` | 大写 / 小写 |
| `trim` | 去首尾空格 |
| `join(', ')` | 列表拼成字符串 |
| `safe` | 标记为可信 HTML，不转义（慎用！） |
| `escape` | 强制转义（和 safe 相反） |
| `first` / `last` | 取第一个 / 最后一个 |
| `int` / `float` | 转数字 |
| `tojson` | 转 JSON（给 JS 用，自动转义） |
| `truncate(50)` | 截断到 50 字符（列表摘要常用） |

✅ 博客用法：文章摘要 `{{ post.summary|truncate(80) }}`；Markdown 渲染结果 `{{ post.rendered_html|safe }}`。

## 4.3 模板继承：extends / block / include

这是 Jinja2 最强大的功能，博客 `base.html` 就是靠它让所有页面共用头部导航和页脚：

```jinja
{# base.html —— 公共骨架 #}
<html>
<head><title>{% block title %}默认标题{% endblock %}</title></head>
<body>
  {% include 'nav.html' %}          {# 直接嵌入公共导航 #}
  <main>{% block content %}{% endblock %}</main>
  {% include 'footer.html' %}
</body>
</html>
```

```jinja
{# post_detail.html —— 子页面 #}
{% extends 'base.html' %}
{% block title %}{{ post.title }}{% endblock %}
{% block content %}
  <h1>{{ post.title }}</h1>
  {{ post.rendered_html|safe }}
{% endblock %}
```

| 语法 | 作用 |
|---|---|
| `{% extends 'base.html' %}` | 声明继承谁（必须在子模板第一行） |
| `{% block 名字 %}` | 开一个可被覆盖的"插槽" |
| `{{ super() }}` | 在子块里调用父块原有内容 |
| `{% include 'nav.html' %}` | 把另一个模板原样嵌入（适合公共片段） |

## 4.4 循环与判断

```jinja
{% for post in posts %}
  {% if post.published %}
    <h2>{{ post.title }}</h2>
  {% else %}
    <span style="color:gray">（草稿）</span>
  {% endif %}
{% else %}
  <p>一个文章都没有</p>          {# 列表为空时才执行 #}
{% endfor %}
```

循环内可用特殊变量：`loop.index`（从 1 开始）、`loop.index0`（从 0）、`loop.first`、`loop.last`、`loop.length`。

✅ 博客用法：首页文章卡片循环 `{% for post in posts %}`；`loop.first` 给第一条加特殊样式。

## 4.5 自定义过滤器与宏（进阶，非常实用）

**自定义过滤器**——Python 里写函数，注册给模板用：

```python
from markupsafe import Markup   # Jinja2 自带的"安全字符串"类型

@app.template_filter('plural')
def plural(n, word):
    return f"{n} {word}{'s' if n != 1 else ''}"

# 模板里：{{ 3|plural('post') }} → 3 posts
```

**宏（macro）**——模板里的"函数"，重复片段定义一次：

```jinja
{% macro post_card(post) %}
  <div class="card">
    <h2>{{ post.title }}</h2>
    <p>{{ post.summary }}</p>
  </div>
{% endmacro %}

{# 使用 #}
{% for post in posts %}{{ post_card(post) }}{% endfor %}
```

## 4.6 其他常用语法

| 语法 | 作用 |
|---|---|
| `{% set x = 1 %}` | 定义模板内变量 |
| `{% with %}` | 限定作用域（`{% with total = posts|length %}`） |
| `{% raw %}...{% endraw %}` | 原样输出，不解析模板语法（写模板教程时用） |
| `{% from 'macros.html' import post_card %}` | 从别的文件导入宏 |
| `{{ url_for('static', filename='style.css') }}` | 生成静态资源网址（Flask 注入的全局函数） |

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客的 base.html 继承链

博客的页面全部遵循：`base.html`（骨架）→ 子页面（内容块）。调试"这个页面怎么没有导航"时，先确认子页面第一行是不是 `{% extends 'base.html' %}`，以及 `{% block %}` 名字拼写一致。

## 5.2 独立示例：给模板加"时间友好化"过滤器

```python
# 在 app.py 里注册一个模板过滤器：把日期显示成"3 分钟前"
@app.template_filter('timeago')
def timeago(dt):
    import datetime
    delta = datetime.datetime.now() - dt
    seconds = int(delta.total_seconds())
    if seconds < 60:   return '刚刚'
    if seconds < 3600: return f'{seconds // 60} 分钟前'
    if seconds < 86400:return f'{seconds // 3600} 小时前'
    return f'{seconds // 86400} 天前'

# 模板里：<span>{{ post.created_at|timeago }}</span>
```

---

# 第 6 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 忘写 endfor/endif | `TemplateSyntaxError`，还常报错在下一行 | 数清楚每个 {% %} 都有配对 |
| 该加 safe 没加 | 渲染好的 HTML 变成一堆 `<h1>` 文字 | 信任的内容加 `|safe` |
| 用户输入加了 safe | 网页被弹窗/脚本劫持（XSS） | 只给"自己生成的"内容加 safe |
| block 名字拼错 | 子页面内容不显示或错位 | extends/block 名字与 base 完全一致 |
| 变量缺失不报错 | 页面静默显示空白 | 用 `|default('缺失')` 定位 |
| 打包后模板改不动 | 改了源码 templates 没变化 | 模板在 `_internal` 只读区，改源码后要重新打包 |

---

# 第 7 章 学习路径与自测

**学习路径**：先会用 `{{ }}` 和 `{% for %}`（半天）→ 掌握继承三件套（1 天）→ 学过滤器/宏（1 天）→ 自定义过滤器+安全转义（半天）。

**自测题**：

1. `{{ a|default('无') }}` 和 `{{ a }}` 的区别？
2. `|safe` 什么时候能用、什么时候绝对不能用？
3. 子页面要改标题栏，base.html 里需要提前写什么？
4. `{% include %}` 和 `{% extends %}` 的区别？
5. 循环里怎么判断"这是最后一条"？

**答案**：
1. 前者在 a 为空时显示"无"，后者输出空。
2. 内容是自己生成的信任 HTML 时能用；用户输入/不可信内容绝对不能用。
3. base.html 里要有 `<title>{% block title %}...{% endblock %}</title>` 插槽。
4. include 是"嵌入一个片段"；extends 是"继承一个骨架"，子页填 block。
5. `{% if loop.last %}`。

---

> 下一篇：Werkzeug —— Flask 底层引擎全面教程
