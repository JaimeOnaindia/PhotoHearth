// Private photos, API responses and session data are never persisted in Cache Storage.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  if (event.request.mode !== 'navigate') return;
  event.respondWith(fetch(event.request).catch(() => new Response(
    '<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>PhotoHearth · Sin conexión</title><body style="font-family:system-ui;background:#faf9f6;color:#405b49;padding:12vh 8vw;line-height:1.7"><h1>Tu hogar está desconectado.</h1><p>Conecta con la red de tu servidor para volver a ver tus recuerdos.</p><p>Tus fotos siguen en casa. No se han guardado copias en este dispositivo.</p><a href="/">Volver a intentar</a></body></html>',
    { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' } },
  )));
});
