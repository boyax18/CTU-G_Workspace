/** "My semester": the Student's own current-semester subjects, clearance and organizational fee.
 *
 * The data is gated on the backend: until onboarding is finalized for the Active semester the server
 * answers ``onboarding_required`` and this view offers the onboarding instead (no redirect). The
 * historical clearance and fee list stays available in every state (WF11-D17).
 */
import { useEffect, useState } from 'react';
import { DashboardState } from '../../components/dashboard/DashboardStates';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import { secondaryButton } from '../academic/academicStyles.ts';
import { ClearanceList, ResultSummary } from './StudentOnboardingPanel.tsx';
import { OnboardingApiError, getMyHistory, getMySemester, onboardingErrorText, peso } from './onboardingApi.ts';
import type { PeriodRef, Result } from './onboardingApi.ts';

type Current = { status: 'loading' } | { status: 'ready'; semester: PeriodRef; result: Result } | { status: 'required' }
  | { status: 'failed'; error: unknown };
type History = Awaited<ReturnType<typeof getMyHistory>>;

export default function MySemesterPanel() {
  const { navigate } = useDashboardContext();
  const [current, setCurrent] = useState<Current>({ status: 'loading' });
  const [history, setHistory] = useState<History | null>(null);
  const [historyError, setHistoryError] = useState<unknown>(null);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let cancelled = false;
    getMySemester().then((data) => { if (!cancelled) setCurrent({ status: 'ready', ...data }); }).catch((error: unknown) => {
      if (cancelled) return;
      if (error instanceof OnboardingApiError && error.detail.code === 'onboarding_required') setCurrent({ status: 'required' });
      else setCurrent({ status: 'failed', error });
    });
    getMyHistory().then((rows) => { if (!cancelled) setHistory(rows); }).catch((error: unknown) => { if (!cancelled) setHistoryError(error); });
    return () => { cancelled = true; };
  }, [reload]);

  return (
    <div className="space-y-5">
      {current.status === 'loading' && <p role="status" className="dashboard-muted text-sm">Loading your semester…</p>}
      {current.status === 'failed' && (
        <div role="alert" className="dashboard-error-block rounded-xl border p-4 text-sm">
          <p><span aria-hidden="true" className="mr-2 font-bold">!</span>{onboardingErrorText(current.error)}</p>
          <button type="button" className={`${secondaryButton} mt-3`} onClick={() => { setCurrent({ status: 'loading' }); setReload((n) => n + 1); }}>Try again</button>
        </div>)}
      {current.status === 'required' && (
        <DashboardState title="Complete Student Semester Onboarding first" icon="clipboard"
          action={{ label: 'Open semester onboarding', onClick: () => navigate('semester-onboarding') }}>
          Your subjects, clearance and organizational fee for the active semester appear here after your onboarding is completed.
        </DashboardState>)}
      {current.status === 'ready' && (
        <section aria-labelledby="my-semester" className="dashboard-panel space-y-4 rounded-2xl border p-4 sm:p-6">
          <h2 id="my-semester" className="dashboard-heading text-lg font-semibold">{current.semester.label}, S.Y. {current.semester.school_year_label}</h2>
          <ResultSummary result={current.result} level={3} />
        </section>)}
      <section aria-labelledby="my-history" className="dashboard-panel space-y-4 rounded-2xl border p-4 sm:p-6">
        <h2 id="my-history" className="dashboard-heading text-lg font-semibold">Clearance and fee history</h2>
        {historyError !== null && <p role="alert" className="dashboard-error-block rounded-xl border p-3 text-sm">
          <span aria-hidden="true" className="mr-2 font-bold">!</span>{onboardingErrorText(historyError)}</p>}
        {history === null && historyError === null && <p role="status" className="dashboard-muted text-sm">Loading your history…</p>}
        {history !== null && history.length === 0 && <p className="dashboard-muted text-sm">No semester participation is recorded yet.</p>}
        {history !== null && history.length > 0 && (
          <ol className="space-y-4">{history.map((row) => (
            <li key={row.semester.semester_id} className="space-y-2 rounded-xl border p-3">
              <p className="dashboard-heading font-semibold">{row.semester.label}, S.Y. {row.semester.school_year_label} · {row.course_code} Year {row.year_level}</p>
              <p className="dashboard-muted text-sm">Organizational fee: {row.fee ? <span className="tabular-nums">{peso(row.fee.amount)} · {row.fee.status}</span> : 'Not assessed'}</p>
              <ClearanceList clearance={row.clearance} title="Clearance" level={3} />
            </li>))}</ol>)}
      </section>
    </div>
  );
}
