// Service worker do Lex Vade Mecum: permite instalar o site como aplicativo.
// Não guarda cópia de nada: toda página e toda lei vêm sempre da rede,
// para que o texto exibido seja sempre o vigente.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', (e) => {
  if (e.request.mode === 'navigate') e.respondWith(fetch(e.request));
});
