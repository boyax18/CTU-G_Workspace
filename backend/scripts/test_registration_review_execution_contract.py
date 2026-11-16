"""AR-6C7C.5 offline isolated contract tests: no Django/MySQL imports or writes."""

import copy
import unittest

from scripts.validate_registration_review_execution_contract import (
    ContractRejected, load_local, verify_contract,
)


class ProtectedExecutionDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = load_local()

    def evaluate(self, *, edit_contract=None, edit_profile=None, edit_source=None, raw=None):
        contract, profile, source, source_raw = copy.deepcopy(self.valid)
        if edit_contract:
            edit_contract(contract)
        if edit_profile:
            edit_profile(profile)
        if edit_source:
            edit_source(source)
        if raw is not None:
            source_raw = raw
        return verify_contract(contract, profile, source, source_raw)

    def assert_refused(self, **kwargs):
        with self.assertRaises(ContractRejected):
            self.evaluate(**kwargs)

    def test_valid_contract_is_still_not_executable(self):
        out = self.evaluate()
        self.assertFalse(out['execution_authorized'])
        self.assertFalse(out['writes_performed'])
        self.assertFalse(out['operator_approved'])
        self.assertFalse(out['database_accessed'])
        self.assertEqual(out['protected_admin_bindings'], 3)

    def test_refuses_declared_execution_authority(self):
        self.assert_refused(edit_contract=lambda x: x.update(execution_authorized=True))

    def test_refuses_declared_database_write_permission(self):
        self.assert_refused(edit_contract=lambda x: x.update(database_writes_authorized=True))

    def test_refuses_unblocked_stage(self):
        self.assert_refused(edit_contract=lambda x: x['allowed_future_sequence'][1].update(decision='APPROVED'))

    def test_refuses_stage_reordering(self):
        self.assert_refused(edit_contract=lambda x: x['allowed_future_sequence'].reverse())

    def test_refuses_extra_service(self):
        self.assert_refused(edit_contract=lambda x: x['intended_records']['services'].append('finance'))

    def test_refuses_extra_permission(self):
        self.assert_refused(edit_contract=lambda x: x['intended_records']['permissions'].append('accounts.profile.self.read'))

    def test_refuses_extra_grant(self):
        self.assert_refused(edit_contract=lambda x: x['intended_records']['role_bindings'].append('access_control.role_permissions.manage'))

    def test_refuses_changed_role(self):
        self.assert_refused(edit_contract=lambda x: x['intended_records'].update(role_name='Technical Super Admin'))

    def test_refuses_approval_identity_in_unsigned_draft(self):
        self.assert_refused(edit_contract=lambda x: x['authorization'].update(system_owner='Someone'))

    def test_refuses_fake_ticket(self):
        self.assert_refused(edit_contract=lambda x: x['authorization'].update(change_ticket='TICKET-123'))

    def test_refuses_unblocked_original_profile(self):
        self.assert_refused(edit_profile=lambda x: x['gates'].update(role_grants='APPROVED'))

    def test_refuses_changed_source_digest(self):
        self.assert_refused(raw=b'not the approved source')

    def test_refuses_changed_school_scope(self):
        self.assert_refused(edit_source=lambda x: next(p for p in x['permissions'] if p['permission_code'].endswith('.read')).update(scope='GLOBAL'))

    def test_refuses_changed_governance_protection(self):
        self.assert_refused(edit_source=lambda x: next(p for p in x['permissions'] if p['permission_code'].endswith('.read')).update(grant_protection='NORMAL'))

    def test_refuses_unbounded_audit_fields(self):
        self.assert_refused(edit_contract=lambda x: x['audit_limits']['old_new_fields'].append('approval_ticket'))

    def test_refuses_changed_audit_reason(self):
        self.assert_refused(edit_contract=lambda x: x['audit_limits'].update(reason_code='ad_hoc'))

    def test_refuses_removing_deny_precedence(self):
        self.assert_refused(edit_contract=lambda x: x['invariants'].remove('deny_precedence'))

    def test_refuses_removing_multi_role_union(self):
        self.assert_refused(edit_contract=lambda x: x['invariants'].remove('multi_role_union'))

    def test_refuses_approval_in_source(self):
        self.assert_refused(edit_source=lambda x: x.update(planning_only=False))


if __name__ == '__main__':
    unittest.main(verbosity=2)
