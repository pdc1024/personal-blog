# 第三方库全面教程 · Pillow

> 面向初学者：这是**零基础起步**的图像处理库全套教程，假设你只会最基础 Python 语法。术语第一次出现都有白话解释。
> 适用版本：Pillow 10.x ｜ 配套知识：配合《Playwright/Selenium》（处理网页截图）、配合《NumPy》（图像本质是数组）、配合《Matplotlib》（图像数据分析）。
> 学习目标：从"只会用画图软件"到"用代码批量处理图片：裁剪、缩放、拼接、加水印、转格式、对比、识别准备"。

## 第 1 章 这个库是什么

### 1.1 一句话认识 Pillow

**Pillow**（PIL 的继任者）是 Python **最基础、最通用的图像处理库**：读图、裁剪、缩放、旋转、调色、拼接、加文字水印、换格式（PNG/JPG/WebP）、批量处理，全部几行代码搞定。

```python
from PIL import Image

img = Image.open("photo.jpg")      # 打开图片
img.thumbnail((800, 800))          # 等比缩小
img.save("photo_small.jpg", quality=85)   # 保存（压缩）
```

### 1.2 为什么需要它

- **网页自动化标配**：Playwright/Selenium 截图后，裁剪、拼长图、加标注、压缩。
- **数据处理标配**：图像转 NumPy 数组做分析；验证码图片预处理后交给 OCR。
- **批量处理**：一千张图统一压缩、统一加水印，手点一天，代码 10 秒。
- 几乎所有图像库（OpenCV 部分功能、matplotlib 图片读写、深度学习预处理）都依赖或兼容 Pillow 的 Image 对象。

### 1.3 和 NumPy 的关系

图像在内存里就是 **H×W×3 的数组**（高×宽×RGB）。Pillow 管"打开/保存/简单编辑"，NumPy 管"像素级运算"——两者配合天下无敌（见 NumPy 教程案例 3）。

## 第 2 章 核心概念与原理

### 2.1 图像 = 像素网格

一张 100×100 的图 = 100 行 × 100 列像素，每个像素是 1 个颜色点。彩色图每个像素由 **RGB** 三个值（0~255）组成：红、绿、蓝。`(255,0,0)` 是纯红，`(0,0,0)` 是黑，`(255,255,255)` 是白。

### 2.2 模式（mode）：图像的颜色体系

- **RGB**：彩色（红绿蓝），最常见。
- **RGBA**：彩色 + 透明度（Alpha，0 透明 ~ 255 不透明）。
- **L**：灰度（0 黑 ~ 255 白，一维）。
- **P**：调色板模式（GIF 等）。

转换：`img.convert("L")`（转灰度）、`img.convert("RGBA")`（转 RGBA）。

### 2.3 尺寸坐标系

```
(0,0) ──── x 向右 ────►
  │
  y     crop((left, top, right, bottom))
  │     裁剪区域：左上角 (left, top)，右下角 (right, bottom)
  ▼
```

Pillow 的裁剪/粘贴都用 `(left, top, right, bottom)` 四元组，**右、下是开区间**（不包含）。

## 第 3 章 安装与版本

```bash
pip install pillow
```

导入注意：**包名是 pillow，导入名是 PIL**（历史原因，PIL 是旧名 Python Imaging Library）：

```python
from PIL import Image   # ✅ 正确
```

当前稳定版 10.x。支持格式：PNG、JPG、WebP、GIF、BMP、TIFF 等几十种，开箱即用。

## 第 4 章 API 全面讲解（✅ = 必会 ｜ ➕ = 推荐 ｜ 🧪 = 进阶）

### 4.1 打开、查看、保存（✅）

```python
from PIL import Image

img = Image.open("photo.jpg")        # 打开（懒加载：还没真正读像素）
print(img.size)                      # (1920, 1080) 宽高
print(img.mode)                      # RGB
print(img.format)                    # JPEG
img.load()                           # 真正读入内存（大图处理前）

# 保存（换格式 = 改扩展名）
img.save("photo.png")
img.save("photo_webp.webp")
img.save("photo.jpg", quality=80)    # JPEG 压缩质量（1~95，越低越小越糊）
img.save("photo.jpg", optimize=True) # 优化体积
```

### 4.2 缩放与裁剪（✅）

```python
# 等比缩放（thumbnail 保持比例，尺寸取较小值）
img.thumbnail((800, 800))
img.save("small.png")

# 指定尺寸（会拉伸变形）
resized = img.resize((400, 300))

# 裁剪：crop((left, top, right, bottom))
cropped = img.crop((100, 100, 500, 400))
```

### 4.3 旋转、翻转、镜像（✅）

```python
img.rotate(90)                    # 逆时针 90°（图会超出画布，用 expand=True 扩画布）
img.rotate(90, expand=True)       # 旋转并自动扩大画布（放得下旋转后的图）
img.rotate(45, expand=True, fillcolor=(255, 255, 255))  # 空白处填白色
img.transpose(Image.FLIP_LEFT_RIGHT)   # 水平翻转（镜像）
img.transpose(Image.FLIP_TOP_BOTTOM)   # 垂直翻转
img.transpose(Image.ROTATE_90)         # 顺时针 90°
```

### 4.4 颜色处理（➕）

```python
# 转灰度
gray = img.convert("L")

# 调整亮度/对比度/饱和度/色相
from PIL import ImageEnhance

enhancer = ImageEnhance.Brightness(img); img2 = enhancer.enhance(1.5)   # 亮度 1.5 倍
enhancer = ImageEnhance.Contrast(img);   img2 = enhancer.enhance(1.2)   # 对比度
enhancer = ImageEnhance.Color(img);      img2 = enhancer.enhance(0.5)   # 饱和度
enhancer = ImageEnhance.Sharpness(img);  img2 = enhancer.enhance(2.0)   # 锐度

# 反色
from PIL import ImageOps
inverted = ImageOps.invert(img.convert("L"))   # 反色（灰度）
```

### 4.5 画图：线条、矩形、文字（✅ 水印/标注必备）

```python
from PIL import Image, ImageDraw, ImageFont

img = Image.new("RGB", (800, 400), (255, 255, 255))   # 新建空白画布
draw = ImageDraw.Draw(img)

# 几何图形
draw.line([(50, 50), (700, 50)], fill=(231, 76, 60), width=3)      # 直线
draw.rectangle([(50, 100), (300, 200)], outline=(52, 152, 219), width=2)  # 矩形框
draw.rectangle([(50, 100), (300, 200)], fill=(52, 152, 219))       # 实心矩形
draw.ellipse([(400, 100), (600, 300)], outline=(46, 204, 113), width=2)   # 椭圆/圆

# 文字（中文字体必须指定支持中文的字体文件！）
font = ImageFont.truetype("msyh.ttc", 32)     # Windows 微软雅黑；Mac 用 PingFang.ttc
draw.text((50, 320), "示例水印", font=font, fill=(0, 0, 0))
```

**⚠️ 中文文字坑**：`draw.text` 不指定字体默认用英文位图字体，**中文会显示成方块**。必须 `ImageFont.truetype("中文字体路径", size)`。常见路径：Windows `C:/Windows/Fonts/msyh.ttc`（微软雅黑）、`simhei.ttf`（黑体）。

### 4.6 拼接与粘贴（✅ 长图/拼图必备）

```python
# 横向拼接两张图
img1 = Image.open("a.png")
img2 = Image.open("b.png")
w = img1.width + img2.width
h = max(img1.height, img2.height)
canvas = Image.new("RGB", (w, h), (255, 255, 255))
canvas.paste(img1, (0, 0))
canvas.paste(img2, (img1.width, 0))
canvas.save("join.png")

# 透明图片粘贴（带 Alpha 通道）
logo = Image.open("logo.png").convert("RGBA")
logo = logo.resize((120, 120))
bg = Image.open("bg.jpg").convert("RGBA")
bg.paste(logo, (20, 20), logo)          # 第三个参数是 mask：logo 透明区域不盖住背景
bg.convert("RGB").save("watermarked.jpg")

# 九宫格拼接（自动化截图报告常用）
def make_grid(images, cols=3, cell=(400, 300), bg="white"):
    rows = (len(images) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * cell[0], rows * cell[1]), bg)
    for i, im in enumerate(images):
        im = im.resize(cell)
        canvas.paste(im, ((i % cols) * cell[0], (i // cols) * cell[1]))
    return canvas
```

### 4.7 与 Playwright/Selenium 截图配合（✅ 超实用）

```python
# Playwright 截两个区域 → Pillow 拼接对比
from playwright.sync_api import sync_playwright
from PIL import Image

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://example.com")
    page.screenshot(path="full.png", full_page=True)
    browser.close()

# Pillow 处理：切出顶部导航 + 正文两块，横向拼接成"缩略报告"
img = Image.open("full.png")
nav = img.crop((0, 0, img.width, 200))
body = img.crop((0, 200, img.width, img.height))
canvas = Image.new("RGB", (img.width * 2, img.height), "white")
canvas.paste(nav, (0, 0))
canvas.paste(body, (img.width, 0))
canvas.save("report.png")
```

### 4.8 压缩与体积控制（➕）

```python
# 批量压缩到目标最大边
import os
from PIL import Image

src_dir, dst_dir = "raw", "compressed"
os.makedirs(dst_dir, exist_ok=True)

for name in os.listdir(src_dir):
    if not name.lower().endswith((".jpg", ".png")):
        continue
    img = Image.open(os.path.join(src_dir, name))
    img.thumbnail((1200, 1200))          # 限制最大边
    img.save(os.path.join(dst_dir, name),
             optimize=True, quality=80)  # 质量 80 肉眼几乎无差
print("批量压缩完成")
```

### 4.9 图像转 NumPy / 从 NumPy 生成（🧪）

```python
import numpy as np
from PIL import Image

# 图 → 数组
arr = np.array(Image.open("photo.jpg").convert("RGB"))
print(arr.shape)                    # (高, 宽, 3)

# 数组 → 图
new_img = Image.fromarray(arr.astype("uint8"))
new_img.save("from_array.png")

# 用数组做像素级操作（如把红色调成偏蓝）
arr[:, :, 2] = np.clip(arr[:, :, 2] + 40, 0, 255)   # 蓝色通道 +40
Image.fromarray(arr).save("blue_shift.png")
```

### 4.10 GIF 动图（🧪）

```python
frames = [Image.open(f"frame{i}.png") for i in range(10)]
frames[0].save("anim.gif", save_all=True, append_images=frames[1:],
               duration=100, loop=0)    # duration=每帧毫秒，loop=0 无限循环
```

## 第 5 章 实战项目案例（从小白到大神）

### 案例 1（入门级）：批量加水印

```python
from PIL import Image, ImageDraw, ImageFont
import os

FONT = ImageFont.truetype("msyh.ttc", 36)
WATERMARK = "内部资料"

for name in os.listdir("photos"):
    if not name.lower().endswith((".jpg", ".png")):
        continue
    img = Image.open(os.path.join("photos", name)).convert("RGB")
    draw = ImageDraw.Draw(img)
    # 右下角水印
    w = draw.textlength(WATERMARK, font=FONT)
    x, y = img.width - w - 30, img.height - 40 - 20
    draw.text((x, y), WATERMARK, font=FONT, fill=(255, 255, 255))
    img.save(os.path.join("marked", name), quality=90)
print("全部加水印完成")
```

### 案例 2（进阶级）：网页截图 → 九宫格拼图报告

```python
"""批量打开网页截图 → 缩略 → 九宫格拼成一张总览图"""
from playwright.sync_api import sync_playwright
from PIL import Image

URLS = ["https://example.com/home", "https://example.com/list", "https://example.com/detail"]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    shots = []
    for i, url in enumerate(URLS):
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(url)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=f"shot_{i}.png")
        page.close()
        shots.append(Image.open(f"shot_{i}.png"))
    browser.close()

# 缩略 + 九宫格
thumbs = [im.resize((400, 250)) for im in shots]
rows = (len(thumbs) + 2) // 3
canvas = Image.new("RGB", (400 * 3, 250 * rows), "white")
for i, t in enumerate(thumbs):
    canvas.paste(t, ((i % 3) * 400, (i // 3) * 250))
canvas.save("网页总览.png")
print("已生成总览图")
```

### 案例 3（综合）：**截图对比监控**（Playwright + Pillow）

```python
"""每日对同一页面截图 → 与昨日对比 → 差异超过阈值报警（像素级对比）"""
import os
from datetime import date
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

URL = "https://example.com/"
os.makedirs("shots", exist_ok=True)
TODAY = f"shots/{date.today()}.png"


def take_shot():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(URL)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=TODAY)
        browser.close()


def diff_ratio(a_path, b_path):
    """返回两张图差异像素占比"""
    a = Image.open(a_path).convert("RGB")
    b = Image.open(b_path).convert("RGB").resize(a.size)
    diff = ImageChops.difference(a, b)              # 逐像素差
    if diff.getbbox() is None:
        return 0.0
    gray = diff.convert("L")
    total = a.width * a.height
    changed = sum(1 for p in gray.getdata() if p > 15)
    return changed / total


if __name__ == "__main__":
    take_shot()
    import glob
    shots = sorted(glob.glob("shots/*.png"))
    if len(shots) >= 2:
        ratio = diff_ratio(shots[-2], shots[-1])
        print(f"页面差异率：{ratio:.2%}")
        print("⚠️ 页面有明显变化，请人工检查！" if ratio > 0.05 else "✅ 页面基本稳定")
    else:
        print("今天是第一次截图，明天开始对比")
```

**这个案例是"网页变化监控"的雏形**：配合 Pytest 断言 `ratio < 0.05`、配合定时任务每日运行，就是真实的 UI 监控系统。

## 第 6 章 进阶内容（大神之路）

### 6.1 验证码预处理（OCR 前的标准流程）

```python
from PIL import Image, ImageFilter

cap = Image.open("captcha.png").convert("L")       # 灰度
cap = cap.resize((cap.width * 3, cap.height * 3))  # 放大
cap = cap.point(lambda p: 255 if p > 128 else 0)   # 二值化（>128 变白，否则黑）
cap = cap.filter(ImageFilter.MedianFilter(3))      # 中值滤波去噪点
cap.save("captcha_clean.png")                      # 交给 OCR（如 pytesseract）
```

### 6.2 性能：大批量处理

- `img.load()` 后连续操作更快；用 `thumbnail` 而不是 resize（自动保持比例）。
- 逐行 `getdata()` 慢，大批量像素运算转 NumPy。
- 批量任务用多进程（Pillow 有 GIL，多进程比多线程快）。

### 6.3 与其他库的生态位总结

| 需求 | 用什么 |
| --- | --- |
| 打开/保存/缩放/裁剪/水印 | **Pillow** |
| 像素级复杂运算/滤波 | NumPy + Pillow |
| 专业滤波/计算机视觉 | OpenCV |
| 数据可视化出图 | Matplotlib |
| 网页截图 | Playwright/Selenium → Pillow 处理 |

## 第 7 章 高频坑与排查（新手必看）

| 坑 | 症状 | 解决 |
| --- | --- | --- |
| 中文显示方块 | draw.text 中文变□□ | 必须 `ImageFont.truetype("中文字体.ttc", size)` |
| 导入失败 | `No module named 'PIL'` | 装的是 pillow：`pip install pillow` |
| 图片被拉伸变形 | resize 后比例不对 | 用 `thumbnail`（保持比例） |
| paste 有黑底 | 透明图没处理好 | 原图转 RGBA，paste 时第三个参数传透明图当 mask |
| 裁剪位置不对 | 裁错区域 | 记住 crop((左, 上, 右, 下))，右/下不包含 |
| 保存体积没变小 | 压缩无效 | JPEG 设 `quality=80` + `optimize=True`；PNG 转 JPEG/WebP |
| rotate 后图被切 | 旋转内容超出画布 | `rotate(90, expand=True)` |
| 大图处理卡 | 内存暴涨 | 先 `thumbnail` 缩小再处理；用 NumPy 批量运算 |
| 打开失败格式不支持 | UnidentifiedImageError | 确认文件确实是图片（不是改后缀的假文件） |
| GIF 只显示第一帧 | 只保存了一张 | save 时 `save_all=True, append_images=frames[1:]` |

## 第 8 章 学习路径与自测

**学习路径**：
1. 打开/查看属性/保存换格式（半天）
2. thumbnail/resize/crop（半天）
3. rotate/transpose（半天）
4. 画图 ImageDraw：线条/矩形/文字（1 天）
5. 中文水印 + 批量加水印（半天）
6. 拼接 paste + 透明处理（1 天）
7. 与 Playwright 截图配合（1 天）
8. 压缩与批量处理（半天）
9. 与 NumPy 像素级操作（1 天）
10. 截图对比监控（1-2 天，参考案例 3）

**自测题**：
1. Pillow 的包名和导入名分别是什么？为什么？
2. `thumbnail` 和 `resize` 区别？
3. crop 的参数顺序和开闭区间？
4. 中文文字怎么画才不变方块？
5. 透明 PNG 粘贴到背景上怎么才没有黑底？
6. JPEG 压缩用哪两个参数？
7. 图像转 NumPy 数组用什么？数组形状是什么？
8. 怎么实现"两张图对比差异"？
9. 网页整页截图后想裁出指定区域怎么做？
10. 综合：描述"Playwright 截图 → Pillow 裁剪+拼接 → 存 PNG"的流程。

**答案提示**：
1. 包名 pillow，导入名 PIL（历史遗留，PIL 是旧名）。
2. thumbnail 等比缩小（保持比例）；resize 强制指定尺寸（可能变形）。
3. `crop((left, top, right, bottom))`；右、下是开区间（不包含）。
4. `ImageFont.truetype("msyh.ttc"/"simhei.ttf", size)` 指定中文字体。
5. 背景和前景都转 RGBA，`bg.paste(logo, (x, y), logo)` 第三个参数传 logo 当 mask。
6. `quality`（1-95）+ `optimize=True`。
7. `np.array(img)`；形状 `(高, 宽, 通道数)`，彩色为 3。
8. `ImageChops.difference(a, b)` + 灰度统计非零像素比例（参考案例 3）。
9. `img.crop((left, top, right, bottom))` 按坐标裁（Playwright 截图后就是普通图片）。
10. 参考案例 2：page.screenshot → Image.open → resize/thumbnail → paste 拼接 → save。

<hr>

> 下一篇：《Openpyxl》——Excel 读写库：自动化生成报表、带图表带样式的正式工作簿。
