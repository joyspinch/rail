#!/usr/bin/env python3
"""bake_facing.py — 把机车 / 货箱位图离线烘成"方向精灵表"。

为什么必须离线烘：引擎运行时转不了图——`Canvas.BlitImage` 只有源矩形
(sx,sy,sw,sh)，没有旋转、没有水平翻转，`Gui.SpriteBatch` 的每精灵也只有
dx/dy/dw/dh/sx/sy/sw/sh/tint。所以"运行时把机车转个方向"做不到，朝向只能
在素材阶段烘好，运行时按角度取帧。

做法（照 arena 的 bake_facing.py 那一套）：
  1. 从 **client/assets/ 的入库存图**出发（不是 build/raw 的 AI 原图——入库图
     才是运行时真正贴的那张；原图可能与入库图尺寸/裁切不同）。
  2. 找出车头：AI 机车图里车头是**底部的红色排障器**（真机排障器在机车
     前端；从前往后是 排障器 → 烟囱 → 蒸汽穹 → 煤水车，与图里自下而上的
     顺序一致）。在车头内侧补一枚暖色前照灯——运行时机车只有 64px，光靠
     一小块红色不够醒目，前照灯是"一眼看出朝向"的关键。
  3. 旋转轴 = 贴图中心（= 机车中心）；旋转用"预乘 alpha → 旋转 → 反预乘"，
     半透明边缘的 RGB 不会被插值到黑（直接旋转 RGBA 会带出黑边）。
  4. 帧 0 = 车头朝上，之后每帧顺时针 360/16 = 22.5°，拼成一条横条精灵表
     （帧宽 = 帧高 = 贴图边长）。

角度 → 帧号的映射是纯函数（client/src/RailFacing.zan），用例钉住不回归。

用法：
    python client/tools/bake_facing.py [--assets <assets 目录>]
"""

import argparse
import os
from collections import deque

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

# 方向帧数：16 = 22.5° 一帧。铁轨俯视、机车随时变向，8 帧（45°）在斜向
# 分岔上会明显"转到隔壁去"，16 帧更稳。
FRAMES = 16

# 车头识别：排障器的红。取"红色像素最多的连通块"——车尾煤水车的红色饰条
# 只是一条细边，块远小于排障器。
NOSE_RED_MIN = 90
NOSE_RED_MAX_G = 90
NOSE_RED_MAX_B = 90


def find_nose(img):
    """找出车头（红色排障器）连通块，返回 (cx, top_y) 或 None。

    像素坐标：左上为原点，y 向下。返回的 top_y 是排障器最上沿。
    """
    r, g, b, a = img.split()
    mask = np.zeros((img.height, img.width), dtype=np.uint8)
    px = np.asarray(img)
    hit = ((px[:, :, 0] > NOSE_RED_MIN)
           & (px[:, :, 1] < NOSE_RED_MAX_G)
           & (px[:, :, 2] < NOSE_RED_MAX_B)
           & (np.asarray(a) > 40))
    mask[hit] = 1
    if mask.sum() == 0:
        return None
    # 最大连通块（4 邻接洪泛）。
    seen = np.zeros_like(mask)
    best = None
    best_size = 0
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    for sy, sx in zip(ys.tolist(), xs.tolist()):
        if seen[sy, sx]:
            continue
        q = deque([(sy, sx)])
        seen[sy, sx] = 1
        cells = []
        while q:
            cy, cx = q.popleft()
            cells.append((cy, cx))
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy + dy, cx + dx
                if ny < 0 or ny >= h or nx < 0 or nx >= w:
                    continue
                if seen[ny, nx] or not mask[ny, nx]:
                    continue
                seen[ny, nx] = 1
                q.append((ny, nx))
        if len(cells) > best_size:
            best_size = len(cells)
            best = cells
    if best is None or best_size < 40:
        return None
    cy = [c[0] for c in best]
    cx = [c[1] for c in best]
    return (int(round(sum(cx) / len(cx))), min(cy))


def add_headlight(img, nose):
    """在车头内侧补一枚前照灯（暖色光晕 + 灯芯 + 黄铜环）。

    nose = (cx, top_y)：排障器中心 x 与最上沿 y。灯芯落在排障器正上方
    一点点的位置——那正是真机车前照灯（烟箱正面灯）的位置。
    """
    if nose is None:
        return img
    cx, top = nose
    ly = top - 9
    if ly < 4:
        return img
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([cx - 15, ly - 15, cx + 15, ly + 15],
                                 fill=(255, 206, 120, 110))
    glow = glow.filter(ImageFilter.GaussianBlur(6))
    core = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d2 = ImageDraw.Draw(core)
    # 灯芯：黄铜环 + 亮芯。
    d2.ellipse([cx - 5, ly - 5, cx + 5, ly + 5], fill=(196, 146, 66, 255))
    d2.ellipse([cx - 3, ly - 3, cx + 3, ly + 3], fill=(255, 238, 190, 255))
    # 顺序：机体在下，灯光叠在机体**之上**（叠反了灯会被车身盖住）。
    out = Image.alpha_composite(img, glow)
    out = Image.alpha_composite(out, core)
    return out


def rotate_clean(img, deg):
    """绕图心旋转 deg 度（PIL 正角 = 逆时针），消除黑边。

    做法：RGB 预乘 alpha → 旋转 → 反预乘。直接旋转 RGBA 时，BICUBIC 会把
    透明像素的黑色 RGB 插值进边缘，半透明边缘因此发黑（"黑边"）。
    """
    alpha = np.asarray(img.split()[3], dtype=np.float32) / 255.0
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    pre = rgb * alpha[:, :, None]
    pre_img = Image.fromarray(np.clip(pre, 0, 255).astype(np.uint8), "RGB")
    alpha_img = img.split()[3]

    rot_pre = np.asarray(pre_img.rotate(deg, resample=Image.BICUBIC),
                         dtype=np.float32)
    rot_alpha = np.asarray(alpha_img.rotate(deg, resample=Image.BICUBIC),
                           dtype=np.float32) / 255.0

    safe = np.maximum(rot_alpha, 1e-3)[:, :, None]
    straight = np.clip(rot_pre / safe, 0, 255)
    out = Image.fromarray(straight.astype(np.uint8), "RGB").convert("RGBA")
    out.putalpha(Image.fromarray(
        (np.clip(rot_alpha, 0.0, 1.0) * 255.0).astype(np.uint8), "L"))
    return out


def bake(src_path, out_path, pre, with_headlight, cell_out=0):
    """把一张方形贴图烘成 FRAMES 帧的横条精灵表。

    pre = 烘焙前的预旋转（度，PIL 正角 = 逆时针）。帧 0 = 源图预转 pre 之后
    的朝向；之后每帧再顺时针 360/FRAMES 度。
    cell_out = 输出帧的边长（0 = 用源图边长）。缩到显示尺寸的 2 倍即可，
    再大只是白占体积（精灵表会被拉成 16 帧的长条）。
    """
    img = Image.open(src_path).convert("RGBA")
    if img.width != img.height:
        raise SystemExit("贴图必须正方形：%s (%dx%d)"
                         % (src_path, img.width, img.height))
    if with_headlight:
        nose = find_nose(img)
        if nose is None:
            print("  ! 没认出车头（红色排障器），跳过前照灯")
        else:
            print("  车头（排障器）中心 x=%d 上沿 y=%d" % (nose[0], nose[1]))
            img = add_headlight(img, nose)
    if cell_out and cell_out != img.width:
        img = img.resize((cell_out, cell_out), Image.LANCZOS)
    cell = img.width
    step = 360.0 / FRAMES
    strip = Image.new("RGBA", (cell * FRAMES, cell), (0, 0, 0, 0))
    for i in range(FRAMES):
        # 帧 i = 帧 0 再顺时针转 i×step 度（PIL 逆时针为正，取负）。
        deg = pre - i * step
        frame = rotate_clean(img, deg)
        strip.paste(frame, (i * cell, 0), frame)
    strip.save(out_path, optimize=True)
    print("%-18s %2d 帧 cell=%dx%d -> %s (%d 字节)"
          % (os.path.basename(out_path), FRAMES, cell, cell,
             os.path.basename(out_path), os.path.getsize(out_path)))


def main():
    ap = argparse.ArgumentParser()
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    ap.add_argument("--assets", default=os.path.join(root, "client", "assets"))
    args = ap.parse_args()

    assets = args.assets
    os.makedirs(assets, exist_ok=True)

    # 机车：源图车头朝**下**（红色排障器在下），预转 180° 后帧 0 = 车头朝上。
    bake(os.path.join(assets, "train.png"),
         os.path.join(assets, "train_sheet.png"),
         pre=180, with_headlight=True)
    # 货箱：木箱没有车头，旋转只为让箱面铁箍跟着机车一起转（朝向一致）。
    # 货箱显示只有 0.36 格（17~23 逻辑像素），帧边长 48 已是显示尺寸的 2 倍
    # 以上——再大只是把精灵表撑成 16 帧的长条、白占体积。
    bake(os.path.join(assets, "cargo.png"),
         os.path.join(assets, "cargo_sheet.png"),
         pre=0, with_headlight=False, cell_out=48)

    total = 0
    for f in sorted(os.listdir(assets)):
        if f.endswith("_sheet.png"):
            total += os.path.getsize(os.path.join(assets, f))
    print("精灵表合计: %.1f KB" % (total / 1024.0))


if __name__ == "__main__":
    main()
