# -*- coding: utf-8 -*-
"""SVGからPWAアイコン(PNG)を生成する。pymupdfでレンダリング。"""
import os, fitz

SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="112" fill="#6d5ef0"/>
  <rect x="88" y="96" width="336" height="248" rx="24" fill="#ffffff" opacity="0.14"/>
  <text x="256" y="300" font-family="Helvetica,Arial,sans-serif" font-size="220" font-weight="bold"
        fill="#ffffff" text-anchor="middle">AP</text>
  <rect x="150" y="372" width="212" height="26" rx="13" fill="#ffffff" opacity="0.30"/>
  <rect x="150" y="372" width="132" height="26" rx="13" fill="#ffffff"/>
</svg>'''

os.makedirs("icons", exist_ok=True)
targets = [("icons/icon-512.png", 512), ("icons/icon-192.png", 192), ("icons/apple-touch-icon.png", 180)]
for path, size in targets:
    doc = fitz.open(stream=SVG.encode("utf-8"), filetype="svg")
    page = doc[0]
    zoom = size / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    pix.save(path)
    print(f"{path}: {size}x{size} ({os.path.getsize(path)} bytes)")
