"""Outer gate for HTTPS role-context dev: only the local HTTPS Vite proxy.

Django itself is bound to 127.0.0.1. The trusted proxy is required to replace
X-Forwarded-Proto with 'https' on *every* proxied API request. This header
cannot be used to prove real TLS by itself; never expose Django on LAN.
"""
from django.http import JsonResponse


class HTTPSLANProxyGuard:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (request.META.get("REMOTE_ADDR") not in {"127.0.0.1", "::1"}
                or request.META.get("HTTP_X_FORWARDED_PROTO") != "https"):
            return JsonResponse(
                {"error": {"code": "https_lan_proxy_only",
                           "message": "Use the approved HTTPS frontend address."}},
                status=403,
            )
        return self.get_response(request)
