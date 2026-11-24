"""WF-03.01 Option A: refuse direct network connections to local Django.

Vite's same-origin API proxy connects to Django via 127.0.0.1. If the
operator accidentally exposes Django on 0.0.0.0, non-loopback requests
are rejected before any session or application endpoint is invoked.
"""
from django.http import JsonResponse


class LANDevLoopbackProxyGuard:
    _LOOPBACK_CLIENTS = frozenset({"127.0.0.1", "::1"})

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Never trust X-Forwarded-For to determine whether a request is local.
        if request.META.get("REMOTE_ADDR") not in self._LOOPBACK_CLIENTS:
            return JsonResponse({"error": {"code": "lan_test_proxy_only",
                                           "message": "Use the approved frontend address."}}, status=403)
        return self.get_response(request)
