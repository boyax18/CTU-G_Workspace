"""WF-11.01 dependency contract: activation prerequisites, closure obligations, edit impact.

Each check is a small read-side *source* that reports what it can actually establish:

* Prerequisites (activation, WF11-D03): ``ready`` / ``missing`` / ``unavailable``.
* Obligations (closure/archive, WF11-D11/D12) and impact (Active edits and historical corrections,
  WF11-D05/D06): ``evaluated`` with a real count, or ``unavailable``. An unimplemented module is
  NEVER reported as zero.

Inspected 25 Nov 2026: apps.clearance and apps.group_rating define no models; no Student semester
participation (WF-05.05), fee obligation, clearance or signature record exists. The default bundle
therefore reports those sources as ``unavailable``, which keeps every edit whose impact cannot be
evaluated refused at runtime. Academic offerings are real since academic.0003
(``OfferingPrerequisite``) and the approved semester fee since finance.0001
(``ApprovedFeePrerequisite``); activation still also needs its own switch and HDAC. When
a dependent module is implemented, replace its ``Unavailable*`` entry in ``DEFAULT_BUNDLE`` with a
real read-only adapter; nothing else changes.

A substitute bundle is honoured ONLY on the verified disposable test database (``isolated``). It
never writes records and the real date prerequisite is always applied in addition to it.
"""

import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connections

READY, MISSING, UNAVAILABLE, EVALUATED = "ready", "missing", "unavailable", "evaluated"
REQUIRED_PREREQUISITES = ("approved_fee", "academic_offerings")
CLOSURE_OBLIGATIONS = ("outstanding_clearance_signatures", "unpaid_fee_obligations", "incomplete_onboarding")
IMPACT_RECORDS = ("student_participation", "fee_obligations", "clearance_records")
_TEST_DATABASE = re.compile(r"test_ctug_registration_[0-9a-f]{16}")


class DependencyUnavailable(Exception):
    """A capability depends on a module or institutional source that does not exist yet."""


@dataclass(frozen=True)
class CheckResult:
    key: str
    status: str
    reason: str = ""

    def as_dict(self):
        return {"key": self.key, "status": self.status, "reason": self.reason}


@dataclass(frozen=True)
class CountResult:
    key: str
    status: str
    count: int | None = None
    reason: str = ""

    def as_dict(self):
        return {"key": self.key, "status": self.status, "count": self.count, "reason": self.reason}


class DatesPrerequisite:
    """Real and always applied: both dates configured and start strictly before end."""

    key = "valid_dates"

    def evaluate(self, semester):
        start, end = semester.start_date, semester.end_date
        if start is None or end is None:
            return CheckResult(self.key, MISSING, "dates_incomplete")
        if not start < end:
            return CheckResult(self.key, MISSING, "dates_invalid")
        return CheckResult(self.key, READY)


class OfferingPrerequisite:
    """Real read-only check (academic configuration, migration 0003): at least one offering that is
    valid for THIS semester. Every relationship is re-validated (term, curriculum course/year level,
    Published/Superseded curriculum, Active subject and section). Instructor gaps do not block
    activation: they block the individual Student's later subject confirmation instead."""

    key = "academic_offerings"

    def evaluate(self, semester):
        from .configuration import valid_offerings
        if not valid_offerings(semester.pk).exists():
            return CheckResult(self.key, MISSING, "no_valid_offerings")
        return CheckResult(self.key, READY)


class ApprovedFeePrerequisite:
    """Real read-only check (finance migration 0001): the semester's genuinely approved full
    organizational fee. Delegates to apps.finance.fees.fee_readiness, which distinguishes not
    configured, awaiting approval, disabled, inactive service, inconsistent and unreadable states.
    An approved ₱0.00 is ready; a missing fee never is. Grants no fee-setting authority."""

    key = "approved_fee"

    def evaluate(self, semester):
        from apps.finance.fees import fee_readiness
        return fee_readiness(semester)


class UnavailablePrerequisite:
    def __init__(self, key, reason):
        self.key, self.reason = key, reason

    def evaluate(self, semester):
        return CheckResult(self.key, UNAVAILABLE, self.reason)


class UnavailableCount:
    def __init__(self, key, reason):
        self.key, self.reason = key, reason

    def evaluate(self, semester):
        return CountResult(self.key, UNAVAILABLE, None, self.reason)


@dataclass(frozen=True)
class DependencyBundle:
    prerequisites: tuple
    obligations: tuple
    impact: tuple


DEFAULT_BUNDLE = DependencyBundle(
    prerequisites=(
        # Real since finance.0001. Fee approval itself needs finance.fee_schedule.manage through a
        # genuine Admin role grant (governance pending), so without one no fee can be approved.
        ApprovedFeePrerequisite(),
        # Real since the academic configuration foundation. A query failure (e.g. tables not yet
        # migrated) is reported "unavailable" by _by_key, never as ready.
        OfferingPrerequisite(),
    ),
    obligations=(
        UnavailableCount("outstanding_clearance_signatures", "clearance_not_implemented"),
        UnavailableCount("unpaid_fee_obligations", "fee_obligations_not_implemented"),
        UnavailableCount("incomplete_onboarding", "semester_onboarding_not_implemented"),
    ),
    impact=(
        UnavailableCount("student_participation", "semester_onboarding_not_implemented"),
        UnavailableCount("fee_obligations", "fee_obligations_not_implemented"),
        UnavailableCount("clearance_records", "clearance_not_implemented"),
    ),
)
_DATES = DatesPrerequisite()
_SUBSTITUTE = ContextVar("academic_dependency_substitute", default=None)


def isolated_test_database():
    name = getattr(settings, "REGISTRATION_TEST_DATABASE", "")
    if type(name) is not str or not _TEST_DATABASE.fullmatch(name):
        return False
    config = connections[DEFAULT_DB_ALIAS].settings_dict
    return config.get("NAME") == name and config.get("TEST", {}).get("NAME") == name


@contextmanager
def isolated_bundle(bundle):
    """TEST ONLY: substitute sources for this context; refused outside the isolated database."""
    if not isinstance(bundle, DependencyBundle) or not isolated_test_database():
        raise DependencyUnavailable("Substitute dependency sources are refused outside isolated tests.")
    token = _SUBSTITUTE.set(bundle)
    try:
        yield
    finally:
        _SUBSTITUTE.reset(token)


def current_bundle():
    bundle = _SUBSTITUTE.get()
    if bundle is not None and isolated_test_database():
        return bundle
    return DEFAULT_BUNDLE


def _by_key(sources, semester, keys, missing_result):
    results = {}
    for source in sources:
        try:
            result = source.evaluate(semester)
        except Exception:  # a failing source is an unknown, never a pass
            result = missing_result(getattr(source, "key", ""))
        if result.key in keys and result.key not in results:
            results[result.key] = result
    # A key with no source is unknown, never assumed satisfied.
    return [results.get(key) or missing_result(key) for key in keys]


def evaluate_prerequisites(semester):
    checks = _by_key(current_bundle().prerequisites, semester, REQUIRED_PREREQUISITES,
                     lambda key: CheckResult(key, UNAVAILABLE, "source_unavailable"))
    return [_DATES.evaluate(semester), *checks]


def evaluate_obligations(semester):
    return _by_key(current_bundle().obligations, semester, CLOSURE_OBLIGATIONS,
                   lambda key: CountResult(key, UNAVAILABLE, None, "source_unavailable"))


def evaluate_impact(semester):
    return _by_key(current_bundle().impact, semester, IMPACT_RECORDS,
                   lambda key: CountResult(key, UNAVAILABLE, None, "source_unavailable"))


def missing_prerequisites(semester):
    return [check.key for check in evaluate_prerequisites(semester) if check.status != READY]


# ---- Integration contract for dependent workflows (WF-05.05, WF-06, WF-07) --------------------

def accepts_new_onboarding(semester):
    """WF-05.05 contract: ONLY the Active semester accepts ordinary new Student onboarding.

    Closed and Archived semesters never do; historical participation needs the separate,
    evidenced correction below.
    """
    from .models import SemesterStatus
    return getattr(semester, "status", None) == SemesterStatus.ACTIVE


def request_historical_participation_correction(**_unused):
    """WF11-D14 contract (NOT AVAILABLE): create a missing historical Student participation.

    Requires official CTU verification evidence (security review section 2), atomic participation
    + subjects + clearance + fee creation (WF11-D24) and idempotent reuse of existing obligations.
    None of those modules exist, so this always refuses; no route or command calls it.
    """
    raise DependencyUnavailable("Historical participation corrections require WF-05.05, WF-06, WF-07 and "
                                "an approved CTU verification source.")
