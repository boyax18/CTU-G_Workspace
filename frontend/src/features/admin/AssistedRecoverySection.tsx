/** Account detail: start assisted email recovery for a person who cannot sign in (25 Nov 2026).
 *
 * Shown only with the exact permission hint accounts.school_accounts.assist_recovery; Django
 * re-checks it, the account rules and the privileged-account boundary on every request. The
 * operator attests an out-of-band identity check, then a one-time code is queued to the
 * account's CURRENT email. The operator never sees the code and nothing on the account changes
 * until the holder enters it on Forgot Password. One POST per confirmation; never retried.
 */
import { useId, useRef, useState } from 'react';
import Modal from '../../components/common/Modal';
import { startAssistedRecovery } from './assistedRecoveryApi.ts';
import type { AssistedRecoveryError } from './assistedRecoveryApi.ts';

const ring = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)] disabled:cursor-not-allowed disabled:opacity-50';
const secondaryButton = `dashboard-outline-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${ring}`;
const primaryButton = `dashboard-primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${ring}`;

const REASON_TEXT: Record<string, string> = {
  own_account: 'You cannot start recovery for your own account.',
  privileged_account: 'Administrator and Technical Super Admin accounts need a separately approved recovery process. Nothing was sent.',
  inactive_account: 'This account is inactive. Reactivation is a separate decision; nothing was sent.',
  no_operational_role: 'This account has no active role, so it cannot be recovered here. Nothing was sent.',
  email_missing: 'This account has no email address on file. Nothing was sent.',
  already_verified: 'This account’s email is already verified. The person can use Forgot password directly.',
};

interface Props { accountId: number; name: string; idLabel: string; schoolId: string }

export default function AssistedRecoverySection({ accountId, name, idLabel, schoolId }: Props) {
  const ids = useId();
  const [open, setOpen] = useState(false);
  const [attested, setAttested] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [problem, setProblem] = useState('');
  const [paused, setPaused] = useState(false);
  const inFlight = useRef(false);

  async function confirm() {
    if (inFlight.current || !attested) return;
    inFlight.current = true;
    setBusy(true);
    try {
      const { codeValidSeconds } = await startAssistedRecovery(accountId);
      setProblem('');
      setNotice(`A one-time recovery code is queued for the email address on this account. Delivery is not confirmed `
        + `until the person receives it. Ask them to open Forgot password, choose “I have an account recovery code” and enter it `
        + `within ${Math.max(1, Math.round(codeValidSeconds / 60))} minutes.`);
    } catch (error: unknown) {
      const err = error as AssistedRecoveryError;
      setNotice('');
      if (err.outcomeUnknown) {
        setPaused(true);
        setProblem('We could not confirm whether a code was queued. Reload the account before trying again.');
      } else if (err.reason === 'recovery_wait') {
        setProblem(`A code was queued recently. Wait${err.retryAfter ? ` ${err.retryAfter} seconds` : ''} before queuing another.`);
      } else if (err.reason && REASON_TEXT[err.reason]) {
        setProblem(REASON_TEXT[err.reason]);
      } else if (err.status === 403) {
        setProblem('You do not have permission to start assisted recovery. Nothing was sent.');
      } else if (err.status === 503) {
        setProblem('Assisted recovery is not available right now. Nothing was sent.');
      } else {
        setProblem('Assisted recovery could not be started. Nothing was sent.');
      }
    } finally {
      inFlight.current = false;
      setBusy(false);
      setOpen(false);
      setAttested(false);
    }
  }

  return (
    <section aria-labelledby={`${ids}-title`} className="dashboard-panel rounded-2xl border p-5 sm:p-6">
      <h3 id={`${ids}-title`} className="dashboard-heading text-lg font-semibold">Assisted email recovery</h3>
      <p className="dashboard-muted mt-1 text-sm leading-relaxed">
        For a person who cannot sign in and has never verified their email. After you confirm their identity, a one-time code
        is sent to the email address on this account. Entering it verifies the email and lets them choose a new password.
        You never see the code, and nothing changes until they use it.
      </p>
      {(notice || problem) && (
        <p role={problem ? 'alert' : 'status'}
          className={`${problem ? 'dashboard-error-block' : 'dashboard-success'} mt-4 rounded-xl border p-4 text-sm`}>{problem || notice}</p>
      )}
      <button type="button" className={`${primaryButton} mt-4`} disabled={busy || paused}
        onClick={() => { setNotice(''); setProblem(''); setAttested(false); setOpen(true); }}>
        Send recovery code
      </button>

      <Modal open={open} title="Send an account recovery code?" busy={busy} onClose={() => { if (!busy) setOpen(false); }}
        actions={(
          <>
            <button type="button" className={secondaryButton} disabled={busy} onClick={() => setOpen(false)}>Cancel</button>
            <button type="button" className={primaryButton} disabled={busy || !attested} onClick={() => { void confirm(); }}>
              {busy ? 'Queuing…' : 'Send recovery code'}
            </button>
          </>
        )}>
        <p className="dashboard-heading">{name} ({idLabel} {schoolId})</p>
        <p className="dashboard-muted">The code goes only to the email address already on this account. It is audited.</p>
        <label className="dashboard-heading flex items-start gap-3 text-sm">
          <input type="checkbox" className="mt-1 h-4 w-4" checked={attested} disabled={busy}
            onChange={(event) => setAttested(event.target.checked)} />
          I confirmed this person’s identity in person or through official records, and they confirmed the email address on file is theirs.
        </label>
        {busy && <p role="status" className="dashboard-muted">Queuing the recovery code…</p>}
      </Modal>
    </section>
  );
}
