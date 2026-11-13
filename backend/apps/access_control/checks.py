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
    # There is no approved production ledger schema, trust enrollment or trusted
    # executor integration. Neither a flag nor a caller-supplied certificate can
    # turn an isolated rehearsal into deployment authorization.
    errors.append(Error(
        "Task 2 production executor, durable evidence and institutional release gates remain unverified.",
        hint="See docs/implementation/access-control/CORE_TASK_2_COMPLETION_REPORT.md; live protected apply is disabled.",
        id="access_control.E202",
    ))
    return errors
