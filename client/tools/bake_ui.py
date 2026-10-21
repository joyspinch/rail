#!/usr/bin/env python3
"""bake_ui.py — 画布 UI 的美术底板（程序化生成，可复现）。

为什么是程序化而不是逐张 AI 生成：UI 底板是**大面积平铺**的图（顶栏要
拉到 1280px 宽），AI 生成图的噪声在拉伸后会变成条纹；而且按钮要三态
（常态/悬停/按下）、面板要九宫格拉伸——这些用代码画既精确又可复现。

产出（全部进 client/assets/）：
  ui_panel.png    96x96  九宫格面板底板（机油黑底 + 黄铜框 + 角铆钉）
  ui_btn_sheet.png 8x96x48 按钮三态精灵表（常态/悬停/按下 × 普通/强调/禁用）
  ui_gauge.png    96x96  压力表表盘（指针运行时用线画，不进图）
  ui_shadow.png   64x64  接触阴影（径向衰减的黑斑）

九宫格切角宽度（border）必须与这里的画法一致：
  面板 24、按钮 14 —— 角上的铆钉与圆角都落在 border 内，中间只留可拉伸
的纯色/渐变，放噪声就成条纹了。
"""

import os

from PIL import Image, ImageDraw, ImageFilter

# —— 色板（与 client/src/RailPalette.zan、client/assets/skins/rail/skin.css
#    同一套：机油黑 + 黄铜 + 信号灯红/绿）——
OIL_DARK = (18, 21, 24, 255)
OIL_MID = (34, 39, 44, 255)
OIL_LIGHT = (48, 55, 60, 255)
BRASS = (199, 154, 78, 255)
BRASS_BRIGHT = (232, 200, 122, 255)
BRASS_DARK = (110, 85, 40, 255)
GREEN = (36, 70, 58, 255)
GREEN_HOVER = (47, 97, 82, 255)
GREEN_PRESS = (24, 46, 38, 255)
AMBER = (138, 94, 34, 255)
AMBER_HOVER = (176, 124, 46, 255)
AMBER_PRESS = (96, 64, 22, 255)
GREY = (42, 47, 49, 255)
GREY_EDGE = (58, 65, 69, 255)
CREAM = (238, 228, 200, 255)
DANGER = (224, 90, 78, 255)


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill,
                            outline=outline, width=width)


def make_panel(size=96, border=24, path=None):
    """九宫格面板：机油黑底 + 黄铜框 + 四角铆钉 + 顶部内高光。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 底板：竖向渐变（中间区域会被横向拉伸，渐变是竖向的 → 拉伸无痕）。
    for y in range(size):
        t = y / float(size - 1)
        c = tuple(int(OIL_LIGHT[i] * (1 - t) + OIL_DARK[i] * t)
                  for i in range(3)) + (255,)
        d.line([(0, y), (size, y)], fill=c)
    # 黄铜外框。
    rounded(d, [0, 0, size - 1, size - 1], 10, None, BRASS, 3)
    # 内侧暗线（把边框和底板分开）。
    rounded(d, [3, 3, size - 4, size - 4], 8, None, (12, 14, 16, 255), 1)
    # 顶部内高光 + 底部内阴影：给平板一点体积感。
    d.line([(8, 6), (size - 8, 6)], fill=(70, 80, 86, 255), width=1)
    d.line([(8, size - 6), (size - 8, size - 6)], fill=(8, 9, 10, 255), width=1)
    # 四角铆钉（落在 border 内 → 不会被拉伸变形）。
    r = 4
    for cx, cy in ((11, 11), (size - 11, 11), (11, size - 11),
                   (size - 11, size - 11)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BRASS_DARK)
        d.ellipse([cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1], fill=BRASS)
        d.ellipse([cx - r + 2, cy - r + 2, cx + r - 3, cy + r - 3],
                  fill=BRASS_BRIGHT)
    if path:
        img.save(path, optimize=True)
        print("%-20s %5d bytes  %s" % (os.path.basename(path),
                                       os.path.getsize(path), img.size))
    return img


def make_button(plate, edge, hi, path=None, size=(96, 48), border=14,
                gloss=True):
    """一枚按钮底板：圆角铜框 + 板面 + 顶部高光 + 四角小铆钉。"""
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rounded(d, [0, 0, w - 1, h - 1], 8, plate)
    if gloss:
        # 板面竖向渐变（中间横向拉伸无痕）。
        for y in range(1, h - 1):
            t = (y - 1) / float(max(1, h - 3))
            c = tuple(int(hi[i] * (1 - t) + plate[i] * t) for i in range(3))
            d.line([(3, y), (w - 4, y)], fill=c + (255,))
    rounded(d, [0, 0, w - 1, h - 1], 8, None, edge, 2)
    # 四角铆钉（落在 border 内）。
    r = 2
    for cx, cy in ((7, 7), (w - 7, 7), (7, h - 7), (w - 7, h - 7)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BRASS_BRIGHT)
    if path:
        img.save(path, optimize=True)
    return img


def make_button_sheet(path):
    """8 帧按钮表：0-2 普通三态 / 3-5 强调三态 / 6-7 禁用两态。"""
    frames = [
        make_button(GREEN, BRASS_DARK, (52, 96, 80)),
        make_button(GREEN_HOVER, BRASS, (70, 120, 100)),
        make_button(GREEN_PRESS, BRASS_DARK, (34, 60, 48), gloss=False),
        make_button(AMBER, BRASS_DARK, (168, 118, 46)),
        make_button(AMBER_HOVER, BRASS_BRIGHT, (206, 152, 62)),
        make_button(AMBER_PRESS, BRASS_DARK, (104, 70, 24), gloss=False),
        make_button(GREY, GREY_EDGE, (58, 65, 69), gloss=False),
        make_button(GREY, GREY_EDGE, (58, 65, 69), gloss=False),
    ]
    w, h = frames[0].size
    sheet = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.alpha_composite(f, (i * w, 0))
    sheet.save(path, optimize=True)
    print("%-20s %5d bytes  %s" % (os.path.basename(path),
                                   os.path.getsize(path), sheet.size))
    return sheet


def make_gauge(path, size=96):
    """压力表表盘：黄铜表圈 + 奶白表盘 + 刻度 + 红色危险弧。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size / 2.0
    # 表圈（黄铜）+ 内圈暗环。
    d.ellipse([2, 2, size - 3, size - 3], fill=BRASS)
    d.ellipse([6, 6, size - 7, size - 7], fill=(60, 44, 20, 255))
    d.ellipse([9, 9, size - 10, size - 10], fill=CREAM)
    # 表盘径向渐变（外圈略暗）。
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([9, 9, size - 10, size - 10], fill=(60, 48, 30, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(7))
    img = Image.alpha_composite(img, glow)
    d = ImageDraw.Draw(img)
    d.ellipse([9, 9, size - 10, size - 10], fill=CREAM)
    # 刻度：PIL 的 arc/角度从 3 点钟起**顺时针**量。表盘扫 270°：
    # 起点 135°（7:30，满表）在左下，终点 405°=45°（4:30，空表）在右下。
    # 每 30° 一格共 10 格，90° 一根长刻度。
    import math
    r_out = size / 2.0 - 11
    r_in = size / 2.0 - 15
    r_in_long = size / 2.0 - 20
    for i in range(10):
        a = math.radians(135 + i * 30)
        long = (i % 3 == 0)
        ri = r_in_long if long else r_in
        x0 = c + math.cos(a) * ri
        y0 = c + math.sin(a) * ri
        x1 = c + math.cos(a) * r_out
        y1 = c + math.sin(a) * r_out
        col = DANGER if i >= 7 else (60, 52, 38, 255)
        d.line([(x0, y0), (x1, y1)], fill=col, width=3 if long else 2)
    # 危险区红色扇弧（最后三格：时间不多的一段）。
    d.arc([11, 11, size - 12, size - 12], start=135 + 7 * 30 - 4,
          end=135 + 9 * 30 + 4, fill=DANGER, width=4)
    # 轴心。
    d.ellipse([c - 5, c - 5, c + 5, c + 5], fill=BRASS_DARK)
    d.ellipse([c - 2, c - 2, c + 2, c + 2], fill=BRASS_BRIGHT)
    img.save(path, optimize=True)
    print("%-20s %5d bytes  %s" % (os.path.basename(path),
                                   os.path.getsize(path), img.size))
    return img


def make_shadow(path, size=64):
    """接触阴影：径向衰减的黑斑（椭圆，落地感）。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    c = (size - 1) / 2.0
    for y in range(size):
        for x in range(size):
            dx = (x - c) / c
            dy = (y - c) / c
            # 椭圆：横向半径大、纵向半径小（贴地的影子）。
            r = (dx * dx) + (dy * dy * 2.4)
            if r >= 1.0:
                continue
            a = int(150 * (1.0 - r) ** 1.6)
            px[x, y] = (0, 0, 0, a)
    img = img.filter(ImageFilter.GaussianBlur(1.2))
    img.save(path, optimize=True)
    print("%-20s %5d bytes  %s" % (os.path.basename(path),
                                   os.path.getsize(path), img.size))
    return img


def main():
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    assets = os.path.join(root, "client", "assets")
    os.makedirs(assets, exist_ok=True)
    make_panel(path=os.path.join(assets, "ui_panel.png"))
    make_button_sheet(os.path.join(assets, "ui_btn_sheet.png"))
    make_gauge(os.path.join(assets, "ui_gauge.png"))
    make_shadow(os.path.join(assets, "ui_shadow.png"))


if __name__ == "__main__":
    main()
