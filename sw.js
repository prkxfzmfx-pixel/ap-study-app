// ネットワーク優先・失敗時キャッシュ（オフラインでも起動できるように）
const CACHE = 'apstudy-v11';
const ASSETS = ['./', './index.html', './manifest.webmanifest',
  './questions/manifest.js', './questions/r6a.js', './questions/r7a.js',
  './questions/img/r7a-q1.png',
  './questions/img/r7a-q10.png', './questions/img/r7a-q15.png',
  './questions/img/r7a-q19.png', './questions/img/r7a-q20.png',
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
  e.respondWith(
    fetch(e.request).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(e.request, copy));
      return res;
    }).catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
