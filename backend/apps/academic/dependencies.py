"""WF-11.01 dependency contract: activation prerequisites, closure obligations, edit impact.

Each check is a small read-side *source* that reports what it can actually establish:

* Prerequisites (activation, WF11-D03): ``ready`` / ``missing`` / ``unavailable``.
* Obligations (closure/archive, WF11-D11/D12) and impact (Active edits and historical corrections,
  WF11-D05/D06): ``evaluated`` with a real count, or ``unavailable``. An unimplemented module is
  NEVER reported as zero.

Every default source is now real (26 Nov 2026): academic offerings (academic.0003,
``OfferingPrerequisite``), the approved semester fee (finance.0001, ``ApprovedFeePrerequisite``), and
the WF-05.05 / WF-06.01 / WF-07.02 records created by onboarding finalization (academic.0004,
clearance.0001, finance.0002): Pending clearance requirements, Unpaid fee obligations, unfinished
onboarding Drafts, participations, obligations and clearances (``RecordCount``). A source whose query
fails is reported ``unavailable`` by ``_by_key``, never zero. Activation still needs its own switch
and HDAC; a closure with outstanding records needs the School Admin's explicit acknowledgement, and
an Active edit or historical date correction that affects records needs the affected categories
acknowledged (the records themselves are never rewritten).

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


class RecordCount:
    """Real read-only count of one record category for a semester (``evaluated``)."""

    def __init__(self, key, counter):
        self.key, self._counter = key, counter

    def evaluate(self, semester):
        return CountResult(self.key, EVALUATED, int(self._counter(semester)))


def _pending_requirements(semester):
    from apps.clearance.services import pending_requirement_count
    return pending_requirement_count(semester)


def _unpaid_obligations(semester):
    from apps.finance.obligations import unpaid_obligation_count
    return unpaid_obligation_count(semester)


def _incomplete_onboarding(semester):
    from .models import OnboardingStatus, SemesterOnboarding
    return (SemesterOnboarding.objects.using(DEFAULT_DB_ALIAS).filter(semester_id=semester.pk)
            .exclude(status=OnboardingStatus.COMPLETED).count())


def _participations(semester):
    from .models import SemesterParticipation
    return SemesterParticipation.objects.using(DEFAULT_DB_ALIAS).filter(semester_id=semester.pk).count()


def _obligations(semester):
    from apps.finance.obligations import obligation_count
    return obligation_count(semester)


def _clearances(semester):
    from apps.clearance.services import clearance_count
    return clearance_count(semester)


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
        RecordCount("outstanding_clearance_signatures", _pending_requirements),
        RecordCount("unpaid_fee_obligations", _unpaid_obligations),
        RecordCount("incomplete_onboarding", _incomplete_onboarding),
    ),
    impact=(
        RecordCount("student_participation", _participations),
        RecordCount("fee_obligations", _obligations),
        RecordCount("clearance_records", _clearances),
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


def request_historical_participation_correction(**kwargs):
    """WF11-D14 contract: create a missing historical Student participation from Verified evidence.

    Delegates to apps.academic.historical_participation.correct (School Admin, both
    academic.periods.manage and academic.profiles.manage, its own default-off switch). It creates the
    participation, subjects, one clearance and one obligation snapshot of the ORIGINAL approved fee
    atomically, never reopens the period, and refuses ``historical_fee_unavailable`` without that fee.
    """
    from .historical_participation import correct
    return correct(**kwargs)
