/* The site's service worker (Stage 80 item 62, the 2026-10-13 UI/UX
   audit's F14): the site can be installed, and a phone with no signal
   opens the last board it saw instead of the browser's error page.

   The build (src/site/build.py add_offline) publishes this file at the
   site's root, so it covers all four pages, with SITE_BUILD replaced by a
   hash of the four built pages: every deploy is a new worker, which drops
   the old copies when it takes over.

   A page is always asked of the network first, so a visitor with a
   connection never sees an old board; only when that fails is the copy
   kept from the last visit used. The site's own small files (icons, the
   manifest) are kept from the install. Nothing from another host (ESPN's
   logos and live scores) is touched: it goes to the network as before. */
const SITE_BUILD = '__SITE_BUILD__';
const CACHE = `sportalytics-${SITE_BUILD}`;
const PAGES = ['./', 'nfl/', 'nhl/', 'nba/'];
const FILES = ['assets/site.webmanifest', 'assets/favicon.svg', 'assets/favicon-nhl.svg', 'assets/favicon-nba.svg',
  'assets/apple-touch-icon.png', 'assets/icon-192.png', 'assets/icon-512.png'];

/* A page's copy is kept under its address without the #route or ?query. */
function pageKey(url){
  const u = new URL(url);
  return u.origin + u.pathname.replace(/index\.html$/, '');
}

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PAGES.concat(FILES))).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k.startsWith('sportalytics-') && k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if(req.method !== 'GET') return;
  const url = new URL(req.url);
  if(url.origin !== self.location.origin) return;
  if(req.mode === 'navigate'){
    const key = pageKey(req.url);
    e.respondWith(fetch(req)
      .then(res => {
        if(res.ok){ const copy = res.clone(); caches.open(CACHE).then(c => c.put(key, copy)); }
        return res;
      })
      .catch(() => caches.open(CACHE).then(c => c.match(key).then(hit => hit || c.match(new URL('./', self.registration.scope).href))))
      .then(res => res || Response.error()));
    return;
  }
  e.respondWith(caches.match(req).then(hit => hit || fetch(req)));
});
