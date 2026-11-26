/** The Student's own historical clearance and organizational-fee records (WF11-D17: always available,
 * including while onboarding, Clearance Required or Pending Verification blocks the semester dashboard).
 */
import { useEffect, useState } from 'react';
import { ClearanceList } from './RecordParts.tsx';
import { getMyHistory, onboardingErrorText, peso } from './onboardingApi.ts';

type History = Awaited<ReturnType<typeof getMyHistory>>;

export default function OwnHistory() {
  const [history, setHistory] = useState<History | null>(null);
  const [failure, setFailure] = useState<unknown>(null);
  useEffect(() => {
    let cancelled = false;
    getMyHistory().then((rows) => { if (!cancelled) setHistory(rows); }).catch((error: unknown) => { if (!cancelled) setFailure(error); });
    return () => { cancelled = true; };
  }, []);
  return (
    <section aria-labelledby="my-history" className="dashboard-panel space-y-4 rounded-2xl border p-4 sm:p-6">
      <h2 id="my-history" className="dashboard-heading text-lg font-semibold">Clearance and fee history</h2>
      {failure !== null && <p role="alert" className="dashboard-error-block rounded-xl border p-3 text-sm">
        <span aria-hidden="true" className="mr-2 font-bold">!</span>{onboardingErrorText(failure)}</p>}
      {history === null && failure === null && <p role="status" className="dashboard-muted text-sm">Loading your history…</p>}
      {history !== null && history.length === 0 && <p className="dashboard-muted text-sm">No semester participation is recorded yet.</p>}
      {history !== null && history.length > 0 && (
        <ol className="space-y-4">{history.map((row) => (
          <li key={row.semester.semester_id} className="space-y-2 rounded-xl border p-3">
            <p className="dashboard-heading font-semibold">{row.semester.label}, S.Y. {row.semester.school_year_label} · {row.course_code} Year {row.year_level}</p>
            <p className="dashboard-muted text-sm">Organizational fee: {row.fee ? <span className="tabular-nums">{peso(row.fee.amount)} · {row.fee.status}</span> : 'Not assessed'}</p>
            <ClearanceList clearance={row.clearance} title="Clearance" level={3} />
          </li>))}</ol>)}
    </section>
  );
}
