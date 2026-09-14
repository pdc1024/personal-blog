# 第三方库全面教程 · Playwright

> 面向初学者：这是**零基础起步**的浏览器自动化全套教程，假设你只会最基本的 Python 语法（print、def、for、if 就够）。每个专业术语第一次出现都有白话解释。
> 适用版本：Playwright 1.4x ｜ 配套知识：建议先读本站《Requests》《BeautifulSoup4》《Pandas》《Pillow》《Openpyxl》《Pytest》教程——第 5 章的综合联动案例会用它们。
> 学习目标：从"完全没碰过自动化"到"能独立写一个自动登录、抓数据、出报表的完整脚本"。

## 第 1 章 这个库是什么

### 1.1 一句话认识 Playwright

**Playwright** 是微软开发的一个**浏览器自动化框架**——它能让 Python 代码"替你做网页上的事"：打开网页、点击按钮、填写表单、翻页、截图、下载文件、抓取网页里的数据。

它的核心能力是：**真的启动一个浏览器（Chrome、Edge、Firefox、Safari 都行），像真人一样操作网页**，而不是像 Requests 那样只发 HTTP 请求。

| 对比项 | Requests | Selenium | **Playwright** |
| --- | --- | --- | --- |
| 本质 | 发 HTTP 请求（不渲染网页） | 驱动真实浏览器 | 驱动真实浏览器 |
| JS 动态内容 | ❌ 拿不到 | ✅ 能拿到 | ✅ 能拿到 |
| 等待元素 | 手动 sleep | 显式等待（较啰嗦） | **自动等待（核心优势）** |
| 定位元素 | 无（用解析库） | find_element（较繁琐） | **Locator 定位器（简洁）** |
| 多浏览器 | 无关 | 需各自 driver | 一套 API 全支持 |
| 官方录制工具 | 无 | 有（Selenium IDE，较老） | **codegen 录制（非常好用）** |

### 1.2 为什么现在学它（它能干嘛）

1. **网页自动化测试**：写完网站后，用脚本自动检查每个页面能不能正常打开、按钮点了有没有反应——这是 Playwright 最主流的用途（对标测试工程师岗位）。
2. **爬取 JS 渲染的网页**：很多网站的数据是 JavaScript 动态加载的，Requests 拿到的是空壳 HTML，Playwright 等页面渲染完再抓。
3. **自动填表 / 批量操作**：比如每天自动登录后台、导出报表、给某系统批量录入数据。
4. **网页截图 / 生成 PDF**：自动给网页截图做存档、把网页转成 PDF 报告。
5. **监控网页状态**：定时打开某个网页，检查是否正常，异常时截图留证。

### 1.3 和博客项目的关系

Playwright **不在**博客项目的技术栈里（博客是 Flask 后端 + pywebview 桌面壳）。它属于"浏览器自动化"方向，是 Python 生态里**最值得单独掌握的实用技能**之一——你学会后，可以给自己的博客写自动回归测试、自动截图存档，或给任何网站做自动化。

## 第 2 章 核心概念与原理（先懂这 5 个再写代码）

### 2.1 浏览器 / 上下文 / 页面：Playwright 的三层模型

Playwright 把"一个浏览器"拆成三层，理解这三层是理解一切的钥匙：

```
浏览器 (Browser)          ← 整个浏览器程序，可同时开很多窗口
  └── 上下文 (Context)    ← 一个"独立隔间"：cookie、登录状态互相隔离
        └── 页面 (Page)   ← 一个标签页，你操作的对象
```

- **Browser（浏览器）**：`p.chromium.launch()` 启动的浏览器实例。一个脚本通常只启动一个（启动很贵）。
- **Context（上下文）**：相当于"无痕模式的一个窗口"。不同 Context 之间的 cookie、登录状态**完全隔离**——你可以在 Context A 登录账号 1，在 Context B 登录账号 2，互不干扰。这是 Selenium 很难做到的。
- **Page（页面）**：一个标签页。你 99% 的操作都在 Page 上：`page.goto()` 打开网址、`page.click()` 点击。

> **白话比喻**：Browser 是浏览器软件，Context 是"无痕窗口"（关掉就什么都没了），Page 是窗口里的标签页。

### 2.2 有头模式 vs 无头模式

- **有头模式（默认）**：会弹出真实浏览器窗口，你能看到它在操作——**初学调试用这个**，看得见才知道发生了什么。
- **无头模式（headless=True）**：浏览器在后台运行，不弹窗口——服务器、自动化任务用这个，省资源。

```python
# 无头模式（服务器/批量任务）
browser = p.chromium.launch(headless=True)
# 有头模式（调试用，默认就是有头）
browser = p.chromium.launch(headless=False)
```

### 2.3 CDP：Playwright 和浏览器说话的"语言"

**CDP（Chrome DevTools Protocol，Chrome 开发者工具协议）** 是 Chrome/Edge 提供的一套"遥控接口"——你在浏览器按 F12 打开开发者工具能做的所有事（看网络请求、改元素、截图），CDP 都能通过代码做到。

Playwright 内部就是用 CDP（对 Chromium 系浏览器）和 Firefox/WebKit 各自的协议来遥控浏览器的。**你不需要会 CDP**，只需要知道：Playwright 之所以能"拦截网络请求、监听控制台、录屏"，都是因为这个底层协议。

### 2.4 Locator（定位器）：Playwright 最核心的思想

**Locator（定位器）** 是 Playwright 的灵魂概念：**它不是"找到的那个元素"，而是"怎么找到它的规则"**。

对比旧一代工具（Selenium）：

```python
# Selenium 风格：立即找元素，找不到就报错，页面一变就失效
element = driver.find_element(By.ID, "submit")
element.click()

# Playwright 风格：先描述"规则"，执行动作时才真正去找
submit = page.get_by_role("button", name="提交")   # 一个"定位器"，还没去找
submit.click()                                      # 点击时才会找+等+点
```

**Locator 的两大好处**：
1. **自动重试**：点击时如果元素还没加载出来，它会自动等（见 2.5 自动等待），页面加载慢也不怕。
2. **可组合**：可以从一个 Locator 再往下找，如 `row.filter(has_text="Python").get_by_role("button").click()`。

### 2.5 自动等待 + Web-First 断言：不用再写 time.sleep

这是 Playwright 对开发者体验的最大革命：

- **自动等待（Auto-waiting）**：执行 `click()`、`fill()` 等操作前，Playwright 会自动等元素"可操作"（可见、可用、不被遮挡），**默认最多等 30 秒**。所以你**几乎不需要** `time.sleep()`。
- **Web-First 断言**：用 `expect()` 做判断时，它也会自动重试，直到条件成立或超时。比如"等文字变成 加载完成"，它会反复检查直到成立。

> **反模式**：`time.sleep(3)` 是"固定等 3 秒"——页面 1 秒就加载完了浪费 2 秒，10 秒才加载完又不够。Playwright 的自动等待是"等到位为止"，又快又稳。**新手要戒掉 time.sleep。**

## 第 3 章 安装与版本

### 3.1 安装分两步（很多新手只做第一步导致报错）

```bash
# 第一步：装 Python 库
pip install playwright

# 第二步（关键！）：下载浏览器内核
playwright install chromium
```

**为什么必须装第二步**：Playwright 不是"遥控你已装的 Chrome"，而是**自带一个独立的浏览器内核**（chromium），`playwright install` 就是把这个内核下载到本地。**只装库不装内核，运行必报错**（报错信息类似 `Executable doesn't exist ... chromium`）。

可选内核：

```bash
playwright install chromium        # 只装 Chromium（够用，推荐新手）
playwright install firefox         # 装 Firefox 内核
playwright install webkit          # 装 WebKit（Safari 内核）
playwright install --with-deps chromium   # 服务器 Linux 上要装系统依赖
```

### 3.2 版本说明

- 当前稳定版：1.4x（1.40+）。API 高度稳定，本文代码在 1.4x 均可运行。
- 查看版本：`pip show playwright`
- **同步 API（sync_api）** 和 **异步 API（async_api）** 两套写法，功能完全一样：同步版用 `from playwright.sync_api import sync_playwright`（普通脚本用这个，简单直观）；异步版用 `async`/`await`（要和高并发/异步框架配合时用）。

### 3.3 第一个程序：验证环境

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:          # ① 启动 Playwright（必须放在 with 里）
    browser = p.chromium.launch()     # ② 启动浏览器（有头模式，会弹窗口）
    page = browser.new_page()         # ③ 开一个新标签页
    page.goto("https://example.com")  # ④ 打开网址
    print(page.title())               # ⑤ 打印网页标题
    browser.close()                   # ⑥ 关闭浏览器（记得关！）
```

跑通它，你的环境就 OK 了。

## 第 4 章 API 全面讲解（✅ = 必会 ｜ ➕ = 推荐 ｜ 🧪 = 进阶）

> 所有代码用同步 API 演示，`page` 都来自 `browser.new_page()`。

### 4.1 启动与关闭（✅）

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # launch() 常用参数
    browser = p.chromium.launch(
        headless=False,      # False=弹窗口（调试）；True=后台（生产）
        slow_mo=300,         # 每一步操作慢放 300 毫秒，方便看过程（调试神器）
        channel="msedge",    # 用你电脑上已装的 Edge 而不是自带内核（可选）
    )
    context = browser.new_context()   # 建一个上下文（隔离的隔间）
    page = context.new_page()         # 在上下文里开标签页
    # ... 你的操作 ...
    browser.close()                   # 结束必须关，否则残留浏览器进程
```

**新手最容易犯的错**：忘了 `browser.close()` 或脚本中途报错，导致一堆残留浏览器进程。更稳的写法用 try/finally：

```python
browser = p.chromium.launch()
try:
    page = browser.new_page()
    page.goto("https://example.com")
    print(page.title())
finally:
    browser.close()      # 无论成不成功都关闭
```

### 4.2 Page 的基本方法（✅）

```python
page.goto("https://example.com")           # 打开网址（默认等页面 load 事件）
page.title()                               # 拿<title>标题
page.url                                   # 拿当前 URL
page.content()                             # 拿整个页面的 HTML 源码（配合解析库用）
page.text_content("h1")                    # 拿第一个 h1 的文本（不推荐，见 Locator）
page.reload()                              # 刷新
page.go_back() / page.go_forward()         # 后退 / 前进
page.wait_for_url("**/home")               # 等 URL 变成某个模式（跳转后常用）
```

### 4.3 Locator 定位全家桶（✅ 核心中的核心）

**① 按角色定位（最推荐，最接近真人视角）**：

```python
page.get_by_role("button", name="登录")      # 找"登录"按钮
page.get_by_role("link", name="文章详情")     # 找超链接
page.get_by_role("heading", name="欢迎")      # 找标题元素
page.get_by_role("textbox", name="用户名")    # 找输入框（按关联的 label）
page.get_by_role("checkbox").check()          # 找复选框
```

**② 按文本定位**：

```python
page.get_by_text("阅读全文")                  # 含该文本的元素
page.get_by_text("阅读全文", exact=True)      # 文本完全相等
```

**③ 按表单相关属性定位**：

```python
page.get_by_label("用户名")                   # 按 <label> 文本定位输入框
page.get_by_placeholder("请输入密码")          # 按 placeholder 提示文字定位
page.get_by_alt_text("logo")                  # 按图片 alt 属性
page.get_by_title("工具提示")                  # 按 title 属性
page.get_by_test_id("submit-btn")             # 按 data-testid 属性（测试专用，最稳）
```

**④ 通用 CSS / XPath**：

```python
page.locator("#main .card h2")               # CSS 选择器
page.locator("xpath=//div[@class='card']")   # XPath
```

**⑤ 组合与过滤（Locator 威力所在）**：

```python
rows = page.locator("table tbody tr")                    # 所有行
rows.filter(has_text="Python")                            # 只保留含"Python"的行
rows.filter(has=page.locator("td.price"))                 # 只保留有价格列的行
rows.first / rows.last / rows.nth(2)                      # 第 1 个 / 最后 1 个 / 第 3 个
row = page.locator("tr").filter(has_text="Python")
row.get_by_role("button", name="删除").click()            # 在该行内找删除按钮
```

> **⚠️ 严格模式**：如果 Locator 匹配到**多个**元素，Playwright 默认会报错（比 Selenium 静默点第一个更安全）。要明确选哪个就用 `.first` / `.last` / `.nth(n)` / `.filter()`。

### 4.4 页面操作（✅）

```python
page.get_by_placeholder("搜索").fill("Python 教程")   # 填输入框（fill 是清空后输入）
page.get_by_placeholder("搜索").type("abc")            # 逐字输入（模拟打字，慢，少用）
page.get_by_role("button", name="登录").click()        # 点击
page.get_by_role("button", name="登录").dblclick()     # 双击
page.get_by_role("checkbox").check()                   # 勾选
page.get_by_role("checkbox").uncheck()                 # 取消勾选
page.locator("select#city").select_option("广州")       # 下拉选择（按 value/文本/索引）
page.locator(".item").hover()                          # 悬停（触发下拉菜单）
page.locator("#drag").drag_to(page.locator("#drop"))   # 拖拽
page.keyboard.press("Enter")                           # 按键盘（回车/组合键）
page.keyboard.type("hello")                            # 键盘输入
page.mouse.move(100, 200)                              # 鼠标移动到坐标
page.mouse.click(100, 200)                             # 鼠标点击坐标
```

**点击的补充**：元素被遮挡时（比如有悬浮层盖住），Playwright 会等它可点击；实在点不到可以用 `locator.click(force=True)` 强制点击（慎用，先想为什么点不到）。

### 4.5 Web-First 断言（✅ 判断"网页状态对不对"）

```python
from playwright.sync_api import expect

expect(page).to_have_title("首页")                        # 页面标题是
expect(page).to_have_url("https://example.com/home")     # URL 是
expect(page.get_by_text("登录成功")).to_be_visible()      # 元素可见
expect(page.get_by_text("登录成功")).to_be_hidden()       # 元素隐藏
expect(page.locator("h1")).to_have_text("欢迎回来")        # 元素文本是
expect(page.locator("h1")).to_contain_text("欢迎")        # 元素文本包含
expect(page.locator("input")).to_have_value("python")     # 输入框的值是
expect(page.locator(".item")).to_have_count(5)            # 元素数量是 5
expect(page.get_by_role("button")).to_be_enabled()        # 按钮可用
expect(page.get_by_role("button")).to_be_disabled()       # 按钮禁用
expect(page.get_by_role("checkbox")).to_be_checked()      # 复选框已勾选
expect(page.locator("img")).to_have_attribute("src", "logo.png")  # 属性是
```

**这些断言都会自动等待**（最多 5 秒默认）：先等条件成立再通过，不等条件变坏。判断"加载完成后出现某文字"用它最合适。

### 4.6 等待策略（✅ 会这一组就够）

```python
page.wait_for_load_state("networkidle")       # 等网络空闲（页面资源都加载完）
page.wait_for_selector(".card")               # 等某个选择器出现（老 API，能用但 Locator 更优）
page.wait_for_url("**/order/success")          # 等 URL 匹配（下单成功跳转后）
page.wait_for_timeout(1000)                    # 固定等 1 秒（万不得已才用！）
# 更推荐：直接用 Locator 的自动等待，不需要手动 wait
```

> 记住优先顺序：**Locator 自动等待 > expect 断言等待 > wait_for_xxx > wait_for_timeout**。

### 4.7 网络拦截（🧪 进阶但超实用）

拦截请求、伪造响应、屏蔽图片（加速加载）：

```python
# 屏蔽所有图片请求（页面秒开）
page.route("**/*.png", lambda route: route.abort())
page.route("**/*.jpg", lambda route: route.abort())

# 拦截 API 请求，返回假数据（mock 接口，测试神器）
def mock_api(route):
    if "/api/user" in route.request.url:
        route.fulfill(status=200, content_type="application/json",
                      body='{"name": "测试用户", "vip": true}')
    else:
        route.continue_()          # 其他请求放行

page.route("**/api/**", mock_api)

# 等待某个请求的响应（如等待数据接口返回）
with page.expect_response("**/api/list") as resp_info:
    page.get_by_role("button", name="加载").click()
response = resp_info.value
print(response.json())              # 直接拿到接口的 JSON 数据！
```

**这是"爬 JS 网站"的进阶大招**：很多网站的数据来自 XHR 接口，你可以不解析页面，直接 `expect_response` 抓接口 JSON。

### 4.8 截图与 PDF（✅ 最常用的功能之一）

```python
page.screenshot(path="home.png")                    # 截图当前视口
page.screenshot(path="full.png", full_page=True)    # 整页长截图（滚动到底拼起来）
page.screenshot(path="part.png", clip={"x": 0, "y": 0, "width": 500, "height": 400})  # 截指定区域
page.locator(".card").screenshot(path="card.png")   # 只截某个元素

# Chromium 系内核可以把网页存成 PDF（headless 模式下更稳定）
page.pdf(path="report.pdf", format="A4", print_background=True)
```

> 注意：`page.pdf()` 只在 headless 模式或 Chromium 系内核下可用（Firefox/WebKit 不支持）。

### 4.9 文件下载与上传（➕）

```python
# 下载：必须用 expect_download 包住触发下载的动作
with page.expect_download() as dl_info:
    page.get_by_role("button", name="导出报表").click()
download = dl_info.value
download.save_as("报表.xlsx")        # 保存到本地
print(download.suggested_filename)   # 建议的文件名

# 上传：set_input_files 直接给文件路径
page.locator('input[type="file"]').set_input_files("C:/data/a.csv")
# 多文件
page.locator('input[type="file"]').set_input_files(["a.csv", "b.csv"])
```

### 4.10 多标签页 / 弹窗处理（➕）

```python
# 页面里点了"在新标签打开"的链接后：
with context.expect_page() as new_page_info:     # 监听新标签页事件
    page.get_by_text("在新窗口打开").click()
new_page = new_page_info.value                    # 拿到新标签页
new_page.wait_for_load_state()                    # 等它加载
print(new_page.title())

# 处理 alert 弹窗（自动点"确定"）
page.on("dialog", lambda dialog: dialog.accept())
page.get_by_role("button", name="删除").click()   # 弹窗自动被接受
```

### 4.11 移动端模拟（➕）

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    iphone = p.devices["iPhone 13"]               # 取 iPhone 13 的设备参数
    context = p.chromium.launch().new_context(
        **iphone,                                  # 一键变成手机浏览器
        locale="zh-CN",                            # 语言
        timezone_id="Asia/Shanghai",               # 时区
    )
    page = context.new_page()
    page.goto("https://example.com")               # 此时看到的是手机版页面
```

### 4.12 录制脚本：codegen（✅ 强烈推荐先用它）

**codegen（代码生成器）** 是 Playwright 自带的录制工具：**你手动在浏览器里点一遍，它自动生成 Python 代码**。

```bash
playwright codegen https://example.com
```

会弹出浏览器 + 一个代码窗口。你在浏览器里操作，代码窗口实时生成对应代码（还能切换 sync/async 和选择定位器类型）。**初学阶段用它生成骨架，再手动精修**，效率翻倍。

### 4.13 调试工具（➕）

```python
# 方法 1：脚本中暂停，打开一个 Playwright Inspector 调试器
page.pause()

# 方法 2：trace 录制——记录整个操作过程，之后可视化回放
context = browser.new_context(trace="on")        # 开始录制
# ... 操作 ...
context.tracing.stop(path="trace.zip")           # 保存录制文件
# 然后用命令回放：playwright show-trace trace.zip
```

Trace 回放能看到每一步操作、网络请求、控制台报错、截图——**排查复杂问题时无敌**。

## 第 5 章 实战项目案例（从小白到大神）

### 案例 1（入门级）：自动截图网页 + 保存 PDF —— 10 行代码

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)     # 后台运行
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto("https://example.com")
    page.screenshot(path="screenshot_full.png", full_page=True)
    page.pdf(path="page.pdf", format="A4")         # 存成 PDF
    print("标题：", page.title())
    browser.close()
```

**要点回顾**：goto 自动等加载、screenshot 整页长图、pdf 存文档、记得 close。

### 案例 2（进阶级）：模拟登录 + 抓取 JS 动态数据 + 存 CSV

场景：某数据后台，列表数据是 JS 异步加载的，Requests 拿不到，用 Playwright 登录后抓取并保存。

```python
import csv
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://example.com/login")

    # ① 登录
    page.get_by_label("用户名").fill("myuser")
    page.get_by_label("密码").fill("mypass")
    page.get_by_role("button", name="登录").click()
    expect(page.get_by_text("欢迎回来")).to_be_visible()   # 自动等到登录成功

    # ② 打开数据页，等 JS 渲染完成
    page.goto("https://example.com/data")
    expect(page.locator("table tbody tr")).to_have_count(10)  # 等 10 行数据出现

    # ③ 提取每行数据
    rows = page.locator("table tbody tr")
    data = []
    for i in range(rows.count()):
        row = rows.nth(i)
        data.append({
            "name": row.locator("td").nth(0).inner_text(),
            "value": row.locator("td").nth(1).inner_text(),
        })

    # ④ 存 CSV
    with open("data.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "value"])
        writer.writeheader()
        writer.writerows(data)

    print("抓取完成：", len(data), "条")
    browser.close()
```

**要点回顾**：expect 等待登录成功、Locator 的 count/nth/inner_text 遍历行、utf-8-sig 防 Excel 乱码。

### 案例 3（综合联动 🚀）：Playwright + Requests + BeautifulSoup4 + Pandas + Pillow + Openpyxl 全联动

**场景**：一个"商品价格监控系统"——用 Playwright 登录电商后台（或模拟登录态）抓取 JS 渲染的商品列表页；用 Requests 请求商品接口拿原始数据；用 BeautifulSoup4 解析列表页 HTML；用 Pandas 清洗统计；用 Pillow 把价格波动拼成对比图；用 Openpyxl 导出 Excel 日报；最后用 Pytest 风格断言校验结果。

```python
"""
商品价格监控 · 全联动案例
用到的库：playwright + requests + beautifulsoup4 + pandas + pillow + openpyxl
安装：pip install playwright requests beautifulsoup4 pandas pillow openpyxl
     playwright install chromium
"""
import io
import json
from datetime import date

import requests
import pandas as pd
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont
from openpyxl import Workbook
from openpyxl.styles import Font
from playwright.sync_api import sync_playwright, expect

BASE = "https://example.com"
USERNAME, PASSWORD = "demo", "demo123"


def login_and_get_html():
    """第 1 步：Playwright 登录 + 拿 JS 渲染后的列表页 HTML"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{BASE}/login")
        page.get_by_label("用户名").fill(USERNAME)
        page.get_by_label("密码").fill(PASSWORD)
        page.get_by_role("button", name="登录").click()
        expect(page.get_by_text("欢迎回来")).to_be_visible()

        page.goto(f"{BASE}/products")
        expect(page.locator(".product-card")).to_have_count(10)   # 等 JS 渲染出 10 个商品
        html = page.content()                                     # 拿到完整渲染后的 HTML
        browser.close()
        return html


def parse_products(html):
    """第 2 步：BeautifulSoup4 解析 HTML，抽出商品数据"""
    soup = BeautifulSoup(html, "html.parser")
    products = []
    for card in soup.select(".product-card"):
        products.append({
            "名称": card.select_one(".name").get_text(strip=True),
            "价格": float(card.select_one(".price").get_text(strip=True).replace("¥", "")),
            "销量": int(card.select_one(".sales").get_text(strip=True)),
            "库存": card.select_one(".stock").get_text(strip=True),
        })
    return products


def fetch_api_prices():
    """第 3 步：Requests 直接请求价格接口，拿到历史价格（模拟）"""
    resp = requests.get(f"{BASE}/api/prices", timeout=10,
                        headers={"User-Agent": "monitor/1.0"})
    resp.raise_for_status()
    return resp.json()["prices"]          # [{"name": "...", "history": [99, 89, ...]}]


def build_report(products, api_prices):
    """第 4 步：Pandas 清洗统计，生成汇总表"""
    df = pd.DataFrame(products)
    # 清洗：去重复、价格大于 0
    df = df.drop_duplicates(subset=["名称"])
    df = df[df["价格"] > 0]
    # 统计：按库存状态分组算平均价、总销量
    summary = df.groupby("库存")["价格"].agg(["mean", "count"]).round(2)
    summary.columns = ["平均价", "商品数"]
    # 找出最便宜和最贵
    cheapest = df.nsmallest(1, "价格").iloc[0]
    priciest = df.nlargest(1, "价格").iloc[0]
    return df, summary, cheapest, priciest, api_prices


def draw_price_chart(api_prices, out_path="price_chart.png"):
    """第 5 步：Pillow 把历史价格画成对比图（没有 matplotlib 时的轻量方案）"""
    img = Image.new("RGB", (600, 300), "#ffffff")
    draw = ImageDraw.Draw(img)
    # 画坐标轴
    draw.line([(60, 250), (560, 250)], fill="#000000", width=2)
    draw.line([(60, 30), (60, 250)], fill="#000000", width=2)
    # 画每个商品的历史价格折线
    colors = ["#e74c3c", "#3498db", "#27ae60"]
    for idx, item in enumerate(api_prices[:3]):
        prices = item["history"]
        n = len(prices)
        points = []
        for i, price in enumerate(prices):
            x = 60 + i * (480 / max(n - 1, 1))
            y = 250 - (price - min(prices)) / (max(prices) - min(prices) + 1e-9) * 200
            points.append((x, y))
        draw.line(points, fill=colors[idx % 3], width=2)
        draw.text((60 + idx * 180, 15), item["name"], fill=colors[idx % 3])
    img.save(out_path)
    return out_path


def export_excel(df, summary, chart_path, out_path="价格日报.xlsx"):
    """第 6 步：Openpyxl 导出 Excel 日报"""
    wb = Workbook()
    ws = wb.active
    ws.title = "商品数据"
    # 表头
    for col, name in enumerate(df.columns, start=1):
        cell = ws.cell(row=1, column=col, value=name)
        cell.font = Font(bold=True)
    # 数据
    for r, row in df.iterrows():
        for c, name in enumerate(df.columns, start=1):
            ws.cell(row=int(r) + 2, column=c, value=row[name])
    # 第二个 sheet：汇总
    ws2 = wb.create_sheet("汇总")
    for r, row in summary.iterrows():
        ws2.cell(row=r + 1, column=1, value=r)
        ws2.cell(row=r + 1, column=2, value=row["平均价"])
        ws2.cell(row=r + 1, column=3, value=row["商品数"])
    ws3 = wb.create_sheet("说明")
    ws3.cell(row=1, column=1,
             value=f"生成日期：{date.today()} ｜ 截图：{chart_path} ｜ 数据来源：example.com")
    wb.save(out_path)
    return out_path


def verify(df, summary):
    """第 7 步：断言校验（Pytest 风格），结果不对就抛异常"""
    assert len(df) >= 10, "商品数量不足 10 条"
    assert (df["价格"] > 0).all(), "存在非法价格"
    assert summary["平均价"].min() > 0, "平均价异常"
    print("✅ 全部校验通过：", len(df), "个商品，平均价",
          round(df["价格"].mean(), 2))


if __name__ == "__main__":
    html = login_and_get_html()                 # 1. Playwright 抓渲染后 HTML
    products = parse_products(html)             # 2. BeautifulSoup4 解析
    api_prices = fetch_api_prices()             # 3. Requests 抓接口
    df, summary, cheapest, priciest, _ = build_report(products, api_prices)  # 4. Pandas 统计
    chart = draw_price_chart(api_prices)        # 5. Pillow 画图
    excel = export_excel(df, summary, chart)    # 6. Openpyxl 导出
    verify(df, summary)                         # 7. 断言校验
    print("最便宜：", cheapest["名称"], cheapest["价格"])
    print("最贵：", priciest["名称"], priciest["价格"])
    print("已导出：", excel)
```

**这个案例教会你的**：
- 每个库各司其职：Playwright 管"浏览器操作与登录态"、Requests 管"轻量接口"、bs4 管"HTML 解析"、Pandas 管"数据清洗统计"、Pillow 管"轻量绘图"、Openpyxl 管"Excel 落盘"。
- 数据流水线思想：`采集 → 解析 → 清洗 → 分析 → 展示 → 落盘 → 校验`，这是所有数据自动化项目的通用骨架。

## 第 6 章 进阶内容（大神之路）

### 6.1 与 Pytest 集成：把脚本变成测试用例

Playwright 官方推荐搭配 Pytest 使用（`pip install pytest-playwright`）：

```python
# test_shop.py
from playwright.sync_api import expect

def test_login(page):                      # page 是 pytest 自动提供的 fixture
    page.goto("https://example.com/login")
    page.get_by_label("用户名").fill("demo")
    page.get_by_label("密码").fill("demo123")
    page.get_by_role("button", name="登录").click()
    expect(page.get_by_text("欢迎回来")).to_be_visible()
    expect(page).to_have_title("首页")
```

运行：`pytest test_shop.py`。pytest-playwright 自动管理浏览器生命周期、失败自动截图、支持 `--headed` 调试模式。**这是把 Playwright 用于正式项目的最佳姿势**。

### 6.2 并行执行：加快大批量用例

```bash
pytest test_shop.py -n 4          # 4 个 worker 并行跑（需 pip install pytest-xdist）
```

Playwright 天然支持多进程并行（每个 worker 独立浏览器），几十个用例几秒钟跑完。

### 6.3 服务器 / CI 上跑（无界面环境）

```bash
playwright install --with-deps chromium   # 装浏览器 + 系统依赖库
```

然后在代码里 `headless=True` 即可。常见 CI（GitHub Actions、Jenkins）都有官方缓存插件，装一次内核后续秒级。

### 6.4 复用登录态：存储与加载（省去反复登录）

```python
# 存登录态
context = browser.new_context()
page = context.new_page()
page.goto("https://example.com/login")
# ... 登录 ...
context.storage_state(path="state.json")     # 保存 cookie + localStorage

# 下次直接加载，免登录
context = browser.new_context(storage_state="state.json")
page = context.new_page()
page.goto("https://example.com")             # 已经是登录状态！
```

### 6.5 网络层高级用法：修改请求头 / 代理 / 证书

```python
context = browser.new_context(
    extra_http_headers={"User-Agent": "Mozilla/5.0 ..."},
    proxy={"server": "http://proxy.example.com:8080"},
    ignore_https_errors=True,          # 忽略证书错误（测试自签证书网站）
)
```

### 6.6 从 Selenium 迁移对照表

| 能力 | Selenium | Playwright |
| --- | --- | --- |
| 找元素 | `driver.find_element(By.ID, "x")` | `page.locator("#x")` |
| 点击 | `element.click()` | `locator.click()` |
| 输入 | `element.send_keys("x")` | `locator.fill("x")` |
| 等元素 | `WebDriverWait(...).until(...)` | `expect(locator).to_be_visible()` |
| 拿 HTML | `driver.page_source` | `page.content()` |
| 截整页 | 需第三方 | `page.screenshot(full_page=True)` |
| 无头 | `options.add_argument("--headless")` | `launch(headless=True)` |

### 6.7 性能与工程建议

1. **浏览器只启动一次**：一个脚本共用一个 browser（launch 很贵），用 context 区分任务。
2. **能不用截图解析就别用**：优先 `expect_response` 抓接口 JSON，比解析渲染后的 DOM 快且稳。
3. **选择器优先级**：`get_by_role` / `get_by_test_id` > `get_by_text` > CSS > XPath（越贴近用户语义越稳）。
4. **尊重目标网站**：控制频率（加 delay）、遵守 robots.txt、只采集合法授权数据，避免给服务器造成压力（自动化技术本身合法，滥用反爬对抗有风险，请用于正当用途）。

## 第 7 章 高频坑与排查（新手必看）

| 坑 | 症状 | 解决 |
| --- | --- | --- |
| 只装了库没装浏览器 | `Executable doesn't exist at ...chromium` | 运行 `playwright install chromium` |
| 还在用 time.sleep 等页面 | 时快时慢、偶发报错 | 改用 Locator 自动等待 / expect 断言 |
| 元素匹配到多个 | `strict mode violation`（严格模式报错） | 用 `.first` / `.nth(0)` / `.filter(has_text=...)` 明确目标 |
| 元素被遮挡点不到 | `element is not visible / not stable` | 等它自动可点击；或先 hover 展开；最后才考虑 force=True |
| 点击后页面跳转太快 | 后续操作找不到元素 | 在跳转后用 `expect(page).to_have_url(...)` 或等目标元素出现 |
| 下载没反应 | 下载按钮点了没文件 | 必须用 `with page.expect_download():` 包住点击动作 |
| 多标签页拿错页 | 操作一直作用在旧页面 | 用 `context.expect_page()` 拿新页面对象，别再用旧 page |
| 无头模式截图空白 | 页面没加载完就截了 | 先 `expect` 关键元素可见，再截图 |
| 忘了 close 浏览器 | 一堆残留浏览器进程 | try/finally 或 with 结构保证关闭 |
| 同步异步 API 混用 | 各种奇怪报错 | 一个脚本只选一种；普通脚本用 sync_api |
| 服务器上跑不起来 | 缺系统库 | `playwright install --with-deps chromium` |
| 中文输入/显示乱码 | 页面或打印乱码 | 页面用 `locale="zh-CN"`；文件写入用 utf-8 / utf-8-sig |

## 第 8 章 学习路径与自测

**学习路径（小白到大神路线图）**：
1. 安装环境 + 跑通第一个程序（半天）
2. codegen 录制一个登录流程，看生成的代码（半天，成就感最强）
3. Locator 定位全家桶 + 点击/填表（1 天）
4. expect 断言 + 自动等待（1 天，重点中的重点）
5. 截图 + 文件下载上传（半天）
6. 网络拦截 expect_response（1 天，爬虫进阶大招）
7. 多标签页 + 移动端模拟（半天）
8. 案例 1→2→3 逐个手写（2 天）
9. pytest-playwright 集成 + 并行（1 天）
10. 独立做一个自动化小项目（比如给自己的网站写自动回归，2-3 天）

**自测题**（每题都能答上来才算通关）：
1. Playwright 的 Browser / Context / Page 三层各是什么？为什么登录态隔离很重要？
2. 为什么说"不需要 time.sleep"？自动等待的机制是什么？
3. `get_by_role("button", name="登录")` 和 `locator("button")` 有什么区别？为什么推荐前者？
4. 一个按钮匹配到 3 个元素，点击会怎样？怎么选中第 2 个？
5. 怎么判断"登录成功"？（至少两种写法）
6. `expect_response` 有什么用？什么场景下比解析 DOM 更好？
7. 下载文件为什么必须用 `expect_download` 包住？
8. 无头模式下截图空白，先查什么？
9. 怎么保存登录态避免每次重新登录？
10. 综合题：描述一个"每日自动登录 → 抓 3 页数据 → 清洗 → 出 Excel + 截图"的流程，用哪些库、每步用什么 API？

**答案提示**：
1. 浏览器=整个程序；上下文=隔离隔间（cookie/登录态）；页面=标签页。隔离=不同账号互不串。
2. 点击/断言前 Playwright 自动等元素可操作/条件成立（默认 30 秒/5 秒），比固定 sleep 又快又稳。
3. role 按"语义"找（按钮=button、链接=link），贴近真人视角，页面结构变了也不易断；locator 按 CSS 结构找，结构变了就失效。
4. 严格模式报错；用 `.nth(1)`。
5. `expect(page.get_by_text("欢迎回来")).to_be_visible()` 或 `expect(page).to_have_url("**/home")`。
6. 拦截并等待接口响应，直接拿 JSON——JS 数据多走接口，比解析渲染后的 DOM 快且稳。
7. 下载是异步的，expect_download 监听下载事件并持有下载句柄，否则文件可能被清理。
8. 先确认页面加载完成（expect 关键元素可见）再截图；headless 下可能还要等 networkidle。
9. `context.storage_state(path="state.json")` 存，`new_context(storage_state="state.json")` 加载。
10. 参考第 5 章案例 3 的流水线骨架。

<hr>

> 下一篇：《Requests》——和 Playwright 搭配最频繁的"轻量请求"库，HTTP 请求的万能瑞士军刀。
