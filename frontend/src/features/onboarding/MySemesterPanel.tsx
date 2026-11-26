/** "My semester": the Student's own current-semester subjects, clearance and organizational fee.
 *
 * Semester-dependent: the shared Student boundary routes a Student here only after finalized
 * onboarding, and the server gates the data itself (``onboarding_required``). If the server still
 * refuses (another tab, a newly activated semester), the boundary is refreshed and re-routes.
 * The historical clearance and fee list stays available in every state (WF11-D17).
 */
import { useEffect, useState } from 'react';
import { DashboardState } from '../../components/dashboard/DashboardStates';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import { secondaryButton } from '../academic/academicStyles.ts';
import OwnHistory from './OwnHistory.tsx';
import { useStudentGate } from './studentGateRules.ts';
import { ResultSummary } from './RecordParts.tsx';
import { OnboardingApiError, getMySemester, onboardingErrorText } from './onboardingApi.ts';
import type { PeriodRef, Result } from './onboardingApi.ts';

type Current = { status: 'loading' } | { status: 'ready'; semester: PeriodRef; result: Result } | { status: 'required' }
  | { status: 'failed'; error: unknown };

export default function MySemesterPanel() {
  const { navigate } = useDashboardContext();
  const gate = useStudentGate();
  const { refresh } = gate;
  const [current, setCurrent] = useState<Current>({ status: 'loading' });
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let cancelled = false;
    getMySemester().then((data) => { if (!cancelled) setCurrent({ status: 'ready', ...data }); }).catch((error: unknown) => {
      if (cancelled) return;
      if (error instanceof OnboardingApiError && error.detail.code === 'onboarding_required') {
        setCurrent({ status: 'required' });
        refresh(); // the server is authoritative: re-read the boundary, which re-routes this view
      } else setCurrent({ status: 'failed', error });
    });
    return () => { cancelled = true; };
  }, [reload, refresh]);

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
      <OwnHistory />
    </div>
  );
}
