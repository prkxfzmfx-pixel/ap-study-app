# -*- coding: utf-8 -*-
"""構造保持パーサv2で、収録済み全問の問題文(text)をローカルキャッシュから機械的に再生成する。
既存の explanation・answer・choices など問題文以外のフィールドは変更しない（textと図フィールドのみ更新）。
インライン画像（数式・記号・小図）は [[img:...]] プレースホルダとして問題文中に保持し、
不足画像だけを厳守条件（2秒間隔・200のみ・キャッシュ）で追加取得する。再スクレイピング（HTML再取得）はしない。

usage: python tools/regen_text.py            # 全回を再生成
       python tools/regen_text.py r1a h31h   # 指定回のみ
"""
import io, os, re, sys, json, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('bd', os.path.join(ROOT, 'tools', 'build_from_dojo.py'))
bd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bd)


def load_js(path):
    js = io.open(path, encoding='utf-8').read()
    mm = re.search(r'AP_REGISTER\(\s*(\{.*?\})\s*,\s*(\[.*\])\s*\)\s*;', js, re.S)
    meta = json.loads(mm.group(1))
    qs = json.loads(mm.group(2))
    return meta, qs


def write_js(path, meta, qs, label):
    lines = [
        f'/* {label} 応用情報技術者試験 午前（収録{len(qs)}問）',
        ' * 問題文・選択肢・図表: IPA公開の過去問題（出典明記のうえ再利用）。解説はAI生成。',
        ' * 問題文は構造保持パーサv2で生成（改行・箇条書き・分数・インライン画像[[img:...]]を保持）。',
        ' */',
        'window.AP_REGISTER(',
        json.dumps(meta, ensure_ascii=False) + ',',
        json.dumps(qs, ensure_ascii=False, indent=1),
        ');',
    ]
    io.open(path, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')


def main():
    keys = sys.argv[1:]
    qdir = os.path.join(ROOT, 'questions')
    files = [f for f in os.listdir(qdir) if re.match(r'[rh]\d.*\.js$', f)]
    if keys:
        files = [f for f in files if f[:-3] in keys]
    changed_total = 0
    big_diffs = []
    choice_diffs = []
    missing_cache = []
    for f in sorted(files):
        key = f[:-3]
        meta, qs = load_js(os.path.join(qdir, f))
        ddir = bd.dojo_dir(key)
        nchanged = 0
        for q in qs:
            n = q['qnum']
            cache_path = os.path.join(ROOT, 'data', 'cache', ddir, f'q{n}.html')
            if not os.path.exists(cache_path):
                missing_cache.append(f'{key}-q{n}')
                continue
            html = bd.ol_repl(bd.decode(io.open(cache_path, 'rb').read()))
            mondai = bd.extract_div(html, 'id="mondai"')
            if mondai is None:
                continue
            newtext, imgs = bd.build_mondai(mondai, key, n, ddir, allow_net=True)
            if not newtext:
                continue
            # 選択肢も再抽出（分数などネストspanの切れを修正）。有効な4肢のときだけ更新。
            newch, img_choice = bd.extract_choices(html)
            if newch and not img_choice and all(newch.values()) and newch != q.get('choices'):
                q['choices'] = newch
                nchanged += 1
                choice_diffs.append(f'{key}-q{n}')
            old = q.get('text', '')
            if newtext != old:
                # 変化量（正規化して空白差だけの微差は無視）
                norm_old = re.sub(r'\s+', '', old)
                norm_new = re.sub(r'\s+', '', newtext)
                delta = abs(len(norm_new) - len(norm_old)) + (0 if norm_old == norm_new else 1)
                q['text'] = newtext
                nchanged += 1
                if norm_old != norm_new:
                    big_diffs.append((f'{key}-q{n}', len(norm_old), len(norm_new)))
            # 図フィールド更新
            q['hasImage'] = bool(imgs)
            if imgs:
                q['img'] = imgs[0]
            else:
                q.pop('img', None)
            q.pop('_multi_img', None)
        write_js(os.path.join(qdir, f), meta, qs, meta.get('label', key))
        changed_total += nchanged
        print(f'{key}: 問題文更新 {nchanged}問 / 全{len(qs)}問')
    print(f'\n=== 合計 {changed_total}箇所（問題文＋選択肢）を更新 ===')
    if choice_diffs:
        print(f'選択肢を修正した問題 {len(choice_diffs)}件:', choice_diffs)
    if missing_cache:
        print(f'キャッシュ無し {len(missing_cache)}問:', missing_cache[:10])
    # 内容が変わった（空白以外）問題を変化量順に
    big_diffs.sort(key=lambda x: abs(x[2] - x[1]), reverse=True)
    print(f'\n内容変化のある問題 {len(big_diffs)}件（変化量大きい順・上位25）:')
    for qid, o, nn in big_diffs[:25]:
        print(f'  {qid}: {o}字 -> {nn}字')


if __name__ == '__main__':
    main()
