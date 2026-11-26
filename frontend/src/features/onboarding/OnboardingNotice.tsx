/** Overview notice from the shared Student boundary (no separate request).
 *
 * A Student-only session never sees the overview before completion: the boundary routes it to
 * Semester onboarding. A multi-role session without role context keeps its other modules and sees
 * this notice instead. After a successful finalization it confirms the completion once.
 */
import { useEffect } from 'react';
import { secondaryButton } from '../academic/academicStyles.ts';
import { useStudentGate } from './studentGateRules.ts';
import type { DashboardRoute } from './onboardingApi.ts';

const TEXT: Partial<Record<DashboardRoute, { title: string; body: string; action: string }>> = {
  onboarding: { title: 'Complete your semester onboarding', action: 'Open semester onboarding',
    body: 'Confirm your student type, subjects, course and year level for the active semester. Your semester records open when it is completed.' },
  clearance_required: { title: 'Clearance required', action: 'View clearance requirement',
    body: 'Your previous semester clearance must be cleared before you can onboard for the active semester.' },
  verification_required: { title: 'Official verification needed', action: 'View what is needed',
    body: 'The School Admin must verify your official CTU records in person before onboarding opens.' },
};

export default function OnboardingNotice({ onOpen }: { onOpen: () => void }) {
  const gate = useStudentGate();
  const { clearCompleted, justCompleted } = gate;
  useEffect(() => () => { if (justCompleted) clearCompleted(); }, [justCompleted, clearCompleted]);
  if (gate.status !== 'ready') return null;
  if (gate.route === 'dashboard' && justCompleted) {
    return (
      <p role="status" tabIndex={-1} className="dashboard-success rounded-xl border p-4 text-sm">
        <span aria-hidden="true" className="mr-2 font-bold">✓</span>Your semester onboarding is complete. Your subjects, clearance
        requirements and organizational fee are in My semester.</p>);
  }
  const copy = gate.route ? TEXT[gate.route] : undefined;
  if (!copy) return null;
  const body = gate.state === 'pending_verification'
    ? 'Your confirmation is waiting for an in-person CTU verification by the School Admin. Nothing has been billed.' : copy.body;
  return (
    <section aria-labelledby="onboarding-notice" className="dashboard-panel rounded-2xl border p-4 sm:p-6">
      <h2 id="onboarding-notice" className="dashboard-heading text-lg font-semibold">{gate.state === 'pending_verification'
        ? 'Semester onboarding: pending verification' : copy.title}</h2>
      <p className="dashboard-muted mt-1 text-sm leading-relaxed">{body}</p>
      <button type="button" className={`${secondaryButton} mt-4`} onClick={onOpen}>{copy.action}</button>
    </section>
  );
}
