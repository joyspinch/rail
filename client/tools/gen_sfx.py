"""合成 RAIL 的音效 WAV（22050Hz / 16bit / 单声道）。

不走图像 API：音效是纯波形，直接用 numpy 合成，省时间也省配额。
输出：client/assets/sfx/<name>.wav

用法：python client/tools/gen_sfx.py
"""
import os
import wave

import numpy as np

RATE = 22050
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "client", "assets", "sfx")


def env(n, attack=0.01, release=0.25):
    """线性起音 + 指数衰减的包络。"""
    a = max(1, int(n * attack))
    r = max(1, int(n * release))
    e = np.ones(n, dtype=np.float64)
    e[:a] = np.linspace(0.0, 1.0, a)
    e[a:] = np.exp(-np.linspace(0, 6.0, n - a))
    if r < n:
        e[-r:] *= np.linspace(1.0, 0.0, r)
    return e


def tone(freq, dur, kind="sine", detune=0.0):
    n = int(RATE * dur)
    t = np.arange(n) / RATE
    if kind == "sine":
        w = np.sin(2 * np.pi * freq * t)
    elif kind == "square":
        w = np.sign(np.sin(2 * np.pi * freq * t))
    elif kind == "tri":
        w = 2.0 * np.abs(2.0 * (freq * t - np.floor(freq * t + 0.5))) - 1.0
    else:  # saw
        w = 2.0 * (freq * t - np.floor(freq * t))
    if detune:
        w = 0.6 * w + 0.4 * np.sin(2 * np.pi * (freq * (1.0 + detune)) * t)
    return w


def seq(notes, dur_each, kind="sine", gap=0.0):
    """notes: [(freq, dur_scale), ...] 依次拼接。"""
    out = []
    for freq, scale in notes:
        d = dur_each * scale
        w = tone(freq, d, kind) * env(int(RATE * d))
        out.append(w)
        if gap:
            out.append(np.zeros(int(RATE * gap)))
    return np.concatenate(out) if out else np.zeros(1)


def noise(dur, lp=0.35):
    rng = np.random.default_rng(20261021)
    n = int(RATE * dur)
    w = rng.standard_normal(n)
    # 一阶低通把白噪声揉成"闷响"
    out = np.empty(n)
    prev = 0.0
    for i in range(n):
        prev = prev + lp * (w[i] - prev)
        out[i] = prev
    return out


def save(name, data, gain=0.55):
    data = np.clip(data * gain, -1.0, 1.0)
    pcm = (data * 32767.0).astype("<i2")
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())
    print("%-10s %6d bytes" % (name, os.path.getsize(path)))


def main():
    os.makedirs(OUT, exist_ok=True)

    # 汽笛：两声叠加的长鸣，缓慢起音。
    n = int(RATE * 0.55)
    t = np.arange(n) / RATE
    whistle = (0.6 * np.sin(2 * np.pi * 523 * t)
               + 0.4 * np.sin(2 * np.pi * 784 * t)) * env(n, attack=0.12, release=0.30)
    save("whistle", whistle, 0.45)

    # 选择：短促咔哒。
    n = int(RATE * 0.09)
    click = tone(1180, 0.09, "square") * env(n, attack=0.005, release=0.6)
    save("select", click, 0.35)

    # 送达：上行三音（明亮铃）。
    save("deliver", seq([(659, 1.0), (880, 1.0), (1319, 1.4)], 0.10), 0.5)

    # 错误站台：下行闷响（方波）。
    save("error", seq([(233, 1.0), (175, 1.6)], 0.16, "square"), 0.4)

    # 撞击：噪声爆 + 低频闷锤。
    n = int(RATE * 0.45)
    crash = noise(0.45) * np.exp(-np.linspace(0, 5, n)) * 0.9
    crash += tone(70, 0.45, "sine") * env(n, attack=0.002, release=0.9) * 0.8
    save("crash", crash, 0.6)

    # 关卡完成：四音上行号角。
    save("levelup", seq([(523, 1.0), (659, 1.0), (784, 1.0), (1047, 1.8)], 0.13), 0.5)

    # 全通关：更长号的号角 + 尾音。
    win = seq([(523, 1.0), (659, 1.0), (784, 1.0), (1047, 1.5),
               (880, 1.0), (1047, 2.4)], 0.14)
    save("win", win, 0.5)

    # 失败：下行小调。
    save("fail", seq([(440, 1.0), (370, 1.0), (294, 2.2)], 0.17, "tri"), 0.45)

    print("SFX_DONE")


if __name__ == "__main__":
    main()
