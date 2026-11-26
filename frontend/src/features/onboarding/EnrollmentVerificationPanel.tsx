/** School Admin: in-person CTU enrollment verification (WF-05.04 minimum), verified non-enrollment gaps
 * (WF11-D15/16) and the evidenced historical participation correction (WF11-D14).
 *
 * Only a controlled CTU record reference is entered (never a scan or document contents). Recording a
 * verification never onboards the Student: the Student confirms their own onboarding afterwards. No
 * one can verify their own records. Django decides access on every request (proposed
 * academic.profiles.manage mapping, School Admin role context, Deny precedence).
 */
import { useEffect, useId, useState } from 'react';
import type { FormEvent } from 'react';
import Modal from '../../components/common/Modal.tsx';
import { NoticeBlock } from '../academic/config/configUi.tsx';
import type { Notice } from '../academic/config/configUi.tsx';
import { compactButton, destructiveButton, fieldClass, primaryButton, secondaryButton } from '../academic/academicStyles.ts';
import { ACADEMIC_CONFIGURATION_ENABLED } from '../academic/academicConfigurationConfig.ts';
import { listCourses, listSubjects } from '../academic/academicConfigurationApi.ts';
import type { Course, Subject } from '../academic/academicConfigurationApi.ts';
import { HISTORICAL_PARTICIPATION_CORRECTION_ENABLED } from './onboardingConfig.ts';
import {
  correctHistoricalParticipation, getHistoricalPreview, getStudentRecord, onboardingErrorText, peso, recordEvidence, recordGap,
  revokeEvidence, revokeGap, searchStudents,
} from './onboardingApi.ts';
import type { HistoricalPreview, PeriodRecord, StudentRef, StudentType } from './onboardingApi.ts';

const CLASSIFICATIONS = [['continuing', 'Continuing'], ['returning', 'Returning'], ['newcomer', 'Newcomer'], ['transferee', 'Transferee']] as const;
const REVOKE_REASONS = [['recorded_in_error', 'Recorded in error'], ['superseded_by_ctu_record', 'Superseded by a CTU record'],
  ['identity_mismatch', 'Identity mismatch']] as const;
const REFERENCE = /^[A-Za-z0-9][A-Za-z0-9 .\-/#]{2,79}$/;
const BLOCKER_TEXT: Record<string, string> = {
  period_not_historical: 'Only a Closed or Archived semester can receive a historical correction.',
  evidence_required: 'Record the verified CTU enrollment for this semester first.',
  participation_exists: 'The student already has a participation for this semester.',
  gap_conflict: 'A verified non-enrollment gap exists for this semester.',
  historical_fee_unavailable: 'The semester has no approved original fee, so no obligation can be created and the correction is not available.',
  feature_disabled: 'Historical correction is not enabled on the server.',
};
type Dialog = { kind: 'evidence' | 'gap' | 'revoke' | 'revoke-gap' | 'historical'; row: PeriodRecord } | null;

function Failure({ error }: { error: unknown }) {
  return <p role="alert" className="dashboard-error-block rounded-xl border p-3 text-sm"><span aria-hidden="true" className="mr-2 font-bold">!</span>{onboardingErrorText(error)}</p>;
}
const periodLabel = (row: PeriodRecord) => `${row.semester.label}, S.Y. ${row.semester.school_year_label}`;

function EvidenceDialog({ student, row, onClose, onDone }: { student: StudentRef; row: PeriodRecord; onClose: () => void; onDone: (n: Notice) => void }) {
  const ids = useId();
  const [courses, setCourses] = useState<Course[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [q, setQ] = useState('');
  const [values, setValues] = useState({ classification: row.evidence?.entry_classification ?? 'continuing',
    course: row.evidence ? String(row.evidence.course.course_id) : '', year: row.evidence ? String(row.evidence.year_level) : '',
    reference: '', asOf: '' });
  const [chosen, setChosen] = useState<Map<number, string>>(new Map((row.evidence?.subjects ?? []).map((s) => [s.subject_id, s.code])));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  useEffect(() => {
    if (!ACADEMIC_CONFIGURATION_ENABLED) return undefined;
    let cancelled = false;
    listCourses({ status: 'Active' }).then((p) => { if (!cancelled) setCourses(p.results); }).catch((e: unknown) => { if (!cancelled) setFailure(e); });
    return () => { cancelled = true; };
  }, []);
  useEffect(() => {
    if (!ACADEMIC_CONFIGURATION_ENABLED) return undefined;
    let cancelled = false;
    const timer = window.setTimeout(() => {
      listSubjects({ status: 'Active', q: q.trim() || undefined }).then((p) => { if (!cancelled) setSubjects(p.results); })
        .catch((e: unknown) => { if (!cancelled) setFailure(e); });
    }, 300);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [q]);
  const set = (name: keyof typeof values) => (value: string) => { setValues((v) => ({ ...v, [name]: value })); setErrors((e) => ({ ...e, [name]: '' })); };
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (!values.course) found.course = 'Choose the course shown on the CTU record.';
    if (!values.year) found.year = 'Choose the year level shown on the CTU record.';
    if (chosen.size === 0 || chosen.size > 20) found.subjects = 'Choose 1 to 20 subjects shown on the CTU record.';
    if (!REFERENCE.test(values.reference.trim().replace(/\s+/g, ' '))) found.reference = 'Enter the CTU record reference (3 to 80 letters, digits, spaces, . - / #).';
    setErrors(found);
    if (Object.keys(found).length) { document.getElementById(`${ids}-${Object.keys(found)[0]}`)?.focus(); return; }
    setBusy(true); setFailure(null);
    try {
      await recordEvidence({ student_account_id: student.account_id, semester_id: row.semester.semester_id,
        entry_classification: values.classification, course_id: Number(values.course), year_level: Number(values.year),
        subject_ids: [...chosen.keys()], source_reference: values.reference.trim().replace(/\s+/g, ' '),
        source_as_of: values.asOf || null, expected_evidence_id: row.evidence?.evidence_id ?? null });
      onDone({ kind: 'success', text: `Verification recorded for ${periodLabel(row)}. The student must still confirm their own onboarding.` });
    } catch (e: unknown) { setFailure(e); } finally { setBusy(false); }
  }
  const field = (name: string) => (errors[name] ? <p id={`${ids}-${name}-error`} className="dashboard-error mt-1 text-xs">{errors[name]}</p> : null);
  return (
    <Modal open title={row.evidence ? 'Replace the verified enrollment record?' : 'Record verified CTU enrollment?'} busy={busy} onClose={onClose}
      actions={<><button type="button" className={secondaryButton} disabled={busy} onClick={onClose}>Cancel</button>
        <button type="submit" form={`${ids}-form`} className={primaryButton} disabled={busy}>{busy ? 'Recording…' : 'Record verification'}</button></>}>
      <form id={`${ids}-form`} noValidate onSubmit={(e) => void submit(e)} aria-busy={busy} className="space-y-4">
        <p className="dashboard-muted text-sm">{student.ctug_id} · {periodLabel(row)}. Enter only what the official CTU record shows. Do not upload
          or type document contents. {row.evidence ? 'The current record is kept in history as superseded.' : ''} This action is audited.</p>
        <p className="dashboard-muted text-xs">Fields marked * are required.</p>
        {!ACADEMIC_CONFIGURATION_ENABLED && <p className="dashboard-warning rounded-xl border p-3 text-sm">Course and subject lists need Academic settings, which is not enabled.</p>}
        <fieldset disabled={busy} className="grid gap-4 sm:grid-cols-2">
          <div><label htmlFor={`${ids}-classification`} className="dashboard-heading mb-1 block text-sm font-medium">CTU entry classification *</label>
            <select id={`${ids}-classification`} className={fieldClass} value={values.classification} onChange={(e) => set('classification')(e.target.value)}>
              {CLASSIFICATIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></div>
          <div><label htmlFor={`${ids}-course`} className="dashboard-heading mb-1 block text-sm font-medium">Course *</label>
            <select id={`${ids}-course`} className={fieldClass} value={values.course} aria-describedby={errors.course ? `${ids}-course-error` : undefined}
              onChange={(e) => set('course')(e.target.value)}>
              <option value="">Choose the course</option>
              {courses.map((c) => <option key={c.course_id} value={c.course_id}>{c.code} · {c.name}</option>)}</select>{field('course')}</div>
          <div><label htmlFor={`${ids}-year`} className="dashboard-heading mb-1 block text-sm font-medium">Year level *</label>
            <select id={`${ids}-year`} className={fieldClass} value={values.year} aria-describedby={errors.year ? `${ids}-year-error` : undefined}
              onChange={(e) => set('year')(e.target.value)}>
              <option value="">Choose the year level</option>
              {[1, 2, 3, 4, 5, 6].map((y) => <option key={y} value={y}>Year {y}</option>)}</select>{field('year')}</div>
          <div><label htmlFor={`${ids}-reference`} className="dashboard-heading mb-1 block text-sm font-medium">CTU record reference *</label>
            <input id={`${ids}-reference`} className={fieldClass} maxLength={80} value={values.reference} autoComplete="off"
              aria-describedby={`${ids}-reference-hint${errors.reference ? ` ${ids}-reference-error` : ''}`} onChange={(e) => set('reference')(e.target.value)} />
            <p id={`${ids}-reference-hint`} className="dashboard-muted mt-1 text-xs">For example a document control number. It is stored but never shown in audit history.</p>
            {field('reference')}</div>
          <div><label htmlFor={`${ids}-asOf`} className="dashboard-heading mb-1 block text-sm font-medium">Record date (optional)</label>
            <input id={`${ids}-asOf`} type="date" className={fieldClass} value={values.asOf} onChange={(e) => set('asOf')(e.target.value)} /></div>
        </fieldset>
        <fieldset disabled={busy} className="space-y-2">
          <legend className="dashboard-heading text-sm font-semibold">Enrolled subjects on the CTU record * ({chosen.size} selected)</legend>
          <label htmlFor={`${ids}-subjects`} className="dashboard-muted block text-xs">Search subjects by code or title</label>
          <input id={`${ids}-subjects`} className={fieldClass} value={q} maxLength={50} aria-describedby={errors.subjects ? `${ids}-subjects-error` : undefined}
            onChange={(e) => setQ(e.target.value)} />
          {field('subjects')}
          <ul className="max-h-60 space-y-1 overflow-y-auto">
            {[...new Map([...subjects.map((s) => [s.subject_id, s.code] as const), ...chosen]).entries()].map(([sid, code]) => {
              const subject = subjects.find((s) => s.subject_id === sid);
              return (<li key={sid}><label className="flex min-h-11 items-center gap-2 text-sm">
                <input type="checkbox" className="h-4 w-4" checked={chosen.has(sid)} onChange={(e) => {
                  setErrors((x) => ({ ...x, subjects: '' }));
                  setChosen((prev) => { const next = new Map(prev); if (e.target.checked) next.set(sid, code); else next.delete(sid); return next; });
                }} /><span className="dashboard-heading">{code}{subject ? ` · ${subject.title}` : ''}</span></label></li>);
            })}
          </ul>
        </fieldset>
        {failure !== null && <Failure error={failure} />}
      </form>
    </Modal>
  );
}

function ReferenceDialog({ student, row, onClose, onDone }: { student: StudentRef; row: PeriodRecord; onClose: () => void; onDone: (n: Notice) => void }) {
  const ids = useId();
  const [reference, setReference] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = reference.trim().replace(/\s+/g, ' ');
    if (!REFERENCE.test(value)) { setError('Enter the CTU record reference (3 to 80 letters, digits, spaces, . - / #).'); document.getElementById(`${ids}-ref`)?.focus(); return; }
    setBusy(true); setFailure(null);
    try {
      await recordGap({ student_account_id: student.account_id, semester_id: row.semester.semester_id, source_reference: value });
      onDone({ kind: 'success', text: `Verified non-enrollment recorded for ${periodLabel(row)}. Earlier clearances and fees are unchanged.` });
    } catch (e: unknown) { setFailure(e); } finally { setBusy(false); }
  }
  return (
    <Modal open title="Record verified non-enrollment?" busy={busy} onClose={onClose}
      actions={<><button type="button" className={secondaryButton} disabled={busy} onClick={onClose}>Cancel</button>
        <button type="submit" form={`${ids}-form`} className={primaryButton} disabled={busy}>{busy ? 'Recording…' : 'Record non-enrollment'}</button></>}>
      <form id={`${ids}-form`} noValidate onSubmit={(e) => void submit(e)} className="space-y-3">
        <p className="dashboard-muted text-sm">Record this only when the official CTU records show that {student.ctug_id} was not enrolled in
          {' '}{periodLabel(row)}. It lets the student onboard later without completing an older clearance first; it never clears that
          clearance or removes unpaid fees. This action is audited.</p>
        <label htmlFor={`${ids}-ref`} className="dashboard-heading block text-sm font-medium">CTU record reference *</label>
        <input id={`${ids}-ref`} className={fieldClass} maxLength={80} value={reference} disabled={busy} autoComplete="off"
          aria-describedby={error ? `${ids}-ref-error` : undefined} onChange={(e) => { setReference(e.target.value); setError(''); }} />
        {error && <p id={`${ids}-ref-error`} className="dashboard-error text-xs">{error}</p>}
        {failure !== null && <Failure error={failure} />}
      </form>
    </Modal>
  );
}

function RevokeDialog({ row, gap, onClose, onDone }: { row: PeriodRecord; gap: boolean; onClose: () => void; onDone: (n: Notice) => void }) {
  const ids = useId();
  const [reason, setReason] = useState<string>(REVOKE_REASONS[0][0]);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  async function confirm() {
    setBusy(true); setFailure(null);
    try {
      if (gap && row.gap) await revokeGap(row.gap.gap_id, row.gap.version);
      else if (row.evidence) await revokeEvidence(row.evidence.evidence_id, row.evidence.version, reason);
      onDone({ kind: 'success', text: `${gap ? 'Non-enrollment record' : 'Verification'} revoked for ${periodLabel(row)}.` });
    } catch (e: unknown) { setFailure(e); } finally { setBusy(false); }
  }
  return (
    <Modal open title={gap ? 'Revoke the non-enrollment record?' : 'Revoke the verified enrollment record?'} busy={busy} onClose={onClose}
      actions={<><button type="button" className={secondaryButton} disabled={busy} onClick={onClose}>Cancel</button>
        <button type="button" className={destructiveButton} disabled={busy} onClick={() => void confirm()}>{busy ? 'Revoking…' : 'Revoke record'}</button></>}>
      <p className="dashboard-muted text-sm">{periodLabel(row)}. The record stays in history as revoked.{' '}
        {gap ? 'The student needs this verification again before onboarding.' : 'The student cannot complete onboarding on it any more.'} This action is audited.</p>
      {!gap && (<div><label htmlFor={`${ids}-reason`} className="dashboard-heading mb-1 block text-sm font-medium">Reason *</label>
        <select id={`${ids}-reason`} className={fieldClass} value={reason} disabled={busy} onChange={(e) => setReason(e.target.value)}>
          {REVOKE_REASONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></div>)}
      {failure !== null && <Failure error={failure} />}
    </Modal>
  );
}

function HistoricalDialog({ student, row, onClose, onDone }: { student: StudentRef; row: PeriodRecord; onClose: () => void; onDone: (n: Notice) => void }) {
  const ids = useId();
  const [preview, setPreview] = useState<HistoricalPreview | null>(null);
  const [type, setType] = useState<StudentType>('Regular');
  const [chosen, setChosen] = useState<number[]>([]);
  const [note, setNote] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  useEffect(() => {
    let cancelled = false;
    getHistoricalPreview(student.account_id, row.semester.semester_id).then((p) => { if (!cancelled) setPreview(p); })
      .catch((e: unknown) => { if (!cancelled) setFailure(e); });
    return () => { cancelled = true; };
  }, [student.account_id, row.semester.semester_id]);
  async function confirm() {
    if (!preview?.evidence) return;
    const text = note.trim().replace(/\s+/g, ' ');
    if (!chosen.length) { setError('Choose the offering of every verified subject.'); return; }
    if (text.length < 10 || text.length > 500) { setError('Explain the correction in 10 to 500 characters.'); document.getElementById(`${ids}-note`)?.focus(); return; }
    setBusy(true); setFailure(null); setError('');
    try {
      await correctHistoricalParticipation({ student_account_id: student.account_id, semester_id: row.semester.semester_id,
        expected_evidence_id: preview.evidence.evidence_id, student_type: type, offering_ids: chosen, reason_note: text });
      onDone({ kind: 'success', text: `Historical participation recorded for ${periodLabel(row)}. The semester stays ${row.semester.status}.` });
    } catch (e: unknown) { setFailure(e); } finally { setBusy(false); }
  }
  const subjectOf = new Map((preview?.options ?? []).map((o) => [o.offering_id, o.subject.subject_id]));
  return (
    <Modal open title="Record a historical participation?" busy={busy} onClose={onClose}
      actions={<><button type="button" className={secondaryButton} disabled={busy} onClick={onClose}>Cancel</button>
        <button type="button" className={primaryButton} disabled={busy || !preview?.can_confirm} onClick={() => void confirm()}>
          {busy ? 'Recording…' : 'Record participation'}</button></>}>
      {!preview && failure === null && <p role="status" className="dashboard-muted text-sm">Checking the records…</p>}
      {preview && (<>
        <p className="dashboard-muted text-sm">{student.ctug_id} · {periodLabel(row)}. This creates the participation, its subjects, one
          Uncleared clearance with Pending requirements and one Unpaid fee obligation of the semester’s original approved fee
          {preview.fee ? ` (${peso(preview.fee.amount)})` : ''}. The semester is not reopened. This action is audited.</p>
        {preview.blockers.map((b) => <p key={b} className="dashboard-warning rounded-xl border p-3 text-sm"><span aria-hidden="true" className="mr-2 font-bold">!</span>{BLOCKER_TEXT[b] ?? 'This correction is not available.'}</p>)}
        {preview.can_confirm && (<fieldset disabled={busy} className="space-y-3">
          <legend className="dashboard-heading text-sm font-semibold">Student type *</legend>
          <div className="flex flex-wrap gap-4">{(['Regular', 'Irregular'] as const).map((v) => (
            <label key={v} className="flex min-h-11 items-center gap-2 text-sm"><input type="radio" name={`${ids}-type`} className="h-4 w-4"
              checked={type === v} onChange={() => setType(v)} />{v}</label>))}</div>
          <p className="dashboard-heading text-sm font-semibold">Offering of each verified subject *</p>
          <ul className="space-y-1">{preview.options.map((o) => {
            const taken = !chosen.includes(o.offering_id) && chosen.some((c) => subjectOf.get(c) === o.subject.subject_id);
            return (<li key={o.offering_id}><label className="flex min-h-11 items-center gap-2 text-sm">
              <input type="checkbox" className="h-4 w-4" checked={chosen.includes(o.offering_id)} disabled={taken || !o.ready_for_confirmation}
                onChange={(e) => { setError(''); setChosen((prev) => e.target.checked ? [...prev, o.offering_id] : prev.filter((x) => x !== o.offering_id)); }} />
              <span className="dashboard-heading">{o.subject.code} · Section {o.section.name} · {o.instructor ? `Instructor: ${o.instructor}` : 'No instructor assigned'}</span></label></li>);
          })}</ul>
          <label htmlFor={`${ids}-note`} className="dashboard-heading block text-sm font-medium">Reason for the correction *</label>
          <textarea id={`${ids}-note`} className={fieldClass} rows={3} maxLength={500} value={note} onChange={(e) => { setNote(e.target.value); setError(''); }} />
          {error && <p role="alert" className="dashboard-error text-xs">{error}</p>}
        </fieldset>)}
      </>)}
      {failure !== null && <Failure error={failure} />}
    </Modal>
  );
}

function StudentRecord({ student }: { student: StudentRef }) {
  const [rows, setRows] = useState<PeriodRecord[] | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let cancelled = false;
    getStudentRecord(student.account_id).then((r) => { if (!cancelled) { setRows(r.periods); setFailure(null); } })
      .catch((e: unknown) => { if (!cancelled) setFailure(e); });
    return () => { cancelled = true; };
  }, [student.account_id, reload]);
  const done = (n: Notice) => { setDialog(null); setNotice(n); setReload((x) => x + 1); };
  return (
    <section aria-labelledby="student-record" className="dashboard-panel space-y-4 rounded-2xl border p-4 sm:p-6">
      <h3 id="student-record" className="dashboard-heading text-lg font-semibold">{student.ctug_id}{student.full_name ? ` · ${student.full_name}` : ''}</h3>
      <NoticeBlock notice={notice} />
      {failure !== null && <Failure error={failure} />}
      {rows === null && failure === null && <p role="status" className="dashboard-muted text-sm">Loading the student’s records…</p>}
      {rows !== null && rows.length === 0 && <p className="dashboard-muted text-sm">No semester has been active in the Workspace yet.</p>}
      {rows !== null && rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[580px] text-left text-sm">
            <caption className="sr-only">Verification by semester</caption>
            <thead><tr className="dashboard-muted border-b text-xs uppercase tracking-wide">
              <th scope="col" className="px-2 py-3">Semester</th><th scope="col" className="px-2 py-3">CTU verification</th>
              <th scope="col" className="px-2 py-3">Workspace records</th><th scope="col" className="px-2 py-3">Actions</th></tr></thead>
            <tbody>{rows.map((row) => {
              const historical = row.semester.status === 'Closed' || row.semester.status === 'Archived';
              return (
                <tr key={row.semester.semester_id} className="border-b align-top last:border-0">
                  <td className="dashboard-heading px-2 py-3 font-semibold">{periodLabel(row)}<span className="dashboard-muted block text-xs font-normal">{row.semester.status}</span></td>
                  <td className="px-2 py-3">{row.evidence
                    ? <span className="dashboard-heading">Enrolled · {row.evidence.course.code} Year {row.evidence.year_level} · {row.evidence.subjects.map((s) => s.code).join(', ')}
                        <span className="dashboard-muted block text-xs">{row.evidence.entry_classification} · {row.evidence.verified_by}</span></span>
                    : row.gap ? <span className="dashboard-heading">Verified not enrolled</span> : <span className="dashboard-muted">Not verified</span>}</td>
                  <td className="dashboard-muted px-2 py-3">{row.participation
                    ? `Participation (${row.participation.source === 'onboarding' ? 'onboarding' : 'historical correction'}) · Clearance ${row.clearance_status ?? '—'} · Fee ${row.fee ? `${peso(row.fee.amount)} ${row.fee.status}` : '—'}`
                    : row.onboarding_status ? `Onboarding ${row.onboarding_status === 'PendingVerification' ? 'pending verification' : row.onboarding_status.toLowerCase()}` : 'None'}</td>
                  <td className="px-2 py-3"><div className="flex flex-wrap gap-2">
                    {!row.participation && !row.gap && <button type="button" className={compactButton} onClick={() => setDialog({ kind: 'evidence', row })}>
                      {row.evidence ? 'Replace verification' : 'Record verification'}</button>}
                    {!row.participation && row.evidence && <button type="button" className={compactButton} onClick={() => setDialog({ kind: 'revoke', row })}>Revoke verification</button>}
                    {historical && !row.participation && !row.evidence && !row.gap && <button type="button" className={compactButton} onClick={() => setDialog({ kind: 'gap', row })}>Record non-enrollment</button>}
                    {row.gap && <button type="button" className={compactButton} onClick={() => setDialog({ kind: 'revoke-gap', row })}>Revoke non-enrollment</button>}
                    {HISTORICAL_PARTICIPATION_CORRECTION_ENABLED && historical && row.evidence && !row.participation && (
                      <button type="button" className={compactButton} onClick={() => setDialog({ kind: 'historical', row })}>Record historical participation</button>)}
                  </div></td>
                </tr>);
            })}</tbody>
          </table>
        </div>)}
      {dialog?.kind === 'evidence' && <EvidenceDialog student={student} row={dialog.row} onClose={() => setDialog(null)} onDone={done} />}
      {dialog?.kind === 'gap' && <ReferenceDialog student={student} row={dialog.row} onClose={() => setDialog(null)} onDone={done} />}
      {(dialog?.kind === 'revoke' || dialog?.kind === 'revoke-gap') && <RevokeDialog row={dialog.row} gap={dialog.kind === 'revoke-gap'} onClose={() => setDialog(null)} onDone={done} />}
      {dialog?.kind === 'historical' && <HistoricalDialog student={student} row={dialog.row} onClose={() => setDialog(null)} onDone={done} />}
    </section>
  );
}

export default function EnrollmentVerificationPanel() {
  const ids = useId();
  const [q, setQ] = useState('');
  const [results, setResults] = useState<StudentRef[] | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<StudentRef | null>(null);
  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setFailure(null);
    try { setResults(await searchStudents(q.trim())); } catch (e: unknown) { setFailure(e); setResults(null); } finally { setBusy(false); }
  }
  return (
    <div className="space-y-5">
      <section aria-labelledby={`${ids}-search`} className="dashboard-panel space-y-4 rounded-2xl border p-4 sm:p-6">
        <h2 id={`${ids}-search`} className="dashboard-heading text-lg font-semibold">Find a student</h2>
        <p className="dashboard-muted text-sm">Use this at the counter, with the student present and their official CTU records checked.
          Students confirm their own onboarding; recording a verification here never completes it for them.</p>
        <form noValidate onSubmit={(e) => void search(e)} className="flex flex-wrap items-end gap-3" aria-busy={busy}>
          <div className="min-w-0 flex-1"><label htmlFor={`${ids}-q`} className="dashboard-heading mb-1 block text-sm font-medium">CTU-G ID starts with</label>
            <input id={`${ids}-q`} className={fieldClass} value={q} maxLength={50} autoComplete="off" onChange={(e) => setQ(e.target.value)} /></div>
          <button type="submit" className={primaryButton} disabled={busy}>{busy ? 'Searching…' : 'Search students'}</button>
        </form>
        {failure !== null && <Failure error={failure} />}
        {results !== null && results.length === 0 && <p className="dashboard-muted text-sm">No matching students.</p>}
        {results !== null && results.length > 0 && (
          <ul className="space-y-2">{results.map((s) => (
            <li key={s.account_id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border p-3 text-sm">
              <span className="dashboard-heading min-w-0 truncate font-semibold">{s.ctug_id}{s.full_name ? ` · ${s.full_name}` : ''}</span>
              <button type="button" className={compactButton} aria-pressed={selected?.account_id === s.account_id}
                onClick={() => setSelected(s)}>Open records</button></li>))}</ul>)}
      </section>
      {selected && <StudentRecord key={selected.account_id} student={selected} />}
    </div>
  );
}
