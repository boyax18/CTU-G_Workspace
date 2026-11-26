"""WF-05.05 / WF11-D17 Student dashboard boundary: route classification and the current-semester gate.

Every API route is classified here (``ROUTE_POLICY``, by URL name; staff routes by prefix) and the
test suite refuses an unclassified route, so a new Student-reachable operation cannot silently skip
the decision. Classes:

* ``semester_dependent`` - needs the Student's finalized participation in the Active semester. The
  operation raises ``OnboardingRequired`` (HTTP 409 ``onboarding_required`` with the server's
  ``state`` and ``route``) until then. Today: the current-semester record (``my-semester``).
* ``onboarding`` - the onboarding flow itself (status, steps, review, finalization).
* ``historical`` - the Student's own historical clearance and fee resolution; never gated.
* ``period`` - the read-only current academic period; never gated.
* ``account`` - sign-in, session, logout, role context, password, email verification and
  registration; never gated (WF11-D17 keeps account, help and logout available).
* ``staff`` - School Admin and governance operations, not reachable by a Student context.

Inspected 26 Nov 2026: the announcements, notifications, group_rating, support, reports and
clearance apps expose no routes, so no existing policy is changed for them. Non-Student role
contexts of a multi-role account are never gated: Student-context authorization decides first.
"""

from .onboarding import (  # re-exported for semester-dependent operations
    OnboardingRequired, active_semester, dashboard_route, require_completed, state_for,
)

SEMESTER_DEPENDENT, ONBOARDING, HISTORICAL, PERIOD, ACCOUNT, STAFF = (
    "semester_dependent", "onboarding", "historical", "period", "account", "staff")
CLASSES = frozenset({SEMESTER_DEPENDENT, ONBOARDING, HISTORICAL, PERIOD, ACCOUNT, STAFF})

ROUTE_POLICY = {
    # Account functions (WF-01 / WF-02 / WF-03 role context): always available.
    "registration-csrf": ACCOUNT, "register": ACCOUNT, "student-registration-status": ACCOUNT,
    "student-registration-verify": ACCOUNT, "student-registration-resend": ACCOUNT,
    "student-registration-cancel": ACCOUNT, "workspace-reapplication-link": ACCOUNT,
    "workspace-reapplication-complete": ACCOUNT, "workspace-login": ACCOUNT, "workspace-logout": ACCOUNT,
    "workspace-session": ACCOUNT, "workspace-forgot-password": ACCOUNT, "workspace-forgot-password-verify": ACCOUNT,
    "workspace-reset-password": ACCOUNT, "workspace-email-verification": ACCOUNT,
    "workspace-email-verification-request": ACCOUNT, "workspace-email-verification-confirm": ACCOUNT,
    "workspace-assisted-recovery-verify": ACCOUNT, "workspace-role-context-switch-normal": ACCOUNT,
    # Read-only period context (needed to show "no active semester" and the onboarding header).
    "academic-catalogue-current-period": PERIOD,
    # The onboarding flow.
    "academic-onboarding-status": ONBOARDING, "academic-onboarding-context": ONBOARDING,
    "academic-onboarding-subject-options": ONBOARDING, "academic-onboarding-type": ONBOARDING,
    "academic-onboarding-subjects": ONBOARDING, "academic-onboarding-course": ONBOARDING,
    "academic-onboarding-review": ONBOARDING, "academic-onboarding-finalize": ONBOARDING,
    # Current-semester Student data: gated on the finalized participation.
    "academic-onboarding-my-semester": SEMESTER_DEPENDENT,
    # Own historical clearance and fee information: always available.
    "academic-onboarding-my-history": HISTORICAL,
}
STAFF_PREFIXES = ("registration-review-", "bulk-registration-review", "school-accounts-", "academic-config-", "academic-school-year",
                  "academic-semester-", "academic-verification-", "academic-historical-", "finance-semester-fee")


def route_class(url_name):
    if url_name in ROUTE_POLICY:
        return ROUTE_POLICY[url_name]
    if isinstance(url_name, str) and url_name.startswith(STAFF_PREFIXES):
        return STAFF
    return None



__all__ = ["ROUTE_POLICY", "STAFF_PREFIXES", "CLASSES", "route_class", "dashboard_route", "OnboardingRequired",
           "require_completed", "active_semester", "state_for"]
