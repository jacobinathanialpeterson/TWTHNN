const DB_NAME = 'GameFilesDB';
const DB_VERSION = 1;
const STORE_NAME = 'files';

// Open IndexedDB
function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'path' });
      }
    };
  });
}

// Get file from IndexedDB by path
async function getFile(db, path) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const req = store.get(path);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

// Guess content type from extension
function getContentType(path) {
  const ext = path.split('.').pop().toLowerCase();
  if (ext === 'html' || ext === 'htm') return 'text/html';
  if (ext === 'js') return 'application/javascript';
  if (ext === 'css') return 'text/css';
  if (ext === 'json') return 'application/json';
  if (['png','jpg','jpeg','gif','bmp','webp'].includes(ext)) return 'image/' + (ext === 'jpg' ? 'jpeg' : ext);
  if (ext === 'svg') return 'image/svg+xml';
  if (ext === 'wasm') return 'application/wasm';
  return 'application/octet-stream';
}

self.addEventListener('install', event => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  const pathParts = url.pathname.split('/').filter(Boolean);

  // Only handle URLs under /play/{gameId}/
  if (pathParts.length < 2 || pathParts[0] !== 'play') {
    return; // Not our scope, let network handle
  }

  const filePath = pathParts.slice(1).join('/'); // e.g. "0019/Build/UnityLoader.js"

  event.respondWith((async () => {
    try {
      const db = await openDb();
      const fileEntry = await getFile(db, filePath);
      if (!fileEntry) {
        // Not found in IndexedDB, fallback to network
        return fetch(event.request);
      }
      const blob = fileEntry.blob;
      const contentType = getContentType(filePath);

      return new Response(blob, {
        status: 200,
        headers: { 'Content-Type': contentType }
      });
    } catch (e) {
      // On error fallback to network
      return fetch(event.request);
    }
  })());
});
