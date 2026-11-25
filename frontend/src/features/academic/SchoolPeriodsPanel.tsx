/** WF-11.01 School years & semesters (dashboard surface).
 *
 * Draft management: create a School Year (Django creates its First and Second semesters as Draft),
 * set Draft dates and delete a genuinely unused Draft year. Lifecycle: review then explicitly confirm
 * activation, closure and archiving (LifecycleDialog); reasoned Active edits and historical
 * corrections (CorrectionDialog); read-only history (PeriodHistory). Confirmations are enabled only
 * when both the server and this build report the action available. Semester fees are not set here.
 * Every request is re-authorized by Django (academic.periods.manage, Admin role context, Deny).
 */
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import Modal from '../../components/common/Modal.tsx';
import { DashboardState } from '../../components/dashboard/DashboardStates';
import { AcademicApiError, createSchoolYear, deleteSchoolYear, listSchoolYears, updateSemesterDates } from './academicPeriodsApi.ts';
import { ACADEMIC_PERIOD_CORRECTIONS_ENABLED, ACADEMIC_PERIOD_TRANSITIONS_ENABLED } from './academicPeriodsConfig.ts';
import type { Transition } from './academicLifecycleApi.ts';
import CorrectionDialog from './CorrectionDialog.tsx';
import LifecycleDialog from './LifecycleDialog.tsx';
import PeriodHistory from './PeriodHistory.tsx';
import {
  badgeClass, compactButton, destructiveButton, fieldClass, formatDate, primaryButton, secondaryButton,
} from './academicStyles.ts';
import {
  parseStartYear, schoolYearBounds, semestersOverlap, validateSemesterRange,
} from './academicPeriodsContract.ts';
import type { ActivationRequirement, FieldName, SchoolYear, SchoolYearPage, SchoolYearStatus, Semester, SemesterStatus } from './academicPeriodsContract.ts';

type Listing = { status: 'loading' } | { status: 'failed'; error: AcademicApiError | null } | { status: 'ready'; data: SchoolYearPage };
type Notice = { kind: 'success' | 'error'; text: string } | null;

const asAcademic = (error: unknown) => (error instanceof AcademicApiError ? error : null);

type Dialog = { kind: Transition | 'correction'; year: SchoolYear; semester: Semester } | null;

const STATUS_MARKS: Record<SemesterStatus | SchoolYearStatus, string> = {
  Draft: '○', Active: '●', Closed: '■', Archived: '▣', 'Between semesters': '◐', Completed: '✓',
};

function StatusBadge({ status }: { status: SemesterStatus | SchoolYearStatus }) {
  const tone = status === 'Active' ? 'dashboard-accent' : status === 'Draft' ? 'dashboard-muted border-dashed' : 'dashboard-heading';
  return <span className={`${badgeClass} ${tone}`}><span aria-hidden="true">{STATUS_MARKS[status]}</span>{status}</span>;
}

const REQUIREMENT_LABELS: Record<ActivationRequirement, string> = {
  valid_dates: 'Valid start and end dates',
  approved_fee: 'Approved semester organization fee',
  academic_offerings: 'Curriculum and subject offerings',
};

function failureCopy(error: AcademicApiError | null): { title: string; detail: string; retry: boolean } {
  switch (error?.detail.code) {
    case 'authentication_required': return { title: 'Your session has ended', detail: 'Sign in again to continue.', retry: false };
    case 'access_denied':
      return error.detail.reason === 'admin_context_required'
        ? { title: 'Switch to your School Admin role', detail: 'School years and semesters can be managed only while your School Admin role is selected.', retry: true }
        : { title: 'You do not have permission to manage school years', detail: 'Ask the Technical Super Admin to check your account access.', retry: false };
    case 'rate_limited': return { title: 'Too many requests', detail: 'Wait a minute, then try again.', retry: true };
    case 'academic_periods_unavailable': return { title: 'School years are not available right now', detail: 'Try again later.', retry: true };
    default: return { title: 'School years could not be loaded', detail: 'Check your connection, then try again.', retry: true };
  }
}

/** Fixed, non-sensitive copy for a refused change. Never server text. */
function changeFailure(error: unknown, subject: string): string {
  const academic = asAcademic(error);
  if (!academic) return `${subject} could not be saved. Reload the list, then try again.`;
  const { code, reason } = academic.detail;
  if (code === 'outcome_unknown') return 'We could not confirm the change. Reload the list to see the current state before trying again.';
  if (code === 'csrf_failed') return 'Security check failed. Refresh the page and try again.';
  if (code === 'access_denied') return reason === 'admin_context_required'
    ? 'Switch to your School Admin role, then try again.' : 'You do not have permission to make this change.';
  if (code === 'rate_limited') return 'Too many requests. Wait a minute, then try again.';
  if (code === 'authentication_required') return 'Your session has ended. Sign in again to continue.';
  if (code === 'period_unavailable') return 'This school year or semester is no longer available. Reload the list.';
  if (code === 'academic_periods_unavailable') return 'School years are not available right now. Try again later.';
  switch (reason) {
    case 'school_year_exists': return 'This school year already exists.';
    case 'stale_version': return 'This semester was changed by someone else. Reload the list and try again.';
    case 'period_not_draft': return 'Only Draft semesters can be changed here.';
    case 'semesters_overlap': return 'The First semester must end before the Second semester starts.';
    case 'period_in_use': return 'This school year is in use and cannot be deleted.';
    case 'confirmation_mismatch': return 'The school year changed. Reload the list and try again.';
    default: return `${subject} could not be saved. Check the details and try again.`;
  }
}

function Prerequisites({ semester }: { semester: Semester }) {
  const items: ActivationRequirement[] = ['valid_dates', 'approved_fee', 'academic_offerings'];
  return (
    <div className="mt-4 border-t pt-3">
      <p className="dashboard-muted text-xs font-semibold">Activation prerequisites</p>
      <ul className="mt-2 space-y-1 text-xs">
        {items.map((item) => {
          const missing = semester.activation.missing.includes(item);
          const note = missing ? 'Not ready' : 'Ready';
          return (
            <li key={item} className="flex items-start justify-between gap-3">
              <span className="dashboard-heading">{REQUIREMENT_LABELS[item]}</span>
              <span className={missing ? 'dashboard-muted whitespace-nowrap' : 'dashboard-accent whitespace-nowrap font-semibold'}>
                <span aria-hidden="true">{missing ? '○ ' : '✓ '}</span>{note}
              </span>
            </li>
          );
        })}
      </ul>
      <p className="dashboard-muted mt-2 text-xs">Activation needs every prerequisite. Review activation for the current details.</p>
    </div>
  );
}

interface EditorProps {
  year: SchoolYear;
  semester: Semester;
  onSaved: (year: SchoolYear, text: string) => void;
  onCancel: () => void;
  onFailed: (text: string, reload: boolean) => void;
}

function DatesEditor({ year, semester, onSaved, onCancel, onFailed }: EditorProps) {
  const ids = useId();
  const startRef = useRef<HTMLInputElement>(null);
  const endRef = useRef<HTMLInputElement>(null);
  const [start, setStart] = useState(semester.start_date ?? '');
  const [end, setEnd] = useState(semester.end_date ?? '');
  const [errors, setErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [busy, setBusy] = useState(false);
  const [overlapReview, setOverlapReview] = useState(false);
  const bounds = schoolYearBounds(year.start_year);
  const sibling = year.semesters.find((s) => s.semester_id !== semester.semester_id);

  useEffect(() => { startRef.current?.focus(); }, []);

  function focusFirst(found: Partial<Record<FieldName, string>>) {
    if (found.start_date) startRef.current?.focus(); else if (found.end_date) endRef.current?.focus();
  }

  async function save(acknowledge: boolean) {
    const payload = { start: start || null, end: end || null };
    setBusy(true);
    try {
      const updated = await updateSemesterDates(semester.semester_id, {
        start_date: payload.start, end_date: payload.end, expected_version: semester.version,
        acknowledge_cross_year_overlap: acknowledge,
      });
      setOverlapReview(false);
      onSaved(updated, `${semester.label} dates for S.Y. ${year.label} were saved.`);
    } catch (error: unknown) {
      setOverlapReview(false);
      const academic = asAcademic(error);
      if (academic?.detail.reason === 'cross_year_overlap' && !acknowledge) { setOverlapReview(true); return; }
      if (academic && Object.keys(academic.detail.fields).length) {
        setErrors(academic.detail.fields);
        focusFirst(academic.detail.fields);
        return;
      }
      const reload = academic?.detail.reason === 'stale_version' || academic?.detail.code === 'outcome_unknown'
        || academic?.detail.code === 'period_unavailable' || academic?.detail.reason === 'period_not_draft';
      onFailed(changeFailure(error, 'The dates'), reload);
    } finally {
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found = validateSemesterRange(start || null, end || null, year.start_year);
    if (!found.start_date && !found.end_date && sibling) {
      const mine: [string | null, string | null] = [start || null, end || null];
      const theirs: [string | null, string | null] = [sibling.start_date, sibling.end_date];
      const overlap = semester.term === 'first' ? semestersOverlap(mine, theirs) : semestersOverlap(theirs, mine);
      if (overlap) found[semester.term === 'first' ? 'end_date' : 'start_date'] = 'The First semester must end before the Second semester starts.';
    }
    setErrors(found);
    if (found.start_date || found.end_date) { focusFirst(found); return; }
    void save(false);
  }

  const field = (name: 'start_date' | 'end_date', label: string, value: string, set: (v: string) => void,
    ref: typeof startRef) => (
    <div className="min-w-0">
      <label htmlFor={`${ids}-${name}`} className="dashboard-muted mb-1 block text-xs font-medium">{label}</label>
      <input ref={ref} id={`${ids}-${name}`} type="date" value={value} min={bounds.min} max={bounds.max}
        disabled={busy} aria-invalid={errors[name] ? true : undefined}
        aria-describedby={errors[name] ? `${ids}-${name}-error` : `${ids}-hint`}
        onChange={(event) => { set(event.target.value); setErrors((e) => ({ ...e, [name]: undefined })); }}
        className={`${fieldClass} disabled:cursor-not-allowed disabled:opacity-60`} />
      {errors[name] && <p id={`${ids}-${name}-error`} className="dashboard-error mt-1 text-xs">{errors[name]}</p>}
    </div>
  );

  return (
    <form noValidate onSubmit={submit} className="mt-4 space-y-3" aria-label={`${semester.label} dates`}>
      <div className="grid gap-3 sm:grid-cols-2">
        {field('start_date', 'Start date', start, setStart, startRef)}
        {field('end_date', 'End date', end, setEnd, endRef)}
      </div>
      <p id={`${ids}-hint`} className="dashboard-muted text-xs">
        Leave a date empty while it is not yet known. Dates must fall from {formatDate(bounds.min)} to {formatDate(bounds.max)}.
      </p>
      <div className="flex flex-wrap justify-end gap-3">
        <button type="button" className={secondaryButton} disabled={busy} onClick={onCancel}>Cancel</button>
        <button type="submit" className={primaryButton} disabled={busy}>{busy ? 'Saving…' : 'Save dates'}</button>
      </div>
      <Modal open={overlapReview} title="Save overlapping dates?" busy={busy} onClose={() => setOverlapReview(false)}
        actions={<>
          <button type="button" className={secondaryButton} disabled={busy} onClick={() => setOverlapReview(false)}>Cancel</button>
          <button type="button" className={primaryButton} disabled={busy} onClick={() => void save(true)}>{busy ? 'Saving…' : 'Save anyway'}</button>
        </>}>
        <p>These dates overlap a semester of another school year.</p>
        <p>Save them only if the overlap is intended. Your confirmation is recorded in the audit history.</p>
      </Modal>
    </form>
  );
}

function SemesterCard({ year, semester, editing, onEdit, onAction, children }: {
  year: SchoolYear; semester: Semester; editing: boolean; onEdit: () => void;
  onAction: (kind: Transition | 'correction') => void; children?: ReactNode;
}) {
  const where = <span className="sr-only"> for {semester.label}, S.Y. {year.label}</span>;
  const actions: [Transition | 'correction', string][] = semester.status === 'Draft' ? [['activation', 'Review activation']]
    : semester.status === 'Active' ? [['closure', 'Review closure'], ['correction', 'Edit active semester']]
      : semester.status === 'Closed' ? [['archive', 'Review archiving'], ['correction', 'Correct dates']]
        : [['correction', 'Correct dates']];
  return (
    <article className="dashboard-panel rounded-xl border p-4" aria-label={`${semester.label}, S.Y. ${year.label}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h4 className="dashboard-heading text-sm font-semibold">{semester.label}</h4>
        <StatusBadge status={semester.status} />
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div><dt className="dashboard-muted text-xs">Start date</dt><dd className="dashboard-heading mt-1 font-medium">{formatDate(semester.start_date)}</dd></div>
        <div><dt className="dashboard-muted text-xs">End date</dt><dd className="dashboard-heading mt-1 font-medium">{formatDate(semester.end_date)}</dd></div>
      </dl>
      {editing ? children : (
        <div className="mt-3 flex flex-wrap gap-2">
          {semester.can_edit_dates && <button type="button" className={compactButton} onClick={onEdit}>Edit dates{where}</button>}
          {actions.map(([kind, label]) => (
            <button key={kind} type="button" className={compactButton} onClick={() => onAction(kind)}>{label}{where}</button>
          ))}
        </div>
      )}
      {semester.status === 'Draft' && <Prerequisites semester={semester} />}
    </article>
  );
}

export default function SchoolPeriodsPanel() {
  const ids = useId();
  const yearRef = useRef<HTMLInputElement>(null);
  const noticeRef = useRef<HTMLDivElement>(null);
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [listing, setListing] = useState<Listing>({ status: 'loading' });
  const [yearText, setYearText] = useState('');
  const [yearError, setYearError] = useState('');
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<number | null>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const [pendingDelete, setPendingDelete] = useState<SchoolYear | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [historyOpen, setHistoryOpen] = useState<ReadonlySet<number>>(new Set());

  function toggleHistory(id: number) {
    setHistoryOpen((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function lifecycleDone(message: string) {
    setDialog(null);
    setHistoryOpen(new Set());
    setNotice({ kind: 'success', text: message });
    reload();
  }

  useEffect(() => {
    let cancelled = false;
    listSchoolYears(page)
      .then((data) => { if (!cancelled) setListing({ status: 'ready', data }); })
      .catch((error: unknown) => { if (!cancelled) setListing({ status: 'failed', error: asAcademic(error) }); });
    return () => { cancelled = true; };
  }, [page, version]);

  useEffect(() => { if (notice?.kind === 'error') noticeRef.current?.focus(); }, [notice]);

  function reload(nextPage = page) {
    setListing({ status: 'loading' });
    setEditing(null);
    if (nextPage !== page) setPage(nextPage); else setVersion((v) => v + 1);
  }

  function replaceYear(updated: SchoolYear) {
    setListing((current) => current.status !== 'ready' ? current : { status: 'ready', data: {
      ...current.data, results: current.data.results.map((y) => (y.school_year_id === updated.school_year_id ? updated : y)),
    } });
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const startYear = parseStartYear(yearText);
    if (startYear === null) {
      setYearError('Enter a starting year from 2000 to 2100.');
      yearRef.current?.focus();
      return;
    }
    setYearError('');
    setCreating(true);
    setNotice(null);
    try {
      const created = await createSchoolYear(startYear);
      setYearText('');
      setNotice({ kind: 'success', text: `S.Y. ${created.label} was created with Draft First and Second semesters.` });
      reload(1);
    } catch (error: unknown) {
      const academic = asAcademic(error);
      if (academic?.detail.fields.start_year) { setYearError(academic.detail.fields.start_year); yearRef.current?.focus(); }
      else setNotice({ kind: 'error', text: changeFailure(error, 'The school year') });
      if (academic?.detail.code === 'outcome_unknown') reload();
    } finally {
      setCreating(false);
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return;
    const target = pendingDelete;
    setDeleting(true);
    try {
      await deleteSchoolYear(target.school_year_id, target.start_year);
      setNotice({ kind: 'success', text: `S.Y. ${target.label} and its two Draft semesters were deleted.` });
      setPendingDelete(null);
      reload();
    } catch (error: unknown) {
      setPendingDelete(null);
      setNotice({ kind: 'error', text: changeFailure(error, 'The school year') });
      reload();
    } finally {
      setDeleting(false);
    }
  }

  const loading = listing.status === 'loading';
  const failure = listing.status === 'failed' ? failureCopy(listing.error) : null;
  const denied = listing.status === 'failed' && listing.error?.detail.code === 'access_denied'
    && listing.error.detail.reason !== 'admin_context_required';

  if (denied && failure) {
    return <DashboardState title={failure.title}>{failure.detail}</DashboardState>;
  }

  const rows = listing.status === 'ready' ? listing.data.results : [];
  const features = listing.status === 'ready' ? listing.data.features : { transitions: false, corrections: false };

  return (
    <div className="space-y-5">
      <section className="dashboard-panel rounded-2xl border p-4 sm:p-6" aria-labelledby={`${ids}-create`}>
        <h2 id={`${ids}-create`} className="dashboard-heading text-lg font-semibold">Create a school year</h2>
        <p className="dashboard-muted mt-1 text-sm">
          The school year is created with a First semester and a Second semester, both in Draft. Nothing is activated automatically.
        </p>
        <form noValidate onSubmit={create} className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-start">
          <div className="sm:w-56">
            <label htmlFor={`${ids}-year`} className="dashboard-muted mb-1 block text-xs font-medium">Starting year</label>
            <input ref={yearRef} id={`${ids}-year`} inputMode="numeric" autoComplete="off" maxLength={4} value={yearText}
              disabled={creating} aria-invalid={yearError ? true : undefined}
              aria-describedby={yearError ? `${ids}-year-error` : `${ids}-year-hint`}
              onChange={(event) => { setYearText(event.target.value); setYearError(''); }}
              className={`${fieldClass} disabled:cursor-not-allowed disabled:opacity-60`} />
            {yearError
              ? <p id={`${ids}-year-error`} className="dashboard-error mt-1 text-xs">{yearError}</p>
              : <p id={`${ids}-year-hint`} className="dashboard-muted mt-1 text-xs">For example, 2026 creates S.Y. 2026–2027.</p>}
          </div>
          <button type="submit" className={`${primaryButton} sm:mt-5`} disabled={creating}>
            {creating ? 'Creating…' : 'Create school year'}
          </button>
        </form>
      </section>

      {notice && (
        <div ref={noticeRef} tabIndex={-1} role={notice.kind === 'error' ? 'alert' : 'status'}
          className={`${notice.kind === 'error' ? 'dashboard-error-block' : 'dashboard-success'} rounded-xl border p-4 text-sm`}>
          <span aria-hidden="true" className="mr-2 font-bold">{notice.kind === 'error' ? '!' : '✓'}</span>{notice.text}
        </div>
      )}

      <section className="dashboard-panel rounded-2xl border p-4 sm:p-6" aria-labelledby={`${ids}-list`} aria-busy={loading}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 id={`${ids}-list`} className="dashboard-heading text-lg font-semibold">School years</h2>
            <p className="dashboard-muted mt-1 text-xs">
              Newest first. A school year’s status comes from its semesters. Semester fees are not set here.
            </p>
          </div>
          <button type="button" className={secondaryButton} disabled={loading} onClick={() => reload()}>Refresh list</button>
        </div>

        {loading && (
          <div className="mt-5 space-y-3" aria-hidden="true">
            {[0, 1].map((i) => <div key={i} className="dashboard-panel h-40 rounded-xl border opacity-60" />)}
          </div>
        )}
        {loading && <p role="status" className="sr-only">Loading school years…</p>}

        {failure && (
          <div role="alert" className="dashboard-error-block mt-5 rounded-xl border p-4 text-sm">
            <p className="font-semibold"><span aria-hidden="true" className="mr-2">!</span>{failure.title}</p>
            <p className="mt-1">{failure.detail}</p>
            {failure.retry && <button type="button" className={`${secondaryButton} mt-3`} onClick={() => reload()}>Try again</button>}
          </div>
        )}

        {listing.status === 'ready' && rows.length === 0 && (
          <div className="mt-5 rounded-xl border border-dashed p-6 text-center">
            <p className="dashboard-heading font-semibold">No school years yet</p>
            <p className="dashboard-muted mt-1 text-sm">Create the first school year above. Its semesters start in Draft.</p>
          </div>
        )}

        {rows.length > 0 && (
          <ul className="mt-5 space-y-4">
            {rows.map((year) => (
              <li key={year.school_year_id} className="rounded-2xl border p-4 sm:p-5" aria-labelledby={`${ids}-sy-${year.school_year_id}`}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 id={`${ids}-sy-${year.school_year_id}`} className="dashboard-heading text-base font-semibold">S.Y. {year.label}</h3>
                    <StatusBadge status={year.status} />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button type="button" className={compactButton} aria-expanded={historyOpen.has(year.school_year_id)}
                      onClick={() => toggleHistory(year.school_year_id)}>
                      {historyOpen.has(year.school_year_id) ? 'Hide history' : 'View history'}<span className="sr-only"> of S.Y. {year.label}</span>
                    </button>
                    {year.can_delete && (
                      <button type="button" className={compactButton} onClick={() => setPendingDelete(year)}>
                        Delete<span className="sr-only"> S.Y. {year.label}</span>
                      </button>
                    )}
                  </div>
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  {year.semesters.map((semester) => (
                    <SemesterCard key={semester.semester_id} year={year} semester={semester}
                      editing={editing === semester.semester_id} onEdit={() => { setNotice(null); setEditing(semester.semester_id); }}
                      onAction={(kind) => { setNotice(null); setDialog({ kind, year, semester }); }}>
                      <DatesEditor year={year} semester={semester} onCancel={() => setEditing(null)}
                        onSaved={(updated, text) => { replaceYear(updated); setEditing(null); setNotice({ kind: 'success', text }); }}
                        onFailed={(text, shouldReload) => { setNotice({ kind: 'error', text }); if (shouldReload) reload(); }} />
                    </SemesterCard>
                  ))}
                </div>
                {historyOpen.has(year.school_year_id) && <PeriodHistory schoolYearId={year.school_year_id} label={year.label} />}
              </li>
            ))}
          </ul>
        )}

        {listing.status === 'ready' && (page > 1 || listing.data.has_next) && (
          <nav aria-label="School year pages" className="mt-5 flex items-center justify-end gap-3">
            <button type="button" className={compactButton} disabled={page <= 1} onClick={() => reload(page - 1)}>Previous</button>
            <span className="dashboard-muted text-xs">Page {page}</span>
            <button type="button" className={compactButton} disabled={!listing.data.has_next} onClick={() => reload(page + 1)}>Next</button>
          </nav>
        )}
      </section>

      {dialog && dialog.kind !== 'correction' && (
        <LifecycleDialog key={`${dialog.kind}-${dialog.semester.semester_id}`} transition={dialog.kind} semester={dialog.semester}
          yearLabel={dialog.year.label} buildEnabled={ACADEMIC_PERIOD_TRANSITIONS_ENABLED && features.transitions}
          onClose={() => setDialog(null)} onDone={(_result, message) => lifecycleDone(message)} />
      )}
      {dialog && dialog.kind === 'correction' && (
        <CorrectionDialog key={`correction-${dialog.semester.semester_id}`} semester={dialog.semester} year={dialog.year}
          buildEnabled={ACADEMIC_PERIOD_CORRECTIONS_ENABLED && features.corrections}
          onClose={() => setDialog(null)} onSaved={(_updated, message) => lifecycleDone(message)} />
      )}

      <Modal open={pendingDelete !== null} title="Delete this school year?" busy={deleting} onClose={() => setPendingDelete(null)}
        actions={<>
          <button type="button" className={secondaryButton} disabled={deleting} onClick={() => setPendingDelete(null)}>Cancel</button>
          <button type="button" className={destructiveButton} disabled={deleting} onClick={() => void confirmDelete()}>
            {deleting ? 'Deleting…' : 'Delete school year'}
          </button>
        </>}>
        <p>S.Y. <strong>{pendingDelete?.label}</strong> and its two Draft semesters will be permanently deleted.</p>
        <p>Only school years that were never activated and have no records can be deleted. This action is audited.</p>
      </Modal>
    </div>
  );
}
