# -*- coding: utf-8 -*-
"""appicon.py —— 应用图标生成（纯 Python + GDI，不依赖 Pillow）

图标设计对齐新 UI：圆角方块 + 靛蓝→紫的 135° 渐变，中间一枚白色图钉。

之所以自己画而不依赖外部图片：托盘图标一旦拿不到 HICON 就完全不显示，
这里保证任何环境都能生成有效图标。
超采样 4 倍再降采样，得到平滑边缘。
"""
import ctypes
import ctypes.wintypes as wt
import math
import struct
import zlib

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)


class ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wt.BOOL), ("xHotspot", wt.DWORD),
                ("yHotspot", wt.DWORD), ("hbmMask", wt.HANDLE),
                ("hbmColor", wt.HANDLE)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wt.DWORD), ("biWidth", wt.LONG), ("biHeight", wt.LONG),
                ("biPlanes", wt.WORD), ("biBitCount", wt.WORD),
                ("biCompression", wt.DWORD), ("biSizeImage", wt.DWORD),
                ("biXPelsPerMeter", wt.LONG), ("biYPelsPerMeter", wt.LONG),
                ("biClrUsed", wt.DWORD), ("biClrImportant", wt.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3)]


user32.GetDC.argtypes = [wt.HWND]
user32.GetDC.restype = ctypes.c_void_p
user32.ReleaseDC.argtypes = [wt.HWND, ctypes.c_void_p]
gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
gdi32.CreateCompatibleDC.restype = ctypes.c_void_p
gdi32.CreateDIBSection.argtypes = [ctypes.c_void_p, ctypes.POINTER(BITMAPINFO),
                                   wt.UINT, ctypes.POINTER(ctypes.c_void_p),
                                   wt.HANDLE, wt.DWORD]
gdi32.CreateDIBSection.restype = wt.HANDLE
gdi32.SelectObject.argtypes = [ctypes.c_void_p, wt.HANDLE]
gdi32.SelectObject.restype = wt.HANDLE
gdi32.DeleteObject.argtypes = [wt.HANDLE]
gdi32.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, wt.UINT, wt.UINT,
                               ctypes.c_void_p]
gdi32.CreateBitmap.restype = wt.HANDLE
user32.CreateIconIndirect.argtypes = [ctypes.POINTER(ICONINFO)]
user32.CreateIconIndirect.restype = wt.HANDLE

# 品牌渐变色（与 theme 保持一致）
C1 = (0x63, 0x66, 0xF1)     # 靛蓝
C2 = (0x8B, 0x5C, 0xF6)     # 紫


def _rrect_sdf(x, y, half, r):
    """点到圆角矩形边界的有符号距离（<0 在内部）。"""
    qx = abs(x) - (half - r)
    qy = abs(y) - (half - r)
    ax = qx if qx > 0 else 0.0
    ay = qy if qy > 0 else 0.0
    return math.hypot(ax, ay) + min(max(qx, qy), 0.0) - r


def _pin_inside(x, y):
    """白色图钉形状（归一化坐标 0..1）。"""
    # 钉头
    if math.hypot(x - 0.5, y - 0.395) <= 0.150:
        return True
    # 钉身（倒三角）
    if 0.495 <= y <= 0.735:
        t = (y - 0.495) / 0.240
        if abs(x - 0.5) <= 0.112 * (1.0 - t):
            return True
    # 底座横线
    if 0.775 <= y <= 0.815 and 0.275 <= x <= 0.725:
        return True
    return False


def rgba(px=32, ss=4):
    """生成 RGBA 图标像素（top-down）。"""
    n = px * ss
    # 先在 n×n 上超采样，再盒式降采样到 px×px
    acc = [[[0, 0, 0, 0] for _ in range(px)] for _ in range(px)]
    half = 0.5
    corner = 0.235          # 圆角半径（相对边长）
    for sy in range(n):
        fy = (sy + 0.5) / n
        cy = fy - 0.5
        ty = (sy // ss)
        row = acc[ty]
        for sx in range(n):
            fx = (sx + 0.5) / n
            cx = fx - 0.5
            # 圆角方块外 → 透明
            if _rrect_sdf(cx, cy, half, corner) > 0.0:
                continue
            if _pin_inside(fx, fy):
                r, g, b, a = 255, 255, 255, 255
            else:
                t = (fx + fy) * 0.5
                r = int(C1[0] + (C2[0] - C1[0]) * t)
                g = int(C1[1] + (C2[1] - C1[1]) * t)
                b = int(C1[2] + (C2[2] - C1[2]) * t)
                a = 255
            cel = row[sx // ss]
            cel[0] += r
            cel[1] += g
            cel[2] += b
            cel[3] += a
    k = ss * ss
    out = bytearray(px * px * 4)
    i = 0
    for y in range(px):
        for x in range(px):
            c = acc[y][x]
            out[i] = c[0] // k
            out[i + 1] = c[1] // k
            out[i + 2] = c[2] // k
            out[i + 3] = c[3] // k
            i += 4
    return bytes(out)


def bgra_premul(px=32):
    """HICON 需要的 top-down 预乘 BGRA。"""
    src = rgba(px)
    n = px * px
    out = bytearray(n * 4)
    for i in range(n):
        r = src[i * 4]
        g = src[i * 4 + 1]
        b = src[i * 4 + 2]
        a = src[i * 4 + 3]
        out[i * 4] = b * a // 255
        out[i * 4 + 1] = g * a // 255
        out[i * 4 + 2] = r * a // 255
        out[i * 4 + 3] = a
    return bytes(out)


def hicon(px=32):
    """生成 HICON（托盘 / 窗口 / 任务栏通用）。"""
    data = bgra_premul(px)
    hdc_screen = user32.GetDC(None)
    mdc = gdi32.CreateCompatibleDC(ctypes.c_void_p(hdc_screen))
    bmi = BITMAPINFO()
    head = bmi.bmiHeader
    head.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    head.biWidth = px
    head.biHeight = -px
    head.biPlanes = 1
    head.biBitCount = 32
    head.biCompression = 0
    bits = ctypes.c_void_p()
    hbm = gdi32.CreateDIBSection(ctypes.c_void_p(mdc), ctypes.byref(bmi), 0,
                                 ctypes.byref(bits), None, 0)
    user32.ReleaseDC(None, hdc_screen)
    gdi32.DeleteDC(ctypes.c_void_p(mdc))
    if not hbm:
        return None
    ctypes.memmove(bits, data, len(data))
    mask = gdi32.CreateBitmap(px, px, 1, 1, None)
    ii = ICONINFO()
    ii.fIcon = True
    ii.hbmMask = mask
    ii.hbmColor = hbm
    hi = user32.CreateIconIndirect(ctypes.byref(ii))
    gdi32.DeleteObject(mask)
    gdi32.DeleteObject(hbm)
    return hi


def png_bytes(px=256):
    """生成 PNG 字节（zlib 是标准库，无需 Pillow）。"""
    src = rgba(px)
    raw = bytearray()
    for y in range(px):
        raw.append(0)                                # filter type 0
        raw += src[y * px * 4:(y + 1) * px * 4]

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", px, px, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
            chunk(b"IEND", b""))


def save_png(path, px=256):
    with open(path, "wb") as f:
        f.write(png_bytes(px))
    return path


def write_png(path, w, h, bgra):
    """把 BGRA 像素写成 PNG（任意尺寸，用于自截验证）。"""
    raw = bytearray()
    for y in range(h):
        raw.append(0)                            # filter 0
        row = bgra[y * w * 4:(y + 1) * w * 4]
        # BGRA -> RGBA
        raw += bytes(b for i in range(0, len(row), 4)
                     for b in (row[i + 2], row[i + 1], row[i], 255))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
                chunk(b"IDAT", zlib.compress(bytes(raw), 6)) +
                chunk(b"IEND", b""))
    return path


def save_ico(path, sizes=(16, 20, 24, 32, 40, 48, 64, 128, 256)):
    """写出多尺寸 .ico（BMP 条目，含 AND 掩码）。"""
    entries = []
    images = []
    for px in sizes:
        src = rgba(px)
        # XOR 位图：BGRA，自下而上
        xor = bytearray()
        for y in range(px - 1, -1, -1):
            for x in range(px):
                i = (y * px + x) * 4
                r, g, b, a = src[i], src[i + 1], src[i + 2], src[i + 3]
                xor += bytes((b, g, r, a))
        # AND 掩码：1bpp，行按 4 字节对齐；32bpp 图标下可全 0
        row = ((px + 31) // 32) * 4
        mask = bytes(row * px)
        bih = BITMAPINFOHEADER()
        bih.biSize = 40
        bih.biWidth = px
        bih.biHeight = px * 2          # XOR + AND
        bih.biPlanes = 1
        bih.biBitCount = 32
        bih.biCompression = 0
        bih.biSizeImage = len(xor) + len(mask)
        hdr = struct.pack("<IiiHHIIiiII", bih.biSize, bih.biWidth,
                          bih.biHeight, bih.biPlanes, bih.biBitCount,
                          bih.biCompression, bih.biSizeImage, 0, 0, 0, 0)
        images.append(hdr + bytes(xor) + mask)

    offset = 6 + 16 * len(sizes)
    for px, img in zip(sizes, images):
        w = 0 if px >= 256 else px
        h = 0 if px >= 256 else px
        entries.append(struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32,
                                   len(img), offset))
        offset += len(img)

    with open(path, "wb") as f:
        f.write(struct.pack("<HHH", 0, 1, len(sizes)))
        for e in entries:
            f.write(e)
        for img in images:
            f.write(img)
    return path
