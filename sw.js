// ネットワーク優先・失敗時キャッシュ（オフラインでも起動できるように）。
// 問題ファイル(questions/*.js)・図表(questions/img/*)は数千規模になりうるため precache せず、
// fetch ハンドラの実行時キャッシュ（ネットワーク優先→成功レスポンスを都度キャッシュ）に任せる。
// precache する ASSETS はアプリシェル（起動に必須の少数ファイル）だけに絞る。
const CACHE = 'apstudy-v15';
const ASSETS = ['./', './index.html', './manifest.webmanifest',
  './questions/manifest.js',
  './icons/icon-192.png', './icons/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== self.location.origin) return; // 同一オリジンのみ扱う
  e.respondWith(
    fetch(e.request).then(res => {
      if (res && res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
      }
      return res;
    }).catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
