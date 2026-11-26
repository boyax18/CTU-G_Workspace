/** WF-05.05 Student Semester Onboarding (dashboard surface).
 *
 * Steps: 1 Student type, 2 Subject confirmation, 3 Course and year level, 4 Final review and explicit
 * confirmation. School Year, Semester and CTU-G ID are read-only from the server. Missing or incorrect
 * data is corrected in person by the School Admin (no online correction request). Nothing here
 * claims enrollment: without a matching verified CTU record the confirmation is Pending Verification.
 * Every state comes from the server; Django re-checks the Student role context and permission.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { DashboardState } from '../../components/dashboard/DashboardStates';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import { NoticeBlock } from '../academic/config/configUi.tsx';
import type { Notice } from '../academic/config/configUi.tsx';
import { fieldClass, formatDate, primaryButton, secondaryButton } from '../academic/academicStyles.ts';
import { ClearanceList, ResultSummary } from './RecordParts.tsx';
import OwnHistory from './OwnHistory.tsx';
import { useStudentGate } from './studentGateRules.ts';
import {
  OnboardingApiError, confirmCourse, confirmSubjects, finalizeOnboarding, getContext, getReview, getStatus, getSubjectOptions,
  onboardingErrorText, peso, saveStudentType,
} from './onboardingApi.ts';
import type { ContextCourse, Draft, Option, PeriodRef, Review, Status, StudentType } from './onboardingApi.ts';

const STEPS = ['Student type', 'Subject confirmation', 'Course and year level', 'Final review'] as const;
const MISMATCH_TEXT: Record<string, string> = { course: 'course', year_level: 'year level', subjects: 'subjects' };
const periodLabel = (p: PeriodRef) => `${p.label}, S.Y. ${p.school_year_label}`;

function ErrorBlock({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  return (
    <div role="alert" className="dashboard-error-block rounded-xl border p-4 text-sm">
      <p><span aria-hidden="true" className="mr-2 font-bold">!</span>{onboardingErrorText(error)}</p>
      {onRetry && <button type="button" className={`${secondaryButton} mt-3`} onClick={onRetry}>Try again</button>}
    </div>
  );
}

function Header({ status }: { status: Status }) {
  return (
    <dl className="grid gap-4 text-sm sm:grid-cols-3">
      <div><dt className="dashboard-muted text-xs">School year</dt><dd className="dashboard-heading font-semibold">{status.semester?.school_year_label ?? '—'}</dd></div>
      <div><dt className="dashboard-muted text-xs">Semester</dt><dd className="dashboard-heading font-semibold">{status.semester
        ? `${status.semester.label} · ${formatDate(status.semester.start_date)} to ${formatDate(status.semester.end_date)}` : '—'}</dd></div>
      <div><dt className="dashboard-muted text-xs">CTU-G ID</dt><dd className="dashboard-heading font-semibold">{status.student?.ctug_id ?? '—'}
        {status.student?.full_name && <span className="dashboard-muted block text-xs font-normal">{status.student.full_name}</span>}</dd></div>
    </dl>
  );
}

function InPerson({ text }: { text: string }) {
  return <p className="dashboard-warning rounded-xl border p-4 text-sm"><span aria-hidden="true" className="mr-2 font-bold">!</span>{text}</p>;
}

function Blocked({ status }: { status: Status }) {
  const e = status.eligibility;
  if (status.state === 'clearance_required') {
    const previous = status.previous_clearance;
    return (
      <section aria-labelledby="clearance-required" className="dashboard-panel space-y-4 rounded-2xl border p-4 sm:p-6">
        <h3 id="clearance-required" className="dashboard-heading text-lg font-semibold">Clearance required</h3>
        <p className="dashboard-muted text-sm">Onboarding for {status.semester ? periodLabel(status.semester) : 'the active semester'} opens
          after your clearance for {previous ? periodLabel(previous.semester) : 'your previous semester'} is cleared: every required
          signature and the School Admin final approval.</p>
        {previous && <ClearanceList clearance={previous.clearance} title={`Clearance · ${periodLabel(previous.semester)}`} />}
        {previous?.fee && <p className="dashboard-heading text-sm">Organizational fee: <span className="tabular-nums">{peso(previous.fee.amount)}</span> · {previous.fee.status}</p>}
        <InPerson text="If you were not enrolled in a semester in between, ask the School Admin in person to verify it against your official CTU records." />
      </section>);
  }
  const missing = e?.missing_gaps ?? [];
  const title = status.state === 'evidence_conflict' ? 'Your records need review' : 'Official verification needed';
  const body = status.state === 'gap_verification_required'
    ? 'You did not take part in the semesters below in the Workspace. A missing record does not prove you were not enrolled, so the School Admin must verify each one against your official CTU records before onboarding opens. Your earlier clearance and any unpaid fees stay as they are.'
    : status.state === 'history_unverified'
      ? 'Your official record says you are continuing, but the Workspace has no participation for the earlier semesters below. The School Admin must verify them in person.'
      : 'Your official CTU record conflicts with your Workspace history. Visit the School Admin in person.';
  return (
    <section aria-labelledby="verification-needed" className="dashboard-panel space-y-4 rounded-2xl border p-4 sm:p-6">
      <h3 id="verification-needed" className="dashboard-heading text-lg font-semibold">{title}</h3>
      <p className="dashboard-muted text-sm">{body}</p>
      {missing.length > 0 && <ul className="list-disc space-y-1 pl-5 text-sm">{missing.map((p) => <li key={p.semester_id} className="dashboard-heading">{periodLabel(p)}</li>)}</ul>}
      <InPerson text={status.correction_instructions} />
    </section>);
}

function StepList({ step, next, onSelect }: { step: number; next: number; onSelect: (s: number) => void }) {
  return (
    <ol aria-label="Onboarding steps" className="grid gap-2 sm:grid-cols-4">
      {STEPS.map((label, index) => {
        const n = index + 1; const current = n === step; const done = n < next;
        return (
          <li key={label}>
            <button type="button" disabled={n > next} aria-current={current ? 'step' : undefined} onClick={() => onSelect(n)}
              className={`${secondaryButton} w-full justify-start text-left ${current ? 'dashboard-accent' : ''}`}>
              <span aria-hidden="true">{done ? '✓' : n}</span><span>Step {n}: {label}{done ? ' (done)' : ''}</span>
            </button>
          </li>);
      })}
    </ol>
  );
}

function StepType({ draft, onSaved }: { draft: Draft; onSaved: (s: Status) => void }) {
  const [choice, setChoice] = useState<StudentType | ''>(draft.student_type ?? '');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!choice) { setError('Choose Regular or Irregular.'); document.getElementById('student-type-Regular')?.focus(); return; }
    setBusy(true); setFailure(null);
    try { onSaved(await saveStudentType(choice, draft.version)); } catch (e: unknown) { setFailure(e); } finally { setBusy(false); }
  }
  return (
    <form noValidate onSubmit={(e) => void submit(e)} aria-busy={busy} className="space-y-4">
      <fieldset disabled={busy} className="space-y-3">
        <legend className="dashboard-heading font-semibold">Are you a Regular or an Irregular student this semester? *</legend>
        {(['Regular', 'Irregular'] as const).map((value) => (
          <label key={value} className="flex min-h-11 items-start gap-3 rounded-xl border p-3 text-sm">
            <input id={`student-type-${value}`} type="radio" name="student-type" className="mt-1 h-4 w-4" checked={choice === value}
              aria-describedby={error ? 'student-type-error' : undefined} onChange={() => { setChoice(value); setError(''); }} />
            <span><span className="dashboard-heading font-semibold">{value}</span>
              <span className="dashboard-muted block">{value === 'Regular' ? 'You take every subject prepared for your section.'
                : 'You take selected offered subjects of your course.'}</span></span>
          </label>))}
        {error && <p id="student-type-error" className="dashboard-error text-sm">{error}</p>}
      </fieldset>
      {failure !== null && <ErrorBlock error={failure} />}
      <button type="submit" className={primaryButton} disabled={busy}>{busy ? 'Saving…' : 'Save and continue'}</button>
    </form>
  );
}

function CourseFields({ courses, courseId, year, onCourse, onYear, disabled, prefix }: {
  courses: ContextCourse[]; courseId: string; year: string; onCourse: (v: string) => void; onYear: (v: string) => void;
  disabled: boolean; prefix: string }) {
  const years = courses.find((c) => String(c.course_id) === courseId)?.year_levels ?? [1, 2, 3, 4, 5, 6];
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <div><label htmlFor={`${prefix}-course`} className="dashboard-heading mb-1 block text-sm font-medium">Course *</label>
        <select id={`${prefix}-course`} className={fieldClass} value={courseId} disabled={disabled} onChange={(e) => onCourse(e.target.value)}>
          <option value="">Choose your course</option>
          {courses.map((c) => <option key={c.course_id} value={c.course_id}>{c.code} · {c.name}</option>)}
        </select></div>
      <div><label htmlFor={`${prefix}-year`} className="dashboard-heading mb-1 block text-sm font-medium">Year level *</label>
        <select id={`${prefix}-year`} className={fieldClass} value={year} disabled={disabled} onChange={(e) => onYear(e.target.value)}>
          <option value="">Choose your year level</option>
          {years.map((y) => <option key={y} value={y}>Year {y}</option>)}
        </select></div>
    </div>
  );
}

function StepSubjects({ status, draft, courses, onSaved }: { status: Status; draft: Draft; courses: ContextCourse[];
  onSaved: (s: Status) => void }) {
  const regular = draft.student_type === 'Regular';
  const start = draft.course ? { course: String(draft.course.course_id), year: String(draft.year_level ?? '') }
    : status.prefill ? { course: String(status.prefill.course_id), year: String(status.prefill.year_level) } : { course: '', year: '' };
  const [courseId, setCourseId] = useState(start.course);
  const [year, setYear] = useState(start.year);
  const [sectionId, setSectionId] = useState(regular && draft.subjects[0] ? String(draft.subjects[0].section.section_id) : '');
  const [loaded, setLoaded] = useState<{ key: string; options: Option[]; complete: boolean } | null>(null);
  const [selected, setSelected] = useState<number[]>(draft.subjects.map((s) => s.offering_id));
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  const sections = courses.find((c) => String(c.course_id) === courseId)?.sections.filter((s) => String(s.year_level) === year) ?? [];
  // Options belong to exactly one query; a stale answer for another choice is never shown.
  const queryKey = courseId && (!regular || (year && sectionId)) ? `${courseId}|${regular ? `${year}|${sectionId}` : ''}` : '';
  const options = loaded && loaded.key === queryKey ? loaded : null;

  useEffect(() => {
    if (!queryKey) return undefined;
    let cancelled = false;
    getSubjectOptions(regular ? { course_id: Number(courseId), year_level: Number(year), section_id: Number(sectionId) }
      : { course_id: Number(courseId) })
      .then((o) => { if (!cancelled) { setLoaded({ key: queryKey, ...o }); setFailure(null); } })
      .catch((e: unknown) => { if (!cancelled) setFailure(e); });
    return () => { cancelled = true; };
  }, [queryKey, courseId, year, sectionId, regular]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const ids = regular ? (options?.options ?? []).map((o) => o.offering_id) : selected;
    if (!courseId || !year) { setError('Choose your course and year level.'); return; }
    if (regular && !sectionId) { setError('Choose your section.'); return; }
    if (!ids.length) { setError(regular ? 'No subjects are prepared for this section.' : 'Choose at least one subject.'); return; }
    if (!confirmed) { setError('Confirm that this is your subject list.'); document.getElementById('subjects-confirm')?.focus(); return; }
    if (draft.version === null) return;
    setBusy(true); setFailure(null); setError('');
    try { onSaved(await confirmSubjects({ course_id: Number(courseId), year_level: Number(year), offering_ids: ids, expected_version: draft.version })); }
    catch (e: unknown) { setFailure(e); } finally { setBusy(false); }
  }
  const chosenSubjects = new Set((options?.options ?? []).filter((o) => selected.includes(o.offering_id)).map((o) => o.subject.subject_id));
  return (
    <form noValidate onSubmit={(e) => void submit(e)} aria-busy={busy} className="space-y-4">
      <p className="dashboard-muted text-xs">Fields marked * are required.</p>
      <fieldset disabled={busy} className="space-y-4">
        <CourseFields courses={courses} courseId={courseId} year={year} disabled={busy} prefix="subjects"
          onCourse={(v) => { setCourseId(v); setSectionId(''); setSelected([]); setConfirmed(false); setError(''); }}
          onYear={(v) => { setYear(v); setSectionId(''); setConfirmed(false); setError(''); }} />
        {regular && (
          <div><label htmlFor="subjects-section" className="dashboard-heading mb-1 block text-sm font-medium">Section *</label>
            <select id="subjects-section" className={fieldClass} value={sectionId} onChange={(e) => { setSectionId(e.target.value); setConfirmed(false); setError(''); }}>
              <option value="">Choose your section</option>
              {sections.map((s) => <option key={s.section_id} value={s.section_id}>{s.name}</option>)}
            </select></div>)}
        {options && options.options.length === 0 && <p className="dashboard-muted text-sm">No offered subjects match this choice.</p>}
        {options && options.options.length > 0 && (
          <fieldset className="space-y-2">
            <legend className="dashboard-heading text-sm font-semibold">{regular ? 'Subjects prepared for your section' : 'Offered subjects of your course'}</legend>
            {options.options.map((o) => {
              const duplicate = !selected.includes(o.offering_id) && chosenSubjects.has(o.subject.subject_id);
              const units = [o.subject.lecture_units && `${o.subject.lecture_units} lec`, o.subject.lab_units && `${o.subject.lab_units} lab`].filter(Boolean).join(' · ');
              const body = (<span className="min-w-0">
                <span className="dashboard-heading font-semibold">{o.subject.code} · {o.subject.title}</span>
                <span className="dashboard-muted block text-xs">Section {o.section.name} · Year {o.section.year_level}{units ? ` · ${units}` : ''} · {o.instructor ? `Instructor: ${o.instructor}` : 'No instructor assigned yet'}</span>
              </span>);
              return regular
                ? <div key={o.offering_id} className="flex items-start gap-3 rounded-xl border p-3 text-sm">
                    <span aria-hidden="true">{o.ready_for_confirmation ? '●' : '!'}</span>{body}</div>
                : <label key={o.offering_id} className="flex min-h-11 items-start gap-3 rounded-xl border p-3 text-sm">
                    <input type="checkbox" className="mt-1 h-4 w-4" checked={selected.includes(o.offering_id)}
                      disabled={!o.ready_for_confirmation || duplicate}
                      onChange={(e) => { setConfirmed(false); setError(''); setSelected((prev) => e.target.checked ? [...prev, o.offering_id] : prev.filter((x) => x !== o.offering_id)); }} />
                    {body}</label>;
            })}
            {!options.complete && regular && <InPerson text="A prepared subject has no assigned instructor yet. Visit the School Admin in person; you cannot confirm an incomplete list." />}
          </fieldset>)}
        <label className="flex min-h-11 items-center gap-2 text-sm font-medium">
          <input id="subjects-confirm" type="checkbox" className="h-4 w-4" checked={confirmed}
            onChange={(e) => { setConfirmed(e.target.checked); setError(''); }} />
          I confirm this is my subject list for this semester *</label>
        {error && <p role="alert" className="dashboard-error text-sm">{error}</p>}
      </fieldset>
      <p className="dashboard-muted text-xs">{status.correction_instructions}</p>
      {failure !== null && <ErrorBlock error={failure} />}
      <button type="submit" className={primaryButton} disabled={busy || (regular && options !== null && !options.complete)}>
        {busy ? 'Confirming…' : 'Confirm subjects'}</button>
    </form>
  );
}

function StepCourse({ draft, courses, onSaved }: { draft: Draft; courses: ContextCourse[]; onSaved: (s: Status, invalidated: boolean) => void }) {
  const [courseId, setCourseId] = useState(draft.course ? String(draft.course.course_id) : '');
  const [year, setYear] = useState(draft.year_level ? String(draft.year_level) : '');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<unknown>(null);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!courseId || !year) { setError('Choose your course and year level.'); document.getElementById('course-course')?.focus(); return; }
    if (draft.version === null) return;
    setBusy(true); setFailure(null);
    try {
      const next = await confirmCourse({ course_id: Number(courseId), year_level: Number(year), expected_version: draft.version });
      onSaved(next, draft.subjects_confirmed && !next.onboarding?.subjects_confirmed);
    } catch (e: unknown) { setFailure(e); } finally { setBusy(false); }
  }
  return (
    <form noValidate onSubmit={(e) => void submit(e)} aria-busy={busy} className="space-y-4">
      <p className="dashboard-muted text-sm">Check the course and year level shown in your official CTU enrollment. If you change them,
        your subjects must be confirmed again.</p>
      <fieldset disabled={busy}>
        <CourseFields courses={courses} courseId={courseId} year={year} disabled={busy} prefix="course"
          onCourse={(v) => { setCourseId(v); setError(''); }} onYear={(v) => { setYear(v); setError(''); }} />
      </fieldset>
      {error && <p role="alert" className="dashboard-error text-sm">{error}</p>}
      {failure !== null && <ErrorBlock error={failure} />}
      <button type="submit" className={primaryButton} disabled={busy}>{busy ? 'Confirming…' : 'Confirm course and year level'}</button>
    </form>
  );
}

function StepReview({ onDone }: { onDone: (s: Status) => void }) {
  const [review, setReview] = useState<Review | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let cancelled = false;
    getReview().then((r) => { if (cancelled) return; if (r === null) void getStatus().then(onDone); else setReview(r); })
      .catch((e: unknown) => { if (!cancelled) setFailure(e); });
    return () => { cancelled = true; };
  }, [reload, onDone]);
  if (!review) return failure !== null ? <ErrorBlock error={failure} onRetry={() => { setFailure(null); setReload((n) => n + 1); }} />
    : <p role="status" className="dashboard-muted text-sm">Preparing your final review…</p>;
  const draft = review.onboarding;
  async function confirm() {
    if (!review || !confirmed) return;
    setBusy(true); setFailure(null);
    try { onDone(await finalizeOnboarding(review)); }
    catch (e: unknown) {
      setFailure(e);
      if (e instanceof OnboardingApiError && ['fee_changed', 'stale_version', 'subjects_changed'].includes(e.detail.reason)) setConfirmed(false);
    } finally { setBusy(false); }
  }
  const blockerText = review.blockers.includes('feature_disabled') ? 'Confirmation is not enabled on the server yet. Your Draft is saved.'
    : review.blockers.includes('fee_unavailable') ? 'The semester fee is not approved yet, so onboarding cannot be completed. Your Draft is saved.'
      : review.blockers.includes('instructor_unassigned') ? 'A subject has no assigned instructor. Visit the School Admin in person.'
        : review.blockers.includes('eligibility_blocked') ? 'A previous requirement must be resolved first.' : '';
  return (
    <div className="space-y-4">
      <dl className="grid gap-4 text-sm sm:grid-cols-2">
        <div><dt className="dashboard-muted text-xs">Student type</dt><dd className="dashboard-heading font-semibold">{draft.student_type}</dd></div>
        <div><dt className="dashboard-muted text-xs">Course and year level</dt>
          <dd className="dashboard-heading font-semibold">{draft.course?.code} · Year {draft.year_level}</dd></div>
        <div><dt className="dashboard-muted text-xs">School year and semester</dt>
          <dd className="dashboard-heading font-semibold">{periodLabel(review.semester)}</dd></div>
        <div><dt className="dashboard-muted text-xs">Full organizational fee</dt>
          <dd className="dashboard-heading font-semibold tabular-nums">{review.fee ? peso(review.fee.amount) : 'Not approved yet'}</dd></div>
      </dl>
      <ul aria-label="Confirmed subjects" className="space-y-2">{draft.subjects.map((s) => (
        <li key={s.offering_id} className="rounded-xl border p-3 text-sm"><span className="dashboard-heading font-semibold">{s.subject.code} · {s.subject.title}</span>
          <span className="dashboard-muted block text-xs">Section {s.section.name} · {s.instructor ? `Instructor: ${s.instructor}` : 'No instructor assigned'}</span></li>))}
      </ul>
      {review.verification === 'verified'
        ? <p role="status" className="dashboard-success rounded-xl border p-3 text-sm"><span aria-hidden="true" className="mr-2 font-bold">✓</span>
            A verified CTU enrollment record matches these details. Confirming completes your onboarding now.</p>
        : <InPerson text={review.verification === 'mismatch'
            ? `Your verified CTU record differs in: ${review.mismatched.map((m) => MISMATCH_TEXT[m] ?? m).join(', ')}. Confirming records Pending Verification. Visit the School Admin in person.`
            : 'No verified CTU enrollment record is available yet. Confirming records Pending Verification; then visit the School Admin in person.'} />}
      <p className="dashboard-muted text-xs">When your onboarding is completed, one clearance with its required signatures and one full
        organizational-fee obligation of the amount shown are created for this semester. No payment is recorded here.</p>
      {blockerText && <p className="dashboard-muted text-sm">{blockerText}</p>}
      <label className="flex min-h-11 items-center gap-2 text-sm font-medium">
        <input type="checkbox" className="h-4 w-4" checked={confirmed} disabled={busy || !review.can_confirm}
          onChange={(e) => setConfirmed(e.target.checked)} />
        I confirm these details are correct</label>
      {failure !== null && <ErrorBlock error={failure} onRetry={() => { setFailure(null); setReview(null); setReload((n) => n + 1); }} />}
      <button type="button" className={primaryButton} disabled={busy || !confirmed || !review.can_confirm} onClick={() => void confirm()}>
        {busy ? 'Confirming…' : 'Confirm onboarding'}</button>
    </div>
  );
}

function Wizard({ status, onStatus }: { status: Status; onStatus: (s: Status) => void }) {
  const draft = status.onboarding as Draft;
  const [step, setStep] = useState<number>(draft.next_step);
  const [courses, setCourses] = useState<ContextCourse[] | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [notice, setNotice] = useState<Notice>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    let cancelled = false;
    getContext().then((c) => { if (!cancelled) setCourses(c); }).catch((e: unknown) => { if (!cancelled) setFailure(e); });
    return () => { cancelled = true; };
  }, []);
  function saved(next: Status, message?: string) {
    onStatus(next);
    const nextStep = next.onboarding?.next_step ?? 1;
    setStep(nextStep);
    setNotice(message ? { kind: 'success', text: message } : null);
    requestAnimationFrame(() => heading.current?.focus());
  }
  return (
    <section aria-labelledby="onboarding-step" className="dashboard-panel space-y-5 rounded-2xl border p-4 sm:p-6">
      <StepList step={step} next={draft.next_step} onSelect={(n) => { setStep(n); setNotice(null); }} />
      <h3 id="onboarding-step" ref={heading} tabIndex={-1} className="dashboard-heading text-lg font-semibold">Step {step}: {STEPS[step - 1]}</h3>
      <NoticeBlock notice={notice} />
      {failure !== null && <ErrorBlock error={failure} />}
      {step === 1 && <StepType key={draft.version ?? 0} draft={draft} onSaved={(s) => saved(s, 'Student type saved.')} />}
      {step === 2 && courses && <StepSubjects key={draft.version ?? 0} status={status} draft={draft} courses={courses} onSaved={(s) => saved(s, 'Subjects confirmed.')} />}
      {step === 3 && courses && <StepCourse key={draft.version ?? 0} draft={draft} courses={courses} onSaved={(s, invalidated) => saved(s,
        invalidated ? 'Course and year level confirmed. Your subjects no longer match, so confirm them again.' : 'Course and year level confirmed.')} />}
      {(step === 2 || step === 3) && !courses && failure === null && <p role="status" className="dashboard-muted text-sm">Loading courses…</p>}
      {step === 4 && <StepReview onDone={onStatus} />}
    </section>
  );
}

export default function StudentOnboardingPanel() {
  const { navigate } = useDashboardContext();
  const gate = useStudentGate();
  const { apply } = gate;
  const [status, setStatus] = useState<Status | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let cancelled = false;
    getStatus().then((s) => { if (!cancelled) { setStatus(s); setFailure(null); apply(s); } })
      .catch((e: unknown) => { if (!cancelled) setFailure(e); });
    return () => { cancelled = true; };
  }, [reload, apply]);

  /** Every server answer (a step, Pending Verification or completion) also updates the shared boundary. */
  const received = useCallback((next: Status) => {
    setStatus(next);
    apply(next);
    // Successful finalization: open the normal Student dashboard (the boundary is already open).
    if (next.outcome === 'completed' && next.dashboard_route === 'dashboard') navigate('overview');
  }, [apply, navigate]);

  if (failure !== null && !status) return <ErrorBlock error={failure} onRetry={() => setReload((n) => n + 1)} />;
  if (!status) return <p role="status" className="dashboard-muted text-sm">Checking your semester onboarding…</p>;
  if (status.state === 'no_active_semester') {
    return (
      <div className="space-y-5">
        <DashboardState title="No active semester" icon="clipboard">There is no active semester right now, so there is nothing to
          onboard and no semester records are created. Your profile and your historical clearance and fee records stay available.</DashboardState>
        <OwnHistory />
      </div>);
  }
  return (
    <div className="space-y-5">
      <section aria-labelledby="onboarding-period" className="dashboard-panel space-y-4 rounded-2xl border p-4 sm:p-6">
        <h2 id="onboarding-period" className="dashboard-heading text-lg font-semibold">Student Semester Onboarding</h2>
        <Header status={status} />
        <p className="dashboard-muted text-xs">These details come from the active semester and your account; they cannot be edited here.</p>
      </section>
      {status.state === 'completed' && status.result && (
        <section aria-labelledby="onboarding-done" className="dashboard-panel space-y-4 rounded-2xl border p-4 sm:p-6">
          <h3 id="onboarding-done" tabIndex={-1} className="dashboard-heading text-lg font-semibold">Onboarding completed</h3>
          <p role="status" className="dashboard-success rounded-xl border p-3 text-sm"><span aria-hidden="true" className="mr-2 font-bold">✓</span>
            Your semester participation, clearance and organizational fee are recorded. Your dashboard is available.</p>
          <ResultSummary result={status.result} />
          <button type="button" className={secondaryButton} onClick={() => navigate('my-subjects')}>Open my semester</button>
        </section>)}
      {['clearance_required', 'gap_verification_required', 'history_unverified', 'evidence_conflict'].includes(status.state) && <Blocked status={status} />}
      {status.state === 'pending_verification' && (
        <InPerson text="Pending verification: no verified CTU enrollment record matches your confirmed details yet. Visit the School Admin in person with your official enrollment record, then return here and confirm your final review again. Nothing has been billed." />)}
      {(status.state === 'onboarding' || status.state === 'pending_verification') && status.onboarding && (
        <Wizard key={`${status.semester?.semester_id ?? 0}-${status.state}`} status={status} onStatus={received} />)}
      <OwnHistory />
    </div>
  );
}
