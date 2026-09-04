# -*- coding: utf-8 -*-
"""生成 icon.ico / icon.png。

图标来源：开源 Material Design Icons 的 push-pin (mdi/pin) 矢量图。
直接解析官方 SVG 的 <path> 路径数据（纯直线段），用 aggdraw 抗锯齿绘制成白色图钉，
合成到强调色圆形底，多尺寸 LANCZOS 输出（alpha 预乘），彻底无手绘锯齿/撕裂。
icon.png 为高清 master，运行时 HICON 也直接取它。
"""
import os
import re
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SIZES = [16, 24, 32, 48, 64, 128, 256]
ACCENT = 0x2E7CF6


def parse_svg_path_pts(d):
    """解析 SVG path 的 M/L/H/V/h/v/l/z 命令（本图标全为直线段），返回绝对坐标点列表。"""
    toks = re.findall(r'[MmLlHhVvZz]|-?\d*\.?\d+', d)
    pts = []
    cur = [0.0, 0.0]
    start = [0.0, 0.0]
    curcmd = None
    idx = 0
    n = len(toks)
    while idx < n:
        t = toks[idx]
        if t in 'MmLlHhVvZz':
            curcmd = t
            idx += 1
            continue
        if curcmd in 'Mm':
            x = float(toks[idx]); y = float(toks[idx + 1]); idx += 2
            if curcmd == 'm':
                x += cur[0]; y += cur[1]
            cur = [x, y]; start = [x, y]; pts.append((x, y))
            curcmd = 'l' if curcmd == 'm' else 'L'
        elif curcmd in 'Ll':
            x = float(toks[idx]); y = float(toks[idx + 1]); idx += 2
            if curcmd == 'l':
                x += cur[0]; y += cur[1]
            cur = [x, y]; pts.append((x, y))
        elif curcmd in 'Hh':
            x = float(toks[idx]); idx += 1
            if curcmd == 'h':
                x += cur[0]
            cur = [x, cur[1]]; pts.append((cur[0], cur[1]))
        elif curcmd in 'Vv':
            y = float(toks[idx]); idx += 1
            if curcmd == 'v':
                y += cur[1]
            cur = [cur[0], y]; pts.append((cur[0], cur[1]))
        elif curcmd in 'Zz':
            pts.append((start[0], start[1]))
    return pts


def get_pin_points():
    """从 pin.svg 读取官方图钉路径点（24x24 坐标系）。"""
    svg = os.path.join(HERE, "pin.svg")
    try:
        txt = open(svg, encoding="utf-8").read()
        m = re.search(r'd="([^"]+)"', txt)
        if m:
            return parse_svg_path_pts(m.group(1))
    except Exception as e:
        print("读取 pin.svg 失败:", e)
    return None


def build_master(size=1024, accent=ACCENT):
    aR, aG, aB = (accent >> 16) & 0xFF, (accent >> 8) & 0xFF, accent & 0xFF
    BG = (aR, aG, aB, 255)
    WHITE = (255, 255, 255, 255)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    try:
        import aggdraw
        d = aggdraw.Draw(img)
        r = size * 0.46
        d.ellipse([size/2 - r, size/2 - r, size/2 + r, size/2 + r], None, aggdraw.Brush(BG))
        d.ellipse([size/2 - r, size/2 - r, size/2 + r, size/2 + r],
                  aggdraw.Pen((255, 255, 255, 255), max(1.0, size / 140.0)), None)
        # 白色图钉（官方 mdi/pin 路径，抗锯齿多边形）
        pts = get_pin_points()
        if pts:
            scale = size * 0.60 / 24.0
            poly = []
            for (x, y) in pts:
                px = size/2 + (x - 12) * scale
                py = size/2 + (y - 12) * scale - size * 0.02
                poly.append(px)
                poly.append(py)
            d.polygon(poly, None, aggdraw.Brush(WHITE))
        d.flush()
    except Exception as e:
        from PIL import ImageDraw
        print("aggdraw 失败，回退:", e)
        dd = ImageDraw.Draw(img)
        dd.ellipse([size*0.04, size*0.04, size*0.96, size*0.96], fill=BG)
    return img


def pack_ico(images):
    """images: list of (size, rgba_topdown_bytes) -> .ico bytes（alpha 预乘）。"""
    out = bytearray()
    out += (0).to_bytes(2, "little")
    out += (1).to_bytes(2, "little")
    out += len(images).to_bytes(2, "little")
    entries = []
    data = []
    offset = 6 + 16 * len(images)
    for size, rgba in images:
        row_bytes = size * 4
        xor_len = row_bytes * size
        and_stride = ((size + 31) // 32) * 4
        and_len = and_stride * size
        total = 40 + xor_len + and_len
        entries.append((size, total, offset))
        offset += total
        data.append((size, rgba, row_bytes, and_stride))
    for size, total, off in entries:
        out += (size & 0xFF).to_bytes(1, "little")
        out += (0 if size == 256 else size).to_bytes(1, "little")
        out += (0).to_bytes(1, "little")
        out += (0).to_bytes(1, "little")
        out += (1).to_bytes(2, "little")
        out += (32).to_bytes(2, "little")
        out += total.to_bytes(4, "little")
        out += off.to_bytes(4, "little")
    for size, rgba, row_bytes, and_stride in data:
        hdr = bytearray()
        hdr += (40).to_bytes(4, "little")
        hdr += size.to_bytes(4, "little", signed=True)
        hdr += (size * 2).to_bytes(4, "little", signed=True)
        hdr += (1).to_bytes(2, "little")
        hdr += (32).to_bytes(2, "little")
        hdr += (0).to_bytes(4, "little")
        hdr += (0).to_bytes(4, "little")
        hdr += (0).to_bytes(4, "little")
        hdr += (0).to_bytes(4, "little")
        hdr += (0).to_bytes(4, "little")
        hdr += (0).to_bytes(4, "little")
        out += hdr
        row = bytearray(row_bytes)
        for y in range(size):
            src_y = size - 1 - y
            base = src_y * row_bytes
            for x in range(size):
                i = base + x * 4
                r, g, b, a = rgba[i], rgba[i+1], rgba[i+2], rgba[i+3]
                row[x*4]     = b * a // 255   # BGRA（Windows 位图要求 BGR 顺序）
                row[x*4 + 1] = g * a // 255
                row[x*4 + 2] = r * a // 255
                row[x*4 + 3] = a
            out += row
        and_scan = bytearray(and_stride)
        for y in range(size):
            src_y = size - 1 - y
            and_scan[:] = b"\x00" * and_stride
            for x in range(size):
                a = rgba[(src_y * size + x) * 4 + 3]
                if a < 128:
                    and_scan[x // 8] |= (1 << (7 - (x % 8)))
            out += and_scan
    return bytes(out)


def main():
    master = build_master(1024, ACCENT)
    master.save(os.path.join(HERE, "icon.png"))
    images = []
    for s in SIZES:
        rgba = master.resize((s, s), Image.LANCZOS).tobytes()
        images.append((s, rgba))
    ico = pack_ico(images)
    dest = os.path.join(HERE, "icon.ico")
    with open(dest, "wb") as f:
        f.write(ico)
    print("已生成:", dest, "%.2f KB" % (len(ico) / 1024.0), "尺寸", SIZES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
