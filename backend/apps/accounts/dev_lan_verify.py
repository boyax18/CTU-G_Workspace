"""Live end-to-end verification of the RUNNING synthetic LAN application.

    manage.py ctug_lan verify --base-url http://<lan-ip>:5173 [--mutate-synthetic]

Drives the real browser path (Vite on the LAN address -> proxy -> loopback
Django) with the synthetic accounts, and checks database effects through the
ORM after proving the connection is the marked synthetic schema. With
``--mutate-synthetic`` it approves/rejects a few synthetic applicants (top the
pool up again with Initialize-CTUG-LAN.ps1). Passwords are read from the local
git-ignored credentials file and never printed.
"""

import json
import os
import subprocess
import sys
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener

from django.conf import settings

from . import dev_lan

REVIEWS = "/api/v1/admin/registration-requests/"
# Existing login (8/min per address) and bulk (3/min) throttles are security controls:
# one verification run fits inside them; wait a minute before running it again.
RATE_LIMITED = "HTTP 429: existing rate limit reached; wait one minute and run the verification once"
DIRECTORY = "/api/v1/admin/school-accounts/"
WF02_CODES = {
    "accounts.registration_requests.read", "accounts.registration_requests.approve",
    "accounts.registration_requests.reject", "accounts.school_accounts.read",
}


class Browser:
    """Minimal same-origin browser: cookie jar, CSRF header, Origin, no proxy, no retries."""

    def __init__(self, base_url):
        self.base = base_url.rstrip("/")
        self.jar = CookieJar()
        self.opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(self.jar))
        self.csrf = None

    def request(self, method, path, body=None, accept="application/json"):
        headers = {"Accept": accept, "Origin": self.base}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if method != "GET" and self.csrf:
            headers["X-CSRFToken"] = self.csrf
        req = Request(self.base + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=20) as response:
                raw, status, hdrs = response.read(), response.status, response.headers
        except HTTPError as exc:
            raw, status, hdrs = exc.read(), exc.code, exc.headers
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else None
        except ValueError:
            payload = raw.decode("utf-8", "replace")
        return status, payload, hdrs

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, body):
        return self.request("POST", path, body)

    def refresh_csrf(self):
        status, payload, _ = self.get("/api/v1/auth/csrf/")
        self.csrf = payload.get("csrfToken") if status == 200 and isinstance(payload, dict) else None
        return status

    def login(self, school_id, password):
        self.refresh_csrf()
        status, _payload, _ = self.post("/api/v1/auth/login/", {"school_id": school_id, "password": password})
        self.refresh_csrf()  # Django rotates the token at login
        return status


def _actions(headers):
    return set(filter(None, (headers.get("X-Workspace-Available-Actions") or "").split(",")))


def _password():
    path = dev_lan.credentials_file()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("PASSWORD="):
            return line.split("=", 1)[1]
    raise dev_lan.DevLanRefused("Synthetic credentials file is missing; run .\\Initialize-CTUG-LAN.ps1.")


def _role_id(session, name):
    for choice in (session.get("role_context") or {}).get("choices", []):
        if choice["role_name"] == name:
            return choice["role_id"]
    return None


def _unsafe_target_refused():
    """A manual Option A start against ctug_workspace must fail before serving anything."""
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings", "DB_NAME": "ctug_workspace",
           "DJANGO_DEBUG": "1", "CTUG_ROLE_CONTEXT_LAN_DEV_ACK": "LAN_HTTP_SYNTHETIC_ONLY_WF0301_A",
           "CTUG_ROLE_CONTEXT_LAN_DEV_IPS": "192.168.0.10", "CTUG_ROLE_CONTEXT_LAN_DEV_IP": "",
           "WORKSPACE_ALLOWED_HOSTS": "localhost,127.0.0.1,[::1],192.168.0.10",
           "WORKSPACE_CSRF_TRUSTED_ORIGINS": "http://192.168.0.10:5173", "CTUG_DEV_LAN_IP": ""}
    result = subprocess.run([sys.executable, "manage.py", "check"], cwd=settings.BASE_DIR, env=env,
                            capture_output=True, text=True, timeout=120)
    return result.returncode != 0 and "synthetic" in (result.stderr + result.stdout)


def run_live_verification(base_url, *, mutate, write):
    from apps.access_control.models import AccessAuditLog, AccountRole
    from .models import Account, UserProfile
    from .outbox_models import RegistrationNotificationOutbox

    results = []

    def check(name, ok, detail=""):
        results.append((name, bool(ok)))
        write(f"{'PASS' if ok else 'FAIL'}  {name}{('  (' + detail + ')') if detail else ''}")
        return bool(ok)

    dev_lan.verify_target()
    password = _password()
    host = urlsplit(base_url).hostname

    # 1-5 infrastructure, database target and anonymous denial
    anon = Browser(base_url)
    status, body, _ = anon.request("GET", "/", accept="text/html")
    check("LAN URL serves the frontend", status == 200 and 'id="root"' in str(body), f"HTTP {status}")
    status, module, _ = anon.request("GET", "/src/features/admin/pendingApplicationsConfig.ts", accept="*/*")
    check("Frontend received registry build flags (WF-02 on, governance off)",
          status == 200 and '"VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED": "1"' in str(module)
          and '"VITE_WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED": "1"' in str(module)
          and '"VITE_WORKSPACE_ROLE_ASSIGNMENT_ENABLED": "0"' in str(module))
    check("Vite API proxy reaches Django", anon.refresh_csrf() == 200 and anon.csrf)
    check("Connected database is the marked synthetic schema",
          settings.DATABASES["default"]["NAME"] == dev_lan.SYNTHETIC_LAN_DATABASE, dev_lan.SYNTHETIC_LAN_DATABASE)
    check("Option A refuses to start against ctug_workspace", _unsafe_target_refused())
    check("Anonymous applicant/directory reads require sign-in",
          anon.get(REVIEWS)[0] == 401 and anon.get(DIRECTORY)[0] == 401)
    try:
        build_opener(ProxyHandler({})).open(f"http://{host}:8000/api/v1/auth/session/", timeout=3)
        direct_refused = False
    except HTTPError:
        direct_refused = False
    except (URLError, OSError):
        direct_refused = True
    check("Django is not reachable directly from the LAN address", direct_refused)

    # 6 School Admin
    admin = Browser(base_url)
    check("School Admin signs in", admin.login("LAN-SCHOOLADMIN-01", password) == 200)
    session = admin.get("/api/v1/auth/session/")[1]
    check("School Admin session has role context and WF-02 permissions",
          session.get("role_context", {}).get("enabled") and WF02_CODES <= set(session.get("permissions", [])))
    status, page, headers = admin.get(REVIEWS)
    pending_ids = [row["account_id"] for row in page.get("results", [])] if status == 200 else []
    check("Applicant Reviews list (pending, paginated)", status == 200 and pending_ids,
          f"{len(pending_ids)} on page 1, has_next={page.get('has_next') if status == 200 else '-'}")
    check("Server advertises individual and bulk decisions",
          {"approve", "reject", "bulk-approve", "bulk-reject"} <= _actions(headers), ",".join(sorted(_actions(headers))))
    status, filtered, _ = admin.get(REVIEWS + "?q=LAN-APPLICANT-I&role=Instructor")
    check("Applicant search and filter", status == 200 and filtered["results"]
          and all(r.get("requested_role") in (None, "Instructor") for r in filtered["results"]))
    status, _detail, headers = admin.get(f"{REVIEWS}{pending_ids[0]}/") if pending_ids else (0, None, {})
    check("Applicant details with decision actions", status == 200 and {"approve", "reject"} <= _actions(headers))

    # 9 read-only Account Management
    status, directory, _ = admin.get(DIRECTORY)
    ids = {row["school_id"]: row["account_id"] for row in directory.get("results", [])} if status == 200 else {}
    check("Account Directory lists ordinary accounts", status == 200 and "LAN-STUDENT-01" in ids)
    student_id = ids.get("LAN-STUDENT-01")
    check("Account detail and history are readable",
          student_id and admin.get(f"{DIRECTORY}{student_id}/")[0] == 200
          and admin.get(f"{DIRECTORY}{student_id}/history/")[0] == 200)
    check("Account status changes stay unmounted (read-only directory)",
          student_id and admin.post(f"{DIRECTORY}{student_id}/suspend/", {"expected_active": True})[0] == 404)

    # 7-8 Technical Super Admin inherits, Active Role switching
    tech = Browser(base_url)
    check("Technical Super Admin signs in", tech.login(dev_lan.OPERATOR_ID, password) == 200)
    session = tech.get("/api/v1/auth/session/")[1]
    tsa_role = _role_id(session, "Technical Super Admin")
    status, switched, _ = tech.post("/api/v1/auth/role-context/", {"role_id": tsa_role})
    check("Active Role switch to Technical Super Admin",
          status == 200 and switched.get("role_context", {}).get("active_role_id") == tsa_role)
    status, _page, headers = tech.get(REVIEWS)
    check("Technical Super Admin context inherits WF-02 (no switch to School Admin)",
          status == 200 and {"approve", "reject", "bulk-approve"} <= _actions(headers)
          and tech.get(DIRECTORY)[0] == 200)
    check("Protected governance routes are not mounted",
          tech.get("/api/v1/admin/role-assignments/")[0] == 404
          and tech.get("/api/v1/admin/role-permissions/")[0] == 404)

    # 13 unauthorized roles
    for school_id in ("LAN-STUDENT-01", "LAN-INSTRUCTOR-01", "LAN-TREASURER-01"):
        other = Browser(base_url)
        signed_in = other.login(school_id, password)
        if signed_in == 429:
            check(f"{school_id} is denied Account Management", False, RATE_LIMITED)
            continue
        check(f"{school_id} is denied Account Management",
              other.get(REVIEWS)[0] == 403 and other.get(DIRECTORY)[0] == 403
              and (not pending_ids or other.post(f"{REVIEWS}{pending_ids[0]}/reject/",
                                                {"rejection_code": "incomplete_submission"})[0] == 403))

    if mutate:
        _verify_decisions(admin, tech, check, Account, AccountRole, UserProfile, AccessAuditLog,
                          RegistrationNotificationOutbox)

    # 14 sign-out ends the session
    admin.post("/api/v1/auth/logout/", {})
    check("Sign-out ends the session", admin.get(REVIEWS)[0] in (401, 403))
    return results


def _pending(Account, role, count, exclude=()):
    return list(Account.objects.filter(request_status="Pending", is_active=False, requested_role__role_name=role)
                .exclude(pk__in=exclude).order_by("account_id").values_list("account_id", flat=True)[:count])


def _verify_decisions(admin, tech, check, Account, AccountRole, UserProfile, AccessAuditLog, Outbox):
    dev_lan.verify_target()
    # 10 individual approval by School Admin
    target = _pending(Account, "Student", 1)
    if not check("Synthetic pending applicants available", target):
        return
    target = target[0]
    before = Outbox.objects.count()
    status, body, _ = admin.post(f"{REVIEWS}{target}/approve/",
                                 {"eligibility_confirmed": True, "eligibility_source": "ctu_main_system_records"})
    account = Account.objects.get(pk=target)
    outbox = Outbox.objects.filter(template_code="registration.approved",
                                   decision_audit_log__target_account_id=target).first()
    check("Approve Applicant: account Approved/Active, role assigned",
          status == 200 and body.get("notification") == "queued" and account.request_status == "Approved"
          and account.is_active and AccountRole.objects.filter(account=account, role__role_name="Student").exists())
    check("Approval audited and individual email durably queued (encrypted)",
          outbox is not None and outbox.delivery_status == "Pending" and outbox.encrypted_recipient
          and account.email.encode() not in bytes(outbox.encrypted_recipient)
          and AccessAuditLog.objects.filter(target_account_id=target).exists())
    check("Duplicate decision is refused",
          admin.post(f"{REVIEWS}{target}/approve/",
                     {"eligibility_confirmed": True, "eligibility_source": "ctu_main_system_records"})[0] == 404)

    # 10/12 individual rejection by Technical Super Admin context
    target = _pending(Account, "Instructor", 1)[0]
    status, body, _ = tech.post(f"{REVIEWS}{target}/reject/", {"rejection_code": "incomplete_submission"})
    outbox = Outbox.objects.filter(template_code="registration.rejected").order_by("-outbox_id").first()
    check("Reject Applicant: registration and profile deleted",
          status == 200 and body.get("notification") == "queued"
          and not Account.objects.filter(pk=target).exists() and not UserProfile.objects.filter(account_id=target).exists())
    check("Rejection email durably queued and survives deletion",
          outbox is not None and outbox.encrypted_recipient and outbox.delivery_status == "Pending"
          and Outbox.objects.count() == before + 2)

    # 11 bulk decisions
    approve_ids = _pending(Account, "Student", 2)
    status, report, _ = admin.post(f"{REVIEWS}bulk/", {"action": "approve", "account_ids": approve_ids,
                                                       "eligibility_confirmed": True})
    if status == 429:
        check("Bulk decisions", False, RATE_LIMITED)
        return
    check("Bulk Approve: per-applicant results, each committed separately",
          status == 200 and report["counts"]["Approved"] == len(approve_ids)

          and all(r.get("notification") == "queued" for r in report["results"])
          and Account.objects.filter(pk__in=approve_ids, request_status="Approved").count() == len(approve_ids))
    reject_ids = _pending(Account, "Student", 2)
    status, report, _ = tech.post(f"{REVIEWS}bulk/", {"action": "reject", "account_ids": [approve_ids[0], *reject_ids],
                                                      "rejection_code": "duplicate_request"})
    outcomes = {r["account_id"]: r["outcome"] for r in report.get("results", [])} if status == 200 else {}
    check("Bulk Reject: already-decided applicant skipped, others rejected and deleted",
          outcomes.get(approve_ids[0]) == "Skipped" and all(outcomes.get(pk) == "Rejected" for pk in reject_ids)
          and not Account.objects.filter(pk__in=reject_ids).exists())
    too_many = list(range(1, 22))
    check("Bulk cap of 20 applicants enforced",
          admin.post(f"{REVIEWS}bulk/", {"action": "reject", "account_ids": too_many,
                                         "rejection_code": "duplicate_request"})[0] == 400)
    check("Every decision queued exactly one outbox row", Outbox.objects.count() == before + 2 + 4)
