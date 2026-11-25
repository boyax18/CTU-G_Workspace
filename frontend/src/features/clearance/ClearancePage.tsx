import { useEffect, useState } from 'react';
import { ApiError, getJSON } from '../../api/client';

interface ClearanceItem {
  id: number;
  office: string;
  status: 'cleared' | 'pending' | 'for_review';
  status_label: string;
  remarks: string;
  updated_at: string;
}

function StatusPill({ status, statusLabel }: { status: ClearanceItem['status']; statusLabel: string }) {
  const styles = {
    cleared: 'border-green-300 bg-green-100 text-green-800',
    pending: 'border-amber-300 bg-amber-100 text-amber-800',
    for_review: 'border-red-300 bg-red-100 text-red-800',
  };
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${styles[status]}`}>
      {statusLabel}
    </span>
  );
}

export default function ClearancePage() {
  const [items, setItems] = useState<ClearanceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    getJSON('/api/v1/clearance/')
      .then((result) => {
        if (!cancelled) setItems(Array.isArray(result) ? result as ClearanceItem[] : []);
      })
      .catch((caught) => {
        if (!cancelled) setError(caught instanceof ApiError ? caught.message : 'Unable to load your clearance.');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const cleared = items.filter((item) => item.status === 'cleared').length;
  const complete = items.length > 0 && cleared === items.length;

  return (
    <div className="space-y-6">
      <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
        <p className="dashboard-eyebrow">Clearance status</p>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
          <h2 className="dashboard-heading text-2xl font-bold">{cleared} / {items.length} offices cleared</h2>
          <span className={`rounded-full border px-3 py-1 text-sm font-semibold ${
            complete ? 'border-green-300 bg-green-100 text-green-800'
              : 'border-amber-300 bg-amber-100 text-amber-800'
          }`}>
            {loading ? 'Checking...' : complete ? 'Complete' : 'Incomplete'}
          </span>
        </div>
      </section>
      {loading && <p className="dashboard-muted text-sm" role="status">Loading clearance items...</p>}
      {error && <div className="dashboard-panel rounded-xl border px-4 py-3 text-sm" role="alert">{error}</div>}
      {!loading && !error && items.length === 0 && (
        <p className="dashboard-muted text-sm">No clearance items have been assigned to you.</p>
      )}
      {!loading && !error && items.length > 0 && (
        <section className="dashboard-panel overflow-x-auto rounded-2xl border p-5 sm:p-6">
          <table className="w-full min-w-[680px] border-collapse text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="px-3 py-3">Office</th><th className="px-3 py-3">Status</th>
                <th className="px-3 py-3">Remarks</th><th className="px-3 py-3">Last updated</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b last:border-0">
                  <td className="dashboard-heading px-3 py-3 font-medium">{item.office}</td>
                  <td className="px-3 py-3"><StatusPill status={item.status} statusLabel={item.status_label} /></td>
                  <td className="dashboard-muted px-3 py-3">{item.remarks || '-'}</td>
                  <td className="dashboard-muted px-3 py-3">
                    {Number.isNaN(Date.parse(item.updated_at)) ? '-' : new Date(item.updated_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
