/** School Admin: the full organizational fee for each semester (Draft → explicit approval → history).
 *
 * Saving a Draft never approves it. Approval is a separate, explicit confirmation with its own server
 * switch, and ₱0.00 needs its own confirmation. Fee approval never activates a semester, and no
 * student fee obligation, payment or receipt is created here. Django decides access on every request
 * (finance.fee_schedule.manage through a genuine Admin role grant; governance pending).
 */
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Modal from '../../components/common/Modal.tsx';
import { DashboardState } from '../../components/dashboard/DashboardStates';
import { NoticeBlock } from '../academic/config/configUi.tsx';
import type { Notice } from '../academic/config/configUi.tsx';
import { badgeClass, destructiveButton, fieldClass, formatDateTime, primaryButton, secondaryButton } from '../academic/academicStyles.ts';
import { SEMESTER_FEE_APPROVAL_ENABLED } from './semesterFeesConfig.ts';
import {
  FeeApiError, approveFee, feeErrorText, getApprovalPreview, getSemesterFee, listSemesterFees, normalizeAmount, peso, saveDraft,
  withdrawDraft,
} from './semesterFeesApi.ts';
import type { ApprovalPreview, FeeState, Revision, SemesterFee, SemesterFeeSummary } from './semesterFeesApi.ts';

const STATE_TEXT: Record<FeeState, string> = {
  not_configured: 'Not configured', draft: 'Draft awaiting approval', approved: 'Approved',
  approved_with_draft: 'Approved · revision in draft',
};
const READINESS_TEXT: Record<string, string> = {
  '': 'Ready: an approved fee is available for semester activation.',
  no_fee_configured: 'Not ready: no fee has been configured for this semester.',
  fee_awaiting_approval: 'Not ready: the Draft fee has not been approved.',
  fee_source_disabled: 'Unavailable: semester fee configuration is switched off.',
  finance_service_inactive: 'Unavailable: the finance service is not active.',
  approved_fee_inconsistent: 'Unavailable: the approval record could not be verified.',
  fee_source_unavailable: 'Unavailable: fee records cannot be read right now.',
};
const WARNING_TEXT: Record<string, string> = {
  zero_amount: 'The full fee for this semester will be ₱0.00.',
  replaces_approved_rate: 'This replaces the current approved fee. The previous rate stays in history.',
  semester_is_active: 'This semester is Active.',
};
const IMPACT_TEXT: Record<string, string> = {
  no_previous_rate: 'No fee was approved before, so no student fee obligation can be affected.',
  semester_never_active: 'The semester has never been active, so no student fee obligation exists yet.',
  fee_obligations_not_implemented: 'Existing student fee obligations cannot be checked yet.',
};

function StateBadge({ state }: { state: FeeState }) {
  const tone = state === 'approved' || state === 'approved_with_draft' ? 'dashboard-accent' : state === 'draft' ? 'dashboard-heading' : 'dashboard-muted border-dashed';
  return <span className={`${badgeClass} ${tone}`}><span aria-hidden="true">{state === 'not_configured' ? '○' : state === 'draft' ? '◐' : '●'}</span>{STATE_TEXT[state]}</span>;
}

function ApprovalDialog({ semesterId, onClose, onApproved }: { semesterId: number; onClose: () => void; onApproved: (fee: SemesterFee) => void }) {
  const [preview, setPreview] = useState<ApprovalPreview | null>(null);
  const [failure, setFailure] = useState('');
  const [reviewed, setReviewed] = useState(false);
  const [zeroConfirmed, setZeroConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getApprovalPreview(semesterId).then((p) => { if (!cancelled) setPreview(p); })
      .catch((error: unknown) => { if (!cancelled) setFailure(feeErrorText(error)); });
    return () => { cancelled = true; };
  }, [semesterId]);

  const zero = preview?.proposed?.amount === '0.00';
  const featureOff = preview ? !preview.feature_enabled || !SEMESTER_FEE_APPROVAL_ENABLED : false;
  const canConfirm = Boolean(preview?.can_confirm) && SEMESTER_FEE_APPROVAL_ENABLED
    && (preview?.warnings.length === 0 || reviewed) && (!zero || zeroConfirmed);

  async function confirm() {
    if (!preview || !canConfirm) return;
    setBusy(true); setFailure('');
    try { onApproved(await approveFee(semesterId, preview, zero)); }
    catch (error: unknown) { setFailure(feeErrorText(error)); }
    finally { setBusy(false); }
  }

  return (
    <Modal open title="Approve this semester fee?" busy={busy} onClose={onClose} actions={<>
      <button type="button" className={secondaryButton} disabled={busy} onClick={onClose}>Cancel</button>
      <button type="button" className={primaryButton} disabled={busy || !canConfirm} onClick={() => void confirm()}>
        {busy ? 'Approving…' : 'Approve fee'}</button>
    </>}>
      {!preview && !failure && <p role="status" className="dashboard-muted">Checking the current state…</p>}
      {preview && (<>
        <p className="dashboard-heading font-semibold">S.Y. {preview.semester.school_year_label} · {preview.semester.label}</p>
        {featureOff && (
          <p role="status" className="dashboard-warning rounded-xl border p-3">
            <span aria-hidden="true" className="mr-2 font-bold">!</span>Feature unavailable: fee approval is not enabled in this release. You can review the Draft only.
          </p>)}
        <dl className="grid grid-cols-2 gap-3">
          <div><dt className="dashboard-muted text-xs">Proposed full fee</dt>
            <dd className="dashboard-heading text-lg font-semibold">{preview.proposed ? peso(preview.proposed.amount) : 'None'}</dd></div>
          <div><dt className="dashboard-muted text-xs">Current approved fee</dt>
            <dd className="dashboard-heading text-lg font-semibold">{preview.current_approved ? peso(preview.current_approved.amount) : 'None'}</dd></div>
          <div><dt className="dashboard-muted text-xs">Revision</dt><dd className="dashboard-heading">{preview.proposed ? `#${preview.proposed.revision_number}` : '—'}</dd></div>
          <div><dt className="dashboard-muted text-xs">Semester status</dt><dd className="dashboard-heading">{preview.semester.status}</dd></div>
        </dl>
        <p className="dashboard-muted"><strong className="dashboard-heading">Effect on student fee obligations: </strong>
          {preview.impact.status === 'evaluated'
            ? `${preview.impact.count} existing obligation${preview.impact.count === 1 ? '' : 's'} use the current fee.`
            : IMPACT_TEXT[preview.impact.reason] ?? 'Existing obligations cannot be checked.'}</p>
        <p className="dashboard-muted">Approval does not activate the semester and does not create any student fee obligation,
          payment or receipt. Approved amounts are never rewritten later. This action is audited.</p>
        {preview.warnings.length > 0 && (
          <div className="dashboard-warning rounded-xl border p-3">
            <p className="font-semibold"><span aria-hidden="true" className="mr-2">!</span>Review before approving</p>
            <ul className="mt-1 list-disc space-y-1 pl-5">{preview.warnings.map((w) => <li key={w}>{WARNING_TEXT[w] ?? 'Another condition needs your review.'}</li>)}</ul>
            <label className="mt-2 flex min-h-11 items-center gap-2 font-medium">
              <input type="checkbox" className="h-4 w-4" checked={reviewed} disabled={busy || featureOff} onChange={(e) => setReviewed(e.target.checked)} />
              I reviewed these warnings</label>
          </div>)}
        {zero && (
          <label className="flex min-h-11 items-center gap-2 font-medium">
            <input type="checkbox" className="h-4 w-4" checked={zeroConfirmed} disabled={busy || featureOff} onChange={(e) => setZeroConfirmed(e.target.checked)} />
            I confirm the full organizational fee for this semester is ₱0.00</label>)}
        {!featureOff && !preview.can_confirm && (
          <p className="dashboard-muted text-xs">{preview.blockers.includes('impact_unavailable')
            ? 'This revision cannot be approved while its effect on existing student fee obligations cannot be checked. The Draft is kept.'
            : preview.blockers.includes('obligations_assessed')
              ? 'Student fee obligations already use the current fee. A financial adjustment process is required.'
              : 'This fee cannot be approved right now.'}</p>)}
      </>)}
      {failure && <p role="alert" className="dashboard-error-block rounded-xl border p-3"><span aria-hidden="true" className="mr-2 font-bold">!</span>{failure}</p>}
    </Modal>
  );
}

function RevisionList({ revisions }: { revisions: Revision[] }) {
  if (revisions.length === 0) return <p className="dashboard-muted mt-2 text-sm">No fee revisions yet.</p>;
  return (
    <ol aria-label="Fee revisions" className="mt-2 space-y-2">
      {revisions.map((r) => (
        <li key={r.revision_id} className="rounded-xl border p-3 text-sm">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="dashboard-heading font-semibold">Revision #{r.revision_number} · {peso(r.amount)}</p>
            <span className={`${badgeClass} ${r.status === 'Approved' ? 'dashboard-accent' : 'dashboard-muted'}`}>{r.status}</span>
          </div>
          <p className="dashboard-muted text-xs">
            Configured {r.configured_at ? formatDateTime(r.configured_at) : 'date not recorded'}{r.configured_by ? ` by ${r.configured_by === 'You' ? 'you' : 'an administrator'}` : ''}
            {r.approved_at ? ` · approved ${formatDateTime(r.approved_at)}${r.approved_by ? ` by ${r.approved_by === 'You' ? 'you' : 'an administrator'}` : ''}` : ''}
            {r.superseded_at ? ` · superseded ${formatDateTime(r.superseded_at)}` : ''}{r.withdrawn_at ? ` · withdrawn ${formatDateTime(r.withdrawn_at)}` : ''}
          </p>
          {r.change_reason && <p className="dashboard-heading mt-1 text-xs break-words">Reason: “{r.change_reason}”</p>}
        </li>
      ))}
    </ol>
  );
}

function FeeDetail({ semesterId, onChanged }: { semesterId: number; onChanged: () => void }) {
  const ids = useId();
  const amountRef = useRef<HTMLInputElement>(null);
  const [fee, setFee] = useState<{ status: 'loading' } | { status: 'failed'; error: unknown } | { status: 'ready'; data: SemesterFee }>({ status: 'loading' });
  const [version, setVersion] = useState(0);
  const [amount, setAmount] = useState('');
  const [reason, setReason] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [dialog, setDialog] = useState<'approve' | 'withdraw' | null>(null);

  useEffect(() => {
    let cancelled = false;
    getSemesterFee(semesterId).then((data) => {
      if (cancelled) return;
      setFee({ status: 'ready', data });
      setAmount(data.draft?.amount ?? '');
      setReason(data.draft?.change_reason ?? '');
    }).catch((error: unknown) => { if (!cancelled) setFee({ status: 'failed', error }); });
    return () => { cancelled = true; };
  }, [semesterId, version]);

  function reload() { setFee({ status: 'loading' }); setVersion((v) => v + 1); onChanged(); }

  if (fee.status === 'loading') return <p role="status" className="dashboard-muted mt-4 text-sm">Loading the semester fee…</p>;
  if (fee.status === 'failed') {
    return <p role="alert" className="dashboard-error-block mt-4 rounded-xl border p-4 text-sm"><span aria-hidden="true" className="mr-2 font-bold">!</span>{feeErrorText(fee.error)}</p>;
  }
  const data = fee.data;
  const canEdit = data.editable && data.features.configuration;

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalized = normalizeAmount(amount);
    const found: Record<string, string> = {};
    if (!amount.trim()) found.amount = 'Enter the fee amount. ₱0.00 must be entered explicitly.';
    else if (normalized === null) found.amount = 'Enter the full fee in pesos, from 0.00 to 100,000.00, with up to two decimal places.';
    const note = reason.trim().replace(/\s+/g, ' ');
    if (data.reason_required && (note.length < 10 || note.length > 500)) found.change_reason = 'Explain the change in 10 to 500 characters.';
    setErrors(found);
    if (Object.keys(found).length) { (found.amount ? amountRef.current : document.getElementById(`${ids}-reason`))?.focus(); return; }
    setBusy(true); setNotice(null);
    try {
      const body: { amount: string; expected_draft_version: number | null; change_reason?: string } = {
        amount: normalized as string, expected_draft_version: data.draft?.version ?? null };
      if (data.reason_required) body.change_reason = note;
      const updated = await saveDraft(semesterId, body);
      setNotice({ kind: 'success', text: `Draft saved: ${peso(updated.draft?.amount ?? normalized as string)}. It is not approved yet.` });
      reload();
    } catch (error: unknown) {
      const fields = error instanceof FeeApiError ? error.detail.fields : {};
      if (Object.keys(fields).length) setErrors(fields); else setNotice({ kind: 'error', text: feeErrorText(error) });
    } finally { setBusy(false); }
  }

  const ready = data.readiness.status === 'ready';
  return (
    <div className="mt-4 space-y-4">
      <section className="dashboard-panel rounded-2xl border p-4 sm:p-5" aria-labelledby={`${ids}-overview`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 id={`${ids}-overview`} className="dashboard-heading text-base font-semibold">S.Y. {data.semester.school_year_label} · {data.semester.label}</h3>
            <p className="dashboard-muted text-xs">Semester status: {data.semester.status}</p>
          </div>
          <StateBadge state={data.state} />
        </div>
        <dl className="mt-4 grid gap-3 sm:grid-cols-3">
          <div><dt className="dashboard-muted text-xs">Approved full fee</dt>
            <dd className="dashboard-heading text-xl font-bold">{data.current_approved ? peso(data.current_approved.amount) : 'None'}</dd></div>
          <div><dt className="dashboard-muted text-xs">Approved</dt>
            <dd className="dashboard-heading text-sm">{data.current_approved?.approved_at ? formatDateTime(data.current_approved.approved_at) : '—'}</dd></div>
          <div><dt className="dashboard-muted text-xs">Current revision</dt>
            <dd className="dashboard-heading text-sm">{data.current_approved ? `#${data.current_approved.revision_number}` : '—'}</dd></div>
        </dl>
        <p className={`mt-3 text-sm ${ready ? 'dashboard-accent font-semibold' : 'dashboard-muted'}`}>
          <span aria-hidden="true">{ready ? '✓ ' : '○ '}</span>{READINESS_TEXT[data.readiness.reason] ?? 'Not ready.'}</p>
        {data.state === 'not_configured' && (
          <p role="status" className="dashboard-warning mt-3 rounded-xl border p-3 text-sm"><span aria-hidden="true" className="mr-2 font-bold">!</span>
            No fee is configured. A semester cannot be activated without an approved fee, and ₱0.00 must be entered and approved explicitly.</p>)}
      </section>

      <NoticeBlock notice={notice} />

      <section className="dashboard-panel rounded-2xl border p-4 sm:p-5" aria-labelledby={`${ids}-editor`}>
        <h3 id={`${ids}-editor`} className="dashboard-heading text-base font-semibold">{data.draft ? `Draft revision #${data.draft.revision_number}` : data.current_approved ? 'Propose a revision' : 'Configure the fee'}</h3>
        {!canEdit ? (
          <p className="dashboard-muted mt-2 text-sm">{data.editable ? 'Fee configuration is not enabled on the server.' : 'Closed and Archived semesters keep their fee history; it cannot be changed here.'}</p>
        ) : (
          <form noValidate onSubmit={(e) => void save(e)} className="mt-3 space-y-3">
            <div className="sm:w-72">
              <label htmlFor={`${ids}-amount`} className="dashboard-muted mb-1 block text-xs font-medium">Full organizational fee (PHP)</label>
              <div className="flex items-center gap-2">
                <span aria-hidden="true" className="dashboard-heading font-semibold">₱</span>
                <input ref={amountRef} id={`${ids}-amount`} inputMode="decimal" autoComplete="off" maxLength={9} value={amount} disabled={busy}
                  aria-invalid={errors.amount ? true : undefined} aria-describedby={errors.amount ? `${ids}-amount-error` : `${ids}-amount-hint`}
                  onChange={(e) => { setAmount(e.target.value); setErrors((x) => ({ ...x, amount: '' })); }} className={fieldClass} />
              </div>
              {errors.amount
                ? <p id={`${ids}-amount-error`} className="dashboard-error mt-1 text-xs">{errors.amount}</p>
                : <p id={`${ids}-amount-hint`} className="dashboard-muted mt-1 text-xs">For example, 1500.00. Enter 0.00 only if the approved full fee is zero.</p>}
            </div>
            {data.reason_required && (
              <div>
                <label htmlFor={`${ids}-reason`} className="dashboard-muted mb-1 block text-xs font-medium">Reason for revising the approved fee</label>
                <textarea id={`${ids}-reason`} rows={3} maxLength={500} value={reason} disabled={busy}
                  aria-invalid={errors.change_reason ? true : undefined} aria-describedby={errors.change_reason ? `${ids}-reason-error` : undefined}
                  onChange={(e) => { setReason(e.target.value); setErrors((x) => ({ ...x, change_reason: '' })); }} className={fieldClass} />
                {errors.change_reason && <p id={`${ids}-reason-error`} className="dashboard-error mt-1 text-xs">{errors.change_reason}</p>}
              </div>)}
            <p className="dashboard-muted text-xs">Saving keeps this as a Draft. It does not change the approved fee or any student record.</p>
            <div className="flex flex-wrap justify-end gap-3">
              {data.draft && <button type="button" className={secondaryButton} disabled={busy} onClick={() => setDialog('withdraw')}>Withdraw draft</button>}
              {data.draft && <button type="button" className={secondaryButton} disabled={busy} onClick={() => setDialog('approve')}>Review approval</button>}
              <button type="submit" className={primaryButton} disabled={busy}>{busy ? 'Saving…' : 'Save draft'}</button>
            </div>
          </form>
        )}
      </section>

      <section className="dashboard-panel rounded-2xl border p-4 sm:p-5" aria-labelledby={`${ids}-history`}>
        <h3 id={`${ids}-history`} className="dashboard-heading text-base font-semibold">Fee history</h3>
        <RevisionList revisions={data.revisions} />
      </section>

      {dialog === 'approve' && (
        <ApprovalDialog semesterId={semesterId} onClose={() => setDialog(null)}
          onApproved={(updated) => { setDialog(null); setNotice({ kind: 'success', text: `The semester fee of ${peso(updated.current_approved?.amount ?? '0.00')} was approved. This action is audited.` }); reload(); }} />)}
      {dialog === 'withdraw' && data.draft && (
        <WithdrawDialog onClose={() => setDialog(null)} amount={data.draft.amount}
          confirm={() => withdrawDraft(semesterId, (data.draft as Revision).version)}
          onDone={() => { setDialog(null); setNotice({ kind: 'success', text: 'The Draft was withdrawn and kept in history.' }); reload(); }} />)}
    </div>
  );
}

function WithdrawDialog({ amount, onClose, confirm, onDone }: { amount: string; onClose: () => void; confirm: () => Promise<unknown>; onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  return (
    <Modal open title="Withdraw this Draft fee?" busy={busy} onClose={onClose} actions={<>
      <button type="button" className={secondaryButton} disabled={busy} onClick={onClose}>Cancel</button>
      <button type="button" className={destructiveButton} disabled={busy} onClick={async () => {
        setBusy(true); setFailure('');
        try { await confirm(); onDone(); } catch (error: unknown) { setFailure(feeErrorText(error)); } finally { setBusy(false); }
      }}>{busy ? 'Withdrawing…' : 'Withdraw draft'}</button>
    </>}>
      <p>The Draft of {peso(amount)} will not be approved. It stays in the fee history, and the approved fee (if any) is unchanged. This action is audited.</p>
      {failure && <p role="alert" className="dashboard-error-block rounded-xl border p-3"><span aria-hidden="true" className="mr-2 font-bold">!</span>{failure}</p>}
    </Modal>
  );
}

export default function SemesterFeesPanel() {
  const selectId = useId();
  const [list, setList] = useState<{ status: 'loading' } | { status: 'failed'; error: unknown } | { status: 'ready'; results: SemesterFeeSummary[] }>({ status: 'loading' });
  const [selected, setSelected] = useState('');
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    listSemesterFees().then((r) => {
      if (cancelled) return;
      setList({ status: 'ready', results: r.results });
      setSelected((current) => current || String(r.results[0]?.semester.semester_id ?? ''));
    }).catch((error: unknown) => { if (!cancelled) setList({ status: 'failed', error }); });
    return () => { cancelled = true; };
  }, [version]);

  if (list.status === 'loading') return <p role="status" className="dashboard-muted text-sm">Loading semester fees…</p>;
  if (list.status === 'failed') {
    const denied = list.error instanceof FeeApiError && list.error.detail.code === 'access_denied';
    return (
      <DashboardState title={denied ? 'Semester fees are set by the School Admin' : 'Semester fees are not available right now'}>
        {feeErrorText(list.error)}
      </DashboardState>
    );
  }
  if (list.results.length === 0) {
    return <p className="dashboard-muted rounded-xl border border-dashed p-4 text-center text-sm">No school years exist yet. Create one in School years &amp; semesters first.</p>;
  }
  return (
    <div className="space-y-2">
      <p className="dashboard-muted text-sm">The School Admin sets and approves the full organizational fee for each semester. The Treasurer
        collects payments separately. Student fee obligations are created only after Student Semester Onboarding.</p>
      <div className="sm:w-96">
        <label htmlFor={selectId} className="dashboard-muted mb-1 block text-xs font-medium">Semester</label>
        <select id={selectId} value={selected} onChange={(e) => setSelected(e.target.value)} className={fieldClass}>
          {list.results.map((s) => (
            <option key={s.semester.semester_id} value={s.semester.semester_id}>
              S.Y. {s.semester.school_year_label} · {s.semester.label} — {STATE_TEXT[s.state]}{s.approved_amount ? ` ${peso(s.approved_amount)}` : ''}
            </option>))}
        </select>
      </div>
      {selected && <FeeDetail key={selected} semesterId={Number(selected)} onChanged={() => setVersion((v) => v + 1)} />}
    </div>
  );
}
