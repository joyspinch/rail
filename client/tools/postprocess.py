"""把 build/raw/ 的 AI 原图后处理成 client/assets/ 的正式素材。

AI 图没有 alpha（纯黑底），所以要洪泛抠黑底抠出 alpha，再裁边、缩放到
显示尺寸的 2 倍入库。竖轨与分岔贴图不额外生成——由横轨图旋转/拼出，
保证轨道接缝对得上。

原图由 client/tools/gen_images.ps1 生成（落 build/raw/，不入库）。
本脚本只做"原图 → 入库图"，路径按脚本位置解析（相对仓库根）。
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "build", "raw")
OUT = os.path.join(ROOT, "client", "assets")


def load_rgba(name):
    img = Image.open(os.path.join(RAW, name)).convert("RGBA")
    return img


def flood_alpha(img, thresh=14):
    """从四边洪泛，把连通的近黑像素抠成透明。"""
    w, h = img.size
    px = img.load()
    seen = bytearray(w * h)
    stack = []
    for x in range(w):
        stack.append((x, 0))
        stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y))
        stack.append((w - 1, y))
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        i = y * w + x
        if seen[i]:
            continue
        r, g, b, a = px[x, y]
        if r > thresh or g > thresh or b > thresh:
            continue
        seen[i] = 1
        px[x, y] = (r, g, b, 0)
        stack.append((x + 1, y))
        stack.append((x - 1, y))
        stack.append((x, y + 1))
        stack.append((x, y - 1))
    return img


def bbox(img):
    return img.getbbox()


def fit_square(img, size):
    """裁成以内容中心为中心的正方形，再缩放到 size。"""
    bb = bbox(img)
    if bb is None:
        return img.resize((size, size), Image.LANCZOS)
    x0, y0, x1, y1 = bb
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    side = max(x1 - x0, y1 - y0)
    half = side // 2 + 2
    lx = max(0, cx - half)
    ly = max(0, cy - half)
    rx = min(img.size[0], cx + half)
    ry = min(img.size[1], cy + half)
    return img.crop((lx, ly, rx, ry)).resize((size, size), Image.LANCZOS)


def save(img, name):
    path = os.path.join(OUT, name)
    img.save(path, optimize=True)
    print("%-16s %5d bytes  %s" % (name, os.path.getsize(path), img.size))


def main():
    os.makedirs(OUT, exist_ok=True)

    # 背景：整幅保留，不抠 alpha，缩到 1024x640 并调色板压体积。
    bg = load_rgba("bg_land.png").convert("RGB").resize((1024, 640), Image.LANCZOS)
    bg = bg.quantize(colors=128, method=Image.MEDIANCUT)
    bg.save(os.path.join(OUT, "bg_land.png"), optimize=True)
    print("%-16s %5d bytes  %s" % ("bg_land.png",
          os.path.getsize(os.path.join(OUT, "bg_land.png")), bg.size))

    # 横轨：抠黑底 → 裁边成正方形 → 128（显示 64 的 2 倍）。
    track = flood_alpha(load_rgba("track_h.png"))
    track = fit_square(track, 128)
    save(track, "track_h.png")

    # 竖轨：横轨转 90°。
    save(track.rotate(90, expand=True), "track_v.png")

    # 分岔：横轨 + 竖轨的半截（北/南各一张）。
    for half, name in ((0, "switch_n.png"), (1, "switch_s.png")):
        vert = track.rotate(90, expand=True)
        piece = vert.crop((0, 64 * half, 128, 64 * half + 64))
        sw = Image.alpha_composite(track, Image.new("RGBA", (128, 128), (0, 0, 0, 0)))
        sw.alpha_composite(piece, (0, 64 * half))
        save(sw, name)

    # 机车 / 货箱 / 站台（方向精灵表由 client/tools/bake_facing.py 从
    # train.png / cargo.png 烘出来）。
    train = fit_square(flood_alpha(load_rgba("train.png")), 128)
    save(train, "train.png")
    cargo = fit_square(flood_alpha(load_rgba("cargo.png")), 64)
    save(cargo, "cargo.png")
    station = fit_square(flood_alpha(load_rgba("station.png")), 160)
    save(station, "station.png")

    total = 0
    for root, _, files in os.walk(OUT):
        for f in files:
            total += os.path.getsize(os.path.join(root, f))
    print("TOTAL assets bytes:", total)


if __name__ == "__main__":
    main()
