# -*- coding: utf-8 -*-
"""問題冊子PDF(画像のみ)を1ページ1PNGにレンダリングする。
目視で問題文・選択肢を書き起こすための素材。
usage: python tools/render_pages.py data/pdf/r6a_qs.pdf data/img/r6a  [zoom]
"""
import sys, os, fitz

pdf = sys.argv[1]
outdir = sys.argv[2]
zoom = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
os.makedirs(outdir, exist_ok=True)
doc = fitz.open(pdf)
mat = fitz.Matrix(zoom, zoom)
for i, pg in enumerate(doc):
    pix = pg.get_pixmap(matrix=mat, colorspace=fitz.csGRAY)
    pix.save(os.path.join(outdir, f"p{i+1:02d}.png"))
print(f"rendered {len(doc)} pages to {outdir} at zoom {zoom}")
