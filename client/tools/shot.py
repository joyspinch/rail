#!/usr/bin/env python3
"""shot.py — 抓 RAIL 运行窗口像素（可发按键 / 可连拍）。

比 zan-lang/scripts/shot_window.py 多三件事：
  * 支持环境变量（RAIL_DEMO / RAIL_FACE / RAIL_SETTINGS / RAIL_TIME …），
    用来摆出验收要截的那些画面；
  * 支持给窗口发按键（--keys "ESC"），用来验证"Esc 真的能弹出设置浮层"
    —— 环境变量直接开浮层只能证明浮层能画，发真按键才能证明接线；
  * 支持连拍（--burst N --interval S），抓短促的画面反馈（红闪、蒸汽）。

按键用两条路都发一遍：PostMessage 直接投递 WM_KEYDOWN（不依赖前台焦点，
最可靠）+ WScript 的 AppActivate/SendKeys（贴近真人按键）。两者都发，
命中哪个算哪个。

用法：
    python client/tools/shot.py <exe> <out.png> [--wait 2.0] [--keys ESC]
                                 [--env K=V]... [--burst N --interval S]
                                 [--key-delay 2.0] [--click x,y]
"""

import argparse
import ctypes
from ctypes import wintypes
import os
import subprocess
import sys
import time

from PIL import Image

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))

SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0

KEYS = {
    "ESC": 0x1B,
    "A": 0x41,
    "D": 0x44,
    "ENTER": 0x0D,
    "SPACE": 0x20,
}


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def find_window(pid):
    """找 pid 拥有的第一个可见顶层窗口（0 = 没找到）。"""
    found = []
    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def visit(hwnd, _):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(callback(visit), 0)
    return found[0] if found else 0


def capture(hwnd, path):
    """抓客户区像素存 PNG，返回 (宽, 高)。"""
    rect = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    w, h = rect.right - rect.left, rect.bottom - rect.top
    window_dc = user32.GetDC(hwnd)
    mem_dc = gdi32.CreateCompatibleDC(window_dc)
    bmp = gdi32.CreateCompatibleBitmap(window_dc, w, h)
    gdi32.SelectObject(mem_dc, bmp)
    gdi32.BitBlt(mem_dc, 0, 0, w, h, window_dc, 0, 0, SRCCOPY)

    info = BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    info.bmiHeader.biWidth = w
    info.bmiHeader.biHeight = -h
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mem_dc, bmp, 0, h, buf, ctypes.byref(info), DIB_RGB_COLORS)
    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")
    img.save(path)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, window_dc)
    return img.size


def post_key(hwnd, vk):
    """直接给窗口投递按键消息（不依赖前台焦点）。

    Win32Shell 的窗口过程把 WM_KEYDOWN 转成 kind=4 的事件，PostMessage
    走的是同一条路；前台锁再紧也拦不住。
    """
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0)
    time.sleep(0.06)
    user32.PostMessageW(hwnd, WM_KEYUP, vk, 0)
    time.sleep(0.3)


def focus(hwnd, pid):
    """把窗口拉到前台并确认（SendKeys 发给前台窗口，没聚焦就是白按）。"""
    script = ("$ws = New-Object -ComObject WScript.Shell; "
              "$null = $ws.AppActivate(%d)" % pid)
    subprocess.run(["powershell", "-NoProfile", "-Command", script],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(30):
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.08)
        if user32.GetForegroundWindow() == hwnd:
            return True
    return False


def send_key(hwnd, vk, pid, activate_ms=700):
    """给窗口发按键：PostMessage + AppActivate/SendKeys 两条路都发。"""
    name = {0x1B: "{ESC}", 0x41: "a", 0x44: "d", 0x0D: "{ENTER}",
            0x20: " "}.get(vk, "{ESC}")
    post_key(hwnd, vk)
    script = ("$ws = New-Object -ComObject WScript.Shell; "
              "$null = $ws.AppActivate(%d); Start-Sleep -Milliseconds %d; "
              "$ws.SendKeys('%s')" % (pid, activate_ms, name))
    subprocess.run(["powershell", "-NoProfile", "-Command", script],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.4)


def click_at(hwnd, pid, x, y):
    """在窗口**客户区** (x, y) 处点一下鼠标（客户区坐标 → 屏幕坐标）。"""
    if not focus(hwnd, pid):
        print("WARN: 窗口没能拿到前台焦点")
    time.sleep(0.2)
    pt = wintypes.POINT(x, y)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    user32.SetCursorPos(pt.x, pt.y)
    time.sleep(0.25)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.08)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe")
    ap.add_argument("out")
    ap.add_argument("--wait", type=float, default=2.0)
    ap.add_argument("--keys", default="")
    ap.add_argument("--env", action="append", default=[])
    ap.add_argument("--burst", type=int, default=0)
    ap.add_argument("--interval", type=float, default=0.25)
    ap.add_argument("--post-wait", type=float, default=0.0)
    ap.add_argument("--key-delay", type=float, default=0.0)
    ap.add_argument("--click", default="")
    args = ap.parse_args()

    env = dict(os.environ)
    for kv in args.env:
        k, _, v = kv.partition("=")
        env[k] = v

    proc = subprocess.Popen([args.exe], cwd=os.path.dirname(args.exe),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            env=env)
    try:
        deadline = time.monotonic() + 10
        hwnd = 0
        while not hwnd and time.monotonic() < deadline:
            hwnd = find_window(proc.pid)
            time.sleep(0.05)
        if not hwnd:
            print("NO WINDOW for pid", proc.pid)
            return 1
        time.sleep(args.wait)
        keys = [x for x in args.keys.split(",") if x.strip()]
        if args.burst > 0 and keys:
            # 连拍时：按键放到后台线程，主线程从头连拍，保证不漏帧。
            import threading

            def press():
                time.sleep(0.1)
                for k in keys:
                    send_key(hwnd, KEYS[k.strip().upper()], proc.pid)
                    if args.key_delay:
                        time.sleep(args.key_delay)

            th = threading.Thread(target=press)
            th.daemon = True
            th.start()
            base, ext = os.path.splitext(args.out)
            for i in range(args.burst):
                p = "%s_%03d%s" % (base, i, ext)
                capture(hwnd, p)
                time.sleep(args.interval)
            th.join(timeout=5)
            print("burst", args.burst, "frames ->", base + "_NNN" + ext)
            return 0
        for k in keys:
            send_key(hwnd, KEYS[k.strip().upper()], proc.pid)
            if args.key_delay:
                time.sleep(args.key_delay)
        if args.post_wait:
            time.sleep(args.post_wait)
        if args.click:
            cx, cy = args.click.split(",")
            click_at(hwnd, proc.pid, int(cx), int(cy))
        if args.burst > 0:
            base, ext = os.path.splitext(args.out)
            for i in range(args.burst):
                p = "%s_%03d%s" % (base, i, ext)
                capture(hwnd, p)
                time.sleep(args.interval)
            print("burst", args.burst, "frames ->", base + "_NNN" + ext)
        else:
            time.sleep(0.6)
            size = capture(hwnd, args.out)
            print("captured", size[0], "x", size[1], "->", args.out)
    finally:
        proc.kill()
        proc.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
