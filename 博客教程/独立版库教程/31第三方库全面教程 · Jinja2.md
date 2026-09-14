# 第三方库全面教程 · Jinja2（独立版）

> 面向初学者：本教程**独立成篇**，假设你会基础 Python 语法。术语第一次出现都有白话解释。
> 适用版本：Jinja2 3.1 ｜ 配套知识：与《Flask》配合使用（Flask 默认模板引擎就是 Jinja2）。
> 学习目标：从"会写 HTML"到"用 Jinja2 把 HTML 变成能自动填数据的动态页面"。

---

# 第 1 章 这个库是什么

## 1.1 一句话认识 Jinja2

**Jinja2** 是 Python 最主流的**模板引擎**：一种"HTML 骨架 + 占位符"技术——页面结构写死在模板里，数据（文章标题、用户名字、商品价格）用占位符标记，运行时 Jinja2 把数据填进去，输出完整 HTML。

```python
from jinja2 import Template

tpl = Template("你好，{{ name }}！")      # {{ }} 是占位符
print(tpl.render(name="小明"))             # 输出：你好，小明！
```

## 1.2 为什么需要它

- **前后端分离思维的前身**：页面逻辑（循环列表、判断登录态）写进模板，Python 代码只负责"给数据"。
- **防注入安全**：Jinja2 自动转义用户输入（`<script>` 变 `&lt;script&gt;`），防止 XSS 攻击。
- Flask 默认内置（装 Flask 就带 Jinja2），Django 模板语法也和它极像。

## 1.3 模板 = 字符串 + 语法

任何文本（不限于 HTML）都能当模板：邮件、配置、代码生成、报表文本。Jinja2 只管"占位符替换 + 简单逻辑"。

---

# 第 2 章 核心概念与原理

## 2.1 三种语法

| 语法 | 用途 | 例子 |
|---|---|---|
| `{{ 表达式 }}` | 输出值（会转义） | `{{ post.title }}` |
| `{% 语句 %}` | 逻辑控制（循环/判断/宏） | `{% for p in posts %}` |
| `{# 注释 #}` | 注释（不会输出） | `{# 这是注释 #}` |

## 2.2 变量与属性访问

```python
tpl = Template("{{ user.name }} ｜ {{ user['email'] }}")
print(tpl.render(user={"name": "小明", "email": "a@b.com"}))
```

- `user.name` 和 `user['name']` 等价（Jinja2 自动处理）。
- 变量不存在时默认输出空字符串（不报错）——**这是新手易困惑点**。

## 2.3 渲染 = 模板 + 数据

```python
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates"))  # 从 templates/ 目录加载
tpl = env.get_template("index.html")                     # 加载模板文件
html = tpl.render(posts=[...], user={...})               # 渲染
```

**Environment（环境）** 是 Jinja2 的"总配置 + 模板仓库"：加载器（loader）决定模板从哪找，过滤器、全局函数都挂在环境上。

---

# 第 3 章 安装与版本

```bash
pip install jinja2
```

- 当前稳定版 3.1。
- **Flask 用户不用单独装**——Flask 依赖里自带 Jinja2。
- 独立使用：`from jinja2 import Template`（字符串模板）或 Environment（文件模板）。

---

# 第 4 章 API 全面讲解

> 标注：✅ = 必会；➕ = 推荐；🧪 = 进阶

## 4.1 输出变量与过滤器（✅）

```jinja2
{{ name }}                  {# 直接输出 #}
{{ price | round(2) }}      {# 过滤器：| 后面是处理函数 #}
{{ content | truncate(100) }}   {# 截断到 100 字符 #}
{{ text | upper }}          {# 转大写 #}
{{ date | strftime("%Y-%m-%d") }}   {# 格式化时间（Flask 内置过滤器） #}
```

**常用过滤器**：`upper`/`lower` 大小写、`capitalize` 首字母大写、`title`、`trim` 去空格、`length` 长度、`default('x', true)` 缺省值、`join(', ')` 列表拼串、`safe` 不转义（**慎用**）、`escape` 转义。

## 4.2 逻辑控制：for 与 if（✅）

```jinja2
{# for 循环 #}
<ul>
{% for post in posts %}
  <li>{{ post.title }}</li>
{% else %}
  <li>暂无文章</li>          {# 列表为空时执行 #}
{% endfor %}
</ul>

{# if 判断 #}
{% if user %}
  <p>欢迎，{{ user.name }}</p>
{% elif user is none %}
  <p>请登录</p>
{% else %}
  <p>未知用户</p>
{% endif %}

{# 循环内置变量 #}
{% for p in posts %}
  {{ loop.index }}       {# 从 1 开始 #}
  {{ loop.index0 }}      {# 从 0 开始 #}
  {{ loop.first }}       {# 是不是第一个 #}
  {{ loop.last }}        {# 是不是最后一个 #}
  {{ loop.length }}      {# 总数 #}
{% endfor %}
```

## 4.3 模板继承（✅ 网站布局的标准姿势）

`base.html`（父模板，定义整体布局）：

```jinja2
<!DOCTYPE html>
<html>
<head><title>{% block title %}默认标题{% endblock %}</title></head>
<body>
  <header>导航栏</header>
  <main>{% block content %}{% endblock %}</main>
  <footer>版权信息</footer>
</body>
</html>
```

`index.html`（子模板，只写自己的部分）：

```jinja2
{% extends "base.html" %}          {# 继承 #}
{% block title %}首页{% endblock %} {# 覆盖标题块 #}
{% block content %}
  <h1>这里是首页内容</h1>
{% endblock %}
```

**核心思想**：导航/页脚写一次，所有页面继承——改一处全站生效。

## 4.4 宏（macro）：模板里的"函数"（➕）

```jinja2
{# macros.html #}
{% macro render_card(post) %}
  <div class="card">
    <h2>{{ post.title }}</h2>
    <p>{{ post.body | truncate(50) }}</p>
  </div>
{% endmacro %}

{# 使用 #}
{% from "macros.html" import render_card %}
{% for p in posts %}
  {{ render_card(p) }}
{% endfor %}
```

## 4.5 include 与 import（➕）

```jinja2
{% include "header.html" %}          {# 直接嵌入另一个模板 #}
{% import "macros.html" as m %}      {# 导入宏集合 #}
{{ m.render_card(post) }}
```

## 4.6 自定义过滤器（🧪 进阶神器）

```python
from jinja2 import Environment

env = Environment()

def money(value):
    return f"¥{value:,.2f}"          # 12345 → ¥12,345.00

env.filters['money'] = money          # 注册过滤器

tpl = env.from_string("价格：{{ price | money }}")
print(tpl.render(price=12345))        # 价格：¥12,345.00
```

## 4.7 转义与安全（✅ 安全底线）

```jinja2
{{ user_input }}            {# 默认转义：<script> 变 &lt;script&gt; #}
{{ user_input | safe }}     {# 不转义（只有确信安全才用！XSS 风险） #}
```

- 默认 `autoescape=True`（HTML 模板），用户输入必须走默认转义。
- 用 `| safe` 等于告诉 Jinja2"这段是我的可信代码"——**用户输入千万别 safe**。

## 4.8 模板中调用 Python 函数（➕）

```python
# Python 侧把函数传进模板
def time_ago(dt):
    ...  # 计算"3 小时前"

html = tpl.render(posts=posts, time_ago=time_ago)
```

```jinja2
{{ time_ago(post.created_at) }}    {# 模板里直接调用 #}
```

---

# 第 5 章 实战项目案例

## 案例 1（入门级）：生成批量邮件内容

```python
from jinja2 import Template

tpl = Template("""尊敬的{{ name }}：
    您的订单 {{ order_id }} 已发货，预计 {{ date }} 送达。
    感谢您在本店购物！""")

users = [{"name": "张三", "order_id": "A001", "date": "9月18日"},
         {"name": "李四", "order_id": "A002", "date": "9月19日"}]

for u in users:
    print(tpl.render(**u))
    print("-" * 30)
```

## 案例 2（进阶级）：博客文章列表页（数据驱动渲染）

```python
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates"))
tpl = env.get_template("list.html")

posts = [
    {"title": "Python 入门", "author": "小明", "views": 1200,
     "tags": ["Python", "教程"]},
    {"title": "Flask 实战", "author": "小红", "views": 800,
     "tags": ["Flask", "Web"]},
]
html = tpl.render(posts=posts, site_name="我的博客")
with open("output.html", "w", encoding="utf-8") as f:
    f.write(html)
print("已生成 output.html")
```

`templates/list.html`：

```jinja2
<!DOCTYPE html>
<html>
<head><title>{{ site_name }}</title></head>
<body>
<h1>{{ site_name }}</h1>
{% for p in posts %}
  <div class="post">
    <h2>{{ p.title }}</h2>
    <p>作者：{{ p.author }} ｜ 阅读：{{ p.views }}</p>
    {% if p.tags %}
      <p>标签：{% for t in p.tags %}<span>{{ t }}</span> {% endfor %}</p>
    {% endif %}
  </div>
{% else %}
  <p>还没有文章</p>
{% endfor %}
</body>
</html>
```

## 案例 3（综合）：**模板继承搭建完整网站**（base + 首页 + 详情 + 404）

```jinja2
{# base.html —— 全局布局 #}
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>{% block title %}{{ site_name }}{% endblock %}</title>
  <style>
    body { font-family: sans-serif; margin: 0; }
    header { background: #2c3e50; color: white; padding: 12px; }
    nav a { color: white; margin-right: 15px; text-decoration: none; }
    main { padding: 20px; min-height: 400px; }
    footer { background: #ecf0f1; padding: 10px; text-align: center; }
    .card { border: 1px solid #ddd; padding: 12px; margin: 10px 0; }
    .muted { color: #888; font-size: 13px; }
  </style>
</head>
<body>
<header><nav><a href="/">首页</a><a href="/about">关于</a></nav></header>
<main>{% block content %}{% endblock %}</main>
<footer>© 2026 {{ site_name }}</footer>
</body>
</html>
```

```jinja2
{# index.html —— 首页 #}
{% extends "base.html" %}
{% block title %}首页 - {{ super() }}{% endblock %}
{% block content %}
  <h1>最新文章</h1>
  {% for p in posts %}
    <div class="card">
      <h2><a href="/post/{{ p.id }}">{{ p.title }}</a></h2>
      <p class="muted">{{ p.created_at.strftime('%Y-%m-%d') }} ｜ {{ p.author }}</p>
    </div>
  {% endfor %}
{% endblock %}
```

```jinja2
{# 404.html —— 错误页 #}
{% extends "base.html" %}
{% block title %}页面不存在{% endblock %}
{% block content %}
  <h1>404</h1>
  <p>你访问的页面不存在。</p>
  <a href="/">回到首页</a>
{% endblock %}
```

```python
# 渲染三页（配合 Flask 时由 render_template 完成）
env = Environment(loader=FileSystemLoader("templates"))
pages = {
    "index.html": env.get_template("index.html").render(posts=posts, site_name="我的博客"),
    "404.html": env.get_template("404.html").render(site_name="我的博客"),
}
```

---

# 第 6 章 进阶内容（大神之路）

## 6.1 模板沙箱（安全执行不可信模板）

```python
from jinja2.sandbox import SandboxedEnvironment

env = SandboxedEnvironment()       # 禁掉危险能力（文件读写等）
tpl = env.from_string("{{ ''.__class__.__mro__ }}")   # 会被拦截
```

## 6.2 性能：模板缓存与预编译

```python
# Flask 里模板默认缓存；独立使用时 env.cache 自动管理
# 批量渲染时复用 env.get_template（不要每次重新加载）
```

## 6.3 与 Django 模板的差异速查

| 能力 | Jinja2 | Django |
|---|---|---|
| 循环 | `{% for %}` | 一样 |
| 过滤器 | `| truncate` | `| truncatechars:50` |
| URL 反推 | `url_for('index')` | `{% url 'index' %}` |
| 继承 | `{% extends %}` | 一样 |
| 转义 | 默认自动 | 默认自动 |

---

# 第 7 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 变量不显示 | 输出空白 | 检查 render 传参名和模板变量名一致 |
| 未定义变量报错 | `UndefinedError` | 传参漏了；或 `{{ x | default('缺省') }}` |
| XSS 被注入 | 页面弹窗/乱码 | 用户输入别用 `| safe` |
| 继承没生效 | 子模板内容不显示 | 子模板第一行必须是 `{% extends %}` |
| 循环变量名冲突 | 数据不对 | 循环变量别和外部变量重名 |
| 过滤器不存在 | `TemplateAssertionError` | 确认拼写/是否注册自定义过滤器 |
| 中文乱码 | 输出乱码 | 文件用 UTF-8 保存；HTML 加 `<meta charset="UTF-8">` |
| 模板找不到 | `TemplateNotFound` | 检查 loader 目录路径和文件名 |
| safe 用了之后样式崩 | 内容被当 HTML 解析 | 尽量转义；需要富文本用 markdown 转安全 HTML |
| 宏参数不匹配 | 渲染报错 | 宏定义参数和调用参数一一对应 |

---

# 第 8 章 学习路径与自测

**学习路径**：
1. `{{ }}` 输出 + 基础过滤器（半天）
2. for/if + loop 变量（1 天）
3. 模板继承 extends/block（1 天，重点）
4. 宏 macro + include/import（1 天）
5. 自定义过滤器（半天）
6. 转义与安全（半天，必配）
7. 与 Flask 配合 render_template（1 天）
8. 综合网站（模板继承 + 循环 + 判断）（2 天）

**自测题**：
1. `{{ }}`、`{% %}`、`{# #}` 分别干什么？
2. `user.name` 和 `user['name']` 有区别吗？
3. 循环列表为空时怎么办？（两种方式）
4. 模板继承解决什么问题？子模板第一行写什么？
5. `| safe` 是干什么的？为什么危险？
6. loop.index 和 loop.index0 区别？
7. 怎么给模板加一个自定义过滤器？
8. `include` 和 `extends` 区别？
9. 变量没定义会怎样？怎么给缺省值？
10. 综合：用模板继承 + 循环 + 判断搭一个文章列表页。

**答案提示**：
1. 输出表达式 / 逻辑语句 / 注释。
2. 没有，Jinja2 自动兼容两种写法。
3. `{% for %}{% else %}` 分支；或 `| default`。
4. 布局复用，改一处全站生效；`{% extends "base.html" %}` 放第一行。
5. 关闭转义直接输出 HTML；用户输入用 safe 会 XSS 注入。
6. index 从 1 开始，index0 从 0 开始。
7. `env.filters['名字'] = 函数`。
8. include 嵌入模板内容；extends 建立父子继承关系。
9. 输出空；`{{ x | default('缺省') }}`。
10. 参考案例 3：base 布局 + for 循环文章 + if 判断空列表。

---

> 下一篇：《Werkzeug（独立版）》——WSGI 工具库：Flask 的地基。
