# 第三方库全面教程 · PyAutoGUI

> 面向初学者：这是**零基础起步**的桌面自动化库全套教程，假设你只会最基础 Python 语法。术语第一次出现都有白话解释。
> 适用版本：PyAutoGUI 0.9.5x ｜ 配套知识：配合《Playwright/Selenium》（网页内自动化）与《Pillow》（屏幕截图识别）组成"浏览器 + 桌面"全栈自动化。
> 学习目标：从"手动点鼠标"到"用代码控制鼠标键盘：自动点击、自动输入、屏幕找图、窗口操作、定时任务"。

## 第 1 章 这个库是什么

### 1.1 一句话认识 PyAutoGUI

**PyAutoGUI** 是 Python 的**桌面级自动化库**：它直接控制你的鼠标和键盘，模拟真人"移动鼠标、点击、打字、按快捷键"，还能截屏、在屏幕上找图片、控制窗口。

```python
import pyautogui

pyautogui.moveTo(500, 300, duration=1)     # 鼠标移动到 (500,300)
pyautogui.click()                          # 点击
pyautogui.typewrite("hello")               # 打字
```

### 1.2 网页自动化 vs 桌面自动化（先分清边界）

| | Playwright/Selenium | PyAutoGUI |
| --- | --- | --- |
| 控制对象 | 浏览器内部（DOM 元素） | 整个桌面（任何软件） |
| 定位方式 | 元素选择器（精确） | 坐标/屏幕找图（粗糙） |
| 稳定性 | 高（按元素找） | 低（靠坐标，窗口一动就偏） |
| 适用范围 | 网页 | 任何桌面软件（Excel、微信、游戏、老系统） |

**正确姿势**：能用 Playwright/Selenium 的**绝对优先用它们**（稳）；PyAutoGUI 用于**它们碰不到的地方**——桌面软件、登录弹窗、系统对话框、老旧非网页程序。

### 1.3 危险警告（必须知道）

**PyAutoGUI 会真的控制你的电脑**——写错代码可能乱点乱删。解决：
1. `pyautogui.FAILSAFE = True`（默认开）：鼠标甩到屏幕**左上角**（0,0）立即紧急停止。
2. `pyautogui.PAUSE = 0.5`：每步之间停 0.5 秒，留反应时间。
3. 先小步测试，再跑完整流程。

## 第 2 章 核心概念与原理

### 2.1 屏幕坐标系

```
(0,0) ──── x 向右 ────► (width, 0)
  │
  y
  │
  ▼
(0, height)          (width, height)
```

- 左上角是 (0,0)，x 向右增大，y 向下增大。
- 单位是**像素**。
- 多显示器时坐标可能是负数（副屏在左边）。

### 2.2 截图找图原理

`pyautogui.locateOnScreen("btn.png")` 的原理：截取当前屏幕 → 在屏幕像素里**模板匹配**找和目标小图最像的位置。**注意**：
- 小图必须和屏幕上的实际显示**像素级一致**（分辨率、缩放比例、颜色）。
- 屏幕缩放（Windows 150% 缩放）会导致匹配失败——这是高频坑。
- 适合"固定界面、按钮不变"的场景。

### 2.3 安全机制

- **FAILSAFE**：默认启用，鼠标移到左上角立即抛 `FailSafeException` 停止脚本。
- **PAUSE**：全局步间暂停，防止动作太快失控。

## 第 3 章 安装与版本

```bash
pip install pyautogui
```

- Windows 无额外依赖；macOS 需要辅助功能权限；Linux 需要 xdotool 等。
- 验证（**先别乱动**，只查屏幕）：

```python
import pyautogui
print(pyautogui.size())        # (1920, 1080) 屏幕分辨率
print(pyautogui.position())    # 当前鼠标位置
```

## 第 4 章 API 全面讲解（✅ = 必会 ｜ ➕ = 推荐 ｜ 🧪 = 进阶）

### 4.1 鼠标移动与点击（✅）

```python
import pyautogui

pyautogui.FAILSAFE = True       # 安全开关
pyautogui.PAUSE = 0.3           # 每步停 0.3 秒

# 移动（duration 秒内平滑移动，像真人）
pyautogui.moveTo(500, 300, duration=0.5)        # 移动到绝对坐标
pyautogui.moveRel(50, 0, duration=0.3)          # 相对当前位置移动

# 点击
pyautogui.click()                               # 当前鼠标位置单击
pyautogui.click(500, 300)                       # 移动到 (500,300) 再单击
pyautogui.doubleClick(500, 300)                 # 双击
pyautogui.rightClick(500, 300)                  # 右键
pyautogui.middleClick(500, 300)                 # 中键

# 拖拽（从 A 拖到 B）
pyautogui.dragTo(800, 500, duration=1)          # 按住左键拖到目标
pyautogui.dragRel(100, 0, duration=1)           # 相对拖拽

# 滚动
pyautogui.scroll(300)          # 向上滚 300 格（负数向下）
```

### 4.2 键盘输入（✅）

```python
import pyautogui

pyautogui.typewrite("hello world", interval=0.05)      # 打字（间隔秒）
pyautogui.press("enter")                               # 按单个键
pyautogui.press("a")                                   # 小写 a
pyautogui.press(["a", "b", "c"])                       # 依次按

# 组合键（快捷键）
pyautogui.hotkey("ctrl", "c")        # 复制
pyautogui.hotkey("ctrl", "v")        # 粘贴
pyautogui.hotkey("alt", "tab")       # 切换窗口

# 常用键名
# enter, esc, tab, space, backspace, delete, home, end,
# up/down/left/right, ctrl, alt, shift, win
# f1~f12, num0~9（小键盘）
```

**⚠️ 中文输入**：`typewrite` 只支持英文和 ASCII 字符。中文输入用系统剪贴板方案：

```python
import pyautogui, pyperclip

pyperclip.copy("中文内容")              # 写入剪贴板（需 pip install pyperclip）
pyautogui.hotkey("ctrl", "v")          # 粘贴
```

### 4.3 消息框（✅ 人机交互）

```python
import pyautogui

pyautogui.alert("任务完成！")                    # 提示框（点确定继续）
answer = pyautogui.confirm("是否继续？", buttons=["是", "否"])
if answer == "是":
    ...
password = pyautogui.password("请输入密码")       # 密码输入框
text = pyautogui.prompt("请输入内容")             # 文本框
```

### 4.4 屏幕截图（✅）

```python
import pyautogui

img = pyautogui.screenshot()               # 全屏截图（PIL Image 对象）
img.save("screen.png")

img2 = pyautogui.screenshot(region=(100, 100, 500, 400))   # 只截区域
# region = (left, top, width, height)
```

### 4.5 屏幕找图（➕ 关键但需小心）

```python
import pyautogui

# 在屏幕上找目标小图，返回 (left, top, width, height)
pos = pyautogui.locateOnScreen("button.png", confidence=0.8)
if pos:
    center = pyautogui.center(pos)          # 得到中心点
    pyautogui.click(center)                 # 点它
else:
    print("没找到按钮")

# 找多个
for box in pyautogui.locateAllOnScreen("icon.png", confidence=0.8):
    print(pyautogui.center(box))

# 找不到时抛出（onScreen 默认不抛，需要配合循环等待）
```

**⚠️ confidence 参数需要额外装 opencv-python**：`pip install opencv-python`。不用 confidence 则要求像素级精确匹配。

### 4.6 等待图片出现（➕ 自动化必备循环）

```python
import pyautogui, time

def wait_until_found(image, timeout=15, interval=0.5):
    """最多等 timeout 秒，直到图片出现并返回位置"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        pos = pyautogui.locateOnScreen(image, confidence=0.8)
        if pos:
            return pyautogui.center(pos)
        time.sleep(interval)
    raise TimeoutError(f"{timeout} 秒内没找到 {image}")

center = wait_until_found("confirm_btn.png")
pyautogui.click(center)
```

### 4.7 窗口控制（➕）

```python
import pyautogui

# 获取当前活动窗口标题
print(pyautogui.getActiveWindow())

# 获取所有窗口（Windows 上可用 pygetwindow，配合安装）
import pygetwindow as gw
for w in gw.getAllTitles():
    print(w)

win = gw.getWindowsWithTitle("记事本")[0]
win.activate()                 # 激活
win.maximize()                 # 最大化
win.minimize()                 # 最小化
win.moveTo(100, 100)           # 移动
win.resizeTo(800, 600)         # 改大小
```

### 4.8 像素取色（🧪）

```python
import pyautogui

color = pyautogui.pixel(500, 300)        # 该坐标颜色 (r, g, b)
print(color)
print(pyautogui.pixelMatchesColor(500, 300, (255, 0, 0)))  # 是不是红色
```

## 第 5 章 实战项目案例（从小白到大神）

### 案例 1（入门级）：自动填表小工具

```python
"""打开记事本 → 自动输入 → 保存"""
import pyautogui, time

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.4

# 打开记事本（用系统运行框）
pyautogui.hotkey("win", "r")                  # 打开运行
pyautogui.typewrite("notepad")                # 输入命令
pyautogui.press("enter")
time.sleep(2)                                 # 等记事本打开

# 输入内容（英文）
pyautogui.typewrite("Hello from PyAutoGUI!", interval=0.03)
pyautogui.press("enter")
pyautogui.typewrite("This is line 2.")

# 保存
pyautogui.hotkey("ctrl", "s")                 # 打开保存对话框
time.sleep(1)
pyautogui.typewrite("C:/Users/Administrator/Desktop/auto.txt")
pyautogui.press("enter")
print("保存完成（若弹出覆盖确认请手动处理或加截图处理）")
```

### 案例 2（进阶级）：Excel 批量操作（桌面版 Office 自动化）

```python
"""打开 Excel 文件 → 找到"操作"列 → 自动填写 100 行"""
import pyautogui, time, subprocess

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

# 用系统默认程序打开 Excel 文件
subprocess.Popen(["start", "", r"C:\data\tasks.xlsx"], shell=True)
time.sleep(4)                                 # 等 Excel 完全打开

# 思路：鼠标点 A2 → 输入 → 按方向键下 → 输入……
# 关键 API 组合：
# 1. 先人工把鼠标移到"第一个单元格"位置（或用截屏找图）
pyautogui.click(300, 300)                     # 假设 A2 在屏幕 (300,300)
for i in range(100):
    pyautogui.typewrite(f"task_{i:03d}")
    pyautogui.press("down")                   # 移到下一行
print("批量填写完成")
```

**⚠️ 真实项目建议**：能用 openpyxl 直接写 Excel 就别用 PyAutoGUI 点——**能用库解决的绝不用鼠标**。PyAutoGUI 只用于"真的没有库能碰"的桌面软件。

### 案例 3（综合）：**Playwright + PyAutoGUI 混合自动化**（联动案例）

```python
"""网页自动化 + 桌面自动化混合：下载报表 → 处理系统弹窗 → 桌面 Excel 汇总"""
import pyautogui, time
from playwright.sync_api import sync_playwright

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

# ① Playwright：网页内操作（精确、稳定）
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)   # 有头模式（要配合桌面）
    page = browser.new_page()
    page.goto("https://example.com/report")
    page.get_by_role("button", name="导出 Excel").click()
    time.sleep(3)                                 # 等下载对话框

# ② PyAutoGUI：处理浏览器下载/保存弹窗（Playwright 管不到的系统对话框）
#    假设弹窗焦点已自动切到保存对话框
pyautogui.typewrite(r"C:\data\report.xlsx")       # 输入保存路径
pyautogui.press("enter")
time.sleep(2)

# ③ 桌面自动化：打开文件管理器确认下载成功
pyautogui.hotkey("win", "e")
time.sleep(1)
pyautogui.hotkey("ctrl", "l")                     # 地址栏
pyautogui.typewrite(r"C:\data")
pyautogui.press("enter")
time.sleep(1)

# ④ 检查文件是否在（用 Python 文件操作验证，别靠眼睛）
import os
if os.path.exists(r"C:\data\report.xlsx"):
    print("✅ 下载成功：report.xlsx")
else:
    print("❌ 下载失败，请检查弹窗处理")
```

**联动要点**：
- Playwright 负责**网页内部**（定位/点击/等待）。
- PyAutoGUI 负责**系统级**（下载弹窗、文件管理器、其他桌面软件）。
- 混合项目里**用文件系统/日志验证结果**，不要"猜着操作"。

### 案例 4（进阶）：**截屏找图版自动签到**

```python
"""每天定时：打开网站 → 屏幕找图点击签到按钮 → 截图留证"""
import pyautogui, time
from PIL import Image

def wait_click(image, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        pos = pyautogui.locateOnScreen(image, confidence=0.8)
        if pos:
            pyautogui.click(pyautogui.center(pos))
            return True
        time.sleep(0.5)
    return False

# 打开浏览器（用 pygetwindow 或直接快捷键）
pyautogui.hotkey("win", "r")
pyautogui.typewrite("https://example.com/checkin")
pyautogui.press("enter")
time.sleep(5)

if wait_click("checkin_btn.png"):
    print("已点击签到按钮")
    time.sleep(2)
    pyautogui.screenshot("checkin_result.png")     # 截图留证（配合 Pillow 处理）
else:
    print("没找到签到按钮（可能已签到或页面变了）")
```

## 第 6 章 进阶内容（大神之路）

### 6.1 图像识别增强：模板预处理

截屏找图失败时，用 Pillow 先统一尺寸/灰度再匹配：

```python
from PIL import Image
import pyautogui

# 把目标小图转为和屏幕一致的颜色模式
img = Image.open("btn.png").convert("RGB")
img.save("btn_rgb.png")
pos = pyautogui.locateOnScreen("btn_rgb.png", confidence=0.7)
```

### 6.2 坐标的"相对化"处理（抗布局变化）

```python
# 先找窗口左上角，再按偏移计算所有点击位置
win_pos = pyautogui.locateOnScreen("window_title.png", confidence=0.8)
if win_pos:
    base_x, base_y = pyautogui.center(win_pos)
    pyautogui.click(base_x + 200, base_y + 150)   # 相对窗口点
```

### 6.3 定时自动化（配合 schedule）

```python
import schedule, time, pyautogui

def daily_task():
    print("开始每日任务")
    # 你的自动化逻辑
    pyautogui.alert("每日任务完成")

schedule.every().day.at("09:00").do(daily_task)
while True:
    schedule.run_pending()
    time.sleep(1)
```

### 6.4 安全运行规范（重要）

1. 调试时 `FAILSAFE=True` + `PAUSE=0.5` + 先跑小范围。
2. 关键操作前截屏备份（`pyautogui.screenshot("before.png")`）。
3. 用 try/finally 保证异常时也能恢复（如把鼠标移回安全区）。
4. 生产环境优先用无头/库方案，PyAutoGUI 只做"最后的手段"。

## 第 7 章 高频坑与排查（新手必看）

| 坑 | 症状 | 解决 |
| --- | --- | --- |
| 屏幕缩放导致找图失败 | locateOnScreen 找不到 | Windows 缩放改回 100%；或用 confidence + opencv；截图用相同分辨率 |
| 中文输入乱码/无效 | typewrite 中文没反应 | 用 pyperclip 复制 + ctrl+v |
| 鼠标失控乱点 | 脚本跑飞了 | 立即把鼠标甩左上角（FAILSAFE）；先小步测试 |
| 窗口移动后点错位置 | 点到别的地方 | 先找窗口位置再相对偏移；避免写死坐标 |
| 找不到图片 | locateOnScreen 返回 None | 确认小图 = 屏幕上实际显示（用 pyautogui.screenshot 区域截图对比） |
| 权限被拒（macOS） | 控制不了鼠标 | 系统设置 → 隐私与安全性 → 辅助功能 授权 |
| 多显示器坐标错乱 | 点错屏 | 主屏副屏坐标不同；用 pyautogui.size() 确认范围 |
| 没有置信度参数 | confidence 报错 | `pip install opencv-python` |
| 弹窗焦点不在目标窗口 | 输入到别处 | 先 pygetwindow activate 目标窗口，或点击窗口标题栏 |
| 速度太快漏步骤 | 动作没完成 | 加大 PAUSE / 加 time.sleep |

## 第 8 章 学习路径与自测

**学习路径**：
1. 屏幕信息 + 鼠标移动点击（半天）
2. 键盘输入 + 组合键（半天）
3. 消息框交互（半天）
4. 截图 + 区域截图（半天）
5. 屏幕找图 + 等待循环（1 天）
6. 窗口控制 pygetwindow（半天）
7. 案例 1→3 手写（2 天）
8. Playwright + PyAutoGUI 混合（1-2 天，重点）
9. 定时任务 + 安全规范（1 天）

**自测题**：
1. FAILSAFE 和 PAUSE 分别是什么？为什么必须有？
2. 屏幕坐标系原点和单位？
3. `moveTo` 和 `moveRel` 区别？
4. typewrite 为什么不支持中文？怎么解决？
5. 屏幕找图的原理和两个坑？
6. confidence 参数需要装什么？
7. Playwright 和 PyAutoGUI 的分工原则？
8. 多显示器/缩放屏幕找图失败怎么办？
9. 怎么等一个图片出现再点击？
10. 综合：设计"网页下载报表 + 处理保存弹窗 + 桌面确认文件"的混合自动化。

**答案提示**：
1. FAILSAFE 鼠标甩左上角紧急停止；PAUSE 步间暂停防失控。
2. 左上角 (0,0)，x 右 y 下，单位像素。
3. moveTo 绝对坐标；moveRel 相对当前移动。
4. typewrite 只支持 ASCII；用 `pyperclip.copy("中文")` + `hotkey("ctrl","v")`。
5. 模板匹配像素找图；坑是屏幕缩放/分辨率不一致导致失败、写死坐标不稳。
6. opencv-python。
7. 网页内部用 Playwright，系统级（弹窗/桌面软件）用 PyAutoGUI；能用库绝不用鼠标。
8. 系统缩放改 100%，或用 confidence=0.7~0.8 容错，截图用相同分辨率。
9. 参考 4.6 wait_until_found 循环（locateOnScreen + time.sleep 轮询 + 超时）。
10. 参考案例 3：Playwright click 导出 → PyAutoGUI 处理保存框 → os.path.exists 验证 → PyAutoGUI 打开文件管理器复核。

<hr>

> 本篇是"网页自动化搭配库"系列最后一份。至此四份搭配库（Pytest/Pillow/Openpyxl/PyAutoGUI）已齐，与 Playwright 教程第 5 章案例 3 的"7 库联动价格监控"共同构成完整的自动化学习矩阵。
