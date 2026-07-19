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
4. **問題冊子PDFは全ページ画像**（テキスト非埋め込み）。設問文・選択肢は自動抽出できないので、`data/img/<key>/pNN.png` を目視して書き起こす。**図表を含む問題は `tools/crop_fig.py` で該当図を切り出し（`questions/img/<qid>.png`）、問題データに `"hasImage": true, "img": "questions/img/<qid>.png"` を付けて表示できる**（アプリの `.qimg` 対応済み・`verify.py` が img ファイル存在を検証）。切り出しが困難な問題（選択肢自体が図など）のみ収録を見送り、報告する。
5. データ本体はユーザー端末のlocalStorage（キー `apstudy.v1`）。保存構造を変えるときは `migrate()` に旧→新変換を追加し、テストに移行ケースを足す。既存データを壊すと復元不能。
6. レイアウトの根幹を壊さない: `fitViewport()`、body/main/navのflex構造、セーフエリア対応。**`position: fixed` や新規の `100vh/100dvh` を使わない**（iOSスタンドアロンで高さがバグる）。
7. グラフ色は検証済みパレット（午前=blue #2a78d6 / 午後=orange #eb6834、ダーク別調整）。合格ライン60%の破線を維持。色を足すときは凡例・ラベルを必ず併記。
8. 新しいファイルを追加したら `sw.js` の `ASSETS` に追記し、`CACHE` 名の数字を+1する（apstudy-v2 → v3）。

## 🔖 次回の再開メモ（過去問の大量収録：道場抽出パイプライン運用中）

- **方針転換済み（ユーザー/コーディネーター合意）**: 目視書き起こしから **`tools/build_from_dojo.py` による自動抽出**へ移行。過去問道場ページからIPA著作物（問題文・選択肢・問題の図表）のみを取得し、道場の解説文(#kaisetsu)・独自コンテンツは**取得しない**。解説は自前生成（後続）。アプリのIPA出典明記は維持。
- **厳守条件（ツールが自動遵守／破れたら中止報告）**: 2秒以上間隔・逐次（並列禁止）・`data/cache/`（gitignore）にHTMLキャッシュし再取得しない・**HTTP 200以外（403/429含む）で即中止・回避策を講じない**・正解は `data/answers.json`（IPA由来）。robots.txt はAI学習用4UA(GPTBot等)を`Disallow:/`、`User-agent:*`規則なし・対象パス制限なし（確認済み）。
- **目標**: まず9回（r7a,r7h,r6a,r6h,r5a,r5h,r4a,r3a,r3h＝720問）を解説なしで全収録。**余力があれば全年度（道場収録の平成21春〜最新・約41回3,280問）まで拡張**。古い回で `answers.json` に正解が無い回は、先にIPA解答例PDFから抽出（`build_answers.py`系）。**正解の裏取り不可の回（r4h等ベクター化PDF）は収録見送り・報告**。r4h（令和4春）は除外。
- **収録状況（manifest.js）— 主要9回は完了・配信確認済み（合計675問）**:
  - r7a 令和7年秋 78問（手起こし38=解説付き＋抽出40）／r7h 令和7年春 75／r6a 令和6年秋 78（手起こし14=解説付き＋抽出64）／r6h 令和6年春 76／r5a 令和5年秋 72／r5h 令和5年春 70／r4a 令和4年秋 77／r3a 令和3年秋 74／r3h 令和3年春 75。
  - 各回の80問との差＝選択肢自体が図（論理ゲート・composite画像など）の問で自動見送り（合計45問）。
  - **解説生成（フェーズ1）＝完了**: 収録9回675問すべてに解説を付与済み（r7a・r7h・r6a・r6h・r5a・r5h・r4a・r3a・r3h、全回 `hasExpl:true`）。各回とも verify OK・smoke全PASS・push・配信確認済み。解説の書式は「正解肢がなぜ正しいか2〜3文＋誤答肢ア〜エ各1文」。手法: 解説マップJSON `{qid:文}` を作り `scratchpad/inject_expl.py <key> <map.json>`（空explanationのみ置換・既存手起こし解説は保護）で注入。図表問は `questions/img/<qid>.png` を目視して数値確認済み。
  - **フェーズ2＝全年度収録＝完了**: 平成21年春〜令和7年秋の**全32回・約2,384問を収録済み**（令和7秋〜令和3春の9回＋r2a・r1a・平成31春〜平成21春）。全回 verify OK・smoke全PASS・push・配信確認済み。正解はすべてIPA解答例PDF由来（answers.json）。平成回の分野(cat)はPDFに列が無くTデフォルト（未検証項目のため許容）。平成23年春は震災で特別試験＝道場 `23_toku`（build_from_dojo.py と app dojoUrl が特別対応済み）。**残タスク: 新規22回（r2a〜h21h）の解説生成**（令和7秋〜令和3春の9回は解説済み）。
  - **解説生成の残り**: 令和7秋〜令和3春と同じ品質仕様（正解肢2〜3文＋誤答肢ア〜エ各1文・answers.jsonと矛盾禁止）で、新しい回から順に生成。手法はフェーズ1と同じ（解説マップJSON→`inject_expl.py <key> <map.json>`で空欄のみ注入→manifestと.js metaの`hasExpl`をtrueへ）。図表問は該当図を目視（**ぼやけて数字を誤読しやすいのでfitzで4〜5倍に拡大して確認する。h28a問77は仕入500を1000と誤読しかけた実例あり**）。
  - **進捗（2026-07-20時点）**: r2a〜h29h＋**h28a・h28h・h27a・h27h＝解説完了**（hasExpl:true）。**残り12回: h26a→h26h→h25a→h25h→h24a→h24h→h23a→h23h→h22a→h22h→h21a→h21h**。コーディネーター指示により**1回ごとにverify→smoke→commit→push**。injectスクリプトは `scratchpad/inject_expl.py`（in-place置換・空欄のみ・既存保護）。図表問はfitzで4倍拡大して数値確認する運用が定着。
  - **表示品質修正（v16でリリース済み）**: 問題文・選択肢の上付き/下付きは `[[sup:x]]`/`[[sub:x]]` プレースホルダで保持し、`qTextHtml()` が `<sup>/<sub>` に描画（キャレット `10^5` 表記も上付きに描画）。パーサ（build_from_dojo.py の strip_tags）が `<sup>/<sub>` を当該プレースホルダで出力。旧データ（`^`/`_` 表記でlogの底など欠落）は `regen_text.py` で全回再生成済み。r2a問1のlog底が復元済み。
  - **1回分の収録手順（確立済み・参考）**: ①IPA公式ページ `https://www.ipa.go.jp/shiken/mondai-kaiotu/<YYYY><元号>.html`（例 2017h29.html）を WebFetch し、AP午前の `_ap_am_ans.pdf` URL（att/ハッシュ込み）を特定。②`tools/exams.json` に1行追記（qs/ans）。③`scratchpad/merge_answers.py <key>`（IPA解答例PDFから80問の正解・分野を抽出し answers.json に**追記のみ**。既存回は不変。80問揃わなければ収録見送り＝ベクター化PDF等）。④`python tools/build_from_dojo.py <key>`（道場を2.2s間隔で逐次取得・キャッシュ済みは再取得しない・図表も取得・選択肢が図の問は自動見送り）。**セッション中断対策で必ずforeground実行**（backgroundは境界で殺される。中断したらcacheから再開＝再実行で続きを取得）。⑤manifestに1ブロック追記（included実数・hasExpl:false）。⑥verify→smoke→commit→push→配信確認。
  - **キー命名**: 令和=r（r1a=令和元年秋。build_from_dojo.pyは year==1 で「令和元年」表記に対応済み）、平成=h（h29h=平成29春）。dojo_dir は年2桁ゼロ埋め＋_aki/_haru（h29h→29_haru, r1a→01_aki）。**verify.py と smoke は平成(h)キー対応済み**（旧 verify は `r\d` のみ照合の不具合があり `[rh]\d` に修正、smoke は問IDから回キーを取得する方式に修正）。
- **全年度拡張の未整備事項**: 平成回は `answers.json` に正解が無い。**先にIPA解答例PDFから正解抽出（`build_answers.py`系）が必要**。`tools/exams.json` に対象回のPDF URL登録→答え抽出→`build_from_dojo.py <key>`。**正解の裏取り不可の回（ベクター化PDF等）は収録見送り・報告**。平成キーは `h29h`（平成29春）形式で `build_from_dojo.py` の dojo_dir はそのまま対応（年2桁＋_haru/_aki）。41回規模では初回ロード時間・localStorage容量の実測と、必要なら manifest 遅延ロード化を検討。
- **1回分の手順**: `python tools/build_from_dojo.py <key>`（既存問は保持し欠けを抽出追記）→ `questions/manifest.js` の該当 `included` を実数へ更新（無い回は exams に1行追加）→ `python tools/verify.py`（解説なしはWARN・OK）→ `node test/smoke.test.js`（全PASS）→ コミット・push・配信確認。**sw.js は編集不要**（ASSETSはアプリシェルのみ＝実行時キャッシュに一本化済み。index.html を変えた時だけ CACHE 数字+1。現在 apstudy-v12）。
- **問題文は構造保持パーサv2で生成**（`build_from_dojo.py` の `strip_tags`/`build_mondai`）。道場HTMLの改行(`<br>`/段落)・箇条書き(`<li>`は「・」付き改行)・分数(`<span class="frac">`→`（分子）/（分母）`)・上下付きを保持し、**問題文中のインライン画像（数式・記号・小図）は `[[img:questions/img/<key>-q<N>[_i].png]]` プレースホルダとして本文中に埋め込む**。アプリは `qTextHtml()` でプレースホルダを `<img>` に置換し、`.qtext{white-space:pre-wrap}` で改行表示、`.qtext img` でインライン表示する。旧テキスト（改行/数式/記号が潰れていた不具合）は `python tools/regen_text.py`（キャッシュから機械再生成・explanation等は不変・不足画像だけ厳守条件で追加取得）で全回修正済み。`verify.py` はプレースホルダ参照画像の存在も検証する。
- **画像**: 図表は `#mondai` 内の画像だけを取得（解説の図は取らない）。1問に複数画像があればすべて `[[img:...]]` として本文中に保持。選択肢自体が図の問題は自動で見送り＆列挙報告。
- **解説の後続追加**: 解説なし問題は `explanation:""`。アプリは正解表示＋「解説は準備中」で正しく動く（確認済み）。後続バッチで回ごとに解説生成→`explanation`を埋める。
- **パフォーマンス（41回規模想定）**: SWは実行時キャッシュ化済み。manifestは全回を `document.write` で逐次ロード。要監視: localStorage(`apstudy.v1`)容量・年度別タブの表示件数・初回ロード時間。大規模化で問題が出たら manifest 分割ロードや遅延ロードを検討（未対応）。
- **テスト注意**: smokeは春秋(term)で answers キーを出し分け済み（`r{year}{a|h}`）。解説は任意（あれば40字以上）。年度固有件数のassertは調整済み。

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

- タブ5つ: ホーム / カレンダー / 年度別 / 演習 / 設定。`render()` が state.tab に応じて main.innerHTML を丸ごと書き換える。イベントはHTML属性のonclick
- 「年度別」タブ（`viewSummary`）= 年度別サマリ。回ごとの進捗バー＋タップでその回の弱点復習（`startYearReview`）。旧・正答率折れ線グラフは廃止（`examSummaryHtml(tappable)` に集約。年度別進捗は演習トップから外し重複解消）
- 演習の解答は `recordPracticeAnswer()` で当日の practice ログ（source:'practice'）に集計され、カレンダー・ストリーク・サマリに自動連携する
- 習熟ステータス: `mastery[qid] = { status:'ok'|'weak', correctStreak }`。未挑戦=記録なし／正解=ok／弱点=weak。**挑戦済み=正解+弱点**。弱点は復習で連続`RESOLVE_STREAK`(=2)回正解すると`ok`へ戻す（「克服」ラベルは設けない）。「わからない」選択（`UNKNOWN`）は不正解扱い（弱点行き・正答率にも不正解計上）
- 演習の中断・再開: `store.session = { mode,label,queue,idx,picked }` を都度 `persistSession()` で保存。演習トップに `validSession()` なら「前回の続きから」ボタン、`resumeSession()` で復帰。完了で null 化
- 年度別進捗: `examProgress(year,term)` が `{included,attempted,correct,weak}` を返す。演習トップ・設定でプログレスバー表示
- 保存スキーマは version 3（v2→v3で旧 `{seen,correctStreak,wrong}` を `{status,correctStreak}` へ移行。`migrate()` 参照）
- 過去問道場の照合リンク（外部リンクのみ・スクレイピング禁止）: `dojoUrl()`。ディレクトリは「元号内の年2桁ゼロ埋め + _haru/_aki」、午前=q{N}.html、午後=pm{NN}.html。令和6年秋=06_aki、平成29年春=29_haru
- 試験日の既定 2026-10-28 は「令和8年度 前期試験 科目A 実施開始日」（CBT化で従来の秋期は廃止）。根拠はREADME参照
- バックアップは家計簿・筋トレアプリと同一仕様: クラウド自動バックアップ（起動時＋前面復帰時に1日1回、非公開リポ `prkxfzmfx-pixel/app-backups` の `apstudy.json` へGitHub API PUT。`cloudBackup()`）＋かんたん設定コード（`PIN_BLOB`をAES-GCM復号）＋JSONエクスポート/インポート。トークンはlocalStorage `apstudy.cloudToken` のみ。**平文トークン・6桁コードをコード/コミット/テストに書かない**。`PIN_BLOB` はユーザーのコード＋トークンで `node tools\make-pin-blob.js <コード> <トークン>` をローカル実行して生成し貼る（未登録の間はトークン直接貼り付けで有効化）
- 設定タブは 試験日／統計／クラウド自動バックアップ／データ のみ。収録過去問一覧は「年度別」タブに集約（設定からは撤去）。ホームに「直近の記録」は置かない（データは保持しカレンダー・サマリで利用）
