/**
 * Service Worker for AI Publisher Pro
 * Provides offline support, caching, and background sync
 */

const CACHE_NAME = 'ai-publisher-v2.7.0';
const STATIC_CACHE = 'static-v2.7.0';
const DYNAMIC_CACHE = 'dynamic-v2.7.0';

// Static assets to cache on install
const STATIC_ASSETS = [
  '/ui',
  '/ui/app.html',
  '/ui/app/main.js',
  '/ui/app/styles.css',
  '/ui/app/websocket.js',
  '/ui/app/editor.js',
  '/ui/app/modal.css',
  '/ui/app/toggle.css',
  '/ui/shared/navbar.css',
  '/ui/manifest.json',
  // External CDN resources (cache for offline)
  'https://cdn.tailwindcss.com',
  'https://unpkg.com/lucide@latest/dist/umd/lucide.js',
];

// API routes to cache dynamically
const CACHEABLE_API_ROUTES = [
  '/profiles',
  '/health',
];

// Routes that should always go to network
const NETWORK_ONLY_ROUTES = [
  '/translate',
  '/upload',
  '/api/jobs',
  '/ws',
  '/api/auth',
];

/**
 * Install event - cache static assets
 */
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Caching static assets');
        return cache.addAll(STATIC_ASSETS.filter(url => url.startsWith('/')));
      })
      .then(() => {
        // Skip waiting to activate immediately
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Cache install failed:', error);
      })
  );
});

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => {
              // Delete old cache versions
              return name !== STATIC_CACHE &&
                     name !== DYNAMIC_CACHE &&
                     name !== CACHE_NAME;
            })
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => {
        // Take control of all clients
        return self.clients.claim();
      })
  );
});

/**
 * Fetch event - handle requests with caching strategies
 */
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip WebSocket connections
  if (url.protocol === 'ws:' || url.protocol === 'wss:') {
    return;
  }

  // Network-only routes
  if (isNetworkOnlyRoute(url.pathname)) {
    event.respondWith(networkOnly(request));
    return;
  }

  // Static assets - cache first
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // API routes - network first with cache fallback
  if (isCacheableAPIRoute(url.pathname)) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Default - stale while revalidate
  event.respondWith(staleWhileRevalidate(request));
});

/**
 * Check if route should only use network
 */
function isNetworkOnlyRoute(pathname) {
  return NETWORK_ONLY_ROUTES.some(route => pathname.startsWith(route));
}

/**
 * Check if URL is a static asset
 */
function isStaticAsset(pathname) {
  const staticExtensions = ['.js', '.css', '.png', '.jpg', '.svg', '.woff', '.woff2'];
  return staticExtensions.some(ext => pathname.endsWith(ext)) ||
         pathname.startsWith('/ui/');
}

/**
 * Check if API route is cacheable
 */
function isCacheableAPIRoute(pathname) {
  return CACHEABLE_API_ROUTES.some(route => pathname.startsWith(route));
}

/**
 * Cache-first strategy
 */
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.error('[SW] Cache-first fetch failed:', error);
    return new Response('Offline', { status: 503 });
  }
}

/**
 * Network-first strategy with cache fallback
 */
async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    return new Response(JSON.stringify({ error: 'Offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Network-only strategy
 */
async function networkOnly(request) {
  try {
    return await fetch(request);
  } catch (error) {
    return new Response(JSON.stringify({ error: 'Network unavailable' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Stale-while-revalidate strategy
 */
async function staleWhileRevalidate(request) {
  const cache = await caches.open(DYNAMIC_CACHE);
  const cached = await cache.match(request);

  const fetchPromise = fetch(request)
    .then((response) => {
      if (response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => cached);

  return cached || fetchPromise;
}

/**
 * Background sync for failed uploads
 */
self.addEventListener('sync', (event) => {
  console.log('[SW] Sync event:', event.tag);

  if (event.tag === 'upload-retry') {
    event.waitUntil(retryFailedUploads());
  }
});

/**
 * Retry failed uploads from IndexedDB
 */
async function retryFailedUploads() {
  // This would integrate with IndexedDB to retry failed uploads
  console.log('[SW] Retrying failed uploads...');
  // Implementation depends on how uploads are stored
}

/**
 * Push notification handling
 */
self.addEventListener('push', (event) => {
  if (!event.data) return;

  const data = event.data.json();
  console.log('[SW] Push received:', data);

  const options = {
    body: data.body || 'New notification',
    icon: '/ui/icons/icon-192x192.png',
    badge: '/ui/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: data.data || {},
    actions: data.actions || [],
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'AI Publisher Pro', options)
  );
});

/**
 * Notification click handling
 */
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.action);

  event.notification.close();

  const urlToOpen = event.notification.data?.url || '/ui';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Focus existing window if available
        for (const client of clientList) {
          if (client.url.includes('/ui') && 'focus' in client) {
            return client.focus();
          }
        }
        // Open new window
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

/**
 * Message handling from main app
 */
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);

  switch (event.data.type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;

    case 'CLEAR_CACHE':
      caches.keys().then((names) => {
        names.forEach((name) => caches.delete(name));
      });
      break;

    case 'CACHE_URLS':
      if (event.data.urls) {
        caches.open(DYNAMIC_CACHE).then((cache) => {
          cache.addAll(event.data.urls);
        });
      }
      break;
  }
});

console.log('[SW] Service worker loaded');
