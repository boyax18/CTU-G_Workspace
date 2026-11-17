/** WF-02.03 Approve applicant account: the approval section of the WF-02.02 detail.
 *
 * Shown only when the approval switch is on AND the session reports the exact approve permission;
 * that is a hint only, and Django re-checks the permission, the email evidence (D-44) and the
 * attestation (D-45) on the request. The reviewer cites the ONE fixed source for the role and
 * confirms they checked it; CTU-G Workspace never claims to have verified enrollment or employment.
 * The role is shown read-only and never sent. One POST per confirmation, never repeated: an
 * uncertain result locks the form until the application is reloaded (D-48).
 */
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Modal from '../../components/common/Modal';
import { approveApplication } from './registrationReviewApi.ts';
import { ELIGIBILITY_SOURCE_FOR_ROLE, ELIGIBILITY_SOURCE_LABELS } from './registrationReviewApiContract.ts';
import type { ApplicantDetail, EligibilitySource } from './registrationReviewApiContract.ts';

const primaryButton = 'dashboard-primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)] disabled:cursor-not-allowed disabled:opacity-50';
const secondaryButton = 'dashboard-outline-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)] disabled:cursor-not-allowed disabled:opacity-50';
const fieldClass = 'dashboard-panel min-h-11 w-full rounded-lg border px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]';

type Phase = 'idle' | 'confirming' | 'submitting';

interface Failure { code: string; title: string; detail: string; reload: boolean }

/** Fixed messages only; server text is never displayed. */
function failureFor(code: string): Failure {
  const f = (title: string, detail: string, reload = false) => ({ code, title, detail, reload });
  switch (code) {
    case 'email_unverified':
      return f('Approval was refused: the email address is not verified.', 'The address on file has no matching verification, so the application stays pending. Reload it to see its current evidence.', true);
    case 'eligibility_unconfirmed':
      return f('Approval was refused: the eligibility confirmation was not accepted.', 'The application stays pending. Check the source and your confirmation, then try again.');
    case 'approval_not_allowed':
      return f('Approval is not allowed for this application.', 'The application stays pending. Reload it to see its current state.', true);
    case 'access_denied':
      return f('You do not have permission to approve applications.', 'The application was not approved. Ask a School Admin to check your account access.');
    case 'authentication_required':
      return f('Your session has ended.', 'The application was not approved. Sign in again to continue.');
    case 'rate_limited':
      return f('Too many requests.', 'The application was not approved. Wait a minute, then try again.');
    case 'review_unavailable':
      return f('Approval is not available right now.', 'The application was not approved. Try again later.');
    case 'invalid_request':
      return f('The approval request was not accepted.', 'The application was not approved. Reload it, then try again.', true);
    case 'outcome_unknown':
      return f('We could not confirm whether the application was approved.', 'Do not approve it again yet. Reload the application to check its current status first.', true);
    default:
      return f('The approval could not be sent.', 'The application was not approved. Check your connection, then try again.');
  }
}

const errorCode = (error: unknown) =>
  error && typeof error === 'object' && 'code' in error ? String((error as { code: unknown }).code) : '';

interface Props {
  data: ApplicantDetail;
  /** The server confirmed this exact approval. */
  onApproved: () => void;
  /** The application is no longer pending (404): show the detail's unavailable state. */
  onGone: () => void;
  /** Re-read the application (GET only). */
  onReload: () => void;
}

export default function ApplicantApprovalPanel({ data, onApproved, onGone, onReload }: Props) {
  const ids = useId();
  const role = data.requested_role;
  const expected: EligibilitySource = ELIGIBILITY_SOURCE_FOR_ROLE[role];
  const subject = data.institutional_check.subject === 'enrollment' ? 'enrollment' : 'employment or appointment';
  const emailReady = data.email_evidence.state === 'verified';
  const [source, setSource] = useState<'' | EligibilitySource>('');
  const [confirmed, setConfirmed] = useState(false);
  const [errors, setErrors] = useState<{ source?: string; confirmed?: string }>({});
  const [phase, setPhase] = useState<Phase>('idle');
  const [failure, setFailure] = useState<Failure | null>(null);
  const inFlight = useRef(false);
  const sourceRef = useRef<HTMLSelectElement>(null);
  const confirmRef = useRef<HTMLInputElement>(null);
  const alertRef = useRef<HTMLDivElement>(null);
  const locked = failure?.code === 'outcome_unknown';

  // After the dialog closes on a refusal, move focus to the message (after Modal returns it).
  useEffect(() => { if (failure && phase === 'idle') alertRef.current?.focus(); }, [failure, phase]);

  function openConfirmation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked || inFlight.current) return;
    const next: typeof errors = {};
    if (source !== expected) next.source = 'Choose the source where you checked eligibility.';
    if (!confirmed) next.confirmed = `Confirm that you checked the applicant's ${subject}.`;
    setErrors(next);
    if (next.source) { sourceRef.current?.focus(); return; }
    if (next.confirmed) { confirmRef.current?.focus(); return; }
    setFailure(null);
    setPhase('confirming');
  }

  async function confirmApproval() {
    if (inFlight.current || source !== expected || !confirmed) return; // duplicate-submit guard
    inFlight.current = true;
    setPhase('submitting');
    try {
      await approveApplication(data.account_id, expected);
      onApproved();
    } catch (error: unknown) {
      const code = errorCode(error);
      if (code === 'request_unavailable') { onGone(); return; }
      setFailure(failureFor(code));
      if (code === 'eligibility_unconfirmed') setConfirmed(false);
      setPhase('idle');
    } finally {
      inFlight.current = false;
    }
  }

  const sourceHint = `${ids}-source-hint`;
  const sourceError = `${ids}-source-error`;
  const confirmError = `${ids}-confirm-error`;
  const busy = phase === 'submitting';
  const name = data.full_name ?? 'this applicant';

  return (
    <section aria-labelledby={`${ids}-title`} className="dashboard-panel rounded-2xl border p-5 sm:p-6">
      <h3 id={`${ids}-title`} className="dashboard-heading text-lg font-semibold">Approve application</h3>
      <p className="dashboard-muted mt-1 text-sm">
        Approving activates this account and assigns the {role} role. Rejection is a separate step.
      </p>

      <h4 className="dashboard-heading mt-4 text-sm font-semibold">Before you approve</h4>
      <ul className="mt-2 space-y-2 text-sm">
        <li className="flex gap-2">
          <span aria-hidden="true" className={emailReady ? 'dashboard-accent' : 'dashboard-error'}>{emailReady ? '✓' : '✕'}</span>
          <span className="dashboard-heading">
            {emailReady ? 'Email ownership is verified for the current address.' : 'Email ownership is not verified for the current address.'}
          </span>
        </li>
        <li className="flex gap-2">
          <span aria-hidden="true" className="dashboard-muted">!</span>
          <span className="dashboard-heading">
            Institutional eligibility: you confirm it below. CTU-G Workspace does not verify {data.institutional_check.subject}.
          </span>
        </li>
      </ul>

      {failure && (
        <div ref={alertRef} tabIndex={-1} role="alert" className="dashboard-error-block mt-4 rounded-xl border p-4 text-sm focus:outline-none">
          <p className="font-semibold"><span aria-hidden="true">! </span>{failure.title}</p>
          <p className="mt-1">{failure.detail}</p>
          {failure.reload && <button type="button" className={`${secondaryButton} mt-3`} onClick={onReload}>Reload application</button>}
        </div>
      )}

      {!emailReady ? (
        <p role="status" className="dashboard-warning mt-4 rounded-xl border p-4 text-sm">
          This application cannot be approved. Approval requires a verified email for the address now on file.
        </p>
      ) : (
        <form noValidate onSubmit={openConfirmation} aria-busy={busy} className="mt-4">
          <fieldset disabled={busy || locked} className="space-y-4">
            <legend className="dashboard-muted text-xs">Fields marked * are required.</legend>
            <dl className="grid gap-1 sm:grid-cols-[11rem_minmax(0,1fr)] sm:gap-4">
              <dt className="dashboard-muted text-xs font-medium uppercase tracking-wider sm:pt-0.5">Role to assign</dt>
              <dd className="dashboard-heading text-sm font-semibold">{role} <span className="dashboard-muted font-normal">(the requested role; it cannot be changed)</span></dd>
            </dl>
            <label className="dashboard-muted flex flex-col gap-1 text-xs font-medium">
              Where you checked eligibility *
              <select ref={sourceRef} value={source} className={fieldClass}
                aria-invalid={errors.source ? true : undefined}
                aria-describedby={errors.source ? `${sourceError} ${sourceHint}` : sourceHint}
                onChange={(event) => { setSource(event.target.value as '' | EligibilitySource); setErrors({ ...errors, source: undefined }); }}>
                <option value="">Choose the source you checked</option>
                <option value={expected}>{ELIGIBILITY_SOURCE_LABELS[expected]}</option>
              </select>
            </label>
            {errors.source && <p id={sourceError} className="dashboard-error -mt-2 text-xs">{errors.source}</p>}
            <p id={sourceHint} className="dashboard-muted -mt-2 text-xs leading-relaxed">
              {role === 'Student'
                ? "Student enrollment is managed by CTU's main system. Only that source is accepted for a Student."
                : 'Employment or appointment is confirmed through institutional employment records. Only that source is accepted for an Instructor.'}
            </p>
            <div>
              <label className="dashboard-heading flex min-h-11 items-start gap-3 text-sm">
                <input ref={confirmRef} type="checkbox" checked={confirmed}
                  className="mt-0.5 h-5 w-5 shrink-0 accent-[color:var(--db-button)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]"
                  aria-invalid={errors.confirmed ? true : undefined}
                  aria-describedby={errors.confirmed ? confirmError : undefined}
                  onChange={(event) => { setConfirmed(event.target.checked); setErrors({ ...errors, confirmed: undefined }); }} />
                <span>
                  {role === 'Student'
                    ? "I checked this applicant's current enrollment in CTU main system enrollment records, and they are eligible. *"
                    : "I checked this applicant's employment or appointment in institutional employment records, and they are eligible. *"}
                </span>
              </label>
              {errors.confirmed && <p id={confirmError} className="dashboard-error mt-1 text-xs">{errors.confirmed}</p>}
            </div>
            <p className="dashboard-muted text-xs leading-relaxed">
              Your confirmation is recorded with your account, the source and the time of approval. Do not enter or upload documents.
            </p>
            <button type="submit" className={primaryButton}>Approve application</button>
            {locked && (
              <p className="dashboard-muted text-xs">Approval is paused until you reload the application.</p>
            )}
          </fieldset>
        </form>
      )}

      <Modal open={phase !== 'idle'} title="Confirm approval?" busy={busy} onClose={() => setPhase('idle')}
        actions={(
          <>
            <button type="button" className={secondaryButton} disabled={busy} onClick={() => setPhase('idle')}>Cancel</button>
            <button type="button" className={primaryButton} disabled={busy} onClick={confirmApproval}>
              {busy ? 'Approving…' : 'Confirm approval'}
            </button>
          </>
        )}>
        <p className="dashboard-heading">
          Approve {name} ({data.id_label} {data.school_id}) as {role === 'Instructor' ? 'an' : 'a'} {role}?
        </p>
        <p className="dashboard-muted">
          This activates the account, assigns the {role} role and records your confirmation that you checked{' '}
          {ELIGIBILITY_SOURCE_LABELS[expected]}. It is audited and cannot be undone here.
        </p>
        {busy && <p role="status" className="dashboard-muted">Approving the application…</p>}
      </Modal>
    </section>
  );
}
