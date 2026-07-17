# 応用情報 学習記録アプリ（PWA）

応用情報技術者試験の学習記録＋内蔵過去問演習アプリ。**修正指示を受けたら、必ず下の「修正フロー」を上から順に全部実行すること。**編集だけして終わるのは作業未完了。

- 公開URL: https://prkxfzmfx-pixel.github.io/ap-study-app/
- リポジトリ: https://github.com/prkxfzmfx-pixel/ap-study-app （公開。このフォルダが作業コピー）
- 姉妹アプリ: 筋トレ `..\_workout_app\`、家計簿 `..\_kakeibo_app\`。基盤（flexレイアウト・PWA構成・ネットワーク優先SW・単一index.html・スモークテスト方式）は共通。UI変更を他方へ波及させるかは、仮定で済ませず他方のindex.htmlをgrepして事実確認し、結果を報告した上でユーザーに確認。

## 構成

| ファイル | 内容 |
|---|---|
| index.html | アプリ本体。CSS/JSすべてこの1ファイル（外部ライブラリ・CDN禁止） |
| questions/manifest.js | 収録回マニフェスト。アプリ起動時に `document.write` で各回を動的ロード |
| questions/`<key>`.js | 各回の問題データ。`window.AP_REGISTER(meta, questions)` を呼ぶ（JSON互換で記述） |
| sw.js | Service Worker（ネットワーク優先・オフラインキャッシュ） |
| data/answers.json | IPA解答例から抽出・検証した正解データ（検証の基準。コミットする） |
| tools/ | 過去問取り込みパイプライン（build_exam.py / build_answers.py）と検証（verify.py） |
| test/smoke.test.js | スモークテスト（DOMスタブ + Function評価方式） |

（`data/pdf/` `data/img/` は .gitignore。IPA PDFの再配布回避と容量削減のため。パイプラインで再取得できる）

## 絶対に守ること

1. **正解は必ずIPA公式「解答例」PDF由来**とする。問題を追加・編集したら `python tools/verify.py` を実行し、収録全問の `answer` が `data/answers.json`（＝IPA解答例）と一致することを確認する。手打ちで正解を書かない。
2. **解説（explanation）はAI生成**であり誤りうる。結果画面と設定画面下部の「AI生成である」旨の注記を消さない。解説を追加・修正したら、結論（推す肢）が `answer` と矛盾しないか必ず読み返す。
3. **出典明記を消さない**。IPAは出典明記を条件に問題の再利用を認めている。結果画面の出典表示・設定画面・READMEのIPA出典を維持する。
4. **問題冊子PDFは全ページ画像**（テキスト非埋め込み）。設問文・選択肢は自動抽出できないので、`data/img/<key>/pNN.png` を目視して書き起こす。図・表・プログラムを含む問題は `hasImage:true` にせず**収録しない**（v1方針）。
5. データ本体はユーザー端末のlocalStorage（キー `apstudy.v1`）。保存構造を変えるときは `migrate()` に旧→新変換を追加し、テストに移行ケースを足す。既存データを壊すと復元不能。
6. レイアウトの根幹を壊さない: `fitViewport()`、body/main/navのflex構造、セーフエリア対応。**`position: fixed` や新規の `100vh/100dvh` を使わない**（iOSスタンドアロンで高さがバグる）。
7. グラフ色は検証済みパレット（午前=blue #2a78d6 / 午後=orange #eb6834、ダーク別調整）。合格ライン60%の破線を維持。色を足すときは凡例・ラベルを必ず併記。
8. 新しいファイルを追加したら `sw.js` の `ASSETS` に追記し、`CACHE` 名の数字を+1する（apstudy-v2 → v3）。

## 過去問の回を追加する手順

```
# 1. tools/exams.json に回とPDF URLを追記（a=秋, h=春）
python tools/build_exam.py <key>     # 例: r6h。DL→解答抽出→answers.json→ページ画像化
# 2. data/img/<key>/pNN.png を目視し、図表なし問題を questions/<key>.js に AP_REGISTER 形式で書き起こす
#    正解は data/answers.json の値をそのまま使う。解説はIPA解答例と突き合わせて書く（80問バッチ・都度保存）
# 3. questions/manifest.js の exams に <key> を追加（included件数を正しく）
# 4. sw.js の ASSETS に questions/<key>.js を追加し CACHE を+1
# 5. test/smoke.test.js は manifest駆動で全回を読むので通常は変更不要
python tools/verify.py               # 公式解答との全問一致を検証（NGが出たら直す）
```

解説が重い回は「解説なし（正解表示のみ）」で先に公開し、後続バッチで解説を足してよい（`hasExpl` フラグで管理）。

## 修正フロー（この順で必ず全部やる）

1. `index.html` / `questions/*` を編集する
2. 問題を触ったら **`python tools/verify.py`** → 検証OKを確認（PYTHONIOENCODING=utf-8 推奨）
3. テスト実行: `node test\smoke.test.js` → **全項目PASSするまで次に進まない**。新機能を足したらテストケースも追加
4. コミット & push（メッセージは日本語で内容を書く）:
   ```powershell
   git add -A; git commit -m "変更内容"; git push
   ```
   （gitが見つからないシェルでは `C:\Program Files\Git\cmd\git.exe` を絶対パスで）
5. 配信確認（push後1〜2分）。今回の変更にしか含まれない固有文字列で判定:
   ```powershell
   (Invoke-WebRequest "https://prkxfzmfx-pixel.github.io/ap-study-app/?v=$(Get-Random)" -UseBasicParsing).Content -match "新コード固有の文字列"
   ```
6. **5分待っても旧版のままなら GitHub Pages のビルド詰まり**。再ビルドを蹴る:
   ```powershell
   & "C:\Program Files\GitHub CLI\gh.exe" api repos/prkxfzmfx-pixel/ap-study-app/pages/builds -X POST
   & "C:\Program Files\GitHub CLI\gh.exe" api repos/prkxfzmfx-pixel/ap-study-app/pages/builds/latest --jq .status
   ```
7. ユーザーへの完了報告に必ず含める: **「スマホでアプリを完全終了→開き直しで反映。1回で変わらなければもう一度終了→起動」**

## 実装メモ

- タブ5つ: ホーム / カレンダー / グラフ / 演習 / 設定。`render()` が state.tab に応じて main.innerHTML を丸ごと書き換える。イベントはHTML属性のonclick
- 演習の解答は `recordPracticeAnswer()` で当日の practice ログ（source:'practice'）に集計され、カレンダー・グラフ・ストリークに自動連携する
- 弱点判定: `mastery[qid] = { seen, correctStreak, wrong }`。wrong かつ correctStreak<2 が弱点、>=2 で克服（`MASTER_STREAK`）
- 過去問道場の照合リンク（外部リンクのみ・スクレイピング禁止）: `dojoUrl()`。ディレクトリは「元号内の年2桁ゼロ埋め + _haru/_aki」、午前=q{N}.html、午後=pm{NN}.html。令和6年秋=06_aki、平成29年春=29_haru
- 試験日の既定 2026-10-28 は「令和8年度 前期試験 科目A 実施開始日」（CBT化で従来の秋期は廃止）。根拠はREADME参照
