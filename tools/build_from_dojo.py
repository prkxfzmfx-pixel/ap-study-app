# -*- coding: utf-8 -*-
"""過去問道場の問題ページから IPA著作物（問題文・選択肢・問題の図表）だけを抽出し、
questions/<key>.js を生成する。道場の解説文(#kaisetsu)・サイト独自コンテンツは一切取得・保存しない。

厳守条件（本ツールが自動で守る）:
  - リクエスト間隔 2秒以上・単純なシーケンシャル取得（並列なし）
  - 取得HTMLは data/cache/<dir>/ にキャッシュし再取得しない
  - HTTP 200 以外（403/429含む）は即中止（回避策を講じない）
  - 抽出対象は #mondai（問題文＋図）と #select_a/i/u/e（選択肢）のみ。#kaisetsu は触れない
  - 正解は data/answers.json（IPA解答例由来）を使用。answers.json に無い回は中止
  - 既存 questions/<key>.js の問題（手起こし・解説付き）はそのまま保持し、欠けている問だけ追加

usage: python tools/build_from_dojo.py <key>        # 例: r7a, r7h, r6h ...
       python tools/build_from_dojo.py <key> --dry  # 取得せずキャッシュ済みのみで生成を試す
"""
import io, os, re, sys, json, time, html as htmlmod, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, 'data', 'cache')
IMGDIR = os.path.join(ROOT, 'questions', 'img')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
DELAY = 2.2
BASE = 'https://www.ap-siken.com/kakomon'


def dojo_dir(key):
    m = re.match(r'^([rh])(\d+)([ah])$', key)
    if not m:
        raise SystemExit(f'ABORT: key 形式が不正: {key}（例 r7a, h29h）')
    _, yr, tm = m.groups()
    # 平成23年は東日本大震災で春が特別試験となり、道場は 23_toku を用いる。
    if key == 'h23h':
        return '23_toku'
    return f'{int(yr):02d}_{"aki" if tm == "a" else "haru"}'


def fetch(url, cache_path, allow_net):
    if os.path.exists(cache_path):
        return io.open(cache_path, 'rb').read(), False
    if not allow_net:
        return None, False
    time.sleep(DELAY)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status = getattr(r, 'status', r.getcode())
            data = r.read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f'ABORT: HTTP {e.code} for {url} — ブロック兆候の可能性。中止して報告する。')
    except Exception as e:
        raise SystemExit(f'ABORT: 取得失敗 {url}: {e}')
    if status != 200:
        raise SystemExit(f'ABORT: HTTP {status} for {url}')
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    io.open(cache_path, 'wb').write(data)
    return data, True


def decode(b):
    for enc in ('utf-8', 'cp932', 'euc-jp'):
        try:
            return b.decode(enc)
        except Exception:
            pass
    return b.decode('utf-8', 'replace')


def ol_repl(s):
    """<span class="ol">X</span> を各文字への上線（結合上線 U+0305）に変換して span を除去。"""
    def f(m):
        inner = re.sub(r'<[^>]+>', '', m.group(1))
        return ''.join(c + '̅' for c in inner)
    return re.sub(r'<span class="ol">(.*?)</span>', f, s, flags=re.S)


def strip_tags(s):
    s = re.sub(r'<sup>(.*?)</sup>', lambda m: '^' + re.sub(r'<[^>]+>', '', m.group(1)), s, flags=re.S)
    s = re.sub(r'<sub>(.*?)</sub>', lambda m: '_' + re.sub(r'<[^>]+>', '', m.group(1)), s, flags=re.S)
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = htmlmod.unescape(s)
    return re.sub(r'[ \t　]+', ' ', re.sub(r'\s+', ' ', s)).strip()


def extract_div(html, marker):
    i = html.find(marker)
    if i < 0:
        return None
    open_end = html.find('>', i) + 1
    depth, j = 1, open_end
    while j < len(html) and depth > 0:
        nd = html.find('<div', j)
        nc = html.find('</div>', j)
        if nc < 0:
            break
        if 0 <= nd < nc:
            depth += 1
            j = nd + 4
        else:
            depth -= 1
            j = nc + 6
    return html[open_end:j - 6]


def imgs_in(s):
    return re.findall(r'<img[^>]*\ssrc="([^"]+)"', s)


def load_existing(key):
    path = os.path.join(ROOT, 'questions', key + '.js')
    if not os.path.exists(path):
        return {}
    js = io.open(path, encoding='utf-8').read()
    mm = re.search(r'AP_REGISTER\(\s*(\{.*?\})\s*,\s*(\[.*\])\s*\)\s*;', js, re.S)
    if not mm:
        raise SystemExit(f'ABORT: 既存 {key}.js を解析できない')
    qs = json.loads(mm.group(2))
    return {int(q['qnum']): q for q in qs}


def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: python tools/build_from_dojo.py <key> [--dry]')
    key = sys.argv[1]
    allow_net = '--dry' not in sys.argv
    ddir = dojo_dir(key)
    term = 'aki' if key[-1] == 'a' else 'haru'
    year = int(re.match(r'^[rh](\d+)[ah]$', key).group(1))
    gengo_yr = '元' if year == 1 else str(year)
    label = f'令和{gengo_yr}年{"秋" if term=="aki" else "春"}' if key[0] == 'r' else f'平成{gengo_yr}年{"秋" if term=="aki" else "春"}'

    answers = json.load(io.open(os.path.join(ROOT, 'data', 'answers.json'), encoding='utf-8'))
    if key not in answers:
        raise SystemExit(f'ABORT: answers.json に {key} が無い（正解の裏取り不可のため収録見送り）')
    akey = answers[key]['answers']

    existing = load_existing(key)
    os.makedirs(IMGDIR, exist_ok=True)

    out = {}
    skipped = []   # 画像選択肢など収録見送り
    scraped = 0
    kept = 0
    figs = 0
    for n in range(1, 81):
        if n in existing:
            out[n] = existing[n]
            kept += 1
            continue
        official = akey.get(str(n))
        if official is None:
            skipped.append((n, 'answers.jsonに正解なし'))
            continue
        url = f'{BASE}/{ddir}/q{n}.html'
        cache_path = os.path.join(CACHE, ddir, f'q{n}.html')
        data, _ = fetch(url, cache_path, allow_net)
        if data is None:
            skipped.append((n, 'キャッシュ無し(--dry)'))
            continue
        html = decode(data)
        html_ol = ol_repl(html)

        mondai = extract_div(html_ol, 'id="mondai"')
        if mondai is None:
            skipped.append((n, '#mondai抽出不可'))
            continue
        m_imgs = [s for s in imgs_in(mondai) if s.lower().endswith(('.png', '.gif', '.jpg', '.jpeg'))]
        text = strip_tags(mondai)
        if not text:
            skipped.append((n, '問題文が空'))
            continue

        # 選択肢
        ch = {}
        img_choice = False
        for sfx, kana in (('a', 'ア'), ('i', 'イ'), ('u', 'ウ'), ('e', 'エ')):
            m = re.search(r'<span id="select_%s">(.*?)</span>' % sfx, html_ol, re.S)
            if not m:
                ch = None
                break
            inner = m.group(1)
            if '<img' in inner:
                img_choice = True
            ch[kana] = strip_tags(inner)
        if ch is None or img_choice or any(not v for v in ch.values()):
            skipped.append((n, '選択肢が図/空（画像選択肢のため見送り）'))
            continue

        q = {
            'id': f'{key}-q{n}', 'year': year, 'term': term, 'part': 'am',
            'qnum': n, 'cat': answers[key].get('cats', {}).get(str(n), 'T'),
            'answer': official, 'hasImage': False,
            'text': text, 'choices': ch, 'explanation': ''
        }
        # 問題図（#mondai内のみ）。複数ある場合は先頭を採用し警告。
        if m_imgs:
            src = m_imgs[0]
            img_url = f'{BASE}/{ddir}/{src}' if not src.startswith('http') else src
            ext = os.path.splitext(src)[1].lower()
            target_rel = f'questions/img/{key}-q{n}{ext}'
            target = os.path.join(ROOT, target_rel)
            if not os.path.exists(target):
                idata, _ = fetch(img_url, os.path.join(CACHE, ddir, '_img', os.path.basename(src)), allow_net)
                if idata is not None:
                    io.open(target, 'wb').write(idata)
            if os.path.exists(target):
                q['hasImage'] = True
                q['img'] = target_rel
                figs += 1
                if len(m_imgs) > 1:
                    q['_multi_img'] = len(m_imgs)
        out[n] = q
        scraped += 1

    qs = [out[n] for n in sorted(out)]
    has_expl = any(q.get('explanation') for q in qs)
    meta = {'key': key, 'year': year, 'term': term, 'label': label,
            'total': 80, 'included': len(qs), 'hasExpl': has_expl}

    # 書き出し
    lines = []
    lines.append(f'/* {label} 応用情報技術者試験 午前（収録{len(qs)}問）')
    lines.append(' * 問題文・選択肢・図表: IPA公開の過去問題（出典明記のうえ再利用）。解説はAI生成で後続追加。')
    lines.append(' * 生成: tools/build_from_dojo.py（道場の解説文・独自コンテンツは取得していない）。')
    lines.append(' */')
    lines.append('window.AP_REGISTER(')
    lines.append(json.dumps(meta, ensure_ascii=False) + ',')
    lines.append(json.dumps(qs, ensure_ascii=False, indent=1))
    lines.append(');')
    outpath = os.path.join(ROOT, 'questions', key + '.js')
    io.open(outpath, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')

    print(f'[{key}] {label}  収録{len(qs)}問 (既存保持{kept}/新規抽出{scraped}/図{figs})  見送り{len(skipped)}問')
    for n, why in skipped:
        print(f'   見送り 問{n}: {why}')


if __name__ == '__main__':
    main()
