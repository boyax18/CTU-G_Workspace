import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError } from '../../api/client';
import { getFinanceSummary, submitPayment } from './api';
import type { FinanceSummary, Payment } from './api';

const money = (value: string | number) =>
  new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' }).format(Number(value));

function StatusPill({ status }: { status: Payment['status'] }) {
  return (
    <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${
      status === 'verified'
        ? 'border-green-300 bg-green-100 text-green-800'
        : 'border-amber-300 bg-amber-100 text-amber-800'
    }`}>
      {status === 'verified' ? 'Verified' : 'Pending verification'}
    </span>
  );
}

export default function FinancePage() {
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [amount, setAmount] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    try {
      setSummary(await getFinanceSummary());
      setError('');
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to load finance information.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsed = Number(amount);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError('Amount must be greater than zero.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      await submitPayment(parsed);
      setAmount('');
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to submit payment.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && <div className="dashboard-panel rounded-xl border px-4 py-3 text-sm" role="alert">{error}</div>}
      {loading ? (
        <p className="dashboard-muted text-sm" role="status">Loading finance information...</p>
      ) : summary ? (
        <>
          <section className="grid gap-4 sm:grid-cols-3" aria-label="Finance summary">
            {[
              ['Total assessment', summary.total],
              ['Paid', summary.paid],
              ['Balance', summary.balance],
            ].map(([label, value]) => (
              <article key={String(label)} className="dashboard-panel rounded-2xl border p-5">
                <p className="dashboard-muted text-sm">{label}</p>
                <p className="dashboard-heading mt-2 text-2xl font-bold">{money(String(value))}</p>
              </article>
            ))}
          </section>

          <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
            <h2 className="dashboard-heading text-lg font-semibold">Submit payment</h2>
            <form className="mt-4 flex flex-col gap-3 sm:flex-row" onSubmit={onSubmit} noValidate>
              <label className="dashboard-heading flex-1 text-sm font-medium">
                Amount
                <input
                  type="number"
                  min="0.01"
                  step="0.01"
                  className="mt-2 w-full rounded-lg border px-3 py-2"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                  placeholder="0.00"
                />
              </label>
              <button
                type="submit"
                disabled={submitting || !amount}
                className="mt-auto min-h-11 rounded-lg bg-green-700 px-5 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                {submitting ? 'Submitting...' : 'Submit payment'}
              </button>
            </form>
          </section>

          <section className="dashboard-panel overflow-x-auto rounded-2xl border p-5 sm:p-6">
            <h2 className="dashboard-heading text-lg font-semibold">Payment history</h2>
            {summary.payments.length === 0 ? (
              <p className="dashboard-muted mt-3 text-sm">No payments submitted yet.</p>
            ) : (
              <table className="mt-4 w-full min-w-[600px] border-collapse text-sm">
                <thead>
                  <tr className="border-b text-left">
                    <th className="px-3 py-3">Reference</th>
                    <th className="px-3 py-3">Amount</th>
                    <th className="px-3 py-3">Status</th>
                    <th className="px-3 py-3">Submitted</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.payments.map((payment) => (
                    <tr key={payment.id} className="border-b last:border-0">
                      <td className="dashboard-heading px-3 py-3 font-medium">{payment.reference}</td>
                      <td className="px-3 py-3">{money(payment.amount)}</td>
                      <td className="px-3 py-3"><StatusPill status={payment.status} /></td>
                      <td className="dashboard-muted px-3 py-3">
                        {Number.isNaN(Date.parse(payment.created_at)) ? '-' : new Date(payment.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
