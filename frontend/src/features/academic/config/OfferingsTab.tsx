/** Semester subject offerings and their instructor assignments.
 * An offering is an actual subject offered to one section in one semester (not the curriculum plan).
 * Offering writes and instructor assignments each need their own server switch and build flag. */
import { useEffect, useId, useState } from 'react';
import type { FormEvent } from 'react';
import Modal from '../../../components/common/Modal.tsx';
import { ACADEMIC_OFFERING_WRITES_ENABLED, ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED } from '../academicConfigurationConfig.ts';
import {
  assignInstructor, assignmentHistory, configErrorText, createOffering, endAssignment, listCandidates, listOfferings,
  listSections, listSemesters, removeOffering, searchInstructors,
} from '../academicConfigurationApi.ts';
import type { Assignment, Candidate, Features, Instructor, Offering, Section, SemesterRef } from '../academicConfigurationApi.ts';
import { compactButton, fieldClass, formatDateTime, primaryButton, secondaryButton } from '../academicStyles.ts';
import { ConfirmDialog, LoadFailure, NoticeBlock, StatusBadge } from './configUi.tsx';
import type { Notice } from './configUi.tsx';

type Listing = { status: 'idle' } | { status: 'loading' } | { status: 'failed'; error: unknown }
  | { status: 'ready'; results: Offering[]; validCount: number; semester: SemesterRef; features: Features };
type Dialog = { kind: 'assign' | 'end' | 'remove' | 'history'; offering: Offering } | null;

const END_REASONS = [
  { value: 'instructor_unavailable', label: 'Instructor unavailable' },
  { value: 'schedule_change', label: 'Schedule change' },
  { value: 'assignment_error', label: 'Assignment entered in error' },
];
const name = (i: Instructor) => `${i.full_name ?? 'Name not recorded'} (CTU-G ID ${i.ctug_id})`;

function InstructorDialog({ offering, onClose, onDone }: { offering: Offering; onClose: () => void; onDone: (o: Offering) => void }) {
  const ids = useId();
  const [q, setQ] = useState('');
  const [results, setResults] = useState<Instructor[] | null>(null);
  const [choice, setChoice] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');

  async function search(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setFailure('');
    try { setResults(await searchInstructors(q)); } catch (error: unknown) { setFailure(configErrorText(error)); }
  }
  useEffect(() => {
    let cancelled = false;
    searchInstructors('').then((r) => { if (!cancelled) setResults(r); })
      .catch((error: unknown) => { if (!cancelled) setFailure(configErrorText(error)); });
    return () => { cancelled = true; };
  }, []);

  async function confirm() {
    if (choice === null) return;
    setBusy(true); setFailure('');
    try { onDone(await assignInstructor(offering.offering_id, choice, offering.assignment?.assignment_id ?? null)); }
    catch (error: unknown) { setFailure(configErrorText(error)); } finally { setBusy(false); }
  }

  return (
    <Modal open title={offering.assignment ? 'Change the instructor?' : 'Assign an instructor?'} busy={busy} onClose={onClose}
      actions={<>
        <button type="button" className={secondaryButton} disabled={busy} onClick={onClose}>Cancel</button>
        <button type="button" className={primaryButton} disabled={busy || choice === null} onClick={() => void confirm()}>
          {busy ? 'Saving…' : 'Assign instructor'}</button>
      </>}>
      <p className="dashboard-heading font-semibold">{offering.subject.code} · {offering.section.course_code} {offering.section.name}</p>
      {offering.assignment && <p className="dashboard-muted">Current: {name(offering.assignment.instructor)}. The current
        assignment is ended and kept in history.</p>}
      <form role="search" aria-label="Eligible instructors" onSubmit={(e) => void search(e)} className="flex flex-wrap items-end gap-2">
        <label className="dashboard-muted flex flex-1 flex-col gap-1 text-xs font-medium">Search CTU-G ID or name
          <input type="search" value={q} maxLength={50} onChange={(e) => setQ(e.target.value)} className={fieldClass} /></label>
        <button type="submit" className={secondaryButton}>Search</button>
      </form>
      {results === null && !failure && <p role="status" className="dashboard-muted">Loading eligible instructors…</p>}
      {results && results.length === 0 && <p className="dashboard-muted">No eligible instructor matches.</p>}
      {results && results.length > 0 && (
        <fieldset className="space-y-1">
          <legend className="dashboard-muted text-xs font-medium">Eligible instructors</legend>
          {results.map((i) => (
            <label key={i.account_id} className="flex min-h-11 items-center gap-2">
              <input type="radio" name={`${ids}-instructor`} checked={choice === i.account_id} onChange={() => setChoice(i.account_id)} className="h-4 w-4" />
              <span className="dashboard-heading">{name(i)}</span>
            </label>
          ))}
        </fieldset>
      )}
      <p className="dashboard-muted text-xs">Only approved accounts with a current Instructor role are listed. This is a
        subject teaching assignment, not a section adviser appointment. It is audited.</p>
      {failure && <p role="alert" className="dashboard-error-block rounded-xl border p-3"><span aria-hidden="true" className="mr-2 font-bold">!</span>{failure}</p>}
    </Modal>
  );
}

function EndDialog({ offering, onClose, onDone }: { offering: Offering; onClose: () => void; onDone: (o: Offering) => void }) {
  const [reason, setReason] = useState('');
  const ids = useId();
  const assignment = offering.assignment as Assignment;
  return (
    <ConfirmDialog title="End this instructor assignment?" confirmLabel="End assignment" busyLabel="Saving…" destructive
      confirmDisabled={!reason} onClose={onClose}
      confirm={async () => {
        onDone(await endAssignment(offering.offering_id, assignment.assignment_id, reason));
      }}
      onDone={() => undefined}
      body={<>
        <p>{name(assignment.instructor)} will no longer teach {offering.subject.code}. The assignment stays in history,
          and students cannot confirm this subject until a new instructor is assigned. This action is audited.</p>
        <label htmlFor={`${ids}-reason`} className="dashboard-muted mb-1 block text-xs font-medium">Reason</label>
        <select id={`${ids}-reason`} value={reason} onChange={(e) => setReason(e.target.value)} className={fieldClass}>
          <option value="">Choose a reason</option>
          {END_REASONS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
      </>} />
  );
}

function HistoryDialog({ offering, onClose }: { offering: Offering; onClose: () => void }) {
  const [rows, setRows] = useState<Assignment[] | null>(null);
  const [failure, setFailure] = useState('');
  useEffect(() => {
    let cancelled = false;
    assignmentHistory(offering.offering_id).then((r) => { if (!cancelled) setRows(r); })
      .catch((error: unknown) => { if (!cancelled) setFailure(configErrorText(error)); });
    return () => { cancelled = true; };
  }, [offering.offering_id]);
  return (
    <Modal open title="Instructor history" onClose={onClose}
      actions={<button type="button" className={secondaryButton} onClick={onClose}>Close</button>}>
      <p className="dashboard-heading font-semibold">{offering.subject.code} · {offering.section.course_code} {offering.section.name}</p>
      {rows === null && !failure && <p role="status" className="dashboard-muted">Loading history…</p>}
      {failure && <p role="alert" className="dashboard-error-block rounded-xl border p-3">{failure}</p>}
      {rows && rows.length === 0 && <p className="dashboard-muted">No instructor has been assigned yet.</p>}
      {rows && rows.length > 0 && (
        <ol className="space-y-2">{rows.map((a) => (
          <li key={a.assignment_id} className="rounded-xl border p-2">
            <p className="dashboard-heading">{name(a.instructor)}</p>
            <p className="dashboard-muted text-xs">{a.status} · assigned {a.assigned_at ? formatDateTime(a.assigned_at) : 'not recorded'}
              {a.ended_at ? ` · ended ${formatDateTime(a.ended_at)}` : ''}{a.end_reason ? ` (${a.end_reason.replace(/_/g, ' ')})` : ''}</p>
          </li>))}
        </ol>
      )}
    </Modal>
  );
}

export default function OfferingsTab({ canWriteOfferings, canAssign }: { canWriteOfferings: boolean; canAssign: boolean }) {
  const ids = useId();
  const [semesters, setSemesters] = useState<SemesterRef[] | null>(null);
  const [lookupFailure, setLookupFailure] = useState<unknown>(null);
  const [semesterId, setSemesterId] = useState('');
  const [sections, setSections] = useState<Section[]>([]);
  const [listing, setListing] = useState<Listing>({ status: 'idle' });
  const [version, setVersion] = useState(0);
  const [sectionId, setSectionId] = useState('');
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [entryId, setEntryId] = useState('');
  const [adding, setAdding] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [dialog, setDialog] = useState<Dialog>(null);

  useEffect(() => {
    let cancelled = false;
    listSemesters().then((r) => { if (!cancelled) { setSemesters(r.results); if (r.results[0]) setSemesterId(String(r.results[0].semester_id)); } })
      .catch((error: unknown) => { if (!cancelled) setLookupFailure(error); });
    listSections({ status: 'Active' }).then((p) => { if (!cancelled) setSections(p.results); }).catch(() => undefined);
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!semesterId) return;
    let cancelled = false;
    listOfferings(Number(semesterId))
      .then((r) => { if (!cancelled) setListing({ status: 'ready', results: r.results, validCount: r.valid_offering_count, semester: r.semester, features: r.features }); })
      .catch((error: unknown) => { if (!cancelled) setListing({ status: 'failed', error }); });
    return () => { cancelled = true; };
  }, [semesterId, version]);

  useEffect(() => {
    if (!semesterId || !sectionId) return;
    let cancelled = false;
    listCandidates(Number(semesterId), Number(sectionId)).then((r) => { if (!cancelled) setCandidates(r); }).catch(() => undefined);
    return () => { cancelled = true; };
  }, [semesterId, sectionId, version]);

  function reload() { setListing({ status: 'loading' }); setVersion((v) => v + 1); }

  const ready = listing.status === 'ready' ? listing : null;
  const open = ready ? ready.semester.status === 'Draft' || ready.semester.status === 'Active' : false;
  const offeringWrites = canWriteOfferings && Boolean(ready?.features.offering_writes) && ACADEMIC_OFFERING_WRITES_ENABLED;
  const assignWrites = canAssign && Boolean(ready?.features.teaching_assignments) && ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED;

  async function add(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!entryId || !sectionId) { setNotice({ kind: 'error', text: 'Choose a section and a curriculum subject.' }); return; }
    setAdding(true); setNotice(null);
    try {
      const created = await createOffering({ semester_id: Number(semesterId), section_id: Number(sectionId), curriculum_subject_id: Number(entryId) });
      setEntryId('');
      setNotice({ kind: 'success', text: `${created.subject.code} is now offered to ${created.section.course_code} ${created.section.name}.` });
      reload();
    } catch (error: unknown) { setNotice({ kind: 'error', text: configErrorText(error) }); } finally { setAdding(false); }
  }

  if (lookupFailure) return <LoadFailure error={lookupFailure} onRetry={() => window.location.reload()} />;
  if (semesters === null) return <p role="status" className="dashboard-muted text-sm">Loading semesters…</p>;
  if (semesters.length === 0) {
    return <p className="dashboard-muted rounded-xl border border-dashed p-4 text-center text-sm">No school years exist yet. Create one in School years &amp; semesters first.</p>;
  }

  return (
    <div className="space-y-4">
      <section className="dashboard-panel rounded-2xl border p-4 sm:p-5" aria-labelledby={`${ids}-title`} aria-busy={listing.status === 'loading'}>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 id={`${ids}-title`} className="dashboard-heading text-base font-semibold">Semester subject offerings</h3>
            <p className="dashboard-muted mt-1 text-xs">Offerings are actual subjects for a section in one semester. They do not prove any student’s CTU enrollment.</p>
          </div>
          <label className="dashboard-muted flex flex-col gap-1 text-xs font-medium">Semester
            <select value={semesterId} onChange={(e) => { setSemesterId(e.target.value); setListing({ status: 'loading' }); }} className={`${fieldClass} sm:w-72`}>
              {semesters.map((s) => <option key={s.semester_id} value={s.semester_id}>S.Y. {s.school_year_label} · {s.label} ({s.status})</option>)}
            </select>
          </label>
        </div>
        {ready && (
          <p className="dashboard-muted mt-3 text-xs">
            <strong className="dashboard-heading">{ready.validCount}</strong> valid offering{ready.validCount === 1 ? '' : 's'} count toward
            this semester’s activation prerequisites. Activation also requires an approved semester fee, which is not available yet.
          </p>
        )}
        {ready && !offeringWrites && (
          <p role="status" className="dashboard-warning mt-3 rounded-xl border p-3 text-sm">
            <span aria-hidden="true" className="mr-2 font-bold">!</span>Adding or removing offerings is not enabled. Its permission mapping is awaiting access-control review.
          </p>
        )}
        {ready && offeringWrites && open && (
          <form noValidate onSubmit={(e) => void add(e)} className="mt-4 grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end" aria-label="Add an offering">
            <label className="dashboard-muted flex min-w-0 flex-col gap-1 text-xs font-medium">Section
              <select value={sectionId} onChange={(e) => { setSectionId(e.target.value); setEntryId(''); setCandidates([]); }} className={fieldClass}>
                <option value="">Choose…</option>
                {sections.map((s) => <option key={s.section_id} value={s.section_id}>{s.course.code} {s.name} (Year {s.year_level})</option>)}
              </select></label>
            <label className="dashboard-muted flex min-w-0 flex-col gap-1 text-xs font-medium">Curriculum subject
              <select value={entryId} onChange={(e) => setEntryId(e.target.value)} className={fieldClass} disabled={!sectionId}>
                <option value="">{sectionId && candidates.length === 0 ? 'No matching published subject' : 'Choose…'}</option>
                {candidates.map((c) => <option key={c.curriculum_subject_id} value={c.curriculum_subject_id}>{c.subject.code} · {c.subject.title} ({c.curriculum.label})</option>)}
              </select></label>
            <button type="submit" className={primaryButton} disabled={adding}>{adding ? 'Adding…' : 'Add offering'}</button>
          </form>
        )}
        <NoticeBlock notice={notice} />
        {listing.status === 'loading' && <p role="status" className="dashboard-muted mt-4 text-sm">Loading offerings…</p>}
        {listing.status === 'failed' && <LoadFailure error={listing.error} onRetry={reload} />}
        {ready && ready.results.length === 0 && (
          <p className="dashboard-muted mt-4 rounded-xl border border-dashed p-4 text-center text-sm">No offerings for this semester yet.</p>)}
        {ready && ready.results.length > 0 && (
          <ul aria-label="Offerings" className="mt-4 divide-y">
            {ready.results.map((o) => (
              <li key={o.offering_id} className="flex flex-wrap items-start justify-between gap-3 py-3">
                <div className="min-w-0 flex-1 text-sm">
                  <p className="dashboard-heading font-semibold">{o.subject.code} <span className="font-normal">· {o.subject.title}</span></p>
                  <p className="dashboard-muted text-xs">{o.section.course_code} {o.section.name} · Year {o.section.year_level} · {o.curriculum.label}</p>
                  <p className="mt-1 text-xs">
                    <span className="dashboard-muted">Instructor: </span>
                    <span className="dashboard-heading">{o.assignment ? name(o.assignment.instructor) : 'Not assigned'}</span>
                    {o.assignment && !o.assignment.eligible && <span className="dashboard-error font-semibold"> · Not eligible now</span>}
                  </p>
                  <p className="dashboard-muted text-xs">
                    <span aria-hidden="true">{o.ready_for_confirmation ? '✓ ' : '○ '}</span>
                    {o.ready_for_confirmation ? 'Ready for student subject confirmation' : 'Students cannot confirm this subject until an eligible instructor is assigned'}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {assignWrites && open && (
                    <button type="button" className={compactButton} onClick={() => setDialog({ kind: 'assign', offering: o })}>
                      {o.assignment ? 'Change instructor' : 'Assign instructor'}<span className="sr-only"> for {o.subject.code} {o.section.name}</span></button>)}
                  {assignWrites && open && o.assignment && (
                    <button type="button" className={compactButton} onClick={() => setDialog({ kind: 'end', offering: o })}>
                      End assignment<span className="sr-only"> for {o.subject.code} {o.section.name}</span></button>)}
                  <button type="button" className={compactButton} onClick={() => setDialog({ kind: 'history', offering: o })}>
                    Instructor history<span className="sr-only"> for {o.subject.code} {o.section.name}</span></button>
                  {offeringWrites && o.can_remove && (
                    <button type="button" className={compactButton} onClick={() => setDialog({ kind: 'remove', offering: o })}>
                      Remove<span className="sr-only"> {o.subject.code} {o.section.name}</span></button>)}
                </div>
              </li>
            ))}
          </ul>
        )}
        {ready && <p className="dashboard-muted mt-3 text-xs">Semester status: <StatusBadge status={ready.semester.status} /></p>}
      </section>
      {dialog?.kind === 'assign' && (
        <InstructorDialog offering={dialog.offering} onClose={() => setDialog(null)}
          onDone={(o) => { setDialog(null); setNotice({ kind: 'success', text: `${o.subject.code}: the instructor assignment was saved.` }); reload(); }} />)}
      {dialog?.kind === 'end' && (
        <EndDialog offering={dialog.offering} onClose={() => setDialog(null)}
          onDone={(o) => { setDialog(null); setNotice({ kind: 'success', text: `${o.subject.code}: the instructor assignment was ended.` }); reload(); }} />)}
      {dialog?.kind === 'history' && <HistoryDialog offering={dialog.offering} onClose={() => setDialog(null)} />}
      {dialog?.kind === 'remove' && (
        <ConfirmDialog title="Remove this offering?" destructive confirmLabel="Remove offering" busyLabel="Removing…"
          body={<p>{dialog.offering.subject.code} is no longer offered to {dialog.offering.section.course_code} {dialog.offering.section.name}
            in this Draft semester. The curriculum and subject are not changed. This action is audited.</p>}
          onClose={() => setDialog(null)} confirm={async () => { await removeOffering(dialog.offering.offering_id); }}
          onDone={() => { setDialog(null); setNotice({ kind: 'success', text: 'The offering was removed.' }); reload(); }} />)}
    </div>
  );
}
