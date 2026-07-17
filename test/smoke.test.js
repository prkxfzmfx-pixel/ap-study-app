// index.html のインラインJS + questions.js をDOMスタブ上で実行して主要動線を検証する。
// 実行: node test\smoke.test.js （全項目PASSしてからpushすること）
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const root = path.join(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const answers = JSON.parse(fs.readFileSync(path.join(root, 'data', 'answers.json'), 'utf8'));
// index.html の最後の <script> がアプリ本体（前2つはローダ）
const appScripts = html.match(/<script>[\s\S]*?<\/script>/g);
const appJs = /<script>([\s\S]*)<\/script>/.exec(appScripts[appScripts.length - 1])[1];

// ---- スタブ ----
const lsData = {};
const localStorage = {
  getItem: k => (k in lsData ? lsData[k] : null),
  setItem: (k, v) => { lsData[k] = String(v); },
  removeItem: k => { delete lsData[k]; },
};
const elements = {};
function makeEl(id) {
  return { id, innerHTML: '', value: '', files: [], style: {}, textContent: '',
    classList: { add() {}, remove() {} },
    addEventListener() {}, setAttribute() {}, appendChild() {}, click() {}, remove() {}, scrollTo() {} };
}
const document = {
  getElementById: id => elements[id] || (elements[id] = makeEl(id)),
  createElement: tag => makeEl(tag),
  documentElement: { style: { setProperty() {} } },
  body: { appendChild() {} },
  addEventListener() {}, hidden: false,
};
const window = { scrollTo() {}, addEventListener() {}, navigator: {}, screen: { height: 800 }, innerHeight: 800 };
const navigator = {};
const location = { protocol: 'file:', hostname: '' };
const confirm = () => true;
let lastAlert = '';
const alert = m => { lastAlert = m; };
const URL = { createObjectURL: () => 'blob:x', revokeObjectURL() {} };
const Blob = class {};
const FileReader = class { readAsText() {} };

// マニフェスト＋各回ファイルを window に読み込む（アプリのローダ相当）
new Function('window', fs.readFileSync(path.join(root, 'questions', 'manifest.js'), 'utf8'))(window);
window.AP_QUESTIONS = [];
window.AP_EXAMS = [];
window.AP_REGISTER = function (meta, qs) { window.AP_EXAMS.push(meta); for (const q of qs) window.AP_QUESTIONS.push(q); };
for (const e of window.AP_MANIFEST.exams) {
  new Function('window', fs.readFileSync(path.join(root, 'questions', e.file), 'utf8'))(window);
}

// アプリ本体を評価して module.exports を取得
function boot() {
  const mod = { exports: {} };
  new Function('module', 'window', 'document', 'localStorage', 'navigator', 'location', 'confirm', 'alert', 'URL', 'Blob', 'FileReader',
    appJs)(mod, window, document, localStorage, navigator, location, confirm, alert, URL, Blob, FileReader);
  return mod.exports;
}
let api = boot();

// 1) 問題バンクの整合性（全問 正解=IPA公式解答例／選択肢4つ／解説あり）
assert(api.BANK.length >= 10, '問題バンクが読み込まれている: ' + api.BANK.length);
for (const q of api.BANK) {
  const off = answers['r' + q.year + 'a'].answers[String(q.qnum)];
  assert.strictEqual(q.answer, off, `正解一致 ${q.id}: bank=${q.answer} official=${off}`);
  assert.deepStrictEqual(Object.keys(q.choices).sort().join(''), 'アイウエ'.split('').sort().join(''), `選択肢ア〜エ ${q.id}`);
  assert(q.explanation && q.explanation.length >= 40, `解説あり ${q.id}`);
  assert(['ア', 'イ', 'ウ', 'エ'].includes(q.answer), `正解がカナ ${q.id}`);
}
console.log(`OK 問題バンク: ${api.BANK.length}問／全問 正解がIPA解答例と一致・選択肢4・解説あり`);

// 2) 全タブが描画される
for (const t of ['home', 'cal', 'summary', 'practice', 'settings']) {
  api.go(t);
  assert(elements.main.innerHTML.length > 80, t + ' 画面が描画される');
}
console.log('OK 全タブ描画');

// 3) カウントダウン（既定 2026-10-28）
const d = api.daysUntilExam();
assert(typeof d === 'number', 'カウントダウンが数値');
assert.strictEqual(api.store.examDate, '2026-10-28', '既定試験日');
console.log('OK カウントダウン: 既定 2026-10-28 / あと ' + d + '日');

// 4) 手動ログ追加 → グラフ系列に反映
api.startAdd(api.todayISO());
api.formSet('part', 'am'); api.formSet('total', '10'); api.formSet('correct', '7');
api.saveForm();
assert.strictEqual(api.store.logs.filter(l => l.source === 'manual').length, 1, '手動ログ1件');
assert(Math.round(api.partAgg('am').rate) === 70, '午前サマリ 70%');
console.log('OK 手動ログ追加 → 午前サマリ(partAgg)に反映（70%）');

// 5) 演習: 令和6年秋を開始 → 正解を選ぶ → 記録・習熟が更新（未挑戦→正解）
api.pickExam('6_aki');
api.startPractice('year');
assert(api.state.practice && api.state.practice.queue.length === api.BANK.length, '年度演習キュー');
const q0 = api.BANK_BY_ID[api.state.practice.queue[0]];
api.answerQuiz(q0.answer);   // 正解
assert(api.state.practice.picked === q0.answer, '解答が記録される');
assert(api.isOk(q0.id) && api.statusOf(q0.id) === 'ok', '初正解で status=ok（正解）');
assert(api.isAttempted(q0.id), '挑戦済み');
const pracLog = api.store.logs.find(l => l.source === 'practice' && l.part === 'am');
assert(pracLog && pracLog.total === 1 && pracLog.correct === 1, '演習が学習ログに自動連携');
console.log('OK 演習: 未挑戦→正解 で status=ok＋学習ログ自動連携');

// 6) 不正解 → 弱点入り → 復習で連続2回正解すると「正解」に戻る（克服ラベルなし）
api.nextQuiz();
const q1 = api.BANK_BY_ID[api.state.practice.queue[api.state.practice.idx]];
const wrong = ['ア', 'イ', 'ウ', 'エ'].find(k => k !== q1.answer);
api.answerQuiz(wrong);       // 不正解
assert(api.isWeak(q1.id) && api.statusOf(q1.id) === 'weak', '不正解で弱点入り');
assert(!api.isOk(q1.id), 'まだ正解ではない');
api.applyResult(q1.id, true);
assert(api.isWeak(q1.id), '1回正解ではまだ弱点');
api.applyResult(q1.id, true);
assert(api.isOk(q1.id) && !api.isWeak(q1.id), '連続2回正解で status=ok（正解）へ');
console.log('OK 弱点→復習で連続2回正解→正解ステータスへ復帰');

// 7) 復習モードは弱点のみを対象にする
api.resetProgress();
const qa = api.BANK[0], qb = api.BANK[1];
api.applyResult(qa.id, false);   // qaを弱点化
api.startPractice('review');
assert(api.state.practice.queue.length === 1 && api.state.practice.queue[0] === qa.id, '復習は弱点1問のみ');
console.log('OK 復習モード: 弱点のみ出題');

// 8) 過去問道場URL（照合リンク）の形式
assert.strictEqual(api.dojoUrl({ year: 6, term: 'aki', part: 'am', qnum: 10 }), 'https://www.ap-siken.com/kakomon/06_aki/q10.html', '午前URL');
assert.strictEqual(api.dojoUrl({ year: 6, term: 'aki', part: 'pm', qnum: 1 }), 'https://www.ap-siken.com/kakomon/06_aki/pm01.html', '午後URL');
assert.strictEqual(api.dojoUrl({ year: 29, term: 'haru', part: 'am', qnum: 5 }), 'https://www.ap-siken.com/kakomon/29_haru/q5.html', '平成29春URL');
console.log('OK 道場URL形式: 令和6秋q10 / 午後pm01 / 平成29春q5');

// 9) 解説がUI（結果画面）に表示される
api.resetProgress();
api.pickExam('6_aki'); api.startPractice('year'); api.go('practice');
const q9 = api.BANK_BY_ID[api.state.practice.queue[0]];
api.answerQuiz(['ア', 'イ', 'ウ', 'エ'].find(k => k !== q9.answer));  // 不正解でも正解＋解説が出る
assert(elements.main.innerHTML.includes('解説') && elements.main.innerHTML.includes('AIが生成'), '結果画面に解説＋AI注記');
assert(elements.main.innerHTML.includes('道場で照合'), '結果画面に道場照合リンク');
api.endPractice();
console.log('OK 解説UI表示＋AI生成の注記');

// 10) 設定に AI解説の免責＋出典、クラウド自動バックアップUI、収録一覧は撤去
api.go('settings');
const sHtml = elements.main.innerHTML;
assert(sHtml.includes('解説はAI') && sHtml.includes('IPA'), '設定に免責＋出典');
assert(sHtml.includes('クラウド自動バックアップ') && sHtml.includes('かんたん設定コード'), '設定にクラウドバックアップUI');
assert(sHtml.includes('バックアップをエクスポート') && sHtml.includes('すべてのデータを削除'), '設定にJSON入出力＋全削除');
assert(!sHtml.includes('収録している過去問'), '設定から収録一覧を撤去（年度別タブと重複解消）');
console.log('OK 設定: AI免責＋出典／クラウドバックアップUI／収録一覧撤去');

// 11) 移行: v1/v2データ（旧習熟スキーマ）→ v3（notes廃止・status化・source補完）
lsData['apstudy.v1'] = JSON.stringify({
  version: 2, examDate: '2026-10-28', examName: 'x',
  logs: [{ date: '2026-07-01', part: 'am', total: 5, correct: 3 }],
  mastery: {
    'r6a-q4': { seen: 3, correctStreak: 2, wrong: true },   // 旧「克服」→ ok
    'r6a-q6': { seen: 1, correctStreak: 0, wrong: true },   // 旧「弱点」→ weak
    'r6a-q7': { seen: 2, correctStreak: 0, wrong: false }   // seenのみ → ok
  },
  notes: [{ id: 'n1' }]
});
api = boot();
assert.strictEqual(api.store.version, 3, 'v3へ移行');
assert(!('notes' in api.store), '旧notes削除');
assert.strictEqual(api.store.logs[0].source, 'manual', 'source補完');
assert.strictEqual(api.statusOf('r6a-q4'), 'ok', '旧克服→正解');
assert.strictEqual(api.statusOf('r6a-q6'), 'weak', '旧弱点→弱点');
assert.strictEqual(api.statusOf('r6a-q7'), 'ok', 'seenのみ→正解');
console.log('OK 移行 v2→v3（notes廃止・習熟スキーマ変換・source補完）');

// 12) 「わからない」= 不正解扱い（弱点行き・正答率も不正解計上）＋結果画面表示
api.resetProgress();
api.pickExam('6_aki'); api.startPractice('year'); api.go('practice');
const qu = api.BANK_BY_ID[api.state.practice.queue[0]];
const pB = api.store.logs.find(l => l.source === 'practice' && l.part === qu.part && l.date === api.todayISO()) || { total: 0, correct: 0 };
const tB = pB.total, cB = pB.correct;
api.answerQuiz(api.UNKNOWN);
assert.strictEqual(api.state.practice.picked, api.UNKNOWN, '「わからない」が選択として記録');
assert(api.isWeak(qu.id), '「わからない」は弱点入り');
const pA = api.store.logs.find(l => l.source === 'practice' && l.part === qu.part && l.date === api.todayISO());
assert(pA.total === tB + 1 && pA.correct === cB, '正答率は不正解計上（totalのみ+1）');
assert(elements.main.innerHTML.includes('わからない'), '選択肢にわからないが表示される');
assert(elements.main.innerHTML.includes('正解:') && elements.main.innerHTML.includes('解説'), '結果画面に正解＋解説');
console.log('OK 「わからない」=不正解扱い（弱点・不正解計上）＋正解/解説表示');

// 13) 中断・再開: セッションがlocalStorageに保存され、再起動後に続きから
api.resetProgress();
api.pickExam('6_aki'); api.startPractice('year');
api.answerQuiz(api.BANK_BY_ID[api.state.practice.queue[0]].answer);
api.nextQuiz();                          // idx=1 まで進める
assert(api.validSession() && api.store.session.idx === 1, 'セッションが保存されidx=1');
api = boot();                            // アプリ再起動をシミュレート
assert(api.validSession() && api.store.session.idx === 1, '再起動後もセッション永続');
api.go('practice');
assert(elements.main.innerHTML.includes('前回の続きから'), '演習トップに再開ボタン');
api.resumeSession();
assert(api.state.practice && api.state.practice.idx === 1, '中断した問題から再開');
console.log('OK 中断・再開: セッション永続化→続きから再開');

// 14) 年度別進捗の集計＋UI
api.resetProgress();
api.pickExam('6_aki'); api.startPractice('year');
const cur = () => api.BANK_BY_ID[api.state.practice.queue[api.state.practice.idx]];
let cx = cur(); api.answerQuiz(cx.answer); api.nextQuiz();                                   // 正解1
let cy = cur(); api.answerQuiz(['ア', 'イ', 'ウ', 'エ'].find(k => k !== cy.answer)); api.nextQuiz(); // 弱点1
const pr = api.examProgress(6, 'aki');
assert(pr.included === api.BANK.length && pr.correct === 1 && pr.weak === 1 && pr.attempted === 2, '進捗集計: 正解1/弱点1/挑戦2');
api.endPractice(); api.go('summary');
assert(elements.main.innerHTML.includes('pbar'), '年度別サマリに進捗バー表示');
console.log('OK 年度別進捗: 集計＋プログレスバー表示');

// 15) 年度別タブ（旧グラフ）＝年度別サマリ、年度タップでその回の弱点復習
api.resetProgress();
const wq = api.BANK.find(q => q.year === 6 && q.term === 'aki');
api.applyResult(wq.id, false);                  // r6a に弱点を1つ作る
api.go('summary');
const smHtml = elements.main.innerHTML;
assert(smHtml.includes('年度別サマリ') && smHtml.includes('pbar'), '年度別タブに進捗バー');
assert(smHtml.includes("startYearReview(6,'aki')"), '弱点ある回はタップで復習開始');
assert(!smHtml.includes('<svg'), '折れ線グラフSVGは廃止');
api.startYearReview(6, 'aki');
assert(api.state.tab === 'practice' && api.state.practice.mode === 'review', '年度別復習が開始');
assert(api.state.practice.queue.length === 1 && api.state.practice.queue[0] === wq.id, 'その回の弱点のみ出題');
assert(api.validSession(), '年度別復習も中断・再開可能');
api.endPractice();
api.startYearReview(5, 'aki');                    // 収録なし=弱点0 → 開始しない
assert(api.state.practice === null, '弱点0の回はタップしても開始しない');
console.log('OK 年度別タブ＝サマリ／年度タップ復習（弱点のみ・中断再開・0件は非開始・SVG廃止）');

// 16) ホームから「直近の記録」を撤去（データ自体は保持・カレンダーでは表示）
api.go('home');
assert(!elements.main.innerHTML.includes('直近の記録'), 'ホームに直近の記録セクションなし');
assert(api.store.logs.length > 0, '学習ログのデータ自体は保持');
api.calSelect(api.todayISO()); api.go('cal');
assert(elements.main.innerHTML.includes('の記録'), 'カレンダーでは日別の記録を表示');
console.log('OK ホームの直近の記録を撤去（データ保持・カレンダーで利用）');

// 16b) 図表画像つき問題のUI表示（img対応）
api.resetProgress();
const iq = api.BANK[0]; const origImg = iq.img;
iq.img = 'questions/img/_test.png';
api.pickExam('6_aki'); api.startPractice('year'); api.go('practice');
assert(elements.main.innerHTML.includes('class="qimg"') && elements.main.innerHTML.includes('questions/img/_test.png'), '図表画像が表示される');
iq.img = origImg; api.endPractice();
console.log('OK 図表画像つき問題のUI表示（img対応）');

// 17) クラウド自動バックアップ（家計簿と同一仕様: 1日1回・sha更新・スキップ・force）
(async () => {
  const calls = [];
  global.fetch = async (url, opts = {}) => {
    calls.push({ url, method: opts.method || 'GET', body: opts.body });
    if (!opts.method) return { status: 200, ok: true, json: async () => ({ sha: 'abc' }) };
    return { ok: true, status: 200, json: async () => ({}) };
  };
  delete lsData['apstudy.cloudToken']; delete lsData['apstudy.cloudMeta'];
  let r = await api.cloudBackup();
  assert.strictEqual(r.skipped, 'no-token', 'トークン未設定はスキップ');
  lsData['apstudy.cloudToken'] = 'testtoken';
  r = await api.cloudBackup();
  assert(r.ok, 'バックアップ成功');
  assert.strictEqual(calls.length, 2, 'GET(sha取得)+PUT');
  assert(calls[1].url.includes('app-backups/contents/apstudy.json'), 'アップロード先 apstudy.json');
  assert(JSON.parse(calls[1].body).sha === 'abc', '既存ファイルのshaを指定');
  assert(JSON.parse(lsData['apstudy.cloudMeta']).last, 'バックアップ日を記録');
  r = await api.cloudBackup();
  assert.strictEqual(r.skipped, 'done-today', '同日2回目はスキップ');
  r = await api.cloudBackup(true);
  assert(r.ok, 'force指定は同日でも実行');
  console.log('OK クラウド自動バックアップ（1日1回・sha更新・スキップ・force）');

  // 18) かんたん設定コード（6桁→トークン復号）の往復。実コード・実トークンは使わずテスト専用暗号文で検証
  const enc = new TextEncoder();
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const km = await crypto.subtle.importKey('raw', enc.encode('123456'), 'PBKDF2', false, ['deriveKey']);
  const key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt, iterations: 310000, hash: 'SHA-256' }, km, { name: 'AES-GCM', length: 256 }, false, ['encrypt']);
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, enc.encode('github_pat_TESTTOKEN')));
  const blob = Buffer.concat([salt, iv, ct]).toString('base64');
  assert.strictEqual(await api.decryptWithPin('123456', blob), 'github_pat_TESTTOKEN', '正しいコードで復号できる');
  let pinFailed = false;
  try { await api.decryptWithPin('000000', blob); } catch (e) { pinFailed = true; }
  assert(pinFailed, '誤ったコードは復号失敗（AES-GCM認証エラー）');
  console.log('OK かんたん設定コード（復号往復・誤コード検出）');

  console.log('\n=== 全19項目 PASS ===');
})().catch(e => { console.error(e); process.exit(1); });
