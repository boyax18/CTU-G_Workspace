/** WF-02.04 Reject applicant: the rejection section of the WF-02.02 detail.
 *
 * Shown only when the rejection switch is on AND the session reports the exact reject permission;
 * that is a hint only, and Django re-checks the permission, the verified recipient (D-55 revised),
 * the durable outbox (D-54) and every conflict (D-58) on the request. The reviewer picks one of the
 * four fixed reasons (D-56) and sees the exact public wording the applicant will receive; no free
 * text exists. One POST per confirmation, never repeated: an uncertain result pauses rejection
 * until the application is reloaded. Success says the email was QUEUED, never that it was sent.
 */
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Modal from '../../components/common/Modal';
import { rejectApplication } from './registrationReviewApi.ts';
import { REGISTRATION_REJECTION_CODES, REJECTION_PUBLIC_LABELS } from './registrationReviewApiContract.ts';
import type { ApplicantDetail, RegistrationReviewRejectionCode } from './registrationReviewApiContract.ts';

const focusRing = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)] disabled:cursor-not-allowed disabled:opacity-50';
const secondaryButton = `dashboard-outline-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${focusRing}`;
// COMPONENTS §2 destructive style: only for the dialog's confirm button, never the button that opens it.
const destructiveButton = `inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#b91c1c] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#991b1b] ${focusRing}`;
const fieldClass = `dashboard-panel min-h-11 w-full rounded-lg border px-3 py-2 text-sm ${focusRing}`;

type Phase = 'idle' | 'confirming' | 'submitting';

interface Failure { code: string; title: string; detail: string; reload: boolean }

/** Fixed messages only; server text is never displayed. */
function failureFor(code: string): Failure {
  const f = (title: string, detail: string, reload = false) => ({ code, title, detail, reload });
  switch (code) {
    case 'recipient_unverified':
      return f('Rejection was refused: the email address is not verified.', 'The applicant could not be told, so the application stays pending. Reload it to see its current evidence.', true);
    case 'direct_permissions':
      return f('This application cannot be rejected here.', 'It has direct permission records and needs a separate review. The application stays pending.');
    case 'protected_history':
      return f('This application cannot be rejected here.', 'It has history that must be kept and needs a separate review. The application stays pending.');
    case 'rejection_not_allowed':
      return f('Rejection is not allowed for this application.', 'The application stays pending. Reload it to see its current state.', true);
    case 'access_denied':
      return f('You do not have permission to reject applications.', 'The application was not rejected. Ask a School Admin to check your account access.');
    case 'authentication_required':
      return f('Your session has ended.', 'The application was not rejected. Sign in again to continue.');
    case 'rate_limited':
      return f('Too many requests.', 'The application was not rejected. Wait a minute, then try again.');
    case 'review_unavailable':
      return f('Rejection is not available right now.', 'The application was not rejected. Try again later.');
    case 'invalid_request':
      return f('The rejection request was not accepted.', 'The application was not rejected. Reload it, then try again.', true);
    case 'outcome_unknown':
      return f('We could not confirm whether the application was rejected.', 'Do not reject it again yet. Reload the application to check its current status first.', true);
    default:
      return f('The rejection could not be sent.', 'The application was not rejected. Check your connection, then try again.');
  }
}

const errorCode = (error: unknown) =>
  error && typeof error === 'object' && 'code' in error ? String((error as { code: unknown }).code) : '';

interface Props {
  data: ApplicantDetail;
  /** The server confirmed this exact rejection and that its email was queued. */
  onRejected: (code: RegistrationReviewRejectionCode) => void;
  /** The application is no longer pending (404): show the detail's unavailable state. */
  onGone: () => void;
  /** Re-read the application (GET only). */
  onReload: () => void;
}

export default function ApplicantRejectionPanel({ data, onRejected, onGone, onReload }: Props) {
  const ids = useId();
  const recipientReady = data.email_evidence.state === 'verified' && data.email !== null;
  const [code, setCode] = useState<'' | RegistrationReviewRejectionCode>('');
  const [error, setError] = useState('');
  const [phase, setPhase] = useState<Phase>('idle');
  const [failure, setFailure] = useState<Failure | null>(null);
  const inFlight = useRef(false);
  const selectRef = useRef<HTMLSelectElement>(null);
  const alertRef = useRef<HTMLDivElement>(null);
  const locked = failure?.code === 'outcome_unknown';

  // After the dialog closes on a refusal, move focus to the message (after Modal returns it).
  useEffect(() => { if (failure && phase === 'idle') alertRef.current?.focus(); }, [failure, phase]);

  function openConfirmation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked || inFlight.current) return;
    if (!code) {
      setError('Choose the reason for rejecting this application.');
      selectRef.current?.focus();
      return;
    }
    setError('');
    setFailure(null);
    setPhase('confirming');
  }

  async function confirmRejection() {
    if (inFlight.current || !code) return; // duplicate-submit guard
    inFlight.current = true;
    setPhase('submitting');
    try {
      await rejectApplication(data.account_id, code);
      onRejected(code);
    } catch (caught: unknown) {
      const reason = errorCode(caught);
      if (reason === 'request_unavailable') { onGone(); return; }
      setFailure(failureFor(reason));
      setPhase('idle');
    } finally {
      inFlight.current = false;
    }
  }

  const hint = `${ids}-hint`;
  const errorId = `${ids}-error`;
  const busy = phase === 'submitting';
  const name = data.full_name ?? 'this applicant';

  return (
    <section aria-labelledby={`${ids}-title`} className="dashboard-panel rounded-2xl border p-5 sm:p-6">
      <h3 id={`${ids}-title`} className="dashboard-heading text-lg font-semibold">Reject application</h3>
      <p className="dashboard-muted mt-1 text-sm">
        Rejecting deletes this application and the applicant&apos;s registration data. The applicant is told by email and may
        register again. Approval is a separate step.
      </p>

      {failure && (
        <div ref={alertRef} tabIndex={-1} role="alert" className="dashboard-error-block mt-4 rounded-xl border p-4 text-sm focus:outline-none">
          <p className="font-semibold"><span aria-hidden="true">! </span>{failure.title}</p>
          <p className="mt-1">{failure.detail}</p>
          {failure.reload && <button type="button" className={`${secondaryButton} mt-3`} onClick={onReload}>Reload application</button>}
        </div>
      )}

      {!recipientReady ? (
        <p role="status" className="dashboard-warning mt-4 rounded-xl border p-4 text-sm">
          This application cannot be rejected here. A rejection needs a verified email address so the applicant can be told,
          and the address on file is not verified.
        </p>
      ) : (
        <form noValidate onSubmit={openConfirmation} aria-busy={busy} className="mt-4">
          <fieldset disabled={busy || locked} className="space-y-4">
            <legend className="dashboard-muted text-xs">Fields marked * are required.</legend>
            <label className="dashboard-muted flex flex-col gap-1 text-xs font-medium">
              Rejection reason *
              <select ref={selectRef} value={code} className={fieldClass}
                aria-invalid={error ? true : undefined}
                aria-describedby={error ? `${errorId} ${hint}` : hint}
                onChange={(event) => { setCode(event.target.value as '' | RegistrationReviewRejectionCode); setError(''); }}>
                <option value="">Choose a reason</option>
                {REGISTRATION_REJECTION_CODES.map((option) => (
                  <option key={option} value={option}>{REJECTION_PUBLIC_LABELS[option]}</option>
                ))}
              </select>
            </label>
            {error && <p id={errorId} className="dashboard-error -mt-2 text-xs">{error}</p>}
            <p id={hint} className="dashboard-muted -mt-2 text-xs leading-relaxed">
              The applicant sees exactly this reason in the email. Notes or free text are not sent or stored.
            </p>
            <p className="dashboard-heading text-sm">
              <span aria-hidden="true" className="dashboard-accent">✓ </span>
              A rejection email can be queued for {data.email}, the verified address on file.
            </p>
            <button type="submit" className={secondaryButton}>Reject application</button>
            {locked && <p className="dashboard-muted text-xs">Rejection is paused until you reload the application.</p>}
          </fieldset>
        </form>
      )}

      <Modal open={phase !== 'idle'} title="Confirm rejection?" busy={busy} onClose={() => setPhase('idle')}
        actions={(
          <>
            <button type="button" className={secondaryButton} disabled={busy} onClick={() => setPhase('idle')}>Cancel</button>
            <button type="button" className={destructiveButton} disabled={busy} onClick={confirmRejection}>
              {busy ? 'Rejecting…' : 'Confirm rejection'}
            </button>
          </>
        )}>
        <p className="dashboard-heading">
          Reject {name} ({data.id_label} {data.school_id}) with the reason &ldquo;{code ? REJECTION_PUBLIC_LABELS[code] : ''}&rdquo;?
        </p>
        <p className="dashboard-muted">
          This deletes the applicant&apos;s account and registration data, and queues a rejection email to {data.email}.
          It is audited and cannot be undone.
        </p>
        {busy && <p role="status" className="dashboard-muted">Rejecting the application…</p>}
      </Modal>
    </section>
  );
}
