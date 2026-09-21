# 第三方库全面教程 · Jinja2

> 面向初学者到进阶者：博客所有 HTML 页面都是它渲染出来的。
> 学完这份教程，你会掌握 Jinja2 的全部核心语法、模板继承、过滤器、宏、自定义扩展、自动转义，
> 并能对照博客 `templates/base.html`、`index.html` 等真实模板读懂每个标签在做什么。
>
> 适用版本：Jinja2 3.x（Flask 内置）｜ 博客项目：`templates/*.html`（约 30 个模板）
> 学习路线：基础语法（第 1~2 章）→ 模板继承与控制结构（第 3 章）→ 过滤器与宏（第 4 章）→ 项目实战（第 5 章）→ API 与排坑（第 6~7 章）→ 自测（第 8 章）

---

# 第 1 章 认识 Jinja2

## 1.1 一句话定位

Jinja2 是 Flask 内置的**模板引擎**。所谓"模板"，就是一个带占位符的 HTML 文件：

```html
<h1>{{ title }}</h1>
<p>{{ content }}</p>
```

Flask 把 Python 变量 `title='我的文章'`、`content='...'` 传进来，Jinja2 把 `{{ ... }}` 替换成真实值，输出纯 HTML：

```html
<h1>我的文章</h1>
<p>...</p>
```

一句话：**Jinja2 是博客的"页面拼装工"**——HTML 骨架 + Python 数据 → 最终网页。

## 1.2 为什么需要模板引擎

不用模板引擎，你得在 Python 里拼字符串：

```python
html = '<h1>' + title + '</h1><p>' + content + '</p>'
```

字符串一多就乱成一锅粥，还要自己转义特殊字符防 XSS。Jinja2 解决：

- 模板和代码分离（前端设计只管 HTML，后端只管逻辑）；
- 自动 HTML 转义（防 XSS）；
- 模板继承（base.html 统一头部尾部，子模板只写内容区）；
- 过滤器（`{{ content|truncate(100) }}` 自动截断）。

## 1.3 Jinja2 和同类对比

| 引擎 | 特点 |
|---|---|
| **Jinja2** | Flask 内置、语法像 Django、功能全 |
| Mako | 更快、语法像 Python |
| Django Template | Django 自带 |
| Tornado Template | Tornado 内置 |

博客用 Jinja2 是因为 Flask 默认。

## 1.4 最小例子

`templates/hello.html`：

```html
<!DOCTYPE html>
<html>
<body>
  <h1>{{ name }} 的博客</h1>
  <ul>
  {% for post in posts %}
    <li>{{ post.title }}</li>
  {% endfor %}
  </ul>
</body>
</html>
```

Python：

```python
from flask import Flask, render_template
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('hello.html',
                           name='小明',
                           posts=[{'title': 'Python 入门'}, {'title': 'Flask 实战'}])
```

---

# 第 2 章 三种定界符与渲染原理

## 2.1 三种定界符

Jinja2 模板里有三种特殊语法：

| 定界符 | 用途 | 例子 |
|---|---|---|
| `{{ ... }}` | 输出变量 | `{{ post.title }}` |
| `{% ... %}` | 逻辑语句 | `{% for %}`, `{% if %}`, `{% extends %}` |
| `{# ... #}` | 注释 | `{# 不输出到页面 #}` |

**注意**：HTML 注释 `<!-- ... -->` 会发送到浏览器；Jinja 注释 `{# ... #}` 在服务器端就被删掉，用户看不到。

## 2.2 渲染流水线

```
templates/index.html（源文件）
  ↓ Jinja2 编译成 Python 函数
  ↓ 把上下文（post、user）传进去
  ↓ 执行函数，输出字符串
最终 HTML
```

**理解**：Jinja2 模板本质上是被编译成 Python 函数。`{{ post.title }}` 编译成 `str(post.title)`；`{% for %}` 编译成 Python 循环。所以模板里的错误会报 Python 行号。

## 2.3 自动转义（Autoescape）

Jinja2 默认对 `{{ ... }}` 的输出做 HTML 转义：

```python
content = '<script>alert(1)</script>'
{{ content }}
```

输出：

```html
&lt;script&gt;alert(1)&lt;/script&gt;
```

浏览器看到的是文本，不会执行。这是防 XSS 的第一道防线。

**需要输出原始 HTML 时**加 `|safe`：

```html
{{ post.rendered_html|safe }}
```

博客的 `rendered_html` 列是服务端用 python-markdown 渲染好的 HTML，自己可信，所以用 `|safe`。

**铁律**：`|safe` 只加在你信任的内容上；用户输入的内容绝对不要 `|safe`。

## 2.4 点号查找顺序

`{{ post.title }}` 里的 `.` 不是直接查字典键或属性。Jinja2 按顺序尝试：

1. `post['title']`（字典键）；
2. `post.title`（属性）；
3. `post.get('title')`（字典方法）；
4. `post['title']`（列表索引 0 时是 `post.0`）。

所以 Python 类属性和字典键在模板里写法一样。

## 2.5 变量不存在时

Jinja2 默认不报错，输出空字符串：

```html
{{ user.nickname }}   <!-- user 是 None 也不报错，输出空 -->
```

这和 Python 不一样（Python 会抛 AttributeError）。好处是模板容错好，坏处是拼错字段名不会发现。调试时开 `TRAPUNDEFINED=True` 让它严格报错。

---

# 第 3 章 模板继承与控制结构

## 3.1 模板继承：base.html

所有页面共用头部、尾部、导航栏。用继承避免重复：

`templates/base.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{% block title %}我的博客{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
  <nav>
    <a href="/">首页</a>
    <a href="/archive">归档</a>
  </nav>

  {% block content %}{% endblock %}

  <footer>© 2026</footer>
</body>
</html>
```

`templates/index.html`：

```html
{% extends "base.html" %}

{% block title %}首页 - 我的博客{% endblock %}

{% block content %}
  <h1>最新文章</h1>
  {% for post in posts %}
    <article>
      <h2>{{ post.title }}</h2>
      <p>{{ post.summary }}</p>
    </article>
  {% endfor %}
{% endblock %}
```

**关键概念**：

- `{% extends "base.html" %}`：继承父模板；
- `{% block name %}{% endblock %}`：定义可被子模板覆盖的区域；
- 子模板只写自己的 `block`，其他部分全部继承父模板。

## 3.2 block 的三种用法

### 3.2.1 覆盖（override）

```html
{% block content %}
  新内容（父模板里的内容被替换）
{% endblock %}
```

### 3.2.2 追加（super()）

```html
{% block content %}
  {{ super() }}     <!-- 保留父模板内容 -->
  <p>额外加的</p>
{% endblock %}
```

### 3.2.3 嵌套 block

```html
{% block content %}
  {% block header %}{% endblock %}
  {% block body %}{% endblock %}
{% endblock %}
```

## 3.3 include：包含局部模板

```html
{% include '_sidebar.html' %}
{% include '_comments.html' with context %}
```

和继承的区别：
- `extends`：子模板替换父模板的 block；
- `include`：把另一个模板的内容"复制粘贴"进来。

博客把分页、评论、表单片段抽成 `_macro.html` 或单独的 partial 模板。

## 3.4 if 语句

```html
{% if post.published %}
  <span class="badge">已发布</span>
{% elif post.draft %}
  <span class="badge">草稿</span>
{% else %}
  <span class="badge">未知</span>
{% endif %}

{% if posts %}
  <p>共 {{ posts|length }} 篇</p>
{% else %}
  <p>暂无文章</p>
{% endif %}
```

**注意**：`{% elif %}` 不是 `else if`。

## 3.5 for 循环

```html
{% for post in posts %}
  <li>{{ loop.index }}. {{ post.title }}</li>
{% else %}
  <li>没有文章</li>
{% endfor %}
```

`{% else %}` 在列表为空时执行——比 Python 的 for/else 更常用。

**loop 特殊变量**：

| 变量 | 含义 |
|---|---|
| `loop.index` | 当前序号，从 1 开始 |
| `loop.index0` | 从 0 开始 |
| `loop.revindex` | 倒序序号 |
| `loop.first` | 是否第一个 |
| `loop.last` | 是否最后一个 |
| `loop.length` | 列表长度 |
| `loop.cycle('odd', 'even')` | 轮流取值（斑马纹） |

```html
{% for post in posts %}
  <tr class="{{ loop.cycle('odd', 'even') }}">
    <td>{{ loop.index }}</td>
    <td>{{ post.title }}</td>
  </tr>
{% endfor %}
```

## 3.6 过滤器（Filter）：管道 `|`

过滤器像 Unix 管道：把前一个的输出传给后一个。

```html
{{ post.title|upper }}
{{ post.content|truncate(100) }}
{{ post.created_at|date('%Y-%m-%d') }}
```

### 3.6.1 内置常用过滤器

| 过滤器 | 作用 | 例子 |
|---|---|---|
| `default(v)` | 空值时用默认 | `{{ name|default('匿名') }}` |
| `length` | 长度 | `{{ posts|length }}` |
| `join(', ')` | 拼接 | `{{ tags|join(', ') }}` |
| `upper` / `lower` | 大小写 | |
| `trim` | 去空格 | |
| `capitalize` | 首字母大写 | |
| `title` | 每个单词首字母大写 | |
| `truncate(n)` | 截断到 n 字符 | |
| `striptags` | 去 HTML 标签 | |
| `escape` / `e` | 转义 | |
| `safe` | 不转义 | |
| `first` / `last` | 取首/尾 | |
| `round(2)` | 四舍五入 | |
| `int` / `float` / `string` | 类型转换 | |
| `tojson` | 转 JSON | `<script>var data = {{ data|tojson }};</script>` |
| `items` | 字典转键值对 | `{% for k, v in d.items() %}` |

### 3.6.2 过滤器链

```html
{{ post.summary|striptags|truncate(100) }}
```

先去 HTML 标签，再截断到 100 字符。

## 3.7 表达式

```html
{% set name = '小明' %}
{% set x, y = 1, 2 %}

{{ [1, 2, 3]|sum }}
{{ {'a': 1, 'b': 2} | length }}
```

---

# 第 4 章 进阶：宏、自定义过滤器、环境配置

## 4.1 宏（Macro）：模板里的函数

宏就像 Python 函数，封装一段可复用的 HTML：

```html
{% macro input(name, value='', type='text') %}
  <input type="{{ type }}" name="{{ name }}" value="{{ value }}">
{% endmacro %}

{{ input('username') }}
{{ input('password', type='password') }}
{{ input('submit', value='登录', type='submit') }}
```

### 4.1.1 把宏抽到独立文件

`templates/_macros.html`：

```html
{% macro render_pagination(pagination, endpoint) %}
  <div class="pagination">
    {% for p in pagination.iter_pages() %}
      {% if p %}
        <a href="{{ url_for(endpoint, page=p) }}">{{ p }}</a>
      {% else %}
        <span>...</span>
      {% endif %}
    {% endfor %}
  </div>
{% endmacro %}
```

其他模板导入：

```html
{% from '_macros.html' import render_pagination %}

{{ render_pagination(pagination, 'index') }}
```

博客的分页、表单字段、评论卡片都用宏封装。

## 4.2 自定义过滤器（Flask 里）

在 Python 侧给 Jinja2 注册过滤器：

```python
@app.template_filter('local_time')
def local_time(dt):
    return dt.strftime('%Y-%m-%d %H:%M') if dt else ''

@app.template_filter('reading_time')
def reading_time(content):
    words = len(content) // 500
    return max(1, words)
```

模板里：

```html
{{ post.created_at|local_time }}
阅读约 {{ post.content|reading_time }} 分钟
```

博客的时区过滤器（app.py 第 802 行）就是这么注册的。

## 4.3 自定义全局函数

```python
@app.template_global()
def now():
    return datetime.now()

@app.template_global()
def category_path(cat):
    return f'/category/{cat}/'
```

模板里直接当函数用：`{{ now().year }}`、`{{ category_path('tech') }}`。

## 4.4 自定义测试器（Test）

```python
@app.template_test('admin')
def is_admin(user):
    return user and user.role == 'admin'
```

模板里：

```html
{% if user is admin %}
  <a href="/admin/">后台</a>
{% endif %}
```

## 4.5 环境配置（Environment）

Flask 默认环境够用。高级配置：

```python
app.jinja_env.trim_blocks = True     # 去掉标签后第一个换行
app.jinja_env.lstrip_blocks = True   # 去掉标签前的空白
app.jinja_env.autoescape = True
app.jinja_env.undefined = StrictUndefined  # 未定义变量报错
```

`trim_blocks` + `lstrip_blocks` 让模板输出更干净（不会因为 `{% %}` 留下空行）。

## 4.6 模板继承的坑

- 子模板第一行必须是 `{% extends %}`；
- block 名不要重名；
- 父模板定义了 block 但子模板不覆盖，会输出父模板默认内容；
- `include` 不会改变 block 关系。

## 4.7 静态文件与 url_for

模板里永远用 `url_for('static', filename=...)`，不要硬写 `/static/...`：

```html
<link href="{{ url_for('static', filename='css/style.css') }}">
<img src="{{ url_for('static', filename='img/logo.png') }}">
```

原因：将来如果应用挂在子路径（如 `/blog/`），url_for 自动处理。

---

# 第 5 章 项目实战：博客真实模板逐段讲

## 5.1 base.html：全站骨架

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}{{ site_name }}{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
  {% block head %}{% endblock %}
</head>
<body>
  <header>
    <a href="/" class="logo">{{ site_name }}</a>
    <nav>
      <a href="/">首页</a>
      <a href="/archive/">归档</a>
      <a href="/friends/">友链</a>
      <a href="/about/">关于</a>
    </nav>
  </header>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for category, msg in messages %}
      <div class="alert alert-{{ category }}">{{ msg }}</div>
    {% endfor %}
  {% endwith %}

  <main>
    {% block content %}{% endblock %}
  </main>

  <footer>© {{ current_year }} {{ site_name }}</footer>
  <script src="{{ url_for('static', filename='js/app.js') }}"></script>
  {% block scripts %}{% endblock %}
</body>
</html>
```

**亮点**：
- `{{ site_name }}`、`{{ current_year }}` 来自 `inject_globals`（context_processor）；
- flash 消息在所有页面都能显示；
- `{% block head %}` 和 `{% block scripts %}` 让子模板能加额外的 CSS/JS。

## 5.2 index.html：首页文章列表

```html
{% extends "base.html" %}

{% block title %}{{ site_name }} - 首页{% endblock %}

{% block content %}
  <h1>最新文章</h1>

  {% for post in posts %}
    <article class="post-card">
      <h2>
        <a href="{{ url_for('post_detail', post_id=post.id) }}">
          {{ post.title }}
        </a>
      </h2>
      <p class="meta">
        {{ post.created_at|local_time }} ·
        <span>{{ post.view_count }} 阅读</span>
      </p>
      <p class="summary">{{ post.summary|truncate(120) }}</p>
    </article>
  {% else %}
    <p>还没有文章。</p>
  {% endfor %}

  {% if pagination %}
    <nav class="pagination">
      {% if pagination.has_prev %}
        <a href="{{ url_for('index', page=pagination.prev_num) }}">上一页</a>
      {% endif %}
      <span>{{ pagination.page }} / {{ pagination.pages }}</span>
      {% if pagination.has_next %}
        <a href="{{ url_for('index', page=pagination.next_num) }}">下一页</a>
      {% endif %}
    </nav>
  {% endif %}
{% endblock %}
```

**逐段讲**：
- `extends` 继承 base；
- `{% for post in posts %}` 循环文章；
- `{% else %}` 在 posts 为空时显示"还没有文章"；
- `{{ post.created_at|local_time }}` 用自定义过滤器转时区；
- `{{ post.summary|truncate(120) }}` 截断摘要；
- 分页用 `pagination.has_prev/has_next`。

## 5.3 post_detail.html：文章详情

```html
{% extends "base.html" %}

{% block title %}{{ post.title }} - {{ site_name }}{% endblock %}

{% block content %}
  <article>
    <h1>{{ post.title }}</h1>
    <p class="meta">
      {{ post.created_at|local_time }} · {{ post.view_count }} 阅读
      <button class="like-btn" data-id="{{ post.id }}">
        ❤️ <span class="count">{{ post.likes|length }}</span>
      </button>
    </p>
    <div class="content">
      {{ post.rendered_html|safe }}
    </div>
  </article>

  <section class="comments">
    <h3>评论</h3>
    {% for c in comments %}
      <div class="comment">
        <strong>{{ c.author }}</strong>
        <span>{{ c.created_at|local_time }}</span>
        <p>{{ c.content }}</p>
      </div>
    {% else %}
      <p>还没有评论，来抢沙发。</p>
    {% endfor %}
  </section>
{% endblock %}
```

**关键点**：
- `{{ post.rendered_html|safe }}` 是服务端渲染好的 HTML，加 safe 不转义；
- 评论区 for/else 空状态。

## 5.4 点赞按钮的 AJAX 部分

```html
<script>
document.querySelector('.like-btn').addEventListener('click', async () => {
  const id = this.dataset.id;
  const res = await fetch(`/post/${id}/like/`, { method: 'POST' });
  const data = await res.json();
  this.querySelector('.count').textContent = data.count;
});
</script>
```

---

# 第 6 章 完整 API 速查

## 6.1 语句速查

| 语法 | 作用 |
|---|---|
| `{{ var }}` | 输出变量 |
| `{{ obj.attr }}` / `{{ obj['attr'] }}` | 访问属性 |
| `{% extends "x.html" %}` | 继承 |
| `{% block name %}...{% endblock %}` | 定义 block |
| `{{ super() }}` | 调用父 block |
| `{% include "x.html" %}` | 包含 |
| `{% if %}...{% elif %}...{% else %}...{% endif %}` | 条件 |
| `{% for x in xs %}...{% else %}...{% endfor %}` | 循环 |
| `{% set x = 1 %}` | 赋值 |
| `{{ x|filter }}` | 过滤器 |
| `{% macro name(args) %}...{% endmacro %}` | 宏 |
| `{% from "x" import y %}` | 导入宏 |
| `{# comment #}` | 注释 |

## 6.2 全局函数

| 函数 | 作用 |
|---|---|
| `range(n)` | 类似 Python range |
| `dict(a=1)` | 创建字典 |
| `lipsum(n)` | 生成 Lorem Ipsum |
| `cycler(a,b,c)` | 循环取值 |
| `joiner(',')` | 智能拼接 |
| `namespace()` | 可变容器（在 for 循环外存值） |

## 6.3 全局测试器

| 测试 | 例子 |
|---|---|
| `divisibleby(n)` | `{% if n is divisibleby(2) %}` |
| `even` / `odd` | |
| `defined` / `undefined` | |
| `none` | |
| `string` / `number` / `mapping` / `iterable` | |
| `startingwith(s)` / `endingwith(s)` | |

---

# 第 7 章 高频坑与排查（15 条）

| # | 坑 | 症状 | 解决 |
|---|---|---|---|
| 1 | 用户输入直接 safe | XSS | 只 safe 服务端渲染的内容 |
| 2 | 模板变量拼错 | 不报错但空 | 开发开 StrictUndefined |
| 3 | extends 不在第一行 | 继承不生效 | 子模板第一行必须 extends |
| 4 | block 名重复 | 覆盖错地方 | 全项目 grep block 名 |
| 5 | for 循环改外层变量不生效 | 看不到值 | 用 namespace() |
| 6 | url_for 硬编码路径 | 改路由全坏 | 永远 url_for |
| 7 | 静态文件 404 | 样式没了 | 检查 static 目录和 url_for |
| 8 | 中文乱码 | 页面问号 | 文件存 UTF-8，HTML 加 charset |
| 9 | 过滤器顺序错 | 输出怪 | 先 striptags 再 truncate |
| 10 | |safe 用在用户输入 | 安全漏洞 | 审查所有 safe |
| 11 | macro 参数默认值 | 不生效 | 默认值写在宏定义里 |
| 12 | include 传变量 | 上下文丢失 | 默认带 context，不用 with context |
| 13 | 模板缓存 | 改了不生效 | debug 模式自动重载；或清缓存 |
| 14 | if 用 = 而不是 == | 语法错 | Jinja 用 == 比较 |
| 15 | 循环里 loop.index 从 0 还是 1 | 错位 | loop.index 从 1，loop.index0 从 0 |

---

# 第 8 章 学习路径与自测

## 8.1 学习路径

- 第 1 天：变量、if、for；
- 第 2 天：模板继承、block；
- 第 3 天：过滤器、宏；
- 第 4 天：自定义过滤器、context_processor；
- 第 5 天：对照博客 base.html / index.html 逐行读；
- 第 6 天：尝试加一个自定义过滤器（阅读时长估算）。

## 8.2 自测题

1. `{{ }}`、`{% %}`、`{# #}` 分别做什么？
2. 自动转义是什么？为什么要 `|safe`？
3. 模板继承和 include 的区别？
4. block 里的 `{{ super() }}` 做什么？
5. for 循环的 `{% else %}` 什么时候执行？
6. `loop.index` 和 `loop.index0` 区别？
7. 怎么把一个 Python 函数注册成模板过滤器？
8. `{{ post.title }}` 点号查找按什么顺序？
9. 怎么让所有模板都能用 `{{ site_name }}`？
10. 宏是什么？怎么把宏抽到独立文件？
11. 为什么永远用 `url_for('static')` 而不是硬写路径？
12. 模板里改 for 外面的变量为什么不生效？怎么解决？
13. autoescape 关掉会有什么风险？
14. `{{ post.summary|striptags|truncate(100) }}` 执行顺序？
15. 模板第一行必须写什么？

## 8.3 答案

1. 输出、逻辑语句、注释。
2. 自动转义 HTML 特殊字符防 XSS；`|safe` 告诉 Jinja 这段内容可信，不转义。
3. extends 是父子继承（子覆盖 block）；include 是把另一个模板内容插入当前位置。
4. 输出父模板该 block 的原始内容，再追加新内容。
5. 列表为空时。
6. 前者从 1，后者从 0。
7. `@app.template_filter('名字')` 装饰函数。
8. 字典键 → 属性 → 字典 get。
9. `@app.context_processor` 返回 `{'site_name': ...}`。
10. 宏是模板里的函数；抽到单独文件用 `{% from 'x' import y %}`。
11. 将来应用挂在子路径时 url_for 自动处理；硬写路径全坏。
12. Jinja 的 for 循环有作用域；用 `{% set outer = namespace() %}`。
13. 用户能注入 `<script>`，XSS。
14. 先 striptags 去 HTML，再 truncate 截断。
15. `{% extends "父模板.html" %}`（如果要继承）。

## 8.4 进一步学习

- 官方模板文档：https://jinja.palletsprojects.com/templates/
- Flask 模板：https://flask.palletsprojects.com/quickstart/#rendering-templates

---

> 下一篇：Werkzeug —— Flask 的底层引擎全面教程
