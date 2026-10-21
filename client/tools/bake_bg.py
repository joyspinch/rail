#!/usr/bin/env python3
"""bake_bg.py — 背景的低频层次（俯视航拍视角）。

背景大图是一张俯视乡村图，画面本身没有地平线——所以层次不能画成"远山
天际线"，那在俯视视角里不成立。这里给的是**俯视航拍**该有的层次：

  bg_overlay.png  云影 + 薄雾带：低频（几十像素到几百像素尺度）的软斑，
                  叠在大图上让地面有明暗变化，不是噪点。
  bg_vignette.png 暗角：把注意力收回画面中心。

刻意避开高频噪点：噪点在放大后会变成脏沙，而且和俯视大图的高频细节
（树丛、田埂）打架。低频才有"景深"的感觉。

产出进 client/assets/。
"""

import os

import numpy as np
from PIL import Image, ImageFilter


def make_overlay(path, w=512, h=256, seed=20261021):
    """云影 + 雾带（RGBA，叠在大图上）。"""
    rng = np.random.default_rng(seed)
    # 低频源：32x16 的随机值 → 双三次放大到全图 → 大半径模糊。
    low = rng.random((16, 32)).astype(np.float32)
    cloud = Image.fromarray((low * 255).astype(np.uint8), "L")
    cloud = cloud.resize((w, h), Image.BICUBIC).filter(
        ImageFilter.GaussianBlur(13))
    a = np.asarray(cloud, dtype=np.float32) / 255.0
    # 只取中段：太亮（=雾）太暗（=厚云）都不要，保持低对比。
    a = np.clip((a - 0.40) / 0.30, 0.0, 1.0) ** 1.4 * 0.85

    # 薄雾带：中间一条横向的柔和亮带（清晨河谷的雾）。
    y = np.arange(h, dtype=np.float32)[:, None]
    band = np.exp(-((y - h * 0.58) ** 2) / (2.0 * (h * 0.16) ** 2))
    band = np.repeat(band, w, axis=1) * 0.22

    alpha = np.clip(a + band, 0.0, 0.85)
    # 云影偏冷暗，雾带偏暖亮——分开两张通道再合成。
    shadow_a = np.clip(a * 1.0, 0.0, 1.0)
    fog_a = np.clip(band, 0.0, 1.0)

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    arr[:, :, 0] = 24
    arr[:, :, 1] = 38
    arr[:, :, 2] = 34
    arr[:, :, 3] = (shadow_a * 120).astype(np.uint8)
    img = Image.fromarray(arr, "RGBA")
    fog = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    farr = np.zeros((h, w, 4), dtype=np.uint8)
    farr[:, :, 0] = 226
    farr[:, :, 1] = 226
    farr[:, :, 2] = 198
    farr[:, :, 3] = (fog_a * 90).astype(np.uint8)
    fog = Image.fromarray(farr, "RGBA")
    img = Image.alpha_composite(img, fog)
    img.save(path, optimize=True)
    print("%-20s %5d bytes  %s" % (os.path.basename(path),
                                   os.path.getsize(path), img.size))
    return img


def make_vignette(path, size=256):
    """暗角：中心透明，四角压暗。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = img.load()
    c = (size - 1) / 2.0
    for y in range(size):
        for x in range(size):
            dx = (x - c) / c
            dy = (y - c) / c
            r = (dx * dx + dy * dy) / 2.0
            if r >= 1.0:
                a = 165
            else:
                a = int(165 * (r ** 2.1))
            px[x, y] = (8, 12, 10, a)
    img.save(path, optimize=True)
    print("%-20s %5d bytes  %s" % (os.path.basename(path),
                                   os.path.getsize(path), img.size))
    return img


def main():
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    assets = os.path.join(root, "client", "assets")
    os.makedirs(assets, exist_ok=True)
    make_overlay(os.path.join(assets, "bg_overlay.png"))
    make_vignette(os.path.join(assets, "bg_vignette.png"))


if __name__ == "__main__":
    main()
