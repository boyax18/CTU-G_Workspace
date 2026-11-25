/** Shared pieces of the Academic settings tabs (dashboard surface, docs/design COMPONENTS §2–§6). */
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import Modal from '../../../components/common/Modal.tsx';
import { ConfigApiError, configErrorText } from '../academicConfigurationApi.ts';
import type { DefinitionStatus, Page } from '../academicConfigurationApi.ts';
import { fieldErrors } from './configHelpers.ts';
import { badgeClass, compactButton, destructiveButton, fieldClass, primaryButton, secondaryButton } from '../academicStyles.ts';

export type Notice = { kind: 'success' | 'error'; text: string } | null;

export function StatusBadge({ status }: { status: string }) {
  const marks: Record<string, string> = { Active: '●', Inactive: '○', Retired: '▣', Draft: '○', Published: '●', Superseded: '▣',
    Closed: '■', Archived: '▣' };
  const tone = status === 'Active' || status === 'Published' ? 'dashboard-accent'
    : status === 'Draft' || status === 'Inactive' ? 'dashboard-muted border-dashed' : 'dashboard-heading';
  return <span className={`${badgeClass} ${tone}`}><span aria-hidden="true">{marks[status] ?? '•'}</span>{status}</span>;
}

export function NoticeBlock({ notice }: { notice: Notice }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { if (notice?.kind === 'error') ref.current?.focus(); }, [notice]);
  if (!notice) return null;
  return (
    <div ref={ref} tabIndex={-1} role={notice.kind === 'error' ? 'alert' : 'status'}
      className={`${notice.kind === 'error' ? 'dashboard-error-block' : 'dashboard-success'} rounded-xl border p-3 text-sm`}>
      <span aria-hidden="true" className="mr-2 font-bold">{notice.kind === 'error' ? '!' : '✓'}</span>{notice.text}
    </div>
  );
}

export function LoadFailure({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const detail = error instanceof ConfigApiError ? error.detail : null;
  const denied = detail?.code === 'access_denied';
  return (
    <div role="alert" className="dashboard-error-block mt-4 rounded-xl border p-4 text-sm">
      <p className="font-semibold"><span aria-hidden="true" className="mr-2">!</span>
        {denied ? 'Permission denied' : detail?.code === 'academic_configuration_unavailable' ? 'Academic configuration is unavailable' : 'This list could not be loaded'}</p>
      <p className="mt-1">{configErrorText(error)}</p>
      {!denied && <button type="button" className={`${secondaryButton} mt-3`} onClick={onRetry}>Try again</button>}
    </div>
  );
}

export interface FieldSpec {
  name: string;
  label: string;
  kind?: 'text' | 'select';
  options?: { value: string; label: string }[];
  maxLength?: number;
  hint?: string;
  inputMode?: 'numeric' | 'decimal' | 'text';
  locked?: boolean;
}

type Values = Record<string, string>;

/** A small labelled form used by create panels and edit dialogs; server field errors appear inline. */
export function FieldGroup({ fields, values, errors, disabled, onChange, idPrefix }: {
  fields: FieldSpec[]; values: Values; errors: Record<string, string>; disabled: boolean;
  onChange: (name: string, value: string) => void; idPrefix: string;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {fields.map((field) => {
        const id = `${idPrefix}-${field.name}`;
        const describedBy = errors[field.name] ? `${id}-error` : field.hint ? `${id}-hint` : undefined;
        const common = { id, disabled: disabled || field.locked, 'aria-invalid': errors[field.name] ? true : undefined,
          'aria-describedby': describedBy, className: fieldClass };
        return (
          <div key={field.name} className="min-w-0">
            <label htmlFor={id} className="dashboard-muted mb-1 block text-xs font-medium">{field.label}</label>
            {field.kind === 'select' ? (
              <select {...common} value={values[field.name] ?? ''} onChange={(e) => onChange(field.name, e.target.value)}>
                <option value="">Choose…</option>
                {field.options?.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            ) : (
              <input {...common} value={values[field.name] ?? ''} maxLength={field.maxLength} inputMode={field.inputMode}
                autoComplete="off" onChange={(e) => onChange(field.name, e.target.value)} />
            )}
            {errors[field.name]
              ? <p id={`${id}-error`} className="dashboard-error mt-1 text-xs">{errors[field.name]}</p>
              : field.hint ? <p id={`${id}-hint`} className="dashboard-muted mt-1 text-xs">{field.hint}</p> : null}
          </div>
        );
      })}
    </div>
  );
}


const STATUS_ACTIONS: Record<DefinitionStatus, { status: DefinitionStatus; label: string }[]> = {
  Active: [{ status: 'Inactive', label: 'Make inactive' }, { status: 'Retired', label: 'Retire' }],
  Inactive: [{ status: 'Active', label: 'Make active' }, { status: 'Retired', label: 'Retire' }],
  Retired: [],
};

export interface DefinitionTabProps<T> {
  noun: string;                 // "course"
  title: string;                // "Courses"
  description: string;
  canWrite: boolean;
  searchLabel?: string;
  load: (query: { q?: string; page?: number }) => Promise<Page<T>>;
  keyOf: (item: T) => number;
  labelOf: (item: T) => string;
  statusOf: (item: T) => DefinitionStatus;
  versionOf: (item: T) => number;
  summary: (item: T) => ReactNode;
  createFields: FieldSpec[];
  editFields: (item: T) => FieldSpec[];
  valuesOf: (item: T) => Values;
  create: (values: Values) => Promise<T>;
  update: (item: T, values: Values) => Promise<T>;
  setStatus: (item: T, status: DefinitionStatus) => Promise<T>;
  lockedNote?: (item: T) => string | null;
}

/** List + search + create + edit + audited status changes for one definition type. */
export function DefinitionTab<T>(props: DefinitionTabProps<T>) {
  const ids = useId();
  const [query, setQuery] = useState('');
  const [applied, setApplied] = useState('');
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [state, setState] = useState<{ status: 'loading' } | { status: 'failed'; error: unknown } | { status: 'ready'; data: Page<T> }>({ status: 'loading' });
  const [notice, setNotice] = useState<Notice>(null);
  const [createValues, setCreateValues] = useState<Values>({});
  const [createErrors, setCreateErrors] = useState<Record<string, string>>({});
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<T | null>(null);
  const [statusChange, setStatusChange] = useState<{ item: T; status: DefinitionStatus } | null>(null);
  const { load } = props;

  useEffect(() => {
    let cancelled = false;
    load({ q: applied || undefined, page })
      .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
      .catch((error: unknown) => { if (!cancelled) setState({ status: 'failed', error }); });
    return () => { cancelled = true; };
  }, [load, applied, page, version]);

  function reload() { setState({ status: 'loading' }); setVersion((v) => v + 1); }

  async function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setNotice(null);
    setCreateErrors({});
    try {
      const created = await props.create(createValues);
      setCreateValues({});
      setNotice({ kind: 'success', text: `${props.labelOf(created)} was added. This change is audited.` });
      reload();
    } catch (error: unknown) {
      const fields = fieldErrors(error);
      if (Object.keys(fields).length) setCreateErrors(fields);
      else setNotice({ kind: 'error', text: configErrorText(error) });
    } finally {
      setCreating(false);
    }
  }

  const rows = state.status === 'ready' ? state.data.results : [];
  return (
    <div className="space-y-4">
      {props.canWrite && (
        <section className="dashboard-panel rounded-2xl border p-4 sm:p-5" aria-labelledby={`${ids}-create`}>
          <h3 id={`${ids}-create`} className="dashboard-heading text-base font-semibold">Add a {props.noun}</h3>
          <form noValidate onSubmit={(e) => void submitCreate(e)} className="mt-3 space-y-3">
            <FieldGroup idPrefix={`${ids}-new`} fields={props.createFields} values={createValues} errors={createErrors}
              disabled={creating} onChange={(name, value) => { setCreateValues((v) => ({ ...v, [name]: value }));
                setCreateErrors((e) => ({ ...e, [name]: '' })); }} />
            <div className="flex justify-end">
              <button type="submit" className={primaryButton} disabled={creating}>{creating ? 'Adding…' : `Add ${props.noun}`}</button>
            </div>
          </form>
        </section>
      )}
      <NoticeBlock notice={notice} />
      <section className="dashboard-panel rounded-2xl border p-4 sm:p-5" aria-labelledby={`${ids}-list`} aria-busy={state.status === 'loading'}>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 id={`${ids}-list`} className="dashboard-heading text-base font-semibold">{props.title}</h3>
            <p className="dashboard-muted mt-1 text-xs">{props.description}</p>
          </div>
          {props.searchLabel && (
            <form role="search" aria-label={props.title} className="flex flex-wrap items-end gap-2"
              onSubmit={(e) => { e.preventDefault(); setPage(1); setApplied(query.trim()); reload(); }}>
              <label className="dashboard-muted flex flex-col gap-1 text-xs font-medium">{props.searchLabel}
                <input type="search" value={query} maxLength={50} onChange={(e) => setQuery(e.target.value)} className={`${fieldClass} sm:w-56`} />
              </label>
              <button type="submit" className={secondaryButton}>Search</button>
            </form>
          )}
        </div>
        {state.status === 'loading' && <p role="status" className="dashboard-muted mt-4 text-sm">Loading {props.title.toLowerCase()}…</p>}
        {state.status === 'failed' && <LoadFailure error={state.error} onRetry={reload} />}
        {state.status === 'ready' && rows.length === 0 && (
          <p className="dashboard-muted mt-4 rounded-xl border border-dashed p-4 text-center text-sm">
            {applied ? 'Nothing matches this search.' : `No ${props.noun}s yet.`}</p>
        )}
        {rows.length > 0 && (
          <ul aria-label={props.title} className="mt-4 divide-y">
            {rows.map((item) => {
              const status = props.statusOf(item);
              const label = props.labelOf(item);
              return (
                <li key={props.keyOf(item)} className="flex flex-wrap items-start justify-between gap-3 py-3">
                  <div className="min-w-0 flex-1">{props.summary(item)}</div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={status} />
                    {props.canWrite && status !== 'Retired' && (
                      <button type="button" className={compactButton} onClick={() => { setNotice(null); setEditing(item); }}>
                        Edit<span className="sr-only"> {label}</span></button>
                    )}
                    {props.canWrite && STATUS_ACTIONS[status].map((action) => (
                      <button key={action.status} type="button" className={compactButton}
                        onClick={() => { setNotice(null); setStatusChange({ item, status: action.status }); }}>
                        {action.label}<span className="sr-only"> {label}</span></button>
                    ))}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
        {state.status === 'ready' && (page > 1 || state.data.has_next) && (
          <nav aria-label={`${props.title} pages`} className="mt-3 flex items-center justify-end gap-3">
            <button type="button" className={compactButton} disabled={page <= 1} onClick={() => { setPage((p) => p - 1); reload(); }}>Previous</button>
            <span className="dashboard-muted text-xs">Page {page}</span>
            <button type="button" className={compactButton} disabled={!state.data.has_next} onClick={() => { setPage((p) => p + 1); reload(); }}>Next</button>
          </nav>
        )}
      </section>
      {editing && (
        <EditDialog key={props.keyOf(editing)} title={`Edit ${props.labelOf(editing)}?`} fields={props.editFields(editing)}
          initial={props.valuesOf(editing)} note={props.lockedNote?.(editing) ?? null}
          onClose={() => setEditing(null)} save={(values) => props.update(editing, values)}
          onSaved={(saved) => { setEditing(null); setNotice({ kind: 'success', text: `${props.labelOf(saved)} was updated. This change is audited.` }); reload(); }} />
      )}
      {statusChange && (
        <StatusDialog noun={props.noun} label={props.labelOf(statusChange.item)} status={statusChange.status}
          onClose={() => setStatusChange(null)} confirm={() => props.setStatus(statusChange.item, statusChange.status)}
          onDone={(text) => { setStatusChange(null); setNotice({ kind: 'success', text }); reload(); }} />
      )}
    </div>
  );
}

function EditDialog<T>({ title, fields, initial, note, onClose, save, onSaved }: {
  title: string; fields: FieldSpec[]; initial: Values; note: string | null; onClose: () => void;
  save: (values: Values) => Promise<T>; onSaved: (saved: T) => void;
}) {
  const ids = useId();
  const [values, setValues] = useState<Values>(initial);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [failure, setFailure] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setFailure(''); setErrors({});
    try { onSaved(await save(values)); } catch (error: unknown) {
      const found = fieldErrors(error);
      if (Object.keys(found).length) setErrors(found); else setFailure(configErrorText(error));
    } finally { setBusy(false); }
  }

  return (
    <Modal open title={title} busy={busy} onClose={onClose} actions={<>
      <button type="button" className={secondaryButton} disabled={busy} onClick={onClose}>Cancel</button>
      <button type="submit" form={`${ids}-form`} className={primaryButton} disabled={busy}>{busy ? 'Saving…' : 'Save changes'}</button>
    </>}>
      <form id={`${ids}-form`} noValidate onSubmit={(e) => void submit(e)} className="space-y-3">
        {note && <p className="dashboard-muted text-xs">{note}</p>}
        <FieldGroup idPrefix={ids} fields={fields} values={values} errors={errors} disabled={busy}
          onChange={(name, value) => { setValues((v) => ({ ...v, [name]: value })); setErrors((e) => ({ ...e, [name]: '' })); }} />
        <p className="dashboard-muted text-xs">Saving is audited with your account.</p>
        {failure && <p role="alert" className="dashboard-error-block rounded-xl border p-3"><span aria-hidden="true" className="mr-2 font-bold">!</span>{failure}</p>}
      </form>
    </Modal>
  );
}

function StatusDialog<T>({ noun, label, status, onClose, confirm, onDone }: {
  noun: string; label: string; status: DefinitionStatus; onClose: () => void; confirm: () => Promise<T>; onDone: (text: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  const retire = status === 'Retired';
  const verb = retire ? 'Retire' : status === 'Inactive' ? 'Make inactive' : 'Make active';
  async function run() {
    setBusy(true); setFailure('');
    try {
      await confirm();
      onDone(`${label} is now ${status.toLowerCase()}. This change is audited.`);
    } catch (error: unknown) { setFailure(configErrorText(error)); } finally { setBusy(false); }
  }
  return (
    <Modal open title={`${verb}: ${label}?`} busy={busy} onClose={onClose} actions={<>
      <button type="button" className={secondaryButton} disabled={busy} onClick={onClose}>Cancel</button>
      <button type="button" className={retire ? destructiveButton : primaryButton} disabled={busy} onClick={() => void run()}>
        {busy ? 'Saving…' : verb}</button>
    </>}>
      <p>{retire
        ? `A retired ${noun} stays in every existing record and in history, but it can never be used again.`
        : status === 'Inactive' ? `An inactive ${noun} stays in existing records but cannot be used for new configuration.`
          : `The ${noun} becomes available for new configuration again.`} This change is audited.</p>
      {failure && <p role="alert" className="dashboard-error-block rounded-xl border p-3"><span aria-hidden="true" className="mr-2 font-bold">!</span>{failure}</p>}
    </Modal>
  );
}

/** Generic confirmation dialog for curriculum and offering actions. */
export function ConfirmDialog({ title, body, confirmLabel, busyLabel, destructive = false, confirmDisabled = false, onClose, confirm, onDone }: {
  title: string; body: ReactNode; confirmLabel: string; busyLabel: string; destructive?: boolean; confirmDisabled?: boolean;
  onClose: () => void; confirm: () => Promise<void>; onDone: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState('');
  async function run() {
    setBusy(true); setFailure('');
    try { await confirm(); onDone(); } catch (error: unknown) { setFailure(configErrorText(error)); } finally { setBusy(false); }
  }
  return (
    <Modal open title={title} busy={busy} onClose={onClose} actions={<>
      <button type="button" className={secondaryButton} disabled={busy} onClick={onClose}>Cancel</button>
      <button type="button" className={destructive ? destructiveButton : primaryButton} disabled={busy || confirmDisabled} onClick={() => void run()}>
        {busy ? busyLabel : confirmLabel}</button>
    </>}>
      {body}
      {failure && <p role="alert" className="dashboard-error-block rounded-xl border p-3"><span aria-hidden="true" className="mr-2 font-bold">!</span>{failure}</p>}
    </Modal>
  );
}
