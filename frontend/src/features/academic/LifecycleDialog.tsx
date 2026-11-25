/** WF-11.01 activation (D02-D04, D10), closure (D11) and archiving (D12): review, then explicit confirmation.
 *
 * The dialog shows the server's preview exactly (prerequisites, obligations, warnings, blockers) and
 * sends back what was reviewed: the semester version, the Active semester shown and the warnings shown.
 * Unavailable information is shown as "Cannot be checked yet", never as zero. The confirm button is
 * enabled only when the server reports the action confirmable AND this build's switch is on.
 */
import { useEffect, useState } from 'react';
import Modal from '../../components/common/Modal.tsx';
import { AcademicApiError } from './academicPeriodsApi.ts';
import { confirmTransition, getActivationPreview, getObligationPreview } from './academicLifecycleApi.ts';
import type { Transition } from './academicLifecycleApi.ts';
import {
  OBLIGATION_LABELS, PREREQUISITE_LABELS, dependencyNote, warningLabel,
} from './academicLifecycleContract.ts';
import type { ActivationPreview, ObligationPreview, SemesterRef } from './academicLifecycleContract.ts';
import { formatDate, primaryButton, secondaryButton } from './academicStyles.ts';

type Preview = ActivationPreview | ObligationPreview;
type Load = { status: 'loading' } | { status: 'failed'; code: string; reason: string } | { status: 'ready'; data: Preview };

const COPY: Record<Transition, { title: string; confirm: string; busy: string; effect: string }> = {
  activation: {
    title: 'Activate this semester?', confirm: 'Activate semester', busy: 'Activating…',
    effect: 'Only one semester can be Active. Activation does not create student records, clearances or fees, and it never happens automatically.',
  },
  closure: {
    title: 'Close this semester?', confirm: 'Close semester', busy: 'Closing…',
    effect: 'Closing keeps every student record, unpaid fee and missing clearance signature exactly as it is. Nobody is marked cleared and no payment is settled. New onboarding stops for this semester.',
  },
  archive: {
    title: 'Archive this semester?', confirm: 'Archive semester', busy: 'Archiving…',
    effect: 'Archiving keeps all academic, financial and clearance history and authorized access to resolve it. The semester cannot be reopened, activated again or deleted.',
  },
};

const PREREQUISITE_STATUS: Record<string, { mark: string; text: string; tone: string }> = {
  ready: { mark: '✓', text: 'Ready', tone: 'dashboard-accent font-semibold' },
  missing: { mark: '!', text: 'Missing configuration', tone: 'dashboard-error font-semibold' },
  unavailable: { mark: '○', text: 'Not available yet', tone: 'dashboard-muted' },
};

function refusalText(error: unknown): string {
  const detail = error instanceof AcademicApiError ? error.detail : null;
  if (!detail) return 'The change could not be confirmed. Reload the list before trying again.';
  if (detail.code === 'outcome_unknown') return 'We could not confirm the change. Reload the list to see the current state before trying again.';
  if (detail.code === 'feature_disabled') return 'This action is not enabled on the server.';
  if (detail.code === 'access_denied') return detail.reason === 'admin_context_required'
    ? 'Switch to your School Admin role, then try again.' : 'You do not have permission to make this change.';
  if (detail.code === 'csrf_failed') return 'Security check failed. Refresh the page and try again.';
  switch (detail.reason) {
    case 'prerequisites_missing': return 'Activation prerequisites are not met.';
    case 'active_changed': case 'warnings_changed': return 'The situation changed since this review. Review it again.';
    case 'stale_version': return 'This semester was changed by someone else. Reload and review again.';
    case 'not_draft': case 'not_active': case 'not_closed': return 'This semester is no longer in the expected status. Reload the list.';
    default: return 'The change could not be applied. Reload the list and try again.';
  }
}

interface Props {
  transition: Transition;
  semester: { semester_id: number; label: string };
  yearLabel: string;
  /** This build's switch for confirmations. The server's own state comes from the preview. */
  buildEnabled: boolean;
  onClose: () => void;
  onDone: (result: SemesterRef, message: string) => void;
}

export default function LifecycleDialog({ transition, semester, yearLabel, buildEnabled, onClose, onDone }: Props) {
  const [load, setLoad] = useState<Load>({ status: 'loading' });
  const [version, setVersion] = useState(0);
  const [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const copy = COPY[transition];

  useEffect(() => {
    let cancelled = false;
    const request = transition === 'activation'
      ? getActivationPreview(semester.semester_id) : getObligationPreview(semester.semester_id, transition);
    request
      .then((data) => { if (!cancelled) setLoad({ status: 'ready', data }); })
      .catch((e: unknown) => {
        if (cancelled) return;
        const detail = e instanceof AcademicApiError ? e.detail : null;
        setLoad({ status: 'failed', code: detail?.code ?? '', reason: detail?.reason ?? '' });
      });
    return () => { cancelled = true; };
  }, [transition, semester.semester_id, version]);

  function reload() { setLoad({ status: 'loading' }); setReviewed(false); setError(''); setVersion((v) => v + 1); }

  const data = load.status === 'ready' ? load.data : null;
  const warnings = data?.warnings ?? [];
  const featureOff = data ? !data.feature_enabled || !buildEnabled : false;
  const canConfirm = Boolean(data?.can_confirm) && buildEnabled && (warnings.length === 0 || reviewed);

  async function confirm() {
    if (!data || !canConfirm) return;
    setBusy(true);
    setError('');
    try {
      const result = await confirmTransition(semester.semester_id, transition, {
        expected_version: data.semester.version, acknowledged_warnings: warnings,
        expected_active_semester_id: 'current_active' in data ? data.current_active?.semester_id ?? null : undefined,
      });
      const done = transition === 'activation' ? 'activated' : transition === 'closure' ? 'closed' : 'archived';
      onDone(result, `${semester.label}, S.Y. ${yearLabel}, was ${done}.`);
    } catch (e: unknown) {
      setError(refusalText(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open title={copy.title} busy={busy} onClose={onClose}
      actions={<>
        <button type="button" className={secondaryButton} disabled={busy} onClick={onClose}>Cancel</button>
        <button type="button" className={primaryButton} disabled={busy || !canConfirm} onClick={() => void confirm()}>
          {busy ? copy.busy : copy.confirm}
        </button>
      </>}>
      <p className="dashboard-heading font-semibold">{semester.label}, S.Y. {yearLabel}</p>
      {load.status === 'loading' && <p role="status" className="dashboard-muted">Checking the current state…</p>}
      {load.status === 'failed' && (
        <div role="alert" className="dashboard-error-block rounded-xl border p-3">
          <p><span aria-hidden="true" className="mr-2 font-bold">!</span>{load.code === 'access_denied'
            ? (load.reason === 'admin_context_required' ? 'Permission denied: switch to your School Admin role.' : 'Permission denied: you cannot manage academic periods.')
            : 'The review could not be loaded.'}</p>
          {load.code !== 'access_denied' && <button type="button" className={`${secondaryButton} mt-2`} onClick={reload}>Try again</button>}
        </div>
      )}
      {data && (
        <>
          {featureOff && (
            <p role="status" className="dashboard-warning rounded-xl border p-3">
              <span aria-hidden="true" className="mr-2 font-bold">!</span>Feature unavailable: this action is not enabled in this release. You can review the current state only.
            </p>
          )}
          {'prerequisites' in data && (
            <>
              <p className="dashboard-muted">
                Current Active semester: <strong className="dashboard-heading">{data.current_active
                  ? `${data.current_active.label}, S.Y. ${data.current_active.school_year_label}` : 'None'}</strong>
              </p>
              <ul aria-label="Activation prerequisites" className="space-y-1.5">
                {data.prerequisites.map((check) => {
                  const state = PREREQUISITE_STATUS[check.status];
                  return (
                    <li key={check.key} className="flex items-start justify-between gap-3">
                      <span className="dashboard-heading">{PREREQUISITE_LABELS[check.key]}</span>
                      <span className={`${state.tone} whitespace-nowrap`}><span aria-hidden="true">{state.mark} </span>{state.text}</span>
                    </li>
                  );
                })}
              </ul>
              <p className="dashboard-muted text-xs">Dates: {formatDate(data.semester.start_date)} – {formatDate(data.semester.end_date)}</p>
            </>
          )}
          {'obligations' in data && (
            <ul aria-label="Outstanding obligations" className="space-y-1.5">
              {data.obligations.map((item) => (
                <li key={item.key} className="flex items-start justify-between gap-3">
                  <span className="dashboard-heading">{OBLIGATION_LABELS[item.key]}</span>
                  <span className={`${item.status === 'unavailable' ? 'dashboard-muted' : 'dashboard-heading font-semibold'} whitespace-nowrap`}>
                    {dependencyNote(item.status, item.count)}</span>
                </li>
              ))}
            </ul>
          )}
          <p className="dashboard-muted">{copy.effect} This action is audited.</p>
          {warnings.length > 0 && (
            <div className="dashboard-warning rounded-xl border p-3">
              <p className="font-semibold"><span aria-hidden="true" className="mr-2">!</span>Review before confirming</p>
              <ul className="mt-1 list-disc space-y-1 pl-5">{warnings.map((w) => <li key={w}>{warningLabel(w)}</li>)}</ul>
              <label className="mt-2 flex min-h-11 items-center gap-2 font-medium">
                <input type="checkbox" checked={reviewed} disabled={busy || featureOff || !data.can_confirm}
                  onChange={(e) => setReviewed(e.target.checked)} className="h-4 w-4" />
                I reviewed these warnings
              </label>
            </div>
          )}
          {!featureOff && !data.can_confirm && (
            <p className="dashboard-muted text-xs">This action is not possible until every requirement above is ready.</p>
          )}
          {error && (
            <div role="alert" className="dashboard-error-block rounded-xl border p-3">
              <p><span aria-hidden="true" className="mr-2 font-bold">!</span>{error}</p>
              <button type="button" className={`${secondaryButton} mt-2`} disabled={busy} onClick={reload}>Review again</button>
            </div>
          )}
        </>
      )}
    </Modal>
  );
}
