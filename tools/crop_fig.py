# -*- coding: utf-8 -*-
"""問題冊子PDFの1ページから図表領域を切り出してPNG保存する。
IPAの問題冊子は「1ページ＝1枚の画像」なので図の座標メタは無い。
ページ内の相対位置（0〜1の割合）で切り出す。data/img/<key>/pNN.png を見て割合を目測する。

usage:
  python tools/crop_fig.py <key> <page> <fx0> <fy0> <fx1> <fy1> <outname>
  例: python tools/crop_fig.py r7a 5 0.10 0.42 0.90 0.68 r7a-q5
      → questions/img/r7a-q5.png に保存（questions/<key>.js の "img" にこのパスを書く）

割合はページ左上が(0,0)、右下が(1,1)。fx=横, fy=縦。
"""
import sys, os, fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main():
    if len(sys.argv) < 8:
        print(main.__doc__ if False else 'usage: python tools/crop_fig.py <key> <page> <fx0> <fy0> <fx1> <fy1> <outname>')
        sys.exit(2)
    key = sys.argv[1]
    page = int(sys.argv[2])
    fx0, fy0, fx1, fy1 = [float(x) for x in sys.argv[3:7]]
    outname = sys.argv[7]
    pdf = os.path.join(ROOT, 'data', 'pdf', f'{key}_qs.pdf')
    doc = fitz.open(pdf)
    pg = doc[page - 1]
    r = pg.rect
    clip = fitz.Rect(r.x0 + fx0 * r.width, r.y0 + fy0 * r.height,
                     r.x0 + fx1 * r.width, r.y0 + fy1 * r.height)
    outdir = os.path.join(ROOT, 'questions', 'img')
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f'{outname}.png')
    pix = pg.get_pixmap(matrix=fitz.Matrix(3.0, 3.0), clip=clip, colorspace=fitz.csGRAY)
    pix.save(out)
    print(f'saved {os.path.relpath(out, ROOT)}  ({pix.width}x{pix.height})')
    print(f'  -> questions/{key}.js の該当問題に  "hasImage": true, "img": "questions/img/{outname}.png"  を書く')

if __name__ == '__main__':
    main()
