# -*- coding: utf-8 -*-
"""gen_icon.py —— 生成 icon.ico / icon.png

图标由 appicon.py 纯代码绘制（圆角方块 + 靛蓝→紫渐变 + 白色图钉），
不依赖 Pillow，改一处即可让 exe 图标、任务栏图标、托盘图标与界面 logo 保持一致。

用法：python gen_icon.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import appicon

HERE = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    ico = appicon.save_ico(os.path.join(HERE, "icon.ico"))
    png = appicon.save_png(os.path.join(HERE, "icon.png"), 256)
    for p in (ico, png):
        print("生成 %s (%d bytes)" % (p, os.path.getsize(p)))
