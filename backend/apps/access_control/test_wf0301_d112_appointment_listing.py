"""WF-03.01 D-112 deferred endpoint authorization and response contracts.

Do not execute until consolidated WF-03 test phase, with migration 0004 on a
DISPOSABLE test DB. These minimal smoke contracts supplement full role/security
integration suites, which must still validate all boundaries and CSRF.
"""
from django.test import SimpleTestCase
from django.urls import URLPattern

from .appointment_registry_api import (
    AppointmentCandidateView, AppointmentMySubmissionsView, AppointmentVerifiedQueueView,
)
from .role_assignment_urls import urlpatterns


class AppointmentUIWiringContract(SimpleTestCase):
    def test_three_read_only_routes_are_isolated(self):
        paths = {str(item.pattern): item.callback.cls for item in urlpatterns if isinstance(item, URLPattern)}
        self.assertIs(paths['appointments/candidate/'], AppointmentCandidateView)
        self.assertIs(paths['appointments/my-submissions/'], AppointmentMySubmissionsView)
        self.assertIs(paths['appointments/verified/'], AppointmentVerifiedQueueView)

    def test_listing_views_do_not_accept_mutations(self):
        for view in (AppointmentCandidateView, AppointmentMySubmissionsView, AppointmentVerifiedQueueView):
            self.assertEqual(view.http_method_names, ['get', 'head', 'options'])
