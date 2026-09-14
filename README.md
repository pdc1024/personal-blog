# 个人博客项目 v2.1（Python 全栈）

一个 **开箱即用的 Python 个人博客系统**：支持网页版（浏览器访问）与桌面版（窗口化运行、系统托盘），自带文章管理、Markdown 写作、评论点赞、归档标签、友链、Gitee 同步/新手向导、多用户支持等完整功能。本仓库同时收录了配套的 **零基础全流程学习教程**（4 篇主文档 + 12 个技术栈库详解 + 博客版离线教程网站）。

> 📚 独立的「纯 Python 库教程」（24 份「从小白到大神」教程 + 教程生成器网站）已单独存放于：[所谓的教程](https://gitee.com/pan-decai/the-so-called-tutorial) 仓库。

---

## ✨ 功能特性

| 模块 | 说明 |
|------|------|
| 📝 文章系统 | 新建 / 编辑 / 删除 / 发布与隐藏切换，支持 Markdown 写作、代码高亮、封面图 |
| 💬 评论与点赞 | 文章评论、点赞互动（不依赖任何第三方评论服务） |
| 🗂 归档与标签 | 按年月归档、标签聚合浏览 |
| 🔗 友链管理 | 友情链接的展示与后台管理 |
| 👤 个人资料 | 关于页 / 个人主页配置 |
| 🔄 Gitee 同步 | 一键把博客数据备份到自己的 Gitee 仓库；内置「零门槛 · 新手向导」教你从零连接 Gitee |
| 🖥 桌面版 | pywebview 窗口运行，系统托盘（左键打开 / 右键退出），开机即用 |
| 🔐 登录系统 | 多用户登录、会话持久化（重启不用重登）、防 CSRF |
| 🖼 文件上传 | 头像 / 背景 / 文章配图上传与管理 |
| 📊 健康检查 | `/health` 接口，方便部署监控 |

## 🧰 技术栈

**后端**：Flask · Flask-SQLAlchemy · Werkzeug · Waitress（生产 WSGI 服务器）
**前端**：Jinja2 模板 · Tailwind CSS（静态引入）· Vditor（Markdown 编辑器）· Cropper.js（图片裁剪）
**数据**：SQLite · python-dateutil（时间解析）
**内容**：python-markdown（Markdown 渲染）· Pygments（代码高亮）· PyYAML（配置/批量导入）
**桌面与打包**：pywebview（窗口壳）· PyInstaller（打包绿色版）
**自动化**：Requests（HTTP 调用，Gitee 同步）

## 📁 仓库结构

```
个人博客/
├── 项目源码/                     # 博客系统完整源码
│   ├── app.py                    # 主应用：路由 / 数据库 / 页面渲染（约 2400 行）
│   ├── main.py                   # 桌面版入口：窗口 + 系统托盘
│   ├── config.py                 # 配置加载（.env > 环境变量 > 默认值）
│   ├── sync_engine.py            # Gitee 同步引擎
│   ├── gitee_backup.py           # Gitee 备份/恢复模块
│   ├── check_env.py              # 环境自检工具
│   ├── open_firewall.py          # 防火墙放行脚本
│   ├── requirements.txt          # Python 依赖清单
│   ├── blog_desktop.spec         # PyInstaller 打包配置
│   ├── templates/                # Jinja2 页面模板
│   ├── static/                   # 静态资源（Tailwind / Vditor / Cropper）
│   └── uploads/                  # 上传文件（含示例）
└── 博客教程/                     # 配套学习教程
    ├── 01个人博客项目 · 零基础全流程开发教程.md
    ├── 02个人博客项目 · 第三方库技术栈总目录.md
    ├── 03个人博客项目 · 全代码逐行注释配套文档.md
    ├── 04个人博客项目 · 二次开发进阶文档.md
    ├── 博客版第三方库教程/        # 12 份与项目绑定的库教程（Flask → PyInstaller）
    └── 博客教程站_博客专版/       # 离线教程网站（双击 index.html 即用）
```

## 🚀 快速开始

### 方式一：源码运行（开发 / 学习）

```bash
# 1. 进入源码目录
cd 项目源码

# 2. 安装依赖（建议先创建虚拟环境）
pip install -r requirements.txt

# 3. 启动（默认 http://127.0.0.1:5000）
python app.py
```

> 💡 也可以直接运行桌面版：`python main.py`（需要 Windows + Edge WebView2）

### 方式二：绿色版安装包（免安装）

- 使用 PyInstaller 按 `blog_desktop.spec` 打包：`pyinstaller blog_desktop.spec`
- 生成 `dist/个人博客/` 目录，双击 `个人博客.exe` 即可运行，无需安装 Python。

## ⚙️ 配置说明

项目采用 **`.env` 文件 > 系统环境变量 > 默认值** 的三级配置加载：

1. 首次启动自动生成 `.env`（可参考 `.env.example`）
2. 常用配置项：
   - `SECRET_KEY`：会话密钥（不设置会自动生成并持久化到 `.session_key`）
   - `BLOG_DATA_DIR`：数据目录（数据库 / 上传 / 日志），默认在程序目录下
   - 端口、调试开关等见 `config.py` 顶部说明

> 🔒 安全提示：`.session_key`、`blog.db`、`logs/`、`uploads/` 属于运行时数据，请勿提交到 Git。

## 📚 教程导航（零基础友好）

| 文档 | 适合人群 | 内容 |
|------|----------|------|
| `01 零基础全流程开发教程` | 完全没接触过的人 | 环境搭建 → 逐模块讲解 → 本地运行 → 踩坑排查，全程大白话 |
| `02 第三方库技术栈总目录` | 想了解技术栈的人 | 12 个库在项目里的职责、版本、选型原因 |
| `03 全代码逐行注释文档` | 想彻底看懂代码的人 | 路由 / 数据库 / 页面渲染 / 工具函数逐行注释 |
| `04 二次开发进阶文档` | 想自己加功能的人 | 架构梳理 + 可落地扩展清单 + 分步实现 + 难度标注 |
| `博客版第三方库教程/` | 想深学某个库的人 | 12 份与博客实际用法绑定的库教程 |
| `博客教程站_博客专版/index.html` | 喜欢网页阅读的人 | 离线教程网站，双击即用，支持日间/夜间模式 |

> 📚 想学习更全面的 Python 库（Playwright / Django / Pandas / NumPy 等 24 份「从小白到大神」教程，含教程生成器网站）？请前往独立仓库：[所谓的教程](https://gitee.com/pan-decai/the-so-called-tutorial)

## 📄 License

仅供学习交流使用。本项目使用到的开源组件版权归其各自作者所有。
