"""WF-02.06 View account status and permitted history (owner-approved D-72 to D-78, 18 Nov 2026).

Run: python manage.py test apps.accounts.test_wf0206_account_history --settings=config.test_settings --noinput
Disposable MySQL only; synthetic accounts; the API is reached through the same isolated URLconf as
WF-02.05. Status events are produced by the real WF-02.05 service; approval events by the real
audit writer with the exact WF-02.03 attestation shape.
"""

import threading

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import Resolver404, resolve

from apps.access_control.audit import record_access_audit
from apps.access_control.models import AccessAuditLog, AccountPermission, Service

from .account_status import activate_account, suspend_account
from .models import Account
from .test_wf0205_account_status import API, GATE, URLCONF, World

if not getattr(settings, "REGISTRATION_TEST_DATABASE", "").startswith("test_ctug_registration_"):
    raise ImproperlyConfigured("WF-02.06 tests require --settings=config.test_settings.")

ENTRY_KEYS = {"event", "description", "occurred_at", "actor"}
STATUS_KEYS = ENTRY_KEYS | {"previous_is_active", "new_is_active"}
DETAIL_KEYS = {"account_id", "school_id", "id_label", "name", "full_name", "roles", "is_active", "request_status",
               "created_at", "can_reactivate", "approved_at", "last_status_change"}
FORBIDDEN_TEXT = ("ctu_main_system_records", "eligibility", "email_evidence", "account_status_change", "permission_change",
                  "old_value", "new_value", "role_id", "access_audit_log_id", "password", "@")


def approve_event(world, target, reviewer=None):
    """The exact WF-02.03 approval audit (D-45 attestation shape) through the real audit writer."""
    record_access_audit(
        actor=reviewer or world.reviewer, action="account.registration.approve", target=target,
        role=world.roles["Student"],
        old_value={"account_id": target.pk, "request_status": "Pending", "is_active": False},
        new_value={"account_id": target.pk, "request_status": "Approved", "is_active": True,
                   "role_id": world.roles["Student"].pk, "email_evidence": "verified", "eligibility_confirmed": True,
                   "eligibility_subject": "enrollment", "eligibility_source": "ctu_main_system_records"},
        reason="account_status_change")


def signed_in(account):
    client = Client(enforce_csrf_checks=True)
    client.force_login(account)
    client.cookies[settings.CSRF_COOKIE_NAME] = "e" * 32
    return client


@override_settings(ROOT_URLCONF=URLCONF, **GATE)
class AccountHistoryHTTPTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.w = World()
        cls.student = cls.w.account("7260601", "Student")
        cls.other = cls.w.account("7260602", "Student")
        cls.second_admin = cls.w.account("WF0206-ADMIN2", "Admin")

    def setUp(self):
        cache.clear()
        self.client = signed_in(self.w.reviewer)

    def history(self, target, client=None, **params):
        return (client or self.client).get(f"{API}{target.pk}/history/", params)

    def detail(self, target, client=None):
        return (client or self.client).get(f"{API}{target.pk}/")

    def assert_private(self, response):
        text = response.content.decode()
        for forbidden in FORBIDDEN_TEXT + (self.w.reviewer.school_id, self.second_admin.school_id):
            self.assertNotIn(forbidden, text)

    # -- D-75 status dates -----------------------------------------------------------------------
    def test_detail_status_dates_come_from_trusted_sources_and_never_from_history(self):
        body = self.detail(self.student).json()
        self.assertEqual(set(body), DETAIL_KEYS)
        self.assertEqual((body["approved_at"], body["last_status_change"]), (None, None))  # legacy: "Not recorded"
        self.assertEqual((body["is_active"], body["request_status"]), (True, "Approved"))
        Account.objects.filter(pk=self.student.pk).update(reviewed_at="2026-11-01 08:00:00")
        self.assertTrue(self.detail(self.student).json()["approved_at"].startswith("2026-11-01T08:00:00"))
        approve_event(self.w, self.student)
        audited = AccessAuditLog.objects.get(target_account=self.student, action="account.registration.approve").created_at
        response = self.detail(self.student)
        self.assertEqual(response.json()["approved_at"], audited.isoformat())  # the append-only evidence wins
        self.assert_private(response)
        suspend_account(actor=self.w.reviewer, target_id=self.student.pk, expected_active=True)
        body = self.detail(self.student).json()
        self.assertEqual(set(body["last_status_change"]), STATUS_KEYS)
        self.assertEqual({k: v for k, v in body["last_status_change"].items() if k != "occurred_at"}, {
            "event": "account_deactivated", "description": "Account deactivated", "actor": "You",
            "previous_is_active": True, "new_is_active": False})
        self.assertFalse(body["is_active"])
        # The row is authoritative: a history entry never overrides it.
        Account.objects.filter(pk=self.student.pk).update(is_active=True)
        body = self.detail(self.student).json()
        self.assertEqual((body["is_active"], body["last_status_change"]["new_is_active"]), (True, False))

    # -- D-74 allowlist, D-73 actor labels, ordering ---------------------------------------------
    def test_history_returns_only_allowlisted_minimized_events_newest_first(self):
        approve_event(self.w, self.student)
        suspend_account(actor=self.w.reviewer, target_id=self.student.pk, expected_active=True)
        activate_account(actor=self.second_admin, target_id=self.student.pk, expected_active=False)
        # Not allowlisted for the same target: reapplication, role assignment, governance receipt.
        for action in ("account.registration.reapply", "account.role.assign", "workspace.school_accounts.permission.create"):
            AccessAuditLog.objects.create(actor_account=self.w.reviewer, target_account=self.student, action=action,
                                          new_value={"account_id": self.student.pk}, reason="permission_change")
        suspend_account(actor=self.w.reviewer, target_id=self.other.pk, expected_active=True)  # another account
        response = self.history(self.student)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("no-store", response["Cache-Control"])
        body = response.json()
        self.assertEqual(set(body), {"results", "page", "page_size", "has_next"})
        self.assertEqual((body["page"], body["page_size"], body["has_next"]), (1, 20, False))
        results = body["results"]
        self.assertEqual([r["event"] for r in results], ["account_reactivated", "account_deactivated", "registration_approved"])
        self.assertEqual([r["actor"] for r in results], ["An administrator", "You", "You"])
        self.assertEqual([r["description"] for r in results],
                         ["Account reactivated", "Account deactivated", "Registration approved"])
        self.assertEqual([set(r) for r in results], [STATUS_KEYS, STATUS_KEYS, ENTRY_KEYS])
        self.assertEqual([(r["previous_is_active"], r["new_is_active"]) for r in results[:2]], [(False, True), (True, False)])
        times = [r["occurred_at"] for r in results]
        self.assertEqual(times, sorted(times, reverse=True))
        self.assert_private(response)
        # The same history seen by the other administrator swaps the labels.
        cache.clear()
        other_view = self.history(self.student, client=signed_in(self.second_admin)).json()["results"]
        self.assertEqual([r["actor"] for r in other_view], ["You", "An administrator", "An administrator"])

    def test_recorded_states_are_shown_only_when_they_match_the_event(self):
        AccessAuditLog.objects.create(actor_account=self.w.reviewer, target_account=self.student,
                                      action="account.status.suspend", reason="account_status_change",
                                      old_value={"is_active": "yes"}, new_value=None)
        AccessAuditLog.objects.create(actor_account=self.w.reviewer, target_account=self.student,
                                      action="account.status.activate", reason="account_status_change",
                                      old_value={"is_active": True}, new_value={"is_active": False})
        results = self.history(self.student).json()["results"]
        self.assertEqual([(r["previous_is_active"], r["new_is_active"]) for r in results], [(None, None), (None, None)])

    def test_empty_history_for_legacy_accounts(self):
        self.assertEqual(self.history(self.student).json(), {"results": [], "page": 1, "page_size": 20, "has_next": False})

    # -- pagination ------------------------------------------------------------------------------
    def test_pagination_is_bounded_deterministic_and_validated(self):
        for index in range(45):
            action = "account.status.suspend" if index % 2 == 0 else "account.status.activate"
            AccessAuditLog.objects.create(actor_account=self.w.reviewer, target_account=self.student, action=action,
                                          reason="account_status_change", old_value={"is_active": index % 2 == 1},
                                          new_value={"is_active": index % 2 == 0})
        pages = [self.history(self.student, page=n).json() for n in (1, 2, 3, 4)]
        self.assertEqual([len(p["results"]) for p in pages], [20, 20, 5, 0])
        self.assertEqual([p["has_next"] for p in pages], [True, True, False, False])
        newest_first = list(AccessAuditLog.objects.filter(target_account=self.student).order_by("-pk")
                            .values_list("action", flat=True))
        events = {"account.status.suspend": "account_deactivated", "account.status.activate": "account_reactivated"}
        self.assertEqual([r["event"] for p in pages for r in p["results"]], [events[a] for a in newest_first])
        for bad in ({"page": "0"}, {"page": "10001"}, {"page": "-1"}, {"page": "1.5"}, {"page": "٣"},
                    {"page_size": "100"}, {"sort": "oldest"}, {"actor": "1"}):
            with self.subTest(bad=bad):
                cache.clear()
                self.assertEqual(self.history(self.student, **bad).status_code, 400)
        cache.clear()
        self.assertEqual(self.client.get(f"{API}{self.student.pk}/history/?page=1&page=2").status_code, 400)

    # -- authorization (D-72) --------------------------------------------------------------------
    def test_authorization_deny_precedence_services_and_gates(self):
        anonymous = Client()
        self.assertEqual(self.history(self.student, client=anonymous).status_code, 401)
        for school_id, roles in (("WF0206-S", ("Student",)), ("WF0206-I", ("Instructor",)),
                                 ("WF0206-T", ("Treasurer",)), ("WF0206-TSA", ("Technical Super Admin",))):
            with self.subTest(roles=roles):
                cache.clear()
                self.assertEqual(self.history(self.student, client=signed_in(self.w.account(school_id, *roles))).status_code, 403)
        cache.clear()
        both = self.w.account("WF0206-BOTH", "Admin", "Technical Super Admin")
        self.assertEqual(self.history(self.student, client=signed_in(both)).status_code, 200)
        cache.clear()
        AccountPermission.objects.create(account=both, permission=self.w.perms["read"], effect="Deny")
        self.assertEqual(self.history(self.student, client=signed_in(both)).status_code, 403)
        self.assertEqual(self.detail(self.student, client=signed_in(both)).status_code, 403)
        cache.clear()
        AccountPermission.objects.create(account=self.w.reviewer, permission=self.w.perms["suspend"], effect="Deny")
        self.assertEqual(self.history(self.student).status_code, 200)  # a Deny on suspend leaves read intact
        framework = self.w.account("WF0206-FW", "Admin", is_staff=True, is_superuser=True)
        self.assertEqual(self.history(self.student, client=signed_in(framework)).status_code, 401)
        Service.objects.filter(service_code="access_control").update(is_active=False)
        self.assertEqual(self.history(self.student).status_code, 503)
        Service.objects.filter(service_code="access_control").update(is_active=True)
        with override_settings(WORKSPACE_ACCOUNT_STATUS_ENABLED=False):
            self.assertEqual(self.history(self.student).status_code, 503)
        Account.objects.filter(pk=self.w.reviewer.pk).update(is_active=False)
        self.assertEqual(self.history(self.student).status_code, 401)

    # -- object eligibility and enumeration (D-77) -----------------------------------------------
    def test_ineligible_targets_share_the_detail_404_and_reveal_nothing(self):
        targets = [self.w.account("7260603", status="Pending", active=False),
                   self.w.account("7260604", status="Rejected", active=False),
                   self.w.account("9000606", "Admin"), self.w.account("9000607", "Technical Super Admin"),
                   self.w.account("WF0206-FW2", is_staff=True), self.w.reviewer]
        for target in targets:
            if target.request_status == "Approved":
                approve_event(self.w, target)
        responses = [self.history(t) for t in targets] + [self.client.get(f"{API}2000000000/history/")]
        responses += [self.client.get(f"{API}0/history/")]
        self.assertEqual({r.status_code for r in responses}, {404})
        self.assertEqual({r.content for r in responses}, {self.detail(targets[0]).content})

    def test_read_only_methods_and_no_application_writes(self):
        approve_event(self.w, self.student)
        suspend_account(actor=self.w.reviewer, target_id=self.student.pk, expected_active=True)
        url = f"{API}{self.student.pk}/history/"
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                cache.clear()
                response = getattr(self.client, method)(url, data="{}", content_type="application/json",
                                                        HTTP_X_CSRFTOKEN="e" * 32)
                self.assertEqual(response.status_code, 405)  # read-only: no write method exists
        audits, accounts = AccessAuditLog.objects.count(), list(Account.objects.order_by("pk").values())
        cache.clear()
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(self.history(self.student).status_code, 200)
            self.assertEqual(self.detail(self.student).status_code, 200)
        writes = [q["sql"] for q in queries.captured_queries
                  if q["sql"].lstrip().split(" ", 1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "REPLACE"}]
        self.assertTrue(all("django_session" in sql for sql in writes), writes)  # WF-01.06 idle-time bookkeeping only
        self.assertEqual((AccessAuditLog.objects.count(), list(Account.objects.order_by("pk").values())), (audits, accounts))

    def test_query_count_does_not_grow_with_history_length(self):
        def count():
            cache.clear()
            with CaptureQueriesContext(connection) as queries:
                self.assertEqual(self.history(self.student).status_code, 200)
            return len(queries.captured_queries)
        approve_event(self.w, self.student)
        small = count()
        for _ in range(25):
            AccessAuditLog.objects.create(actor_account=self.w.reviewer, target_account=self.student,
                                          action="account.status.suspend", reason="account_status_change")
        self.assertEqual(count(), small)

    def test_rate_limit_is_the_list_budget(self):
        statuses = [self.history(self.student, page="x").status_code for _ in range(61)]
        self.assertEqual((set(statuses[:60]), statuses[60]), ({400}, 429))

    # -- release surface (D-76) ------------------------------------------------------------------
    def test_normal_and_isolated_history_reads_preserve_status_write_boundary(self):
        from apps.access_control.management.commands.init_registration_review_metadata_local_dev import unexpected_review_routes
        self.assertEqual(resolve(f"{API}1/history/", urlconf="config.urls").url_name, "school-accounts-history")
        self.assertEqual(resolve(f"{API}1/history/", urlconf=URLCONF).url_name, "school-accounts-history")
        for conf in ("config.review_local_urls", "config.review_sandbox_urls"):
            with self.subTest(conf=conf):
                self.assertEqual(resolve(f"{API}1/history/", urlconf=conf).url_name, "school-accounts-history")
                self.assertTrue(any("school-accounts-suspend" in str(r) for r in unexpected_review_routes(conf)))
        self.assertEqual(unexpected_review_routes("config.urls"), [])
        self.assertFalse(hasattr(__import__("config.settings", fromlist=["x"]), "WORKSPACE_ACCOUNT_STATUS_ENABLED"))


@override_settings(ROOT_URLCONF=URLCONF, **GATE)
class AccountHistoryConcurrencyTests(TransactionTestCase):
    def tearDown(self):
        connections.close_all()

    def test_history_reads_stay_consistent_while_a_status_change_commits(self):
        w = World()
        student = w.account("7260699", "Student")
        client = signed_in(w.reviewer)
        seen, errors = [], []
        start = threading.Event()

        def change():
            try:
                start.wait(5)
                suspend_account(actor=w.reviewer, target_id=student.pk, expected_active=True)
            except Exception as exc:  # pragma: no cover - reported below
                errors.append(exc)
            finally:
                connections.close_all()
        worker = threading.Thread(target=change)
        worker.start()
        start.set()
        for _ in range(15):
            cache.clear()
            response = client.get(f"{API}{student.pk}/history/")
            self.assertEqual(response.status_code, 200)
            seen.append(len(response.json()["results"]))
        worker.join(10)
        self.assertEqual(errors, [])
        self.assertTrue(set(seen) <= {0, 1})
        self.assertEqual(seen, sorted(seen))  # never un-sees a committed event
        cache.clear()
        final = client.get(f"{API}{student.pk}/").json()
        self.assertEqual((final["is_active"], final["last_status_change"]["event"]), (False, "account_deactivated"))
