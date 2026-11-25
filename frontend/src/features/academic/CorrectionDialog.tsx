/** WF-11.01 controlled Active-semester edit (D06) and historical correction (D05): dates only.
 *
 * Requires a reason and note, shows the server's downstream impact summary and refuses to save
 * while that impact cannot be evaluated. Status never changes; fee amounts are not edited here.
 */
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Modal from '../../components/common/Modal.tsx';
import { AcademicApiError } from './academicPeriodsApi.ts';
import { schoolYearBounds, validateSemesterRange } from './academicPeriodsContract.ts';
import type { FieldName, SchoolYear } from './academicPeriodsContract.ts';
import { correctSemester, getCorrectionPreview } from './academicLifecycleApi.ts';
import { IMPACT_LABELS, REASON_LABELS, dependencyNote } from './academicLifecycleContract.ts';
import type { CorrectionPreview, ReasonCode } from './academicLifecycleContract.ts';
import { fieldClass, primaryButton, secondaryButton } from './academicStyles.ts';

type Load = { status: 'loading' } | { status: 'failed'; code: string; reason: string } | { status: 'ready'; data: CorrectionPreview };
type Errors = Partial<Record<FieldName, string>>;

interface Props {
  semester: { semester_id: number; label: string; start_date: string | null; end_date: string | null };
  year: { start_year: number; label: string };
  buildEnabled: boolean;
  onClose: () => void;
  onSaved: (year: SchoolYear, message: string) => void;
}

function failureText(error: unknown): string {
  const detail = error instanceof AcademicApiError ? error.detail : null;
  if (!detail) return 'The change could not be saved. Reload the list before trying again.';
  if (detail.code === 'outcome_unknown') return 'We could not confirm the change. Reload the list to see the current state before trying again.';
  if (detail.code === 'feature_disabled') return 'Edits to non-Draft semesters are not enabled on the server.';
  if (detail.code === 'access_denied') return 'You do not have permission to make this change.';
  switch (detail.reason) {
    case 'impact_unavailable': return 'The effect on student, fee or clearance records cannot be checked yet, so this change is not allowed.';
    case 'impact_review_required': return 'This change affects existing records. Review the impact summary and confirm.';
    case 'stale_version': return 'This semester was changed by someone else. Reload and try again.';
    case 'semesters_overlap': return 'The First semester must end before the Second semester starts.';
    case 'no_change': return 'The dates are unchanged.';
    default: return 'The change could not be saved. Check the details and try again.';
  }
}

export default function CorrectionDialog({ semester, year, buildEnabled, onClose, onSaved }: Props) {
  const ids = useId();
  const startRef = useRef<HTMLInputElement>(null);
  const [load, setLoad] = useState<Load>({ status: 'loading' });
  const [start, setStart] = useState(semester.start_date ?? '');
  const [end, setEnd] = useState(semester.end_date ?? '');
  const [reason, setReason] = useState<ReasonCode | ''>('');
  const [note, setNote] = useState('');
  const [impactReviewed, setImpactReviewed] = useState(false);
  const [overlapNeeded, setOverlapNeeded] = useState(false);
  const [overlapReviewed, setOverlapReviewed] = useState(false);
  const [errors, setErrors] = useState<Errors>({});
  const [failure, setFailure] = useState('');
  const [busy, setBusy] = useState(false);
  const bounds = schoolYearBounds(year.start_year);

  useEffect(() => {
    let cancelled = false;
    getCorrectionPreview(semester.semester_id)
      .then((data) => { if (!cancelled) setLoad({ status: 'ready', data }); })
      .catch((e: unknown) => {
        const detail = e instanceof AcademicApiError ? e.detail : null;
        if (!cancelled) setLoad({ status: 'failed', code: detail?.code ?? '', reason: detail?.reason ?? '' });
      });
    return () => { cancelled = true; };
  }, [semester.semester_id]);

  const data = load.status === 'ready' ? load.data : null;
  const featureOff = data ? !data.feature_enabled || !buildEnabled : false;
  const blocked = !data || !data.can_confirm || !buildEnabled;
  const historical = data?.kind === 'historical_correction';

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!data || blocked) return;
    const found: Errors = validateSemesterRange(start || null, end || null, year.start_year);
    if (!start) found.start_date = 'Enter the start date.';
    if (!end) found.end_date = 'Enter the end date.';
    if (!reason) found.reason_code = 'Choose the reason for this change.';
    const trimmed = note.trim().replace(/\s+/g, ' ');
    if (trimmed.length < 10 || trimmed.length > 500) found.reason_note = 'Explain the change in 10 to 500 characters.';
    setErrors(found);
    if (Object.values(found).some(Boolean)) {
      if (found.start_date || found.end_date) startRef.current?.focus();
      else document.getElementById(found.reason_code ? `${ids}-reason` : `${ids}-note`)?.focus();
      return;
    }
    if (data.affected.length && !impactReviewed) { setFailure('Confirm that you reviewed the affected records.'); return; }
    setBusy(true);
    setFailure('');
    try {
      const updated = await correctSemester(semester.semester_id, {
        start_date: start, end_date: end, expected_version: data.semester.version, reason_code: reason as ReasonCode,
        reason_note: trimmed, acknowledged_impacts: data.affected, acknowledge_cross_year_overlap: overlapNeeded && overlapReviewed,
      });
      onSaved(updated, `${semester.label}, S.Y. ${year.label}: the dates were ${historical ? 'corrected' : 'updated'}.`);
    } catch (e: unknown) {
      const detail = e instanceof AcademicApiError ? e.detail : null;
      if (detail?.reason === 'cross_year_overlap') {
        setOverlapNeeded(true);
        setFailure('These dates overlap a semester of another school year. Confirm the overlap below to save anyway.');
      } else if (detail && Object.keys(detail.fields).length) {
        setErrors(detail.fields);
      } else {
        setFailure(failureText(e));
      }
    } finally {
      setBusy(false);
    }
  }

  const title = historical ? 'Correct historical dates?' : 'Edit active semester dates?';
  const disabled = busy || blocked;
  const errorText = (name: FieldName) => errors[name]
    && <p id={`${ids}-${name}-error`} className="dashboard-error mt-1 text-xs">{errors[name]}</p>;

  return (
    <Modal open title={title} busy={busy} onClose={onClose}
      actions={<>
        <button type="button" className={secondaryButton} disabled={busy} onClick={onClose}>Cancel</button>
        <button type="submit" form={`${ids}-form`} className={primaryButton} disabled={disabled}>{busy ? 'Saving…' : 'Save change'}</button>
      </>}>
      <p className="dashboard-heading font-semibold">{semester.label}, S.Y. {year.label}</p>
      {load.status === 'loading' && <p role="status" className="dashboard-muted">Checking the impact on existing records…</p>}
      {load.status === 'failed' && (
        <p role="alert" className="dashboard-error-block rounded-xl border p-3">
          <span aria-hidden="true" className="mr-2 font-bold">!</span>
          {load.code === 'access_denied' ? 'Permission denied: you cannot manage academic periods.' : 'The impact summary could not be loaded.'}
        </p>
      )}
      {data && (
        <form id={`${ids}-form`} noValidate onSubmit={(e) => void submit(e)} className="space-y-3">
          {featureOff && (
            <p role="status" className="dashboard-warning rounded-xl border p-3">
              <span aria-hidden="true" className="mr-2 font-bold">!</span>Feature unavailable: edits to non-Draft semesters are not enabled in this release.
            </p>
          )}
          <p className="dashboard-muted">
            {historical ? 'The semester stays ' : 'The semester stays Active. '}
            {historical ? `${data.semester.status}; it is never reopened. ` : ''}
            Existing student records and fee obligations are never rewritten. This change is audited with your reason.
          </p>
          <div>
            <p className="dashboard-muted text-xs font-semibold">Impact on existing records</p>
            <ul aria-label="Impact on existing records" className="mt-1 space-y-1">
              {data.impact.map((item) => (
                <li key={item.key} className="flex items-start justify-between gap-3">
                  <span className="dashboard-heading">{IMPACT_LABELS[item.key]}</span>
                  <span className={item.status === 'unavailable' ? 'dashboard-muted whitespace-nowrap' : 'dashboard-heading whitespace-nowrap font-semibold'}>
                    {dependencyNote(item.status, item.count)}</span>
                </li>
              ))}
            </ul>
            {data.blockers.includes('impact_unavailable') && (
              <p className="dashboard-muted mt-2 text-xs">Saving is not possible while the impact cannot be checked.</p>
            )}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor={`${ids}-start`} className="dashboard-muted mb-1 block text-xs font-medium">Start date</label>
              <input ref={startRef} id={`${ids}-start`} type="date" value={start} min={bounds.min} max={bounds.max} disabled={disabled}
                aria-invalid={errors.start_date ? true : undefined} aria-describedby={errors.start_date ? `${ids}-start_date-error` : undefined}
                onChange={(e) => { setStart(e.target.value); setErrors((x) => ({ ...x, start_date: undefined })); }} className={fieldClass} />
              {errorText('start_date')}
            </div>
            <div>
              <label htmlFor={`${ids}-end`} className="dashboard-muted mb-1 block text-xs font-medium">End date</label>
              <input id={`${ids}-end`} type="date" value={end} min={bounds.min} max={bounds.max} disabled={disabled}
                aria-invalid={errors.end_date ? true : undefined} aria-describedby={errors.end_date ? `${ids}-end_date-error` : undefined}
                onChange={(e) => { setEnd(e.target.value); setErrors((x) => ({ ...x, end_date: undefined })); }} className={fieldClass} />
              {errorText('end_date')}
            </div>
          </div>
          <div>
            <label htmlFor={`${ids}-reason`} className="dashboard-muted mb-1 block text-xs font-medium">Reason</label>
            <select id={`${ids}-reason`} value={reason} disabled={disabled}
              aria-invalid={errors.reason_code ? true : undefined} aria-describedby={errors.reason_code ? `${ids}-reason_code-error` : undefined}
              onChange={(e) => { setReason(e.target.value as ReasonCode | ''); setErrors((x) => ({ ...x, reason_code: undefined })); }}
              className={fieldClass}>
              <option value="">Choose a reason</option>
              {data.reason_codes.map((code) => <option key={code} value={code}>{REASON_LABELS[code]}</option>)}
            </select>
            {errorText('reason_code')}
          </div>
          <div>
            <label htmlFor={`${ids}-note`} className="dashboard-muted mb-1 block text-xs font-medium">Explanation</label>
            <textarea id={`${ids}-note`} value={note} rows={3} maxLength={500} disabled={disabled}
              aria-invalid={errors.reason_note ? true : undefined}
              aria-describedby={errors.reason_note ? `${ids}-reason_note-error` : `${ids}-note-hint`}
              onChange={(e) => { setNote(e.target.value); setErrors((x) => ({ ...x, reason_note: undefined })); }}
              className={fieldClass} />
            {errors.reason_note ? errorText('reason_note')
              : <p id={`${ids}-note-hint`} className="dashboard-muted mt-1 text-xs">10 to 500 characters. Shown in the period history.</p>}
          </div>
          {data.affected.length > 0 && (
            <label className="flex min-h-11 items-center gap-2 font-medium">
              <input type="checkbox" checked={impactReviewed} disabled={disabled} onChange={(e) => setImpactReviewed(e.target.checked)} className="h-4 w-4" />
              I reviewed the affected records
            </label>
          )}
          {overlapNeeded && (
            <label className="flex min-h-11 items-center gap-2 font-medium">
              <input type="checkbox" checked={overlapReviewed} disabled={disabled} onChange={(e) => setOverlapReviewed(e.target.checked)} className="h-4 w-4" />
              Save despite the overlap with another school year
            </label>
          )}
          {failure && <p role="alert" className="dashboard-error-block rounded-xl border p-3"><span aria-hidden="true" className="mr-2 font-bold">!</span>{failure}</p>}
        </form>
      )}
    </Modal>
  );
}
