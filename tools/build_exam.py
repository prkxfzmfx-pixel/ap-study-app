# -*- coding: utf-8 -*-
"""1つの回を追加するためのワンコマンド・パイプライン。

  python tools/build_exam.py <key>

  例: python tools/build_exam.py r6h

処理:
  1. exams.json から <key> の問題冊子(qs)・解答例(ans)PDF URLを引く
  2. 両PDFをダウンロード（data/pdf/<key>_qs.pdf, _ans.pdf）
  3. 解答例PDFから正解を抽出し、data/answers.json を再生成（全回, build_answers.py）
  4. 問題冊子PDFの全ページをPNG化（data/img/<key>/pNN.png）… 目視で書き起こす素材

  ※ IPAの「問題冊子」PDFは全ページ画像（テキスト非埋め込み）のため、
    設問文・選択肢はOCR/自動抽出できない。ページ画像を見て
    questions/<key>.js に AP_REGISTER(...) 形式で書き起こす（手作業）。
    書き起こし後は必ず `python tools/verify.py` で正解の公式一致を検証すること。
"""
import io, os, sys, json, subprocess, urllib.request, fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def download(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        print(f'  (exists) {os.path.basename(path)}')
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=90) as r, open(path, 'wb') as f:
        f.write(r.read())
    print(f'  downloaded {os.path.basename(path)} ({os.path.getsize(path)} bytes)')


def render(pdf, outdir, zoom=2.0):
    os.makedirs(outdir, exist_ok=True)
    doc = fitz.open(pdf)
    mat = fitz.Matrix(zoom, zoom)
    for i, pg in enumerate(doc):
        pg.get_pixmap(matrix=mat, colorspace=fitz.csGRAY).save(os.path.join(outdir, f'p{i+1:02d}.png'))
    print(f'  rendered {len(doc)} pages -> {os.path.relpath(outdir, ROOT)}')


def main():
    if len(sys.argv) < 2:
        print('usage: python tools/build_exam.py <key>   (例: r6h)')
        sys.exit(2)
    key = sys.argv[1]
    cfg = json.load(io.open(os.path.join(ROOT, 'tools', 'exams.json'), encoding='utf-8'))
    e = next((x for x in cfg['exams'] if x['key'] == key), None)
    if not e:
        print(f'exams.json に key={key} がありません。まず exams.json に追記してください。')
        sys.exit(1)
    print(f'== {e["label"]} ({key}) ==')
    print('1) PDFダウンロード')
    download(e['qs'], os.path.join(ROOT, 'data', 'pdf', f'{key}_qs.pdf'))
    download(e['ans'], os.path.join(ROOT, 'data', 'pdf', f'{key}_ans.pdf'))
    print('2) 解答抽出＋answers.json再生成')
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'build_answers.py')], check=True)
    print('3) 問題ページを画像化')
    render(os.path.join(ROOT, 'data', 'pdf', f'{key}_qs.pdf'), os.path.join(ROOT, 'data', 'img', key))
    print('\n次の手順:')
    print(f'  - data/img/{key}/pNN.png を見て図表なしの問題を questions/{key}.js に書き起こす')
    print(f'    （AP_REGISTER(meta, questions) 形式。正解は data/answers.json の値をそのまま使う）')
    print(f'  - questions/manifest.js の exams に {key} を追加')
    print(f'  - index.html / sw.js の必要箇所とテストを更新')
    print(f'  - python tools/verify.py で公式解答との一致を検証（NGが出たら直す）')


if __name__ == '__main__':
    main()
