# -*- coding: utf-8 -*-
"""「選択肢自体が図」の問題（per-choice画像／合成1枚画像）を収録する専用パイプライン。

build_from_dojo.py が見送っていた画像選択肢問題だけを対象に、選択肢画像を
questions/img/ に取得し、questions/<key>.js へ新規問として追記する。

- 正解は data/answers.json（IPA解答例）。text は #mondai から構造保持で生成（図は[[img:]]）。
- per-choice: 各 <span id="select_x"> 内の画像 → q.choiceImages={ア:..,イ:..,ウ:..,エ:..}
- 合成1枚: 選択肢が単一画像＋ア〜エボタン → q.choicesImage=1枚（分割はせず全体表示）
- choices は {ア:'',..} の4キー空文字（verify/appの4肢前提を満たす）。explanation は '' で後続。
- 厳守条件: bd.fetch を用い 2.2s間隔・逐次・HTTP200以外は即中止・キャッシュ再利用。再実行で続きから。

usage: python tools/build_choice_images.py            # 全回
       python tools/build_choice_images.py r5h h29a   # 指定回のみ
       python tools/build_choice_images.py --dry ...   # 取得せずキャッシュ済みのみ
"""
import io, os, re, sys, json, importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('bd', os.path.join(ROOT, 'tools', 'build_from_dojo.py'))
bd = importlib.util.module_from_spec(spec); spec.loader.exec_module(bd)

IMG_RE = re.compile(r'<img[^>]*\ssrc="([^"]+\.(?:png|gif|jpg|jpeg))"', re.I)
SFX = (('a', 'ア'), ('i', 'イ'), ('u', 'ウ'), ('e', 'エ'))


def per_choice_srcs(html_ol):
    """各選択肢spanが画像のとき {カナ: src} を返す。1つでも画像でなければ None。"""
    out = {}
    for sfx, kana in SFX:
        inner = bd.extract_span(html_ol, f'id="select_{sfx}"')
        if inner is None:
            return None
        m = IMG_RE.search(inner)
        if not m:
            return None
        out[kana] = m.group(1)
    return out


def composite_src(html_ol):
    """選択肢が単一の合成画像（select_xspan無し）のとき、その画像srcを返す。無ければNone。"""
    i = html_ol.find('class="ansbg"')
    if i < 0:
        i = html_ol.find('selectList')
    if i < 0:
        return None
    reg = html_ol[i:i + 2000]
    m = IMG_RE.search(reg)
    return m.group(1) if m else None


def dl(src, ddir, key, n, tag, allow_net):
    """選択肢画像を questions/img/<key>-q<n>-<tag>.<ext> に保存。相対パスを返す（失敗時None）。"""
    ext = os.path.splitext(src)[1].lower()
    target_rel = f'questions/img/{key}-q{n}-{tag}{ext}'
    ok = bd.download_img(src, ddir, target_rel, allow_net)
    return target_rel if ok else None


def load_js(path):
    js = io.open(path, encoding='utf-8').read()
    mm = re.search(r'AP_REGISTER\(\s*(\{.*?\})\s*,\s*(\[.*\])\s*\)\s*;', js, re.S)
    return json.loads(mm.group(1)), json.loads(mm.group(2))


def write_js(path, meta, qs, label):
    lines = [
        f'/* {label} 応用情報技術者試験 午前（収録{len(qs)}問）',
        ' * 問題文・選択肢・図表: IPA公開の過去問題（出典明記のうえ再利用）。解説はAI生成。',
        ' * 選択肢が図の問題は choiceImages（肢別画像）／choicesImage（合成1枚）で表示。',
        ' */',
        'window.AP_REGISTER(',
        json.dumps(meta, ensure_ascii=False) + ',',
        json.dumps(qs, ensure_ascii=False, indent=1),
        ');',
    ]
    io.open(path, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')


def process_key(key, allow_net, report):
    ddir = bd.dojo_dir(key)
    term = 'aki' if key[-1] == 'a' else 'haru'
    year = int(re.match(r'^[rh](\d+)[ah]$', key).group(1))
    ans = json.load(io.open(os.path.join(ROOT, 'data', 'answers.json'), encoding='utf-8'))
    akey = ans[key]['answers']
    cats = ans[key].get('cats', {})
    path = os.path.join(ROOT, 'questions', key + '.js')
    meta, qs = load_js(path)
    have = set(q['qnum'] for q in qs)
    label = meta.get('label', key)
    added = 0
    for n in range(1, 81):
        if n in have or str(n) not in akey:
            continue
        cp = os.path.join(ROOT, 'data', 'cache', ddir, f'q{n}.html')
        if not os.path.exists(cp):
            continue
        html = bd.ol_repl(bd.decode(io.open(cp, 'rb').read()))
        # 画像選択肢か判定
        _, imgc = bd.extract_choices(html)
        per = per_choice_srcs(html) if imgc else None
        comp = None if per else composite_src(html)
        if per is None and comp is None:
            continue  # 画像選択肢ではない（対象外）
        # 問題文（#mondai。図は[[img:]]で保持）
        mondai = bd.extract_div(html, 'id="mondai"')
        text, _mimgs = bd.build_mondai(mondai, key, n, ddir, allow_net) if mondai else ('', [])
        q = {
            'id': f'{key}-q{n}', 'year': year, 'term': term, 'part': 'am',
            'qnum': n, 'cat': cats.get(str(n), 'T'),
            'answer': akey[str(n)], 'hasImage': False,
            'text': text, 'choices': {'ア': '', 'イ': '', 'ウ': '', 'エ': ''},
            'explanation': '',
        }
        if per:
            ci = {}
            for kana, src in per.items():
                sfx = {'ア': 'a', 'イ': 'i', 'ウ': 'u', 'エ': 'e'}[kana]
                rel = dl(src, ddir, key, n, sfx, allow_net)
                if rel is None:
                    ci = None; break
                ci[kana] = rel
            if ci is None:
                report.append((key, n, 'per-choice画像の取得失敗')); continue
            q['choiceImages'] = ci
            q['choiceStyle'] = 'perchoice'
        else:
            rel = dl(comp, ddir, key, n, 'choices', allow_net)
            if rel is None:
                report.append((key, n, '合成画像の取得失敗')); continue
            q['choicesImage'] = rel
            q['choiceStyle'] = 'composite'
        qs.append(q)
        have.add(n)
        added += 1
    qs.sort(key=lambda q: q['qnum'])
    meta['included'] = len(qs)
    meta['hasExpl'] = any(x.get('explanation') for x in qs)
    write_js(path, meta, qs, label)
    print(f'{key}: 追加 {added}問 / 収録計 {len(qs)}問')
    return added


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    allow_net = '--dry' not in sys.argv
    if args:
        keys = args
    else:
        keys = [os.path.basename(f)[:-3] for f in
                __import__('glob').glob(os.path.join(ROOT, 'questions', '*.js'))
                if re.match(r'^[rh]\d', os.path.basename(f))]
    report = []
    total = 0
    for key in sorted(keys):
        total += process_key(key, allow_net, report)
    print(f'\n=== 合計 追加 {total}問 ===')
    if report:
        print('取得できなかった問:')
        for k, n, why in report:
            print(f'  {k}-q{n}: {why}')


if __name__ == '__main__':
    main()
