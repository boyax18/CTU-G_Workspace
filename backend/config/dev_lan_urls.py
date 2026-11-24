"""URLconf for config.dev_lan_settings: registry-approved feature routes + normal routes.

Routes come only from config.dev_features for the active profile. config.urls
itself is unchanged and still never mounts decision or governance mutations.
"""

from django.conf import settings
from django.urls import include, path

from .dev_features import profile_routes
from .urls import urlpatterns as normal_patterns

urlpatterns = [
    *(path(prefix, include(module)) for prefix, module in profile_routes(settings.WORKSPACE_DEV_PROFILE)),
    *normal_patterns,
]
