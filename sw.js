/* ============================================================
   سبائك الفخامة — Service Worker
   إستراتيجية:
   - الصفحة (نavigate): الشبكة أولاً ثم ذاكرة التخزين (تحديث فوري عند التوفر)
   - الأصول (assets): ذاكرة أولاً مع تحديث في الخلفية (سريع جداً)
   يعمل على GitHub Pages ضمن مسار فرعي (نطاق نسبي ./)
   ============================================================ */
'use strict';

const VERSION = 'sabaaek-cache-v2';
const PRECACHE = [
  './',
  './index.html',
  './manifest.webmanifest',
  './assets/favicon.svg',
  './assets/icon-192.png',
  './assets/icon-512.png',
  './assets/apple-touch-icon.png',
  './assets/og-image.png',
  './assets/sabaaek-logo-user.png',
  './assets/sabaaek-site-qr.png',
  './assets/sabaaek-official-logo-alpha.png',
  './assets/sabaaek-official-logo-transparent-web.png',
  './assets/saudi-riyal.svg'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(VERSION)
      .then(cache => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

async function networkFirst(request) {
  try {
    const res = await fetch(request);
    if (res && res.ok) {
      const copy = res.clone();
      caches.open(VERSION).then(cache => cache.put(request, copy));
    }
    return res;
  } catch {
    const cached = await caches.match(request);
    if (cached) return cached;
    return caches.match('./index.html');
  }
}

async function staleWhileRevalidate(request) {
  const cached = await caches.match(request);
  const update = fetch(request).then(res => {
    if (res && res.ok) {
      const copy = res.clone();
      caches.open(VERSION).then(cache => cache.put(request, copy));
    }
    return res;
  }).catch(() => null);
  return cached || update;
}

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // طلبات واجهات الأسعار تُترك للمتصفح مباشرة

  if (req.mode === 'navigate') {
    event.respondWith(networkFirst(req));
  } else {
    event.respondWith(staleWhileRevalidate(req));
  }
});
