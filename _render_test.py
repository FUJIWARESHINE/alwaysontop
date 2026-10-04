# -*- coding: utf-8 -*-
"""离屏渲染验证：把 UI 直接画到内存 DC 存 PNG，不依赖交互窗口站。"""
import ctypes
import os
import sys

sys.path.insert(0, r'D:\Project\alwaysontop')
os.chdir(r'D:\Project\alwaysontop')

import ontop as O
from aurora import BITMAPINFO, BITMAPINFOHEADER, gdi32, user32
from PIL import Image

W, H = 880, 660

FAKE = [
    (1001, 'Microsoft Edge — 工作台', 'msedge.exe', r'C:\Program Files\msedge.exe'),
    (1002, '置顶小工具', 'pythonw.exe', r'C:\Python\pythonw.exe'),
    (1003, '文件资源管理器', 'explorer.exe', r'C:\Windows\explorer.exe'),
    (1004, '网易云音乐', 'cloudmusic.exe', r'C:\Apps\cloudmusic.exe'),
    (1005, '终端', 'WindowsTerminal.exe', r'C:\Windows\System32\WT.exe'),
    (1006, 'Visual Studio Code', 'Code.exe', r'C:\Program Files\VSCode\Code.exe'),
]
PINNED = {1002, 1006}

mode = sys.argv[1] if len(sys.argv) > 1 else 'dark'
out = sys.argv[2] if len(sys.argv) > 2 else 'render.png'
hover = int(sys.argv[3]) if len(sys.argv) > 3 else 2
sel = int(sys.argv[4]) if len(sys.argv) > 4 else 0

app = O.App()
g = O.g
g['dark'] = (mode == 'dark')
app.ui.apply_theme()          # 必须在 dark 设定之后
g['font_cache'] = O.T.make_fonts(1.0)
g['scale'] = 1.0
g['hwnd_main'] = 0
g['himl'] = None
app.hwnd = 0
app.apply_caption_colors = lambda: None
g['rows'] = [(hw, t, e, p, hw in PINNED) for hw, t, e, p in FAKE]
g['sel'] = sel
g['hover_row'] = hover
g['hover'] = O.App.HIT_TOGGLE
g['autotray'] = True
g['autostart'] = True
g['hint'] = '已置顶：Microsoft Edge — 工作台'

app.ui.layout(W, H)

hdc_screen = user32.GetDC(None)
mdc = gdi32.CreateCompatibleDC(ctypes.c_void_p(hdc_screen))
bmi = BITMAPINFO()
h = bmi.bmiHeader
h.biSize = ctypes.sizeof(BITMAPINFOHEADER)
h.biWidth = W
h.biHeight = -H
h.biPlanes = 1
h.biBitCount = 32
h.biCompression = 0
bits = ctypes.c_void_p()
bmp = gdi32.CreateDIBSection(ctypes.c_void_p(hdc_screen), ctypes.byref(bmi), 0,
                             ctypes.byref(bits), None, 0)
gdi32.SelectObject(mdc, bmp)
app.ui.paint(mdc, W, H)
buf = ctypes.string_at(bits, W * H * 4)
Image.frombuffer('RGB', (W, H), buf, 'raw', 'BGRX', 0, 1).save(out)
print('rendered ->', out, (W, H), 'rows=', len(g['rows']))
