# 第三方库全面教程 · Jinja2

> 面向初学者：不假设你懂模板引擎，每个概念第一次出现都用大白话讲透。
> 学完这份教程，你不仅能看懂博客 `templates/` 下所有 HTML，还能自己设计一套带宏、过滤器、继承链的复杂模板系统。
> 适用版本：Jinja2 3.x（Flask 3.x 自带）｜ 博客项目：`templates/` 目录全部页面

---

# 第 1 章 这个库是什么

## 1.1 一句话定位

Jinja2 是 Python 世界最流行的 **模板引擎（Template Engine）**。它解决的问题是：

- 后端 Python 产生数据（文章列表、用户信息）；
- 前端要展示成 HTML；
- 直接用 Python 字符串拼接：`'<h1>' + post.title + '</h1>'`——引号、转义、缩进、XSS 全是坑。

模板引擎的做法是：**写一个 HTML 骨架，在需要数据的地方留空位，让引擎把数据填进去**。

```html
<!-- post.html -->
<h1>{{ post.title }}</h1>
<p>{{ post.body }}</p>
```

```python
render_template('post.html', post={'title': '你好', 'body': '正文'})
# → <h1>你好</h1><p>正文</p>
```

一句话：**Jinja2 是博客的"皮肤工厂"**。`base.html` 是公共骨架，每个子页面往里填自己的内容。

## 1.2 为什么博客选 Jinja2

- **Flask 官方默认**：装 Flask 就自动带上，零配置；
- **语法和 Django Templates / Nunjucks 几乎一样**：学会了一个，其他的也能看懂；
- **性能好**：模板编译成 Python 字节码后执行，比"逐行解析字符串"快几个数量级；
- **功能完整**：继承、宏、过滤器、自动转义、沙箱模式，企业级项目用得上的它都有。

## 1.3 一个最小 Jinja2 程序

不通过 Flask，直接用 Jinja2：

```python
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates'))   # 模板从哪找
template = env.get_template('post.html')                   # 加载
html = template.render(title='你好', body='正文')          # 渲染
print(html)
```

Flask 的 `render_template()` 就是对这套 API 的封装，帮你把 `env` 初始化、上下文传参、自动转义都做好了。

---

# 第 2 章 核心概念与原理

## 2.1 三种定界符

| 符号 | 名字 | 作用 | 例子 |
|---|---|---|---|
| `{{ 变量 }}` | 表达式输出 | 输出一个值 | `{{ post.title }}` |
| `{% 语句 %}` | 控制结构 | 循环、判断、继承、宏 | `{% if post.published %}` |
| `{# 注释 #}` | 注释 | 不输出到 HTML | `{# 这段不会出现在网页里 #}` |

**记忆**：`{{ }}` 是"给数据"，`{% %}` 是"写逻辑"，`{# #}` 是"自言自语"。

## 2.2 渲染流程：模板是怎么跑起来的

```
① 第一次请求某个模板
   ↓
Jinja2 读 .html 文件
   ↓
词法分析 → 语法分析 → 编译成 Python 函数
   （这一步只在第一次做，之后缓存）
   ↓
② 后续每次请求
   调用编译好的 Python 函数，把数据填进去
   ↓
得到 HTML 字符串
```

**为什么快？** 模板只在第一次访问时"编译"成 Python 代码。比如 `{{ post.title }}` 会被编译成 `str(post['title'])` 这样的 Python 表达式，直接跑——比"每次都重新解析模板字符串"快几十倍。

**调试技巧**：在 Flask 里设置 `app.jinja_env.auto_reload = True`（debug 模式默认开），改模板不用重启。生产环境关掉这个检查能再快一点。

## 2.3 变量查找：点号 `.` 是怎么解析的

`{{ post.title }}` 里的 `.`，Jinja2 会按以下顺序尝试：

1. `post['title']`（字典下标）
2. `post.title`（属性访问）
3. `post.title()`（方法调用，如果它是 callable）

**好处**：你的视图函数返回一个 SQLAlchemy 模型对象，模板里写 `{{ post.title }}` 能直接拿到 `Post.title` 列——不管它是字典还是对象都行。

**找不到怎么办？** Jinja2 把不存在的变量当作 `Undefined`，输出空字符串，**不报错**。这既是好事（模板容错）也是坏事（拼错变量名静默失败）。调试时用 `{{ post.title|default('未定义') }}` 能立刻发现。

## 2.4 自动转义：安全的第一道防线

Jinja2 默认把 `{{ 变量 }}` 输出前做 **HTML 转义**：

```
用户输入：<script>alert(1)</script>
{{ 用户输入 }} 输出：&lt;script&gt;alert(1)&lt;/script&gt;
```

浏览器看到的就是普通文字，**不会执行**。这就是防 XSS（跨站脚本攻击）的默认保险。

**什么时候用 `|safe`？** 只有当你确定内容是**自己生成的信任 HTML**（比如 Markdown 渲染好的 HTML 片段），才加 `|safe` 告诉 Jinja2"不用转义，直接输出"。

```jinja
{# 安全：post.rendered_html 是博客后端用 python-markdown 渲染的，作者本人内容 #}
{{ post.rendered_html|safe }}

{# 危险：如果 comment.content 是访客写的，加 safe 等于放行 XSS #}
{{ comment.content|safe }}    {# ❌ 别这么干 #}
```

**MarkupSafe**：`|safe` 返回的是 `markupsafe.Markup` 类型——一种"已经安全、不用再转义"的字符串。理解它对写自定义过滤器很重要。

## 2.5 模板继承（Template Inheritance）

Jinja2 最强大的功能。博客 `base.html` 就是靠它让所有页面共用头部导航和页脚。

### 2.5.1 父模板（base.html）

```jinja
<!DOCTYPE html>
<html>
<head>
  <title>{% block title %}默认标题{% endblock %}</title>
  {% block head %}{% endblock %}
</head>
<body>
  {% include 'nav.html' %}
  <main>
    {% block content %}{% endblock %}
  </main>
  <footer>© {{ year }}</footer>
</body>
</html>
```

`{% block 名字 %}` 是"插槽"——子模板可以填进来。

### 2.5.2 子模板（post_detail.html）

```jinja
{% extends 'base.html' %}

{% block title %}{{ post.title }} - 我的博客{% endblock %}

{% block head %}
<style>.post-body { line-height: 1.8; }</style>
{% endblock %}

{% block content %}
  <article>
    <h1>{{ post.title }}</h1>
    {{ post.rendered_html|safe }}
  </article>
{% endblock %}
```

### 2.5.3 工作原理

1. `{% extends 'base.html' %}` 必须是子模板**第一行**；
2. Jinja2 先加载父模板，把所有 `{% block %}` 记录成"插槽"；
3. 子模板里同名 block 覆盖父模板；
4. 子模板没定义的 block，用父模板默认内容；
5. `{{ super() }}` 在子 block 里调用父 block 原内容——想"在父内容基础上加东西"时用。

### 2.5.4 include vs extends

| 语法 | 作用 | 类比 |
|---|---|---|
| `{% extends 'base.html' %}` | 继承骨架，子填 block | 面向对象里的 class 继承 |
| `{% include 'nav.html' %}` | 把另一个模板原样插进来 | 函数调用 |
| `{% from 'macros.html' import card %}` | 导入宏（函数） | import |

## 2.6 上下文隔离与数据流向

`render_template('x.html', a=1, b=2)` 传的变量，模板里直接用 `{{ a }}`。模板里定义的 `{% set x = 3 %}` 不会泄漏到其他模板。

**请求期间注入的全局变量**（`@app.context_processor`）所有模板都能用，不用每次传——博客的 `inject_globals` 就是这么干的。

---

# 第 3 章 安装与版本

```bash
pip install jinja2          # 用 Flask 的话自动带上
pip show jinja2             # 查看版本
```

Jinja2 3.x 要求 Python 3.7+。博客 `requirements.txt` 显式写出是为了锁定版本，避免未来升级 API 变化。

---

# 第 4 章 API 全面讲解

> 标注：✅ = 博客项目正在用；➕ = 很常用但项目没用到；🧪 = 进阶能力。

## 4.1 变量与属性访问

```jinja
{{ post.title }}              {# 属性访问 #}
{{ post['title'] }}           {# 字典访问，效果一样 #}
{{ posts[0].title }}          {# 列表下标 #}
{{ post.tags|join(', ') }}    {# 过滤器：| 后面跟过滤器名 #}
{{ post.created_at|strftime('%Y-%m-%d') }}   {# 自定义过滤器（见 4.6） #}
```

## 4.2 控制结构

### 4.2.1 if / elif / else

```jinja
{% if post.published %}
  <span class="badge-pub">已发布</span>
{% elif post.draft %}
  <span class="badge-draft">草稿</span>
{% else %}
  <span class="badge-del">已删除</span>
{% endif %}
```

支持 `and` / `or` / `not` / `==` / `!=` / `>` / `<` / `in`：

```jinja
{% if post.published and post.comments|length > 0 %}
  有评论
{% endif %}

{% if 'Python' in post.tags %}
  这篇是 Python
{% endif %}
```

### 4.2.2 for 循环

```jinja
{% for post in posts %}
  <h2>{{ loop.index }}. {{ post.title }}</h2>
{% else %}
  <p>还没有文章</p>          {# 列表为空时才执行 #}
{% endfor %}
```

**`{% else %}` 配合 for** 是 Jinja 的特色：`posts` 为空时执行 else 块。

循环内特殊变量：

| 变量 | 含义 |
|---|---|
| `loop.index` | 当前序号，从 1 开始 |
| `loop.index0` | 当前序号，从 0 开始 |
| `loop.first` | 是否第一条 |
| `loop.last` | 是否最后一条 |
| `loop.length` | 列表总长度 |
| `loop.revindex` | 倒序序号（从 1 开始） |
| `loop.cycle('even', 'odd')` | 交替输出（斑马纹表格） |
| `loop.depth` | 当前递归层级（递归循环用） |

✅ 博客用法：`loop.first` 给首页第一条文章加大图样式；`loop.cycle('row-a','row-b')` 做友链表格斑马纹。

### 4.2.3 set：定义模板内变量

```jinja
{% set total = posts|length %}
<p>共 {{ total }} 篇文章</p>
```

`{% with %}` 限定作用域：

```jinja
{% with x = 1 %}
  在这个块里 x=1
{% endwith %}
出了块 x 不存在
```

## 4.3 过滤器（Filter）大全

`{{ 值|过滤器名(参数) }}`，可叠加：`{{ name|trim|upper }}`。

### 4.3.1 字符串类

| 过滤器 | 作用 | 例子 |
|---|---|---|
| `upper` / `lower` | 大/小写 | `'hi'|upper` → HI |
| `trim` | 去首尾空格 | |
| `capitalize` | 首字母大写其余小写 | |
| `title` | 每个单词首字母大写 | |
| `center(80)` | 居中填充到 80 字符 | |
| `replace('a','b')` | 替换 | |
| `truncate(80, True)` | 截断到 80 字符（第二参数是否带省略号） | |
| `wordcount` | 字数 | |

### 4.3.2 列表/容器类

| 过滤器 | 作用 |
|---|---|
| `length` | 长度 |
| `first` / `last` | 取首/尾 |
| `join(', ')` | 拼成字符串 |
| `sort` | 排序 |
| `unique` | 去重 |
| `sum` / `max` / `min` | 聚合 |
| `map('title')` | 对每个元素应用过滤器 |
| `selectattr('published')` | 过滤属性为真的元素 |

### 4.3.3 默认与安全类

| 过滤器 | 作用 |
|---|---|
| `default('x')` / `d('x')` | 未定义时用默认值 |
| `default('x', boolean=True)` | 空字符串/0/False 也用默认值 |
| `safe` | 标记为信任 HTML，不转义 |
| `escape` / `e` | 强制转义 |

✅ 博客用法：`{{ post.summary|truncate(80) }}` 做摘要；`{{ post.rendered_html|safe }}` 输出 Markdown 渲染结果。

### 4.3.4 日期/数字类

| 过滤器 | 作用 |
|---|---|
| `int` / `float` | 转数字 |
| `round(2)` | 四舍五入到 2 位 |
| `tojson` | 转 JSON（给 JS 用，自动安全转义） |

✅ 博客自定义：`strftime`、`localtime`、`timeago` 等（见 4.6）。

### 4.3.5 tojson：把数据传给 JS

```jinja
<script>
var POSTS = {{ posts|tojson }};
</script>
```

`tojson` 自动处理引号、反斜杠、`</script>`——直接 `{{ posts|safe }}` 会出 XSS。

## 4.4 宏（Macro）：模板里的函数

重复的 HTML 片段定义一次，到处调用：

```jinja
{# macros.html #}
{% macro post_card(post) %}
  <div class="card">
    <h3><a href="/post/{{ post.id }}/">{{ post.title }}</a></h3>
    <p class="meta">{{ post.created_at|strftime('%Y-%m-%d') }}</p>
    <p>{{ post.summary|truncate(60) }}</p>
  </div>
{% endmacro %}
```

其他模板导入并使用：

```jinja
{% from 'macros.html' import post_card %}
{% for post in posts %}
  {{ post_card(post) }}
{% endfor %}
```

**宏的参数默认值**：

```jinja
{% macro post_card(post, show_summary=True) %}
  ...
  {% if show_summary %}<p>{{ post.summary }}</p>{% endif %}
{% endmacro %}
```

**`call` 块**：让宏接受"一段内容"作为参数（像 slot）：

```jinja
{% macro dialog(title) %}
  <div class="dialog">
    <h3>{{ title }}</h3>
    <div class="body">{{ caller() }}</div>
  </div>
{% endmacro %}

{% call dialog('提示') %}
  <p>这是对话框内容</p>
{% endcall %}
```

## 4.5 其他常用语法

| 语法 | 作用 |
|---|---|
| `{% raw %}...{% endraw %}` | 原样输出不解析（写模板教程时用） |
| `{% if 'x' is defined %}` | 判断变量是否存在 |
| `{% loop 递归 %}` | 递归渲染（目录树） |
| `{{ url_for('static', filename='style.css') }}` | Flask 注入的全局函数 |
| `{{ get_flashed_messages() }}` | Flask 注入的 flash 消息 |

## 4.6 自定义过滤器（博客的精髓）

Python 里写函数，注册给模板用：

```python
from markupsafe import Markup

@app.template_filter('strftime')
def _jinja_strftime(dt, fmt='%Y-%m-%d %H:%M'):
    if dt is None:
        return ''
    # v2.8.3：把 UTC 时间转本地时间
    local = _tpl_localtime(dt)
    return local.strftime(fmt)
```

模板里：`{{ post.created_at|strftime('%Y-%m-%d') }}`。

**博客的自定义过滤器族**（app.py 第 802、814 行附近）：

- `strftime(fmt)`：日期格式化（自动转本地时区）；
- `localtime`：UTC → 本地；
- `timeago`：显示成"3 分钟前"；
- `plural(n, 'post')`：复数。

### 4.6.1 过滤器注册的三种方式

```python
# 方式一：装饰器（推荐）
@app.template_filter('upper_first')
def upper_first(s):
    return s[0].upper() + s[1:]

# 方式二：手动注册
def my_filter(s): ...
app.jinja_env.filters['myfilter'] = my_filter

# 方式三：蓝图级
@bp.app_template_filter('x')
def x(s): ...
```

### 4.6.2 自定义全局函数

除了过滤器，还能注册"直接调用的函数"：

```python
@app.template_global()
def recent_posts(limit=5):
    return Post.query.order_by(Post.created_at.desc()).limit(limit).all()
```

模板里直接 `{{ recent_posts(5) }}`——不必从视图传。

### 4.6.3 自定义测试器（is）

```python
@app.template_test('even')
def is_even(n):
    return n % 2 == 0
```

模板里 `{% if loop.index is even %}` 用。

## 4.7 环境配置（Environment）

Flask 已经配好了，但你要知道几个关键开关：

| 配置 | 作用 |
|---|---|
| `autoescape` | 是否自动转义（Flask 默认对 .html 开） |
| `auto_reload` | 模板改了自动重载（debug 开，生产关） |
| `trim_blocks` | 删掉 `{% %}` 后的第一个换行 |
| `lstrip_blocks` | 删掉 `{% %}` 前的缩进空白 |

`app.jinja_env.trim_blocks = True` 能让生成的 HTML 干净很多（不会一堆空行）。

---

# 第 5 章 实战示例

## 5.1 项目内示例：博客的 base.html 继承链

```jinja
{# base.html #}
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{% block title %}{{ site_name }}{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
  {% block head %}{% endblock %}
</head>
<body>
  <nav>
    <a href="{{ url_for('index') }}">首页</a>
    <a href="{{ url_for('archive_index') }}">归档</a>
    <a href="{{ url_for('friend_links') }}">友链</a>
  </nav>

  {% with msgs = get_flashed_messages(with_categories=true) %}
    {% for cat, m in msgs %}<div class="alert-{{ cat }}">{{ m }}</div>{% endfor %}
  {% endwith %}

  <main>{% block content %}{% endblock %}</main>

  <footer>© {{ current_year }} {{ site_name }}</footer>
</body>
</html>
```

子页面 `post_detail.html`：

```jinja
{% extends 'base.html' %}
{% block title %}{{ post.title }} - {{ site_name }}{% endblock %}
{% block content %}
<article>
  <h1>{{ post.title }}</h1>
  <p class="meta">{{ post.created_at|strftime }} · 阅读 {{ post.view_count }}</p>
  <div class="body">{{ post.rendered_html|safe }}</div>
</article>
{% endblock %}
```

**调试"页面怎么没导航"**：先确认子页面第一行是 `{% extends 'base.html' %}`，再确认 `{% block content %}` 名字和 base 里一致（拼写错了不会报错，只是没内容）。

## 5.2 项目内示例：首页文章卡片

```jinja
{% for post in posts %}
  <article class="card {% if loop.first %}featured{% endif %}">
    <h2><a href="{{ url_for('post_detail', post_id=post.id) }}">
      {{ post.title }}
    </a></h2>
    <p class="meta">
      {{ post.created_at|strftime('%Y-%m-%d') }}
      · {{ post.category or '未分类' }}
      · {{ post.view_count }} 阅读
    </p>
    <p>{{ post.summary|truncate(100, True) }}</p>
  </article>
{% else %}
  <p class="empty">还没有文章，去后台写一篇吧。</p>
{% endfor %}
```

## 5.3 独立示例：用宏做分页器

```jinja
{% macro render_pagination(pagination, endpoint) %}
{% if pagination.pages > 1 %}
<nav class="pagination">
  {% if pagination.has_prev %}
    <a href="{{ url_for(endpoint, page=pagination.prev_num) }}">上一页</a>
  {% else %}
    <span class="disabled">上一页</span>
  {% endif %}

  {% for p in pagination.iter_pages() %}
    {% if p %}
      {% if p == pagination.page %}
        <strong>{{ p }}</strong>
      {% else %}
        <a href="{{ url_for(endpoint, page=p) }}">{{ p }}</a>
      {% endif %}
    {% else %}
      <span class="ellipsis">…</span>
    {% endif %}
  {% endfor %}

  {% if pagination.has_next %}
    <a href="{{ url_for(endpoint, page=pagination.next_num) }}">下一页</a>
  {% else %}
    <span class="disabled">下一页</span>
  {% endif %}
</nav>
{% endif %}
{% endmacro %}
```

任何列表页导入就能用：`{% from 'macros.html' import render_pagination %}{{ render_pagination(pagination, 'index') }}`。

## 5.4 独立示例：给模板加"时间友好化"过滤器

```python
@app.template_filter('timeago')
def timeago(dt):
    import datetime
    if dt is None: return ''
    delta = datetime.datetime.now() - dt
    s = int(delta.total_seconds())
    if s < 60:    return '刚刚'
    if s < 3600:  return f'{s // 60} 分钟前'
    if s < 86400: return f'{s // 3600} 小时前'
    if s < 86400 * 30: return f'{s // 86400} 天前'
    return dt.strftime('%Y-%m-%d')
```

模板：`<span>{{ post.created_at|timeago }}</span>`。

---

# 第 6 章 高频坑与排查

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | 忘写 endfor/endif | TemplateSyntaxError，常报在下一行 | 每个 `{% %}` 配对；IDE 装 Jinja 插件 |
| 2 | 该加 safe 没加 | 渲染好的 HTML 变成一堆 `<h1>` 文字 | 信任的内容加 `|safe` |
| 3 | 用户输入加了 safe | 网页被脚本劫持（XSS） | 只给"自己生成的"内容加 safe |
| 4 | block 名拼错 | 子页面内容不显示或错位 | extends/block 名与 base 完全一致 |
| 5 | 变量拼错 | 静默显示空白 | `|default('未定义')` 定位 |
| 6 | extends 不在第一行 | 继承不生效，输出空 | `{% extends %}` 必须第一行 |
| 7 | include 里改了变量 | 外面跟着变 | Jinja include 共享上下文，要隔离用 with |
| 8 | 循环里用了 Python 函数 | 报错 | 模板里只能用传入的、全局的、过滤器 |
| 9 | tojson 忘了 | JS 里收到奇怪字符串 | 数据传 JS 用 `|tojson` |
| 10 | 打包后模板改不动 | 改了源码 templates 没变化 | 模板在 `_internal` 只读区，改后重新打包 |
| 11 | HTML 里一堆空行 | 源码难看 | `app.jinja_env.trim_blocks=True, lstrip_blocks=True` |
| 12 | auto_reload 关了 | 改模板不生效 | debug 模式自动开；手动重启服务 |
| 13 | 中文路径模板找不到 | TemplateNotFound | 用绝对路径或 `Config.TEMPLATE_DIR` |
| 14 | 宏里用外部变量 | 闭包陷阱 | 宏默认只接受显式参数 |
| 15 | 用户评论里写 `{% raw %}` | 被当模板语法解析 | 用户输入永远 `{{ }}` 输出，不会当模板执行（模板只渲染一次） |

**排查万能法**：

1. 报错信息里的 `template line N` 就是模板行号；
2. Flask debug 模式下，浏览器出错页能直接看到模板源码和上下文变量；
3. 临时在视图里 `print(render_template(...))` 看最终 HTML；
4. `{{ post|pprint }}` 在模板里打印变量结构（Flask 自带 pprint 过滤器）。

---

# 第 7 章 学习路径与自测

## 7.1 推荐学习路径

**第 1~2 天：基础语法**
- 会写 `{{ }}`、`{% if %}`、`{% for %}`；
- 读懂博客 `index.html`、`post_detail.html`；
- 目标：能改首页文案、加一个静态页面。

**第 3~4 天：继承与宏**
- 理解 base.html 的 block 机制；
- 把博客里重复的 HTML 片段抽成宏；
- 目标：能新建一个"关于我"页面，继承 base。

**第 5~7 天：过滤器与上下文**
- 学会写自定义过滤器；
- 理解 `@app.context_processor` 注入全局变量；
- 目标：给博客加一个"最后修改时间友好显示"过滤器。

**第 2 周：进阶**
- 学沙箱模式（渲染用户提交的模板片段）；
- 写一个完整的模板组件库（卡片、分页器、标签云）；
- 优化生成 HTML（trim_blocks、去除空行）。

## 7.2 自测题

1. `{{ a|default('无') }}` 和 `{{ a }}` 的区别？
2. `|safe` 什么时候能用、什么时候绝对不能用？
3. 子页面要改标题栏，base.html 里需要提前写什么？
4. `{% include %}` 和 `{% extends %}` 的区别？
5. 循环里怎么判断"这是最后一条"？
6. `{{ post.title }}` 的 `.` 按什么顺序查找？
7. 怎么把一个 Python 列表传给前端 JS？
8. 宏和 include 有什么区别？
9. `{% for %}...{% else %}{% endfor %}` 的 else 什么时候执行？
10. 为什么用户评论里写 `{{ 1+1 }}` 不会被执行？
11. `{{ super() }}` 做什么？
12. 怎么注册一个模板里能用的 Python 函数？

## 7.3 答案

1. 前者在 a 未定义/空时显示"无"，后者输出空字符串。
2. 内容是自己生成的信任 HTML（Markdown 渲染结果）时能用；用户输入/不可信内容绝对不能用。
3. base.html 里要有 `<title>{% block title %}...{% endblock %}</title>` 插槽。
4. include 是"嵌入一个片段"；extends 是"继承骨架"，子页填 block。
5. `{% if loop.last %}`。
6. 先字典下标 `post['title']`，再属性 `post.title`，再方法调用 `post.title()`。
7. `{{ data|tojson }}`，自动安全转义。
8. include 是把另一个模板原样渲染进来（无参数）；宏是模板里定义的函数，能传参、可复用。
9. 列表为空时。
10. 模板只在服务端渲染一次，用户评论作为数据字符串放进模板，`{{ }}` 输出时只做 HTML 转义，不会再被解析成模板语法。
11. 在子 block 里调用父 block 原内容，"叠加"而非"覆盖"。
12. 用 `@app.template_filter('名字')` 装饰函数（过滤器），或 `@app.template_global()` 注册直接调用的函数。

## 7.4 进一步学习

- 官方文档：https://jinja.palletsprojects.com/
- Jinja2 沙箱模式（渲染用户模板）：https://jinja.palletsprojects.com/sandbox/
- 模板继承进阶：https://jinja.palletsprojects.com/template-inheritance/

---

> 下一篇：Werkzeug —— Flask 底层引擎全面教程
