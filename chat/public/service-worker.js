/**
 * Vectora — Service Worker (J.2.4)
 *
 * Estratégia mínima para a versão 1 do PWA:
 *
 * - Cache do app shell: HTML, manifest e ícones (precache na install).
 * - HTML: network-first com fallback de cache (mantém o shell servido
 *   offline; quando há rede, sempre busca a versão mais nova).
 * - Assets versionados em /_next/static/: cache-first (Next.js gera
 *   hashes únicos por build; a URL muda quando o conteúdo muda).
 * - Tudo o mais (APIs, SSE, WebSocket): passa direto sem cache. O chat
 *   exige tempo real; cache atrapalharia.
 *
 * Versão do cache: bumpada quando o shape muda. Caches antigos são
 * limpos no `activate`.
 */

const CACHE_VERSION = "vectora-v1";
const SHELL_CACHE = `${CACHE_VERSION}-shell`;
const STATIC_CACHE = `${CACHE_VERSION}-static`;

const SHELL_URLS = [
  "/",
  "/manifest.json",
  "/favicon-32x32.png",
  "/favicon-600x600.png",
  "/vectora.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(SHELL_URLS))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((k) => !k.startsWith(CACHE_VERSION))
            .map((k) => caches.delete(k)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // APIs, SSE, WebSocket — não cacheia.
  if (
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/auth/") ||
    url.pathname.includes("/vectora.terminal.v1/")
  ) {
    return;
  }

  // Assets versionados do Next: cache-first (hash garante invalidação).
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(
      caches.match(req).then(
        (hit) =>
          hit ||
          fetch(req).then((res) => {
            const clone = res.clone();
            caches
              .open(STATIC_CACHE)
              .then((cache) => cache.put(req, clone))
              .catch(() => {
                /* quota cheia — segue sem cache */
              });
            return res;
          }),
      ),
    );
    return;
  }

  // Navegações HTML: network-first com fallback ao shell.
  const acceptsHtml = req.headers.get("accept")?.includes("text/html");
  if (req.mode === "navigate" || acceptsHtml) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const clone = res.clone();
          caches
            .open(SHELL_CACHE)
            .then((cache) => cache.put(req, clone))
            .catch(() => {});
          return res;
        })
        .catch(() => caches.match(req).then((hit) => hit || caches.match("/"))),
    );
    return;
  }
});
