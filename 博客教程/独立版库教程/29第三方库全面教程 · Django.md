# 第三方库全面教程 · Django（独立版）

> 面向初学者：本教程**独立成篇**，不依赖任何具体项目。假设你已通过本教程站的 Flask 系列掌握了"请求→路由→模板→数据库"的 Web 基本盘；完全不懂 Web 也不怕——每个术语第一次出现都有白话解释。
> 适用版本：Django 5.x ｜ 讲解方式：**Flask ↔ Django 对照**（你已经懂的 Flask 概念就是最好的跳板）。
> 学习目标：从"会写 Flask 小网站"到"能用 Django 独立搭建带后台管理、表单校验、用户认证的完整网站"。

---

# 第 1 章 这个库是什么

## 1.1 一句话认识 Django

Django 是 Python 世界里最**"全家桶"的 Web 框架**。和 Flask 的"轻、自由、要什么自己装"相反，Django 走"**什么都给你配好**"路线：

| 对比 | Flask | Django |
|---|---|---|
| 定位 | 微框架，核心只有路由+响应 | 大而全框架，自带一切 |
| 数据库 | 自己装 Flask-SQLAlchemy | 内置 ORM + 自动建表迁移 |
| 后台管理 | 自己写 | 自带 Admin 后台（杀手锏） |
| 表单 | 自己处理 | 内置 Form 体系（校验/渲染/安全） |
| 用户登录 | 自己写 | 内置完整认证系统 |
| 学习曲线 | 平缓 | 陡一些，但过了山头很省事 |

**比喻**：Flask 像自己攒机（每个零件自己挑），Django 像买品牌整机（开箱即用、配置齐全、官方全包售后）。

## 1.2 什么时候用 Django

- 做**大型网站**、后台管理密集的项目（内容管理、电商、政务、企业站）。
- 需要**开箱即用的后台、认证、表单**——不想每个功能从零写。
- Python 招聘 JD 里的 Web 要求：**Flask 和 Django 是两大主流，都会才不虚**。

## 1.3 Django 的自我定位

官网原话："Django 是一个高水准的 Python Web 框架，鼓励快速开发和干净、务实的设计。" 关键词：**快速开发**（自带电池）、**干净务实**（有约定俗成的规范）。

---

# 第 2 章 核心概念与原理

## 2.1 MVT：Django 的骨架

Django 用 **MVT（Model-View-Template）** 组织代码：

| 概念 | 是什么 | 类比 Flask |
|---|---|---|
| **Model（模型）** | 数据表对应的 Python 类（`models.py`） | `db.Model` 类 |
| **View（视图）** | 处理请求的函数或类（`views.py`） | `app.py` 里的路由函数 |
| **Template（模板）** | 页面模板（`templates/*.html`） | Jinja2 模板 |
| **URL 路由** | `urls.py` 集中配置网址映射 | `@app.route` 装饰器 |

**核心分工**：Model 管数据、View 管逻辑、Template 管展示——三者解耦，改模板不动逻辑，改模型不碰页面。

## 2.2 项目（project）vs 应用（app）：Django 最重要的一道分界

```
mysite/                    ← 项目（整个网站）
├── manage.py              ← 一切命令的入口
├── mysite/                ← 项目配置包（settings.py / urls.py 在这）
└── blog/                  ← 应用（一个功能模块，如"博客""商城""评论"）
    ├── models.py          ← 这个模块的数据模型
    ├── views.py           ← 这个模块的视图
    ├── urls.py            ← 这个模块的路由
    ├── migrations/        ← 自动生成的迁移文件（建表记录）
    └── admin.py           ← 注册进后台管理
```

- **项目** = 整个网站（配置文件 + 多个应用）。
- **应用** = 一个功能模块，各自独立、可复用。

**新手最大困惑**：`python manage.py startapp blog` 创建的是**应用**不是**项目**——项目是 `django-admin startproject mysite` 创建的。

## 2.3 迁移（migration）：Django 自动帮你改数据库

Flask-SQLAlchemy 要手写 `create_all` + 手动 ALTER。Django 的**迁移系统**全自动：

```
改 models.py（加一个字段）
  ↓ python manage.py makemigrations  生成迁移文件（记录"要加什么列"）
  ↓ python manage.py migrate         执行迁移（真的改数据库）
```

**核心认知**：`makemigrations` 是"写方案"，`migrate` 是"执行方案"。迁移文件是历史记录（可回滚 `migrate blog 0001`）——这是手写 ALTER 比不了的。

## 2.4 请求生命周期

```
浏览器 → urls.py 匹配路由 → 中间件(middleware)处理 → 视图函数
  → 视图查 Model / 调 ORM → 渲染 Template → 中间件再处理 → 响应浏览器
```

**中间件（Middleware）**：在请求进视图前、响应出浏览器前"插一手"的钩子（登录检查、日志、Gzip 压缩都在这层）。对应 Flask 的 `before_request` / `after_request`，但更规范、可插拔。

---

# 第 3 章 安装与版本

```bash
pip install django
python -m django --version     # 版本验证（当前稳定版 5.x）
```

Django 5.x 要求 Python 3.10+。安装后自带 `django-admin` 命令。

**建项目三步**（在你想放项目的文件夹里执行）：

```bash
django-admin startproject mysite .      # ① 建项目（. 表示当前目录）
python manage.py startapp blog          # ② 建应用
python manage.py runserver              # ③ 跑起来（默认 8000 端口）
```

浏览器开 `http://127.0.0.1:8000` 看到火箭页 = 成功。

---

# 第 4 章 API 全面讲解

> 标注：✅ = 做网站最常用；➕ = 推荐掌握；🧪 = 进阶

## 4.1 settings.py：全项目配置中心（✅ 必改的几个）

```python
# mysite/settings.py 关键配置
INSTALLED_APPS = [                 # 注册的应用列表（建了 app 必须加进来！）
    'django.contrib.admin',        # 内置后台
    'django.contrib.auth',         # 内置认证
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'blog',                        # ← 你自己的应用要手动加
]

LANGUAGE_CODE = 'zh-hans'          # 后台界面变中文
TIME_ZONE = 'Asia/Shanghai'        # 时区（中国必改，否则时间差 8 小时）
USE_TZ = True                      # 用 UTC 存储，展示时转本地

DATABASES = {                      # 数据库配置（默认 SQLite，零配置）
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

STATIC_URL = 'static/'             # 静态文件 URL 前缀
MEDIA_URL = '/media/'              # 上传文件 URL 前缀
MEDIA_ROOT = BASE_DIR / 'media'    # 上传文件存哪
```

## 4.2 models.py：定义数据模型（✅ 和 Flask-SQLAlchemy 几乎一样）

```python
from django.db import models

class Post(models.Model):
    title = models.CharField(max_length=200)          # 短文本（必填）
    content = models.TextField(default='')            # 长文本
    published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)  # 创建时间自动填
    view_count = models.IntegerField(default=0)
    category = models.CharField(max_length=50, blank=True)

    def __str__(self):                                 # 后台显示名（必须有，否则后台一堆 Post object）
        return self.title

    class Meta:
        ordering = ['-created_at']                     # 默认排序（新的在前）
```

**字段类型对照**：`CharField`=String、`TextField`=Text、`BooleanField`=Boolean、`DateTimeField`=DateTime、`IntegerField`=Integer。**`blank=True`**（表单可空）和 **`null=True`**（数据库可空）是两个不同概念，新手必踩。

改完模型必须跑：

```bash
python manage.py makemigrations blog
python manage.py migrate
```

## 4.3 ORM 查询：Django 的查询全家桶（✅ 增删改查）

```python
# 写入（不用 add + commit，save() 一步到位）
post = Post(title='你好', content='正文')
post.save()                        # 新增或更新都靠它

# 查询
Post.objects.all()                 # 全部（懒执行，真正取值才查库）
Post.objects.filter(published=True)         # 等值过滤
Post.objects.get(pk=1)                      # 按主键查（没有会抛 DoesNotExist！）
Post.objects.get_object_or_404(Post, pk=1)  # 视图里用这个，没有直接 404
Post.objects.filter(title__icontains='python')  # 模糊搜索（双下划线！）
Post.objects.order_by('-created_at')        # 倒序
Post.objects.count()                        # 计数
Post.objects.filter(published=True).count()
Post.objects.all()[:10]                     # 切片 = LIMIT 10

# 修改
post = Post.objects.get(pk=1)
post.title = '新标题'
post.save()

# 删除
post.delete()
Post.objects.filter(published=False).delete()   # 批量删
```

**⭐ 双下划线语法**是 Django ORM 的灵魂：`字段__条件`。常用：`__icontains`（模糊）、`__gt`（大于）、`__lt`、`__in`、`__startswith`、`__isnull`。

**关系字段**（一对多）：

```python
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    # on_delete=models.CASCADE：删文章自动删评论
    # related_name='comments'：post.comments.all() 拿到这篇文章的评论
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

# 多对多：tags = models.ManyToManyField('Tag', related_name='posts')
```

## 4.4 views.py：视图函数（✅ 对照 Flask 路由函数）

```python
from django.shortcuts import render, get_object_or_404
from .models import Post

def index(request):
    posts = Post.objects.filter(published=True).order_by('-created_at')[:10]
    # render() 第一个参数必须是 request！（Flask 不用传，Django 必须）
    return render(request, 'blog/index.html', {'posts': posts})

def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    return render(request, 'blog/post_detail.html', {'post': post})
```

**和 Flask 的最大差异**：Django 视图函数**必须接收 `request` 参数**，渲染模板用 `render(request, 模板, 字典)`——别漏了 request，漏了必报 `TypeError`。

## 4.5 urls.py：路由（✅ Django 没有装饰器，路由集中管）

```python
# mysite/urls.py（项目级）：把路由分发给应用
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),       # 内置后台
    path('', include('blog.urls')),        # 博客应用的路由全部归它管
]

# blog/urls.py（应用级）：
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),                          # 首页
    path('post/<int:pk>/', views.post_detail, name='post_detail'),  # 详情
]
```

**转换器**：`<int:pk>` 对应 Flask 的 `<int:post_id>`（int/str/slug/uuid/path 几种）。`name='index'` 对应 Flask 的 `endpoint`，模板里 `{% url 'post_detail' pk=post.pk %}` 反推网址（对应 Flask 的 `url_for`）。

## 4.6 模板：Django 模板语言（✅ 和 Jinja2 几乎一样）

```html
<!-- blog/templates/blog/index.html -->
{% extends 'base.html' %}
{% block content %}
  {% for post in posts %}
    <h2><a href="{% url 'post_detail' pk=post.pk %}">{{ post.title }}</a></h2>
    <p>{{ post.created_at|date:"Y-m-d" }}</p>          {# 过滤器，| 后面是名字 #}
  {% empty %}
    <p>还没有文章</p>                                    {# 列表为空 #}
  {% endfor %}
{% endblock %}
```

**注意**：Django 模板和 Jinja2 长得像但**不兼容**——`{{ }}`、`{% %}`、`|过滤器` 语法类似，但过滤器名字不同（`|date:"Y-m-d"` vs Flask 的 `|strftime`），`{% url %}` 替代 `url_for`。模板目录查找顺序：每个 app 的 `templates/` 下。

**静态文件**（css/js/图片）：

```html
{% load static %}
<link rel="stylesheet" href="{% static 'css/style.css' %}">
```

## 4.7 Admin 后台：Django 的杀手锏（✅ 零代码后台管理）

```python
# blog/admin.py
from django.contrib import admin
from .models import Post, Comment

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'published', 'created_at')   # 列表显示哪些列
    list_filter = ('published', 'category')               # 侧边筛选
    search_fields = ('title', 'content')                  # 搜索框

admin.site.register(Comment)
```

然后：`python manage.py createsuperuser` 建管理员 → 开 `http://127.0.0.1:8000/admin/` → **数据管理后台直接就有了**。这在 Flask 里要写几十个路由+页面，Django 自带。

## 4.8 表单：Django Form（➕ 自动校验/渲染/防注入）

```python
from django import forms
from .models import Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'category']   # 要渲染哪些字段

# 视图里：
def post_new(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():            # 自动校验必填/长度/类型
            form.save()                # 直接存库（ModelForm 的福利）
            return redirect('index')
    else:
        form = PostForm()
    return render(request, 'blog/post_form.html', {'form': form})
```

**CSRF 防护**：Django 表单默认防跨站请求伪造，模板里 `{% csrf_token %}` 必须加，否则 POST 报 403——这是新手第一坑。

## 4.9 认证系统（➕ 内置用户体系）

```python
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout

@login_required                      # 装饰器：未登录跳登录页
def dashboard(request):
    return render(request, 'blog/dashboard.html', {'user': request.user})
```

内置 User 模型、注册/登录/登出视图、密码哈希、权限组——要加"作者后台"时不用自己写认证。

## 4.10 中间件、信号、DRF（🧪 进阶地图）

| 能力 | 是什么 | 什么时候学 |
|---|---|---|
| **中间件** | 请求前/响应后的全局钩子（登录检查、日志、限流） | 项目要统一处理请求时 |
| **信号（signal）** | 事件通知（如"文章保存后自动生成摘要"） | 解耦业务逻辑时 |
| **Django REST Framework** | 把 Django 项目变成 JSON API（手机 App 后端） | 要做前后端分离/小程序时 |
| **Celery + Django** | 异步任务（发邮件、定时同步） | 有耗时任务时 |

---

# 第 5 章 实战项目案例

## 案例 1（入门级）：15 分钟搭建"文章管理系统"

```python
# ===== ① models.py =====
from django.db import models

class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField(default='')
    published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.title
    class Meta:
        ordering = ['-created_at']

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

# ===== ② views.py =====
from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Comment

def index(request):
    posts = Post.objects.filter(published=True)
    return render(request, 'blog/index.html', {'posts': posts})

def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    comments = post.comments.all()          # related_name 发挥作用
    return render(request, 'blog/post_detail.html',
                  {'post': post, 'comments': comments})

def post_comment(request, pk):
    post = get_object_or_404(Post, pk=pk)
    content = (request.POST.get('content') or '').strip()
    if content:
        Comment.objects.create(post=post, content=content)   # 一步创建+入库
    return redirect('post_detail', pk=post.pk)

# ===== ③ urls.py（blog/urls.py）=====
from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name='index'),
    path('post/<int:pk>/', views.post_detail, name='post_detail'),
    path('post/<int:pk>/comment/', views.post_comment, name='post_comment'),
]

# ===== ④ admin.py：后台管理 =====
from django.contrib import admin
from .models import Post, Comment
admin.site.register(Post)
admin.site.register(Comment)

# ===== ⑤ 模板 blog/templates/blog/index.html =====
# {% for post in posts %}
#   <h2><a href="{% url 'post_detail' pk=post.pk %}">{{ post.title }}</a></h2>
#   <p>{{ post.created_at|date:"Y-m-d" }}</p>
# {% empty %}<p>还没有文章</p>{% endfor %}
```

跑起来：`makemigrations` → `migrate` → `createsuperuser` → `runserver`。**同样的功能**，Django 少了路由装饰器、少了手动 init_db、少写了整个后台——这是"全家桶"的威力。

## 案例 2（进阶级）：分页功能

```python
# views.py
from django.core.paginator import Paginator

def index(request):
    all_posts = Post.objects.filter(published=True)
    paginator = Paginator(all_posts, 10)             # 每页 10 条
    page = request.GET.get('page', 1)                # 当前页码
    posts = paginator.get_page(page)                 # 自动处理越界
    return render(request, 'blog/index.html', {'posts': posts})

# 模板里：
# {% if posts.has_previous %}<a href="?page={{ posts.previous_page_number }}">上一页</a>{% endif %}
# 第 {{ posts.number }} / {{ posts.paginator.num_pages }} 页
# {% if posts.has_next %}<a href="?page={{ posts.next_page_number }}">下一页</a>{% endif %}
```

## 案例 3（进阶级）：带表单校验的文章发布

```python
# forms.py
from django import forms
from .models import Post

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'category']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),   # 自定义控件
        }

# views.py
from django.shortcuts import render, redirect
from .forms import PostForm

def post_new(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            form.save()                    # 校验通过直接入库
            return redirect('index')
    else:
        form = PostForm()
    return render(request, 'blog/post_form.html', {'form': form})

# post_form.html 里关键三行：
# <form method="post">{% csrf_token %}
#   {{ form.as_p }}          ← 自动渲染所有字段（带校验错误信息）
#   <button type="submit">发布</button></form>
```

## 案例 4（综合）：**带登录权限的博客后台**（认证 + 后台 + 上传）

```python
# ① settings.py 加上传配置（已见 4.1）
# ② models.py 加作者与封面图
from django.contrib.auth.models import User

class Post(models.Model):
    ...
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    cover = models.ImageField(upload_to='covers/', blank=True)   # 上传文件

# ③ views.py 加权限控制
from django.contrib.auth.decorators import login_required

@login_required
def my_posts(request):
    posts = Post.objects.filter(author=request.user)   # 只看自己的
    return render(request, 'blog/my_posts.html', {'posts': posts})

# ④ urls.py 注册
urlpatterns += [path('my/', views.my_posts, name='my_posts')]

# ⑤ 静态/媒体文件在 DEBUG 下能访问（开发阶段）：
# mysite/urls.py
from django.conf import settings
from django.conf.urls.static import static
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**案例 4 综合了 Model 关系、ImageField 上传、认证装饰器、URL 分发、静态媒体配置**——这是中小型网站最常用的组合，学完即会搭"带作者体系的内容站"。

---

# 第 6 章 高频坑与排查

| 坑 | 症状 | 解决 |
|---|---|---|
| 忘记 makemigrations | `no such column` / 表不存在 | 改 models 后先 makemigrations 再 migrate |
| 模板 POST 报 403 | `CSRF token missing or incorrect` | 表单里加 `{% csrf_token %}` |
| view 函数报 TypeError | `post_detail() missing 1 required positional argument: 'request'` | 视图第一个参数必须是 `request` |
| render 忘传 request | 各种报错 | `render(request, '模板', {...})` request 必传 |
| 时间差 8 小时 | 后台时间不对 | settings 改 `TIME_ZONE = 'Asia/Shanghai'` + `USE_TZ = True` |
| 图片/静态文件不显示 | 404 | DEBUG=True 时配置 `MEDIA_URL/MEDIA_ROOT` + urls 加 `+ static(...)`；生产用 nginx 托管 |
| 创建了 app 没注册 | 模型表建不出来 / 命令找不到 | `INSTALLED_APPS` 里加上你的 app 名 |
| `get()` 抛异常 | `DoesNotExist` 让 500 | 视图里用 `get_object_or_404` |
| 后台一堆 "Post object (1)" | Admin 显示难看 | models 里加 `__str__` 返回标题 |
| 生产跑 runserver | 警告/性能差 | 部署用 `gunicorn` 或 `waitress` 跑 WSGI |
| 升级后迁移冲突 | 迁移文件打架 | 不要删 migrations 目录；冲突时 `makemigrations --merge` |
| ImageField 报错 | Pillow 未安装 | `pip install Pillow`（Django 上传图片必装） |

---

# 第 7 章 学习路径与自测

**学习路径**（小白到精通路线图）：
1. 搭起项目+应用+第一个 Hello 页面（半天）
2. Model + 迁移 + Admin 后台（1 天，成就感最强）
3. ORM 查询双下划线语法（1 天）
4. 视图 + 路由 + 模板循环（1 天）
5. 表单 + CSRF（1 天）
6. 认证系统（1 天）
7. 中间件 + 信号 + 分页（1 天）
8. 文件上传 + 媒体管理（1 天）
9. DRF 做 API（3 天，进阶）
10. 部署上线（gunicorn/waitress + nginx，2 天）

**自测题**：

1. `startproject` 和 `startapp` 分别创建什么？什么关系？
2. `makemigrations` 和 `migrate` 各干什么？改 models 后忘了哪个会报 "no such column"？
3. `Post.objects.get(pk=1)` 和 `Post.objects.filter(pk=1).first()` 有什么区别？
4. 模板 POST 表单为什么必须加 `{% csrf_token %}`？
5. 删文章时评论自动一起删，靠哪个参数？
6. Django 视图函数和 Flask 路由函数最明显的差别是什么？
7. 后台时间差 8 小时，改哪个配置？
8. `blank=True` 和 `null=True` 有什么区别？
9. 上传图片字段用什么类型？需要装什么依赖？
10. 综合：描述"建项目 → 建应用 → 建模型 → 迁移 → 注册后台 → 写视图路由模板"的完整流程。

**答案**：
1. startproject 建项目（网站配置文件）；startapp 建应用（功能模块）。项目包含多个应用。
2. makemigrations 生成迁移方案，migrate 执行改库。忘了 migrate。
3. get 查不到直接抛 DoesNotExist 异常；filter 查不到返回空查询集不报错（视图里用 get_object_or_404）。
4. 防 CSRF（跨站请求伪造）——Django 内置安全机制，不加就 403。
5. `on_delete=models.CASCADE`。
6. Django 视图必须接收 `request` 参数，且用 `render(request, ...)`；路由在 urls.py 集中配置而非装饰器。
7. `TIME_ZONE = 'Asia/Shanghai'`（配合 `USE_TZ = True`）。
8. blank 控制**表单**是否可空；null 控制**数据库**是否允许 NULL。
9. `models.ImageField(upload_to='...')`，需要 `pip install Pillow`。
10. 参考第 3 章 + 案例 1：startproject → startapp → 写 models → makemigrations/migrate → admin 注册 → 写 views/urls/templates → runserver。

---

> 下一篇：《Flask（独立版）》——从零到精通的微框架全教程。想学别的库？用教程网站的「教程生成器」页输入库名试试！
