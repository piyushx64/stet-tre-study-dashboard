/* PrepPath app shell: keep authenticated pages and study data network-only. */
const VERSION = "preppath-app-v1";
self.addEventListener("install", event => { self.skipWaiting(); });
self.addEventListener("activate", event => { event.waitUntil((async () => { const keys = await caches.keys(); await Promise.all(keys.filter(key => key.startsWith("preppath-") && key !== VERSION).map(key => caches.delete(key))); await self.clients.claim(); })()); });
self.addEventListener("fetch", event => { const url = new URL(event.request.url); if (url.origin !== self.location.origin || event.request.method !== "GET") return; if (url.pathname.startsWith("/api/") || url.pathname === "/login" || url.pathname.startsWith("/admin")) return; /* Do not cache personalized dashboard HTML or API responses. */ });
