/** WF-02.02 Verify and review applicant information: one application, read-only by default.
 *
 * Shows only what the server returns for an application that WF-02.01 would list. Nothing on the
 * page edits the application or is recorded by viewing it, and a verified email is never presented
 * as enrollment, employment or eligibility. WF-02.03 adds ONE approval section, only when the
 * approval switch is on and the session reports the exact approve permission (Django re-checks).
 * WF-02.04 adds ONE rejection section the same way, behind its own switch and the exact reject
 * permission. Neither section changes the other's behaviour; Django serializes the decisions.
 */
import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import ApplicantApprovalPanel from './ApplicantApprovalPanel';
import ApplicantRejectionPanel from './ApplicantRejectionPanel';
import { APPLICANT_APPROVAL_ENABLED, APPLICANT_REJECTION_ENABLED } from './pendingApplicationsConfig.ts';
import { getPendingApplication } from './registrationReviewApi.ts';
import { parseApplicantId, REJECTION_PUBLIC_LABELS } from './registrationReviewApiContract.ts';
import type { ApplicantDataNote, ApplicantDetail, EmailEvidenceState, RegistrationReviewRejectionCode } from './registrationReviewApiContract.ts';

type Loaded =
  | { status: 'loading' }
  | { status: 'failed'; code: string }
  | { status: 'ready'; data: ApplicantDetail }
  | { status: 'approved'; data: ApplicantDetail }
  | { status: 'rejected'; data: ApplicantDetail; code: RegistrationReviewRejectionCode };

const APPROVE_PERMISSION = 'accounts.registration_requests.approve';
const REJECT_PERMISSION = 'accounts.registration_requests.reject';

/** Sub-page description and footer note for the decisions this session may make here. */
function decisionCopy(canApprove: boolean, canReject: boolean): { description: string; note: string } {
  if (canApprove && canReject) {
    return {
      description: 'One pending application. You can approve or reject it; each decision is confirmed first.',
      note: 'Viewing this page records nothing. Django verifies your permission and the decision rules on every request.',
    };
  }
  if (canApprove) {
    return {
      description: 'One pending application. You can approve it after confirming eligibility; nothing else on this page changes it.',
      note: 'Viewing this page records nothing. Rejection is a separate step and is not available here. Django verifies your permission and the approval rules on every request.',
    };
  }
  if (canReject) {
    return {
      description: 'One pending application. You can reject it with a fixed reason; nothing else on this page changes it.',
      note: 'Viewing this page records nothing. Approval is a separate step and is not available here. Django verifies your permission and the rejection rules on every request.',
    };
  }
  return {
    description: 'One pending application, read-only. Nothing on this page approves, rejects or changes it.',
    note: 'This page is read-only. Approval and rejection are separate steps and are not available here. Django verifies your permission on every request.',
  };
}

const outlineButton = 'dashboard-outline-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]';
const badgeClass = 'inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium';

const EVIDENCE: Record<EmailEvidenceState, { badge: string; positive: boolean; text: (email: string | null, at: string) => string }> = {
  verified: {
    badge: 'Email ownership verified', positive: true,
    text: (email, at) => `The applicant confirmed control of ${email ?? 'this address'} with a one-time code on ${at}. This shows control of the email address only. It does not confirm enrollment, employment or eligibility.`,
  },
  no_proof: {
    badge: 'No email proof on record', positive: false,
    text: () => 'This application has no recorded email verification, so the email address is unconfirmed. Whether such applications can be approved is decided by a separate policy that is still open.',
  },
  address_changed: {
    badge: 'Email address changed after verification', positive: false,
    text: () => 'A verification exists, but for a different address than the one now on file. The current address is unconfirmed.',
  },
  no_email: {
    badge: 'No email address on record', positive: false,
    text: () => 'Email ownership cannot be shown because the application has no email address.',
  },
};

const NOTES: Record<ApplicantDataNote, string> = {
  missing_profile: 'No name record exists for this application.',
  missing_first_name: 'The first name was not recorded.',
  missing_last_name: 'The last name was not recorded.',
};

function failure(code: string): { title: string; detail: string; retry: boolean } {
  switch (code) {
    case 'request_unavailable':
      return { title: 'This application is no longer pending.', detail: 'It may have been approved, rejected or withdrawn, or the link is not valid.', retry: false };
    case 'authentication_required':
      return { title: 'Your session has ended.', detail: 'Sign in again to continue.', retry: false };
    case 'access_denied':
      return { title: 'You do not have permission to review applications.', detail: 'Ask a School Admin to check your account access.', retry: false };
    case 'rate_limited':
      return { title: 'Too many requests.', detail: 'Wait a minute, then try again.', retry: true };
    case 'review_unavailable':
      return { title: 'Applications are not available right now.', detail: 'Try again later.', retry: true };
    default:
      return { title: 'The application could not be loaded.', detail: 'Check your connection, then try again.', retry: true };
  }
}

const formatTimestamp = (value: string) =>
  new Date(value).toLocaleString('en-PH', { dateStyle: 'medium', timeStyle: 'short' });

function Value({ value }: { value: string | null }) {
  return value ? <span className="break-words">{value}</span> : <span className="dashboard-muted italic">Not recorded</span>;
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 py-2.5 sm:grid-cols-[11rem_minmax(0,1fr)] sm:gap-4">
      <dt className="dashboard-muted text-xs font-medium uppercase tracking-wider sm:pt-0.5">{label}</dt>
      <dd className="dashboard-heading min-w-0 text-sm">{children}</dd>
    </div>
  );
}

interface Props {
  /** The raw `applicant` query value; validated here before any request. */
  raw: string;
  onBack: () => void;
  /** WF-02.03: the list behind this view is stale after a decision; refresh it. */
  onDecided?: () => void;
  /** WF-02.03 approval switch (D-46); a prop so tests can pin it. */
  approvalEnabled?: boolean;
  /** WF-02.04 rejection switch (D-62); a prop so tests can pin it. */
  rejectionEnabled?: boolean;
}

export default function ApplicantDetailPanel({
  raw, onBack, onDecided, approvalEnabled = APPLICANT_APPROVAL_ENABLED, rejectionEnabled = APPLICANT_REJECTION_ENABLED,
}: Props) {
  const { setSubpage, session } = useDashboardContext();
  const accountId = parseApplicantId(raw);
  const heading = useRef<HTMLHeadingElement>(null);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  // A hint only: Django re-checks the exact permission on the approval request.
  const [loaded, setLoaded] = useState<Loaded>(accountId === null ? { status: 'failed', code: 'request_unavailable' } : { status: 'loading' });
  const actions = loaded.status === 'ready' ? loaded.data.available_actions : undefined;
  const canApprove = approvalEnabled && actions?.includes('approve') === true && session.permissions.includes(APPROVE_PERMISSION);
  const canReject = rejectionEnabled && actions?.includes('reject') === true && session.permissions.includes(REJECT_PERMISSION);
  const copy = decisionCopy(canApprove, canReject);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (accountId === null) return;
    let cancelled = false;
    // GET only; never retried automatically; stale responses are discarded.
    getPendingApplication(accountId)
      .then((data) => {
        if (cancelled) return;
        setLoaded({ status: 'ready', data });
        setSubpage({
          label: `${data.id_label} ${data.school_id}`,
          description: decisionCopy(
            approvalEnabled && data.available_actions?.includes('approve') === true && session.permissions.includes(APPROVE_PERMISSION),
            rejectionEnabled && data.available_actions?.includes('reject') === true && session.permissions.includes(REJECT_PERMISSION),
          ).description,
        });
      })
      .catch((error: unknown) => {
        const code = error && typeof error === 'object' && 'code' in error ? String((error as { code: unknown }).code) : '';
        if (!cancelled) setLoaded({ status: 'failed', code });
      });
    return () => { cancelled = true; };
  }, [accountId, version, setSubpage, approvalEnabled, rejectionEnabled, session.permissions]);

  useEffect(() => () => setSubpage(null), [setSubpage]);
  useEffect(() => {
    if (loaded.status === 'ready') heading.current?.focus();
    if (loaded.status === 'approved' || loaded.status === 'rejected') resultHeading.current?.focus();
  }, [loaded.status]);

  function reload() {
    setLoaded({ status: 'loading' });
    setVersion((current) => current + 1);
  }

  const back = (
    <button type="button" className={outlineButton} onClick={onBack}>
      <span aria-hidden="true">←</span>Back to pending applications
    </button>
  );

  if (loaded.status === 'loading') {
    return <div className="space-y-5">{back}<p role="status" className="dashboard-muted py-8 text-sm">Loading the application…</p></div>;
  }
  if (loaded.status === 'failed') {
    const message = failure(loaded.code);
    return (
      <div className="space-y-5">
        {back}
        <section role="alert" className="dashboard-panel rounded-2xl border p-6 sm:p-8">
          <h2 className="dashboard-heading text-lg font-semibold">{message.title}</h2>
          <p className="dashboard-muted mt-2 text-sm">{message.detail}</p>
          {message.retry && (
            <button type="button" className={`${outlineButton} mt-5`} onClick={reload}>Try again</button>
          )}
        </section>
      </div>
    );
  }

  if (loaded.status === 'approved') {
    const done = loaded.data;
    return (
      <div className="space-y-5">
        {back}
        <section role="status" className="dashboard-success rounded-2xl border p-6 sm:p-8">
          <h2 ref={resultHeading} tabIndex={-1} className="text-lg font-semibold focus:outline-none">
            <span aria-hidden="true">✓ </span>Application approved
          </h2>
          <p className="mt-2 text-sm leading-relaxed">
            {done.full_name ?? 'The applicant'} ({done.id_label} {done.school_id}) is now active with the {done.requested_role} role
            and can sign in. Your approval and eligibility confirmation were recorded.
          </p>
          <p className="mt-2 text-sm leading-relaxed">
            What they can open after signing in depends on the permissions set for the {done.requested_role} role.
          </p>
          <p className="mt-2 text-sm leading-relaxed">
            An approval email has been queued for delivery. Delivery happens separately and is not confirmed here.
          </p>
        </section>
      </div>
    );
  }

  if (loaded.status === 'rejected') {
    const done = loaded.data;
    return (
      <div className="space-y-5">
        {back}
        <section role="status" className="dashboard-success rounded-2xl border p-6 sm:p-8">
          <h2 ref={resultHeading} tabIndex={-1} className="text-lg font-semibold focus:outline-none">
            <span aria-hidden="true">✓ </span>Application rejected
          </h2>
          <p className="mt-2 text-sm leading-relaxed">
            The application from {done.full_name ?? 'the applicant'} ({done.id_label} {done.school_id}) was rejected with the
            reason &ldquo;{REJECTION_PUBLIC_LABELS[loaded.code]}&rdquo;, and their registration data were deleted. Your decision was recorded.
          </p>
          <p className="mt-2 text-sm leading-relaxed">
            A rejection email has been queued for delivery. Delivery happens separately and is not confirmed here. The applicant
            may register again with the same {done.id_label} and email address.
          </p>
        </section>
      </div>
    );
  }

  const data = loaded.data;
  const evidence = EVIDENCE[data.email_evidence.state];
  const student = data.institutional_check.subject === 'enrollment';

  return (
    <div className="space-y-5">
      {back}

      <div>
        <h2 ref={heading} tabIndex={-1} className="dashboard-heading text-xl font-bold focus:outline-none sm:text-2xl">
          {data.full_name ?? 'Name not recorded'}
        </h2>
        <p className="dashboard-muted mt-1 text-sm">{data.id_label} {data.school_id} · {data.requested_role} applicant · Pending review</p>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <section aria-labelledby="applicant-info" className="dashboard-panel rounded-2xl border p-5 sm:p-6">
          <h3 id="applicant-info" className="dashboard-heading text-lg font-semibold">Applicant information</h3>
          <dl className="mt-3 divide-y">
            <Row label="First name"><Value value={data.name.first} /></Row>
            <Row label="Middle name"><Value value={data.name.middle} /></Row>
            <Row label="Last name"><Value value={data.name.last} /></Row>
            <Row label="Suffix"><Value value={data.name.suffix} /></Row>
            <Row label={data.id_label}><span className="font-semibold">{data.school_id}</span></Row>
            <Row label="Requested role">{data.requested_role}</Row>
            <Row label="Submitted"><time dateTime={data.created_at}>{formatTimestamp(data.created_at)}</time></Row>
            <Row label="Request status">Pending review</Row>
          </dl>
          {data.data_notes.length > 0 && (
            <ul className="dashboard-muted mt-3 space-y-1 border-t pt-3 text-sm" aria-label="Data notes">
              {data.data_notes.map((note) => <li key={note}><span aria-hidden="true">! </span>{NOTES[note]}</li>)}
            </ul>
          )}
        </section>

        <section aria-labelledby="email-evidence" className="dashboard-panel rounded-2xl border p-5 sm:p-6">
          <h3 id="email-evidence" className="dashboard-heading text-lg font-semibold">Email verification evidence</h3>
          <dl className="mt-3 divide-y">
            <Row label="Email address"><Value value={data.email} /></Row>
            <Row label="Evidence">
              <span className={`${badgeClass} ${evidence.positive ? 'dashboard-heading' : 'dashboard-muted border-dashed'}`}>
                <span aria-hidden="true">{evidence.positive ? '✓' : '!'}</span>{evidence.badge}
              </span>
            </Row>
          </dl>
          <p className="dashboard-muted mt-3 text-sm leading-relaxed">
            {evidence.text(data.email, data.email_evidence.verified_at ? formatTimestamp(data.email_evidence.verified_at) : '')}
          </p>
        </section>
      </div>

      <section aria-labelledby="institutional" className="dashboard-panel rounded-2xl border p-5 sm:p-6">
        <h3 id="institutional" className="dashboard-heading text-lg font-semibold">Institutional eligibility</h3>
        <p className="mt-3">
          <span className={`${badgeClass} dashboard-muted border-dashed`}>
            <span aria-hidden="true">!</span>{student ? 'Enrollment not verified by CTU-G Workspace' : 'Institutional eligibility not verified by CTU-G Workspace'}
          </span>
        </p>
        <p className="dashboard-muted mt-3 text-sm leading-relaxed">
          {student
            ? "Student enrollment is managed by CTU's main system. Confirm the applicant's enrollment there before any decision. CTU-G Workspace does not record or manage enrollment."
            : "An authorized School Admin must confirm the applicant's employment or appointment through institutional records before any decision."}
        </p>
      </section>

      {canApprove && (
        <ApplicantApprovalPanel data={data}
          onApproved={() => { setLoaded({ status: 'approved', data }); onDecided?.(); }}
          onGone={() => { setLoaded({ status: 'failed', code: 'request_unavailable' }); onDecided?.(); }}
          onReload={reload} />
      )}

      {canReject && (
        <ApplicantRejectionPanel data={data}
          onRejected={(code) => { setLoaded({ status: 'rejected', data, code }); onDecided?.(); }}
          onGone={() => { setLoaded({ status: 'failed', code: 'request_unavailable' }); onDecided?.(); }}
          onReload={reload} />
      )}

      <p className="dashboard-muted text-xs leading-relaxed">{copy.note}</p>
    </div>
  );
}
