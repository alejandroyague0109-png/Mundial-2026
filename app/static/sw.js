// Service Worker Básico para PWA
const CACHE_NAME = 'figus26-v1';

// 1. Instalación: Guardamos cosas básicas (Opcional, por ahora vacío para no dar problemas)
self.addEventListener('install', (event) => {
    self.skipWaiting();
    console.log('👷 Service Worker Instalado');
});

// 2. Activación
self.addEventListener('activate', (event) => {
    console.log('✅ Service Worker Activo');
});

// 3. Intercepción de red (Estrategia: Network First / Red Primero)
// Esto asegura que el usuario siempre vea datos frescos del Mercado.
self.addEventListener('fetch', (event) => {
    event.respondWith(
        fetch(event.request).catch(() => {
            // Si no hay internet, podríamos mostrar una página offline aquí
            // Por ahora, dejamos que el navegador maneje el error
            return caches.match(event.request);
        })
    );
});