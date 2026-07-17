# -*- coding: utf-8 -*-
"""exams.json に列挙した全回について、IPA公式「解答例」PDFをダウンロードし、
午前試験の 問番号→正解→分野 を抽出して data/answers.json を生成する。
正解データは必ずこのIPA公式解答例PDF由来とする（検証の基準）。

usage: python tools/build_answers.py
"""
import io, os, json, re, urllib.request, fitz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KANA = {'ア', 'イ', 'ウ', 'エ'}
CATMAP = {'Ｔ': 'T', 'Ｍ': 'M', 'Ｓ': 'S', 'T': 'T', 'M': 'M', 'S': 'S'}


def download(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as r, open(path, 'wb') as f:
        f.write(r.read())
    print(f'  downloaded {os.path.basename(path)}')


def parse_ans(pdf):
    doc = fitz.open(pdf)
    lines = []
    for pg in doc:
        for ln in pg.get_text('text').splitlines():
            s = ln.strip()
            if s:
                lines.append(s)
    ans, cat = {}, {}
    for i, ln in enumerate(lines):
        m = re.fullmatch(r'問\s*(\d+)', ln)
        if not m:
            continue
        qn = int(m.group(1))
        a = c = None
        for j in range(i + 1, min(i + 5, len(lines))):
            t = lines[j]
            if a is None and t in KANA:
                a = t
            elif a is not None and t in CATMAP:
                c = CATMAP[t]
                break
        if a:
            ans[qn] = a
            if c:
                cat[qn] = c
    return ans, cat


def main():
    cfg = json.load(io.open(os.path.join(ROOT, 'tools', 'exams.json'), encoding='utf-8'))
    out = {}
    for e in cfg['exams']:
        ans_pdf = os.path.join(ROOT, 'data', 'pdf', f'{e["key"]}_ans.pdf')
        print(f'{e["key"]} ({e["label"]}):')
        download(e['ans'], ans_pdf)
        ans, cat = parse_ans(ans_pdf)
        if len(ans) != 80:
            print(f'  SKIP: {len(ans)} answers parsed (期待80)。解答例PDFがテキスト非埋め込み等で抽出不可。除外する。')
            continue
        out[e['key']] = {'year': e['year'], 'term': e['term'], 'label': e['label'],
                         'count': len(ans),
                         'answers': {str(k): v for k, v in sorted(ans.items())},
                         'cats': {str(k): v for k, v in sorted(cat.items())}}
        print(f'  parsed {len(ans)} answers')
    with io.open(os.path.join(ROOT, 'data', 'answers.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('wrote data/answers.json')


if __name__ == '__main__':
    main()
