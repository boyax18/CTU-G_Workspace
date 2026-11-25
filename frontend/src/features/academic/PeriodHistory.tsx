/** WF-11.01 school-year history (read-only, newest first). Text comes from fixed labels, except the
 * School Admin's own correction note. No account identifiers are ever shown. */
import { useEffect, useState } from 'react';
import { getSchoolYearHistory } from './academicLifecycleApi.ts';
import { REASON_LABELS } from './academicLifecycleContract.ts';
import type { HistoryEntry, ReasonCode } from './academicLifecycleContract.ts';
import { compactButton, formatDate, formatDateTime, secondaryButton } from './academicStyles.ts';

type Load = { status: 'loading' } | { status: 'failed' } | { status: 'ready'; entries: HistoryEntry[]; hasNext: boolean };

const FIELD_LABELS = { start_date: 'Start date', end_date: 'End date', status: 'Status' } as const;
const show = (field: keyof typeof FIELD_LABELS, value: string | null) =>
  field === 'status' ? (value ?? 'None') : formatDate(value);

export default function PeriodHistory({ schoolYearId, label }: { schoolYearId: number; label: string }) {
  const [page, setPage] = useState(1);
  const [retry, setRetry] = useState(0);
  const [load, setLoad] = useState<Load>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;
    getSchoolYearHistory(schoolYearId, page)
      .then((data) => {
        if (cancelled) return;
        setLoad((current) => ({ status: 'ready', hasNext: data.has_next,
          entries: page > 1 && current.status === 'ready' ? [...current.entries, ...data.results] : data.results }));
      })
      .catch(() => { if (!cancelled) setLoad({ status: 'failed' }); });
    return () => { cancelled = true; };
  }, [schoolYearId, page, retry]);

  return (
    <section className="mt-4 border-t pt-4" aria-label={`History of S.Y. ${label}`} aria-busy={load.status === 'loading'}>
      <h4 className="dashboard-heading text-sm font-semibold">History</h4>
      {load.status === 'loading' && page === 1 && <p role="status" className="dashboard-muted mt-2 text-sm">Loading history…</p>}
      {load.status === 'failed' && (
        <div role="alert" className="dashboard-error-block mt-2 rounded-xl border p-3 text-sm">
          <p><span aria-hidden="true" className="mr-2 font-bold">!</span>The history could not be loaded.</p>
          <button type="button" className={`${secondaryButton} mt-2`} onClick={() => { setLoad({ status: 'loading' }); setPage(1); setRetry((r) => r + 1); }}>Try again</button>
        </div>
      )}
      {load.status === 'ready' && load.entries.length === 0 && <p className="dashboard-muted mt-2 text-sm">No history recorded yet.</p>}
      {load.status === 'ready' && load.entries.length > 0 && (
        <ol className="mt-2 space-y-3">
          {load.entries.map((entry, index) => (
            <li key={`${entry.occurred_at}-${index}`} className="rounded-xl border p-3 text-sm">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <p className="dashboard-heading font-semibold">
                  {entry.description}{entry.semester && <span className="dashboard-muted font-normal"> · {entry.semester === 'first' ? 'First semester' : 'Second semester'}</span>}
                </p>
                <p className="dashboard-muted text-xs">{formatDateTime(entry.occurred_at)} · {entry.actor}</p>
              </div>
              {Object.keys(entry.changes).length > 0 && (
                <dl className="mt-2 grid gap-1 text-xs sm:grid-cols-3">
                  {(Object.entries(entry.changes) as [keyof typeof FIELD_LABELS, { before: string | null; after: string | null }][]).map(([field, change]) => (
                    <div key={field}>
                      <dt className="dashboard-muted">{FIELD_LABELS[field]}</dt>
                      <dd className="dashboard-heading">{show(field, change.before)} → {show(field, change.after)}</dd>
                    </div>
                  ))}
                </dl>
              )}
              {entry.reason && entry.reason in REASON_LABELS && (
                <p className="dashboard-muted mt-2 text-xs">Reason: {REASON_LABELS[entry.reason as ReasonCode]}</p>
              )}
              {entry.note && <p className="dashboard-heading mt-1 text-xs break-words">“{entry.note}”</p>}
            </li>
          ))}
        </ol>
      )}
      {load.status === 'ready' && load.hasNext && (
        <button type="button" className={`${compactButton} mt-3`} onClick={() => setPage((p) => p + 1)}>Show older entries</button>
      )}
    </section>
  );
}
