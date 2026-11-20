"""Standard-library offline safety tests for AR-6C7C profile preparation."""

import copy
import unittest

from plan_registration_review_profile import load_local, verify, ProfileContractError


class RegistrationReviewProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile, cls.source, cls.digest = load_local()

    def check_rejected(self, modify_profile=None, modify_source=None, digest=None):
        profile = copy.deepcopy(self.profile)
        source = copy.deepcopy(self.source)
        if modify_profile:
            modify_profile(profile)
        if modify_source:
            modify_source(source)
        with self.assertRaises(ProfileContractError):
            verify(profile, source, self.digest if digest is None else digest)

    def test_exact_draft_passes_and_never_approves_or_writes(self):
        report = verify(self.profile, self.source, self.digest)
        self.assertEqual(report['candidate_counts'], {
            'services': 2, 'permissions': 3, 'admin_role_bindings': 3,
        })
        self.assertFalse(report['database_checked'])
        self.assertFalse(report['database_changes'])
        self.assertFalse(report['runtime_approval'])

    def test_rejects_extra_service(self):
        self.check_rejected(modify_profile=lambda p: p['allowlist']['services'].append('finance'))

    def test_rejects_extra_permission(self):
        self.check_rejected(modify_profile=lambda p: p['allowlist']['permissions'].append(
            'accounts.profile.self.read'))

    def test_rejects_different_role_binding(self):
        self.check_rejected(modify_profile=lambda p: p['allowlist']['role_bindings'][0].update(
            role_name='Technical Super Admin'))

    def test_rejects_unblocked_activation_gate(self):
        self.check_rejected(modify_profile=lambda p: p['gates'].update(role_grants='ENABLED'))

    def test_rejects_fake_approval(self):
        self.check_rejected(modify_profile=lambda p: p['approval'].update(system_owner='approved'))

    def test_rejects_unpinned_source(self):
        self.check_rejected(digest='0' * 64)

    def test_rejects_changed_scope_in_source(self):
        def changed(source):
            next(row for row in source['permissions'] if row['permission_code'] ==
                 'accounts.registration_requests.read')['scope'] = 'OWN'
        self.check_rejected(modify_source=changed)

    def test_rejects_missing_binding_in_source(self):
        def changed(source):
            source['default_bindings'] = [row for row in source['default_bindings']
                if row != {'role_name': 'Admin',
                           'permission_code': 'accounts.registration_requests.reject'}]
        self.check_rejected(modify_source=changed)

    def test_rejects_non_planning_source(self):
        self.check_rejected(modify_source=lambda s: s.update(planning_only=False))


if __name__ == '__main__':
    unittest.main(verbosity=2)
