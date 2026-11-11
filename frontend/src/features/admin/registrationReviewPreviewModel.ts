/** AR-6C7D.1: fictional frontend-only registration review data. NEVER a live API contract. */
export type ReviewRole = 'Student' | 'Instructor';
export type ReviewDecision = 'approve' | 'reject';
export type RejectionCode =
  | 'incomplete_submission'
  | 'ineligible_registration'
  | 'identity_mismatch'
  | 'duplicate_request';

export interface DemoRegistration {
  account_id: number;
  school_id: string;
  requested_role: ReviewRole;
  created_at: string;
  status: 'Pending' | 'Approved' | 'Rejected';
}

export const REJECTION_OPTIONS: ReadonlyArray<{ code: RejectionCode; label: string }> = [
  { code: 'incomplete_submission', label: 'Incomplete submission' },
  { code: 'ineligible_registration', label: 'Ineligible registration' },
  { code: 'identity_mismatch', label: 'Identity mismatch' },
  { code: 'duplicate_request', label: 'Duplicate request' },
];

/** Entirely invented identifiers; no connection to the CTU-G database. */
export const DEMO_REGISTRATIONS: readonly DemoRegistration[] = [
  { account_id: 910001, school_id: '9900001', requested_role: 'Student', created_at: '2026-11-09T08:30:00+08:00', status: 'Pending' },
  { account_id: 910002, school_id: '9900002', requested_role: 'Instructor', created_at: '2026-11-09T10:00:00+08:00', status: 'Pending' },
  { account_id: 910003, school_id: '9900003', requested_role: 'Student', created_at: '2026-11-10T09:15:00+08:00', status: 'Pending' },
  { account_id: 910004, school_id: '9900004', requested_role: 'Student', created_at: '2026-11-10T11:25:00+08:00', status: 'Pending' },
  { account_id: 910005, school_id: '9900005', requested_role: 'Instructor', created_at: '2026-11-11T08:05:00+08:00', status: 'Pending' },
];

export function filterPendingRegistrations(
  records: readonly DemoRegistration[],
  search: string,
  role: 'All' | ReviewRole,
): DemoRegistration[] {
  const needle = search.trim();
  return records.filter((record) =>
    record.status === 'Pending'
    && (role === 'All' || record.requested_role === role)
    && (!needle || record.school_id.includes(needle)),
  );
}

export function canSimulateDecision(permissions: readonly string[], action: ReviewDecision): boolean {
  const code = action === 'approve'
    ? 'accounts.registration_requests.approve'
    : 'accounts.registration_requests.reject';
  return permissions.includes('accounts.registration_requests.read') && permissions.includes(code);
}

export function applySimulatedDecision(
  records: readonly DemoRegistration[],
  accountId: number,
  action: ReviewDecision,
  rejectionCode?: RejectionCode,
): DemoRegistration[] {
  if (!Number.isInteger(accountId) || !records.some((item) => item.account_id === accountId && item.status === 'Pending')) {
    throw new Error('This fictional registration is no longer pending.');
  }
  if (action !== 'approve' && action !== 'reject') throw new Error('Unknown decision.');
  if (action === 'reject' && !REJECTION_OPTIONS.some((option) => option.code === rejectionCode)) {
    throw new Error('Select an approved rejection reason.');
  }
  if (action === 'approve' && rejectionCode !== undefined) throw new Error('Approval cannot have a rejection reason.');
  return records.map((record) => record.account_id === accountId
    ? { ...record, status: action === 'approve' ? 'Approved' : 'Rejected' }
    : { ...record });
}
