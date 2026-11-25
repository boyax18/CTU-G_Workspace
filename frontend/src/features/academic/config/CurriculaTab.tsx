/** Curriculum versions: Course → version → year level → semester → subjects.
 * Draft is editable; publishing is explicit; Published and Superseded versions are read-only history.
 * Writes need the server's curriculum switch (no approved exact permission yet) and this build's flag. */
import { useEffect, useId, useState } from 'react';
import type { FormEvent } from 'react';
import { ACADEMIC_CURRICULUM_WRITES_ENABLED } from '../academicConfigurationConfig.ts';
import {
  addCurriculumEntry, configErrorText, createCurriculum, deleteDraftCurriculum, getCurriculum, listCourses, listCurricula,
  listSubjects, publishCurriculum, removeCurriculumEntry, supersedeCurriculum,
} from '../academicConfigurationApi.ts';
import type { Course, Curriculum, Features, Subject } from '../academicConfigurationApi.ts';
import { compactButton, primaryButton, secondaryButton } from '../academicStyles.ts';
import { ConfirmDialog, FieldGroup, LoadFailure, NoticeBlock, StatusBadge } from './configUi.tsx';
import { TERM_OPTIONS, YEAR_LEVEL_OPTIONS, fieldErrors, toInt } from './configHelpers.ts';
import type { Notice } from './configUi.tsx';

type Pending = { kind: 'publish' | 'supersede' | 'delete' } | { kind: 'remove'; entryId: number; label: string } | null;

function CurriculumDetail({ curriculumId, writable, subjects, onChanged, onDeleted }: {
  curriculumId: number; writable: boolean; subjects: Subject[]; onChanged: (text: string) => void; onDeleted: (text: string) => void;
}) {
  const ids = useId();
  const [state, setState] = useState<{ status: 'loading' } | { status: 'failed'; error: unknown } | { status: 'ready'; data: Curriculum }>({ status: 'loading' });
  const [version, setVersion] = useState(0);
  const [values, setValues] = useState<Record<string, string>>({ term: 'first', year_level: '1' });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [pending, setPending] = useState<Pending>(null);

  useEffect(() => {
    let cancelled = false;
    getCurriculum(curriculumId).then(({ curriculum }) => { if (!cancelled) setState({ status: 'ready', data: curriculum }); })
      .catch((error: unknown) => { if (!cancelled) setState({ status: 'failed', error }); });
    return () => { cancelled = true; };
  }, [curriculumId, version]);

  function reload() { setState({ status: 'loading' }); setVersion((v) => v + 1); }

  if (state.status === 'loading') return <p role="status" className="dashboard-muted mt-4 text-sm">Loading curriculum…</p>;
  if (state.status === 'failed') return <LoadFailure error={state.error} onRetry={reload} />;
  const cur = state.data;
  const editable = writable && cur.can_edit;
  const groups = new Map<string, NonNullable<Curriculum['entries']>>();
  for (const entry of cur.entries ?? []) {
    const key = `Year ${entry.year_level} · ${entry.term === 'first' ? 'First' : 'Second'} semester`;
    groups.set(key, [...(groups.get(key) ?? []), entry]);
  }

  async function addEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setErrors({}); setNotice(null);
    try {
      await addCurriculumEntry(cur.curriculum_id, { subject_id: toInt(values.subject_id), year_level: toInt(values.year_level),
        term: values.term === 'second' ? 'second' : 'first', expected_version: cur.version });
      setValues((v) => ({ ...v, subject_id: '' }));
      setNotice({ kind: 'success', text: 'The subject was added to this Draft curriculum.' });
      reload();
    } catch (error: unknown) {
      const fields = fieldErrors(error);
      if (Object.keys(fields).length) setErrors(fields); else setNotice({ kind: 'error', text: configErrorText(error) });
    } finally { setBusy(false); }
  }

  const subjectOptions = subjects.map((s) => ({ value: String(s.subject_id), label: `${s.code} · ${s.title}` }));
  return (
    <section className="dashboard-panel mt-4 rounded-2xl border p-4 sm:p-5" aria-labelledby={`${ids}-title`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 id={`${ids}-title`} className="dashboard-heading text-base font-semibold">{cur.course.code} · {cur.label}</h3>
          <p className="dashboard-muted text-xs">{cur.course.name}{cur.effective_start_year ? ` · from S.Y. ${cur.effective_start_year}` : ''}
            {' '}· {cur.entry_count} subjects · {cur.offering_count} offerings</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusBadge status={cur.status} />
          {editable && <button type="button" className={compactButton} onClick={() => setPending({ kind: 'publish' })}>Publish</button>}
          {editable && <button type="button" className={compactButton} onClick={() => setPending({ kind: 'delete' })}>Delete draft</button>}
          {writable && cur.status === 'Published' && (
            <button type="button" className={compactButton} onClick={() => setPending({ kind: 'supersede' })}>Mark superseded</button>)}
        </div>
      </div>
      {!cur.can_edit && <p className="dashboard-muted mt-2 text-xs">{cur.status} versions are read-only history. Create a new version to change the plan.</p>}
      <NoticeBlock notice={notice} />
      {groups.size === 0 && <p className="dashboard-muted mt-4 rounded-xl border border-dashed p-4 text-center text-sm">No subjects in this curriculum yet.</p>}
      {[...groups.entries()].map(([group, entries]) => (
        <div key={group} className="mt-4">
          <h4 className="dashboard-eyebrow">{group}</h4>
          <ul aria-label={group} className="mt-2 divide-y">
            {entries.map((entry) => (
              <li key={entry.curriculum_subject_id} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm">
                <span className="dashboard-heading">{entry.subject.code} <span className="dashboard-muted">· {entry.subject.title}</span></span>
                {editable && (
                  <button type="button" className={compactButton}
                    onClick={() => setPending({ kind: 'remove', entryId: entry.curriculum_subject_id, label: entry.subject.code })}>
                    Remove<span className="sr-only"> {entry.subject.code}</span></button>)}
              </li>
            ))}
          </ul>
        </div>
      ))}
      {editable && (
        <form noValidate onSubmit={(e) => void addEntry(e)} className="mt-5 space-y-3 border-t pt-4" aria-label="Add a subject to this curriculum">
          <FieldGroup idPrefix={`${ids}-entry`} disabled={busy} values={values} errors={errors}
            onChange={(name, value) => { setValues((v) => ({ ...v, [name]: value })); setErrors((e) => ({ ...e, [name]: '' })); }}
            fields={[{ name: 'subject_id', label: 'Subject', kind: 'select', options: subjectOptions },
              { name: 'year_level', label: 'Year level', kind: 'select', options: YEAR_LEVEL_OPTIONS },
              { name: 'term', label: 'Semester', kind: 'select', options: TERM_OPTIONS }]} />
          <div className="flex justify-end"><button type="submit" className={primaryButton} disabled={busy}>{busy ? 'Adding…' : 'Add subject'}</button></div>
        </form>
      )}
      {pending?.kind === 'publish' && (
        <ConfirmDialog title="Publish this curriculum?" confirmLabel="Publish curriculum" busyLabel="Publishing…"
          body={<p>After publishing, this version can be used for offerings and can no longer be edited. Existing student
            records are not changed. This action is audited.</p>}
          onClose={() => setPending(null)} confirm={async () => { await publishCurriculum(cur.curriculum_id, cur.version); }}
          onDone={() => { setPending(null); onChanged(`${cur.label} was published.`); reload(); }} />
      )}
      {pending?.kind === 'supersede' && (
        <ConfirmDialog title="Mark this curriculum superseded?" confirmLabel="Mark superseded" busyLabel="Saving…"
          body={<p>The version and its existing offerings stay in history, but no new offerings can use it. This action is audited.</p>}
          onClose={() => setPending(null)} confirm={async () => { await supersedeCurriculum(cur.curriculum_id, cur.version); }}
          onDone={() => { setPending(null); onChanged(`${cur.label} is now superseded.`); reload(); }} />
      )}
      {pending?.kind === 'delete' && (
        <ConfirmDialog title="Delete this Draft curriculum?" destructive confirmLabel="Delete draft" busyLabel="Deleting…"
          body={<p>The unpublished Draft and its subject list are permanently deleted. Its audit history is kept.</p>}
          onClose={() => setPending(null)} confirm={async () => { await deleteDraftCurriculum(cur.curriculum_id, cur.version); }}
          onDone={() => { setPending(null); onDeleted(`${cur.label} was deleted.`); }} />
      )}
      {pending?.kind === 'remove' && (
        <ConfirmDialog title={`Remove ${pending.label}?`} confirmLabel="Remove subject" busyLabel="Removing…"
          body={<p>The subject is removed from this Draft curriculum only. The subject definition is not changed.</p>}
          onClose={() => setPending(null)} confirm={async () => { await removeCurriculumEntry(cur.curriculum_id, pending.entryId, cur.version); }}
          onDone={() => { setPending(null); reload(); }} />
      )}
    </section>
  );
}

export default function CurriculaTab({ canWrite }: { canWrite: boolean }) {
  const ids = useId();
  const [courses, setCourses] = useState<Course[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [list, setList] = useState<{ status: 'loading' } | { status: 'failed'; error: unknown } | { status: 'ready'; data: Curriculum[]; features: Features }>({ status: 'loading' });
  const [version, setVersion] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [creating, setCreating] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);

  useEffect(() => {
    let cancelled = false;
    listCurricula().then((page) => { if (!cancelled) setList({ status: 'ready', data: page.results, features: page.features }); })
      .catch((error: unknown) => { if (!cancelled) setList({ status: 'failed', error }); });
    return () => { cancelled = true; };
  }, [version]);
  useEffect(() => {
    let cancelled = false;
    listCourses({ status: 'Active' }).then((p) => { if (!cancelled) setCourses(p.results); }).catch(() => undefined);
    listSubjects({ status: 'Active' }).then((p) => { if (!cancelled) setSubjects(p.results); }).catch(() => undefined);
    return () => { cancelled = true; };
  }, []);

  const serverWrites = list.status === 'ready' && list.features.curriculum_writes;
  const writable = canWrite && serverWrites && ACADEMIC_CURRICULUM_WRITES_ENABLED;
  function reload() { setList({ status: 'loading' }); setVersion((v) => v + 1); }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true); setErrors({}); setNotice(null);
    try {
      const start = values.effective_start_year?.trim();
      const created = await createCurriculum({ course_id: toInt(values.course_id), label: values.label ?? '',
        effective_start_year: start ? toInt(start) : null });
      setValues({});
      setNotice({ kind: 'success', text: `${created.label} was created as a Draft.` });
      setSelected(created.curriculum_id);
      reload();
    } catch (error: unknown) {
      const fields = fieldErrors(error);
      if (Object.keys(fields).length) setErrors(fields); else setNotice({ kind: 'error', text: configErrorText(error) });
    } finally { setCreating(false); }
  }

  return (
    <div className="space-y-4">
      {list.status === 'ready' && !writable && (
        <p role="status" className="dashboard-warning rounded-xl border p-3 text-sm">
          <span aria-hidden="true" className="mr-2 font-bold">!</span>Curriculum changes are not enabled. Their permission
          mapping is awaiting access-control review, so curricula are read-only here.
        </p>
      )}
      {writable && (
        <section className="dashboard-panel rounded-2xl border p-4 sm:p-5" aria-labelledby={`${ids}-create`}>
          <h3 id={`${ids}-create`} className="dashboard-heading text-base font-semibold">Create a curriculum version</h3>
          <form noValidate onSubmit={(e) => void create(e)} className="mt-3 space-y-3">
            <FieldGroup idPrefix={`${ids}-new`} disabled={creating} values={values} errors={errors}
              onChange={(name, value) => { setValues((v) => ({ ...v, [name]: value })); setErrors((e) => ({ ...e, [name]: '' })); }}
              fields={[{ name: 'course_id', label: 'Course', kind: 'select',
                options: courses.map((c) => ({ value: String(c.course_id), label: `${c.code} · ${c.name}` })) },
              { name: 'label', label: 'Version label', maxLength: 40, hint: 'For example, 2024 Revised.' },
              { name: 'effective_start_year', label: 'First school year (optional)', maxLength: 4, inputMode: 'numeric' }]} />
            <div className="flex justify-end"><button type="submit" className={primaryButton} disabled={creating}>{creating ? 'Creating…' : 'Create draft'}</button></div>
          </form>
        </section>
      )}
      <NoticeBlock notice={notice} />
      <section className="dashboard-panel rounded-2xl border p-4 sm:p-5" aria-labelledby={`${ids}-list`} aria-busy={list.status === 'loading'}>
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <h3 id={`${ids}-list`} className="dashboard-heading text-base font-semibold">Curriculum versions</h3>
            <p className="dashboard-muted mt-1 text-xs">A new version never replaces records students already confirmed.</p>
          </div>
          <button type="button" className={secondaryButton} onClick={reload}>Refresh</button>
        </div>
        {list.status === 'loading' && <p role="status" className="dashboard-muted mt-4 text-sm">Loading curricula…</p>}
        {list.status === 'failed' && <LoadFailure error={list.error} onRetry={reload} />}
        {list.status === 'ready' && list.data.length === 0 && (
          <p className="dashboard-muted mt-4 rounded-xl border border-dashed p-4 text-center text-sm">No curriculum versions yet.</p>)}
        {list.status === 'ready' && list.data.length > 0 && (
          <ul aria-label="Curriculum versions" className="mt-4 divide-y">
            {list.data.map((cur) => (
              <li key={cur.curriculum_id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <span className="text-sm"><span className="dashboard-heading font-semibold">{cur.course.code} · {cur.label}</span>
                  <span className="dashboard-muted"> · {cur.entry_count} subjects</span></span>
                <span className="flex items-center gap-2"><StatusBadge status={cur.status} />
                  <button type="button" className={compactButton} aria-pressed={selected === cur.curriculum_id}
                    onClick={() => setSelected(cur.curriculum_id)}>Open<span className="sr-only"> {cur.course.code} {cur.label}</span></button></span>
              </li>
            ))}
          </ul>
        )}
      </section>
      {selected !== null && (
        <CurriculumDetail key={selected} curriculumId={selected} writable={writable} subjects={subjects}
          onChanged={(text) => { setNotice({ kind: 'success', text }); reload(); }}
          onDeleted={(text) => { setSelected(null); setNotice({ kind: 'success', text }); reload(); }} />
      )}
    </div>
  );
}
