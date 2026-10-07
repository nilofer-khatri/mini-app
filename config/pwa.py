from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static


def manifest(request):
    data = {
        "id": "/",
        "name": "SalonSlotly",
        "short_name": "SalonSlotly",
        "description": "Book salon appointments online",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#eff6ff",
        "theme_color": "#1e3a8a",
        "icons": [
            {"src": static("icons/icon-192.png"), "sizes": "192x192",
             "type": "image/png", "purpose": "any"},
            {"src": static("icons/icon-512.png"), "sizes": "512x512",
             "type": "image/png", "purpose": "any"},
            {"src": static("icons/icon-512.png"), "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
    }
    return JsonResponse(data, content_type="application/manifest+json")


# The service worker only shows an "offline" page when there is no internet.
# It never stores booking pages, so availability is always live.
SERVICE_WORKER = """
const CACHE = 'salonslotly-offline-v1';
const OFFLINE_URL = '/offline/';

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.add(OFFLINE_URL)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(() => caches.match(OFFLINE_URL)));
  }
});
"""


def service_worker(request):
    response = HttpResponse(SERVICE_WORKER, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-cache"
    return response


def offline(request):
    return render(request, "offline.html")