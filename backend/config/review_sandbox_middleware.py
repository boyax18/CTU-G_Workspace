"""Do not serve sandbox routes to non-loopback clients, regardless of Host headers."""

from ipaddress import ip_address

from django.http import HttpResponseForbidden


class LoopbackOnlyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # REMOTE_ADDR is the socket peer supplied by the server; do not trust
        # X-Forwarded-For or forwarded Host values for this decision.
        raw = request.META.get("REMOTE_ADDR", "")
        try:
            address = ip_address(raw)
            allowed = address.is_loopback or bool(
                getattr(address, "ipv4_mapped", None)
                and address.ipv4_mapped.is_loopback
            )
        except ValueError:
            allowed = False
        if not allowed:
            return HttpResponseForbidden("Local sandbox only.")
        return self.get_response(request)
