# -*- coding: utf-8 -*-
"""
生成 app.ico —— 用与运行时相同的 GDI 绘制逻辑，输出多尺寸标准 ICO，
供 PyInstaller --icon 嵌入 exe，让 exe 文件在资源管理器/任务栏也显示图标。

用法：  python gen_icon.py          # 输出到 置顶小工具/icon.ico
"""
import os
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "ontop", os.path.join(HERE, "ontop.py"))
ONT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ONT)

# 系统强调色（与运行时一致），读不到就用默认蓝
accent = ONT.get_accent() if hasattr(ONT, "get_accent") else 0x0078D4
SIZES = [16, 24, 32, 48, 64, 128, 256]


def pack_ico(images):
    """images: list of (size, rgba_topdown_bytes) -> .ico bytes."""
    out = bytearray()
    out += (0).to_bytes(2, "little")          # reserved
    out += (1).to_bytes(2, "little")          # type: icon
    out += len(images).to_bytes(2, "little")  # count

    entries = []
    data = []
    offset = 6 + 16 * len(images)
    for size, rgba in images:
        # 每像素4字节 XOR(bottom-up) + 1bpp AND mask(bottom-up)
        row_bytes = size * 4
        xor_len = row_bytes * size
        and_stride = ((size + 31) // 32) * 4
        and_len = and_stride * size
        total = 40 + xor_len + and_len  # BITMAPINFOHEADER + xor + and

        entries.append((size, total, offset))
        offset += total
        data.append((size, rgba, xor_len, and_stride, and_len))

    # ICONDIRENTRY (16 bytes each)
    for size, total, off in entries:
        out += (size & 0xFF).to_bytes(1, "little")
        out += (0 if size == 256 else size).to_bytes(1, "little")  # height(0=256)
        out += (0).to_bytes(1, "little")          # color count
        out += (0).to_bytes(1, "little")          # reserved
        out += (1).to_bytes(2, "little")          # planes
        out += (32).to_bytes(2, "little")         # bit count
        out += total.to_bytes(4, "little")
        out += off.to_bytes(4, "little")

    # Data
    for size, rgba, xor_len, and_stride, and_len in data:
        # BITMAPINFOHEADER (biHeight = 2*size 表示 XOR+AND)
        hdr = bytearray()
        hdr += (40).to_bytes(4, "little")         # biSize
        hdr += size.to_bytes(4, "little", signed=True)       # biWidth
        hdr += (size * 2).to_bytes(4, "little", signed=True)  # biHeight
        hdr += (1).to_bytes(2, "little")          # biPlanes
        hdr += (32).to_bytes(2, "little")         # biBitCount
        hdr += (0).to_bytes(4, "little")          # biCompression
        hdr += (0).to_bytes(4, "little")          # biSizeImage
        hdr += (0).to_bytes(4, "little")          # biXPels
        hdr += (0).to_bytes(4, "little")          # biYPels
        hdr += (0).to_bytes(4, "little")          # biClrUsed
        hdr += (0).to_bytes(4, "little")          # biClrImportant
        out += hdr

        # XOR 数据：ICO 用 bottom-up（行0 = 图像最底行），故将 top-down 反转
        row = bytearray(size * 4)
        for y in range(size):
            src_y = size - 1 - y                 # bottom-up 行号 -> top-down 源行
            src = rgba[src_y * row_bytes: src_y * row_bytes + row_bytes]
            row[:] = src
            out += row

        # AND mask：alpha<128 视为透明 → bit=1；top-down 行反转成 bottom-up
        and_scan = bytearray(and_stride)
        for y in range(size):                     # bottom-up 输出行
            src_y = size - 1 - y                  # top-down 源行
            and_scan[:] = b"\x00" * and_stride
            for x in range(size):
                a = rgba[(src_y * size + x) * 4 + 3]
                if a < 128:
                    byte_i = x // 8
                    bit = 7 - (x % 8)
                    and_scan[byte_i] |= (1 << bit)
            out += and_scan

    return bytes(out)


def main():
    images = []
    for s in SIZES:
        rgba = ONT.draw_icon_rgba(s, accent)
        if rgba is None:
            print("绘制失败 size", s)
            return 1
        images.append((s, rgba))
    ico = pack_ico(images)
    dest = os.path.join(HERE, "icon.ico")
    with open(dest, "wb") as f:
        f.write(ico)
    print("已生成:", dest, "%.2f KB" % (len(ico) / 1024.0), "尺寸", SIZES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
