# -*- coding: utf-8 -*-
"""解答データと問題JSファイルの整合性を機械検証する。

検証内容:
  A. data/answers.json（IPA公式解答例由来）: 各回80問・問番号1..80の連番・正解が全てア〜エ。
  B. questions/ 配下の各回JSファイル: 収録した各問の正解が answers.json（＝IPA解答例）と一致、
     選択肢がア〜エの4つ、解説の有無、hasImage=false の問だけ収録、問番号の重複なし。
  C. questions/manifest.js の included 件数が実ファイルと一致。

usage: python tools/verify.py   （終了コード 0=OK, 1=NG）
"""
import io, os, re, json, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KANA = {'ア', 'イ', 'ウ', 'エ'}
errors = []
warns = []


def load_answers():
    return json.load(io.open(os.path.join(ROOT, 'data', 'answers.json'), encoding='utf-8'))


def check_answers(ans):
    for key, e in ans.items():
        a = e['answers']
        nums = sorted(int(k) for k in a.keys())
        if len(nums) != 80:
            errors.append(f'[A] {key}: 解答数 {len(nums)} (期待80)')
        if nums and nums != list(range(1, len(nums) + 1)):
            errors.append(f'[A] {key}: 問番号が1..{len(nums)}の連番でない')
        for k, v in a.items():
            if v not in KANA:
                errors.append(f'[A] {key} 問{k}: 正解 "{v}" がア〜エでない')


def extract_register(js):
    """questions/rXX.js の AP_REGISTER(meta, questions) を JSON.parse 可能な形で取り出す。
    ファイルは `AP_REGISTER( {..}, [..] );` 形式を想定。"""
    m = re.search(r'AP_REGISTER\s*\(', js)
    if not m:
        return None, None
    i = m.end()
    depth = 1
    start = i
    while i < len(js) and depth > 0:
        c = js[i]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        i += 1
    args = js[start:i - 1]
    # 2引数を分割: 先頭のオブジェクト {...} と 配列 [...]
    return args


def load_question_files():
    qdir = os.path.join(ROOT, 'questions')
    files = [f for f in os.listdir(qdir) if re.match(r'[rh]\d', f) and f.endswith('.js')]
    banks = {}
    for f in files:
        js = io.open(os.path.join(qdir, f), encoding='utf-8').read()
        # meta と questions を素朴に取り出す（JSはJSON互換で書く運用）
        mm = re.search(r'AP_REGISTER\(\s*(\{.*?\})\s*,\s*(\[.*\])\s*\)\s*;', js, re.S)
        if not mm:
            errors.append(f'[B] {f}: AP_REGISTER(meta, questions) を解析できない')
            continue
        try:
            meta = json.loads(mm.group(1))
            qs = json.loads(mm.group(2))
        except Exception as ex:
            errors.append(f'[B] {f}: JSON解析失敗 {ex}')
            continue
        banks[meta.get('key')] = {'file': f, 'meta': meta, 'qs': qs}
    return banks


def check_banks(ans, banks):
    for key, b in banks.items():
        if key not in ans:
            errors.append(f'[B] {b["file"]}: answers.json に {key} がない')
            continue
        akey = ans[key]['answers']
        seen = set()
        for q in b['qs']:
            qid = q.get('id')
            # 図表つき問題は img（切り出し画像）が必須。画像なしのhasImageは収録不可。
            if q.get('hasImage') and not q.get('img'):
                errors.append(f'[B] {qid}: hasImage=true だが img（切り出し画像）がない（図表なしで収録できないならスキップ）')
            if q.get('img'):
                p = os.path.join(ROOT, q['img'])
                if not os.path.exists(p):
                    errors.append(f'[B] {qid}: img ファイルが存在しない: {q["img"]}')
            # 問題文中のインライン画像プレースホルダ [[img:パス]] の参照先も存在確認する。
            for rel in re.findall(r'\[\[img:([^\]]+)\]\]', q.get('text', '')):
                if not os.path.exists(os.path.join(ROOT, rel)):
                    errors.append(f'[B] {qid}: 問題文の画像が存在しない: {rel}')
            # 選択肢が図の問題: choiceImages（肢別）は ア〜エ4キー＋各ファイル存在、choicesImage（合成）はファイル存在。
            ciMap = q.get('choiceImages')
            if ciMap is not None:
                if sorted(ciMap.keys()) != ['ア', 'イ', 'ウ', 'エ']:
                    errors.append(f'[B] {qid}: choiceImages がア〜エの4キーでない')
                for kk, rel in ciMap.items():
                    if not os.path.exists(os.path.join(ROOT, rel)):
                        errors.append(f'[B] {qid}: choiceImages[{kk}] が存在しない: {rel}')
            if q.get('choicesImage') and not os.path.exists(os.path.join(ROOT, q['choicesImage'])):
                errors.append(f'[B] {qid}: choicesImage が存在しない: {q["choicesImage"]}')
            qn = str(q.get('qnum'))
            if qn in seen:
                errors.append(f'[B] {key}: 問{qn} が重複')
            seen.add(qn)
            official = akey.get(qn)
            if official is None:
                errors.append(f'[B] {qid}: answers.json に問{qn}がない')
            elif q.get('answer') != official:
                errors.append(f'[B] {qid}: 正解 {q.get("answer")} が公式 {official} と不一致')
            ch = q.get('choices', {})
            if sorted(ch.keys()) != ['ア', 'イ', 'ウ', 'エ']:
                errors.append(f'[B] {qid}: 選択肢がア〜エの4つでない')
            if not q.get('explanation'):
                warns.append(f'[B] {qid}: 解説なし（正解表示のみで出題）')
        if b['meta'].get('included') != len(b['qs']):
            errors.append(f'[C] {b["file"]}: included={b["meta"].get("included")} だが実際は {len(b["qs"])}問')


def main():
    ans = load_answers()
    check_answers(ans)
    banks = load_question_files()
    check_banks(ans, banks)
    print(f'解答データ: {len(ans)}回 / 問題ファイル: {len(banks)}回')
    for w in warns:
        print('WARN', w)
    if errors:
        for e in errors:
            print('NG  ', e)
        print(f'\n=== 検証NG: {len(errors)}件 ===')
        sys.exit(1)
    total_q = sum(len(b['qs']) for b in banks.values())
    print(f'収録問題数: {total_q}問（全問 正解=IPA公式解答例と一致）')
    print('=== 検証OK ===')


if __name__ == '__main__':
    main()
