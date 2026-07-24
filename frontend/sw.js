// 玄照 PWA Service Worker
// 离线缓存策略:
// - 静态资源 (CSS/JS/icons): cache-first
// - API 请求 (/api/*): network-first, 失败降级到错误提示
// - HTML 页面: network-first, 降级到 cached version

const CACHE_VERSION = 'v1.0.0-2026-07-23';
const STATIC_CACHE = `xuanzhao-static-${CACHE_VERSION}`;
const API_CACHE = `xuanzhao-api-${CACHE_VERSION}`;

const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/static/css/style.css',
  '/static/js/api.js',
  '/chart',
  '/perspectives',
  '/debate',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => {
      return cache.addAll(STATIC_ASSETS).catch(err => {
        console.warn('[SW] 静态资源预缓存部分失败:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(k => k !== STATIC_CACHE && k !== API_CACHE)
            .map(k => caches.delete(k))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // 只处理同源请求
  if (url.origin !== location.origin) return;

  // API 请求: network-first, 失败降级
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // 只缓存 GET 成功的 200 响应
          if (event.request.method === 'GET' && response.status === 200) {
            const clone = response.clone();
            caches.open(API_CACHE).then(c => c.put(event.request, clone));
          }
          return response;
        })
        .catch(() => {
          // 离线时返回上次缓存
          return caches.match(event.request).then(r => {
            if (r) return r;
            return new Response(
              JSON.stringify({error: 'offline', message: '玄照服务离线, 请连接网络'}),
              {status: 503, headers: {'Content-Type': 'application/json'}}
            );
          });
        })
    );
    return;
  }

  // 静态资源 + HTML: cache-first 兜底
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        if (response.status === 200 && event.request.method === 'GET') {
          const clone = response.clone();
          caches.open(STATIC_CACHE).then(c => c.put(event.request, clone));
        }
        return response;
      }).catch(() => {
        // 完全离线, 静态资源没缓存
        if (event.request.destination === 'document') {
          return caches.match('/');
        }
      });
    })
  );
});