"""Deployment checks never accept self-reported security evidence as proof."""

from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def protected_executor_release_checks(app_configs, **kwargs):
    errors = []
    if getattr(settings, "WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER", False) is not True:
        errors.append(Error(
            "Protected writer enforcement is not enabled with an exact boolean True.",
            hint="Coordinate the executor rollout; enabling this gate currently stops covered writes.",
            id="access_control.E201",
        ))
    try:
        from .executor.diagnostics import verify_deployment
        verify_deployment()
    except Exception:
        errors.append(Error(
            "Task 2 production storage, credentials, signed trust or executor readiness is unverified.",
            hint="Deploy approved security SQL and enrolled identities; isolated tests cannot authorize production.",
            id="access_control.E202",
        ))
    return errors
