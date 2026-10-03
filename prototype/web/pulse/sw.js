// Club Pulse — service worker minimal : l'enveloppe de l'application fonctionne hors ligne ; les DONNÉES jamais mises en
// cache (elles sont personnelles et doivent rester à jour). Hors ligne, l'application le dit au lieu d'afficher du périmé.
const ENVELOPPE = "club-pulse-v3";
const FICHIERS = ["/app", "/static/pulse/pulse.css", "/static/pulse/tokens.css", "/static/pulse/icone.svg", "/static/pulse/traduction-de.js", "/app/manifest.webmanifest",
  "/static/pulse/polices/plus-jakarta-sans-latin-wght-normal.woff2", "/static/pulse/polices/plus-jakarta-sans-latin-ext-wght-normal.woff2",
  "/static/pulse/polices/jetbrains-mono-latin-400-normal.woff2", "/static/pulse/polices/jetbrains-mono-latin-500-normal.woff2"];
self.addEventListener("install", (e) => e.waitUntil(caches.open(ENVELOPPE).then((c) => c.addAll(FICHIERS)).then(() => self.skipWaiting())));
self.addEventListener("activate", (e) => e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== ENVELOPPE).map((k) => caches.delete(k))))));
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.pathname.startsWith("/api/")) return;       // API : toujours le réseau
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request, { ignoreSearch: true })));
});
