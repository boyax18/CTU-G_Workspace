"""AR-6C7E.4: explicit, reversible local-dev-only Registration Review cutover.

Separate from, and never unlocks, P3D's frozen transition candidate.
Target: config.settings + local MySQL ctug_workspace, *not production*.
No routes, settings, schema, accounts, or email delivery are edited here.

WARNING: atomicity cannot replace a backup after a completed transaction.
"""

import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction

from apps.access_control.management.commands import (
    exercise_registration_review_activation_recovery_test_only as p3b,
    init_registration_review_inactive_bindings_local_dev as p2,
    init_registration_review_metadata_local_dev as p1,
    report_registration_review_release_gates_p3e as p3e,
    transition_registration_review_p3d as p3d,
)
from apps.access_control.models import AccessAuditLog

LOCAL_CONFIRM = "ctug_workspace:AR-6C7E4:LOCAL-ONLY-TRANSITION"
RISK_ACK = "I_ACCEPT_UNBACKED_LOCAL_DEVELOPMENT_RISK"


class LocalReleaseRefused(RuntimeError):
    """Release does not meet the exact authorized local-development contract."""


def _local_target():
    """No CLI override, alternate settings, remote DB, or accidental test DB."""
    if settings.SETTINGS_MODULE != "config.settings" or settings.DEBUG is not True:
        raise LocalReleaseRefused("Only config.settings in DEBUG local development is writable.")
    try:
        return p2._target(p2.DEV_CONFIRM)
    except Exception as exc:
        raise LocalReleaseRefused("Unexpected local target, routes, backend flags or isolation.") from exc


def _baseline_fingerprint(actor_id, expected_ids, fingerprint):
    if type(fingerprint) is not str or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None:
        raise LocalReleaseRefused("Pass the exact 64-character P3E release fingerprint.")
    try:
        result = p3e.inspect_release_gates(
            actor_account_id=actor_id,
            expected_admin_account_ids=expected_ids,
            expected_fingerprint=fingerprint,
        )
    except Exception as exc:
        raise LocalReleaseRefused("Preactivation authorization snapshot has drifted.") from exc
    if result["activation_released"] is not False:
        raise LocalReleaseRefused("P3D hard lock must remain intact.")
    return result["fingerprint"]


def _preview(mode, actor_id, expected_ids, fingerprint):
    if mode == "activate":
        return _baseline_fingerprint(actor_id, expected_ids, fingerprint)
    if mode == "compensate":
        try:
            p3d._check_compensation_preview(
                actor_account_id=actor_id, expected_admin_account_ids=expected_ids,
            )
        except Exception as exc:
            raise LocalReleaseRefused("Compensation preview refused.") from exc
        return None
    raise LocalReleaseRefused("Unknown transition mode.")


def _perform(*, mode, actor_id, expected_ids, fingerprint, confirmation):
    """Exactly five state flips + five receipts in one durable transaction.

    Test suites can patch ONLY _local_target to the disposable MySQL connection.
    The real CLI never accepts alternate DB/target arguments.
    """
    if mode not in ("activate", "compensate") or confirmation != LOCAL_CONFIRM:
        raise LocalReleaseRefused("Wrong transition mode or exact local release confirmation.")
    if type(actor_id) is not int or not (1 <= actor_id <= 2_147_483_647):
        raise LocalReleaseRefused("Invalid audit actor account ID.")
    try:
        scope = p3b._expected_ids(expected_ids)
    except Exception as exc:
        raise LocalReleaseRefused("Exact comma-separated Admin scope required.") from exc
    if actor_id not in scope:
        raise LocalReleaseRefused("Audit actor not in expected Admin scope.")
    db = _local_target()
    p3b._acquire_lock(db)
    try:
        with transaction.atomic(using=DEFAULT_DB_ALIAS, durable=True):
            before = mode == "compensate"
            actor, admin, services, permissions, bindings = p3b._snapshot(
                actor_id=actor_id, expected_ids=scope, active=before,
            )
            p3b._assert_effective_permissions(scope, active=before)
            if mode == "activate":
                _baseline_fingerprint(actor_id, expected_ids, fingerprint)
                p3b._assert_no_prior_transition_audits()
                for code in p1.SERVICE_CODES:
                    p3d._record_service(service=services[code], actor=actor, activate=True)
                for code in p1.PERMISSION_CODES:
                    permission = permissions[code]
                    p3d._record_binding(
                        binding=bindings[permission.pk], permission=permission,
                        actor=actor, admin=admin, activate=True,
                    )
            else:
                p3b._verify_receipts(
                    event_service=p3b.SERVICE_ACTIVATE,
                    event_binding=p3b.BINDING_ACTIVATE,
                    actor=actor, admin=admin, services=services,
                    permissions=permissions, bindings=bindings,
                    before=False, after=True,
                )
                if AccessAuditLog.objects.filter(
                    action__in=(p3b.SERVICE_DEACTIVATE, p3b.BINDING_DEACTIVATE)
                ).exists():
                    raise LocalReleaseRefused("Existing compensation receipt; manual review required.")
                # Stop granting before disabling services; neither restores decisions.
                for code in p1.PERMISSION_CODES:
                    permission = permissions[code]
                    p3d._record_binding(
                        binding=bindings[permission.pk], permission=permission,
                        actor=actor, admin=admin, activate=False,
                    )
                for code in p1.SERVICE_CODES:
                    p3d._record_service(service=services[code], actor=actor, activate=False)

            after = not before
            p3b._snapshot(actor_id=actor_id, expected_ids=scope, active=after)
            p3b._verify_receipts(
                event_service=p3b.SERVICE_ACTIVATE,
                event_binding=p3b.BINDING_ACTIVATE,
                actor=actor, admin=admin, services=services,
                permissions=permissions, bindings=bindings,
                before=False, after=True,
            )
            if mode == "compensate":
                p3b._verify_receipts(
                    event_service=p3b.SERVICE_DEACTIVATE,
                    event_binding=p3b.BINDING_DEACTIVATE,
                    actor=actor, admin=admin, services=services,
                    permissions=permissions, bindings=bindings,
                    before=True, after=False,
                )
            elif AccessAuditLog.objects.filter(
                action__in=(p3b.SERVICE_DEACTIVATE, p3b.BINDING_DEACTIVATE)
            ).exists():
                raise LocalReleaseRefused("Unexpected compensation receipt.")
            p3b._assert_effective_permissions(scope, active=after)
            _local_target()  # Recheck real target/disabled gates before commit.
        return "LOCAL_ACTIVATED" if mode == "activate" else "LOCAL_COMPENSATED"
    finally:
        p3b._release_lock(db)


class Command(BaseCommand):
    help = "LOCAL DEV ONLY: preview/activate/compensate exact Registration Review permissions."

    def add_arguments(self, parser):
        parser.add_argument("--mode", choices=("activate", "compensate"), required=True)
        parser.add_argument("--actor-account-id", type=int, required=True)
        parser.add_argument("--expected-admin-account-ids", required=True)
        parser.add_argument("--expected-fingerprint", help="Exact P3E SHA-256 for activation.")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--confirm-local-release", default="")
        parser.add_argument("--risk-ack", default="")

    def handle(self, *args, **options):
        mode = options["mode"]
        actor = options["actor_account_id"]
        ids = options["expected_admin_account_ids"]
        fp = options["expected_fingerprint"]
        try:
            _local_target()
            if not options["apply"]:
                _preview(mode, actor, ids, fp)
                self.stdout.write(
                    f"AR-6C7E.4: PREVIEW PASSED; mode={mode}; NO WRITES EXECUTED; "
                    "normal API/routes/UI remain disabled."
                )
                return
            if options["confirm_local_release"] != LOCAL_CONFIRM:
                raise LocalReleaseRefused("Exact local release confirmation required.")
            if options["risk_ack"] != RISK_ACK:
                raise LocalReleaseRefused("Explicit no-backup local risk acknowledgement required.")
            outcome = _perform(
                mode=mode, actor_id=actor,
                expected_ids=ids, fingerprint=fp,
                confirmation=options["confirm_local_release"],
            )
        except Exception as exc:
            raise CommandError(
                "AR-6C7E.4: REFUSED or rolled back; NO SUCCESS reported. "
                "Do not retry without inspecting the current DB state."
            ) from exc
        self.stdout.write(
            f"AR-6C7E.4: {outcome}; exact_admin_scope={ids}; "
            "five auditable state changes; normal API routes still unmounted."
        )
