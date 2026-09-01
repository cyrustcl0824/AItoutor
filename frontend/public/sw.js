const CACHE = "aitutor-read-v2";
const OLD_CACHES = ["aitutor-read-v1"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(["/manifest.webmanifest"])));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(Promise.all(OLD_CACHES.map((name) => caches.delete(name))));
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (url.pathname === "/") {
    event.respondWith(fetch(event.request).then((response) => {
      caches.open(CACHE).then((cache) => cache.put(event.request, response.clone()));
      return response;
    }).catch(() => caches.match(event.request)));
    return;
  }
  if (url.pathname.includes("/textbooks/pages/") || url.pathname.endsWith("manifest.webmanifest")) {
    event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request).then((response) => {
      caches.open(CACHE).then((cache) => cache.put(event.request, response.clone()));
      return response;
    })));
  }
});
