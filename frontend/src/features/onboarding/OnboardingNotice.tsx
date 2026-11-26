/** Overview notice: Student Semester Onboarding is required (WF11-D17). It never redirects: the Student
 * opens onboarding from here, and Sign out, the profile and the historical records stay reachable.
 * Rendered only when the switch is on and the session reports the exact read code. A refusal (for
 * example another role's context) shows nothing here; the onboarding view itself explains it.
 */
import { useEffect, useState } from 'react';
import { secondaryButton } from '../academic/academicStyles.ts';
import { getStatus } from './onboardingApi.ts';
import type { OnboardingState } from './onboardingApi.ts';
import { ONBOARDING_READ_CODE, STUDENT_ONBOARDING_ENABLED } from './onboardingConfig.ts';

const TEXT: Partial<Record<OnboardingState, { title: string; body: string; action: string }>> = {
  onboarding: { title: 'Complete your semester onboarding', action: 'Start semester onboarding',
    body: 'Confirm your student type, subjects, course and year level for the active semester. Your semester dashboard opens when it is completed.' },
  pending_verification: { title: 'Semester onboarding: pending verification', action: 'Open semester onboarding',
    body: 'Your confirmation is waiting for an in-person CTU verification by the School Admin. Nothing has been billed.' },
  clearance_required: { title: 'Clearance required', action: 'View clearance requirement',
    body: 'Your previous semester clearance must be cleared before you can onboard for the active semester.' },
  gap_verification_required: { title: 'Official verification needed', action: 'View what is needed',
    body: 'The School Admin must verify your official CTU records in person before onboarding opens.' },
  history_unverified: { title: 'Official verification needed', action: 'View what is needed',
    body: 'The School Admin must verify your official CTU records in person before onboarding opens.' },
  evidence_conflict: { title: 'Your records need review', action: 'View what is needed',
    body: 'Your official CTU record conflicts with your Workspace history. Visit the School Admin in person.' },
};

export default function OnboardingNotice({ permissions, onOpen }: { permissions: readonly string[]; onOpen: () => void }) {
  const eligible = STUDENT_ONBOARDING_ENABLED && permissions.includes(ONBOARDING_READ_CODE);
  const [state, setState] = useState<OnboardingState | null>(null);
  useEffect(() => {
    if (!eligible) return undefined;
    let cancelled = false;
    getStatus().then((s) => { if (!cancelled) setState(s.state); }).catch(() => { if (!cancelled) setState(null); });
    return () => { cancelled = true; };
  }, [eligible]);
  const copy = state ? TEXT[state] : undefined;
  if (!eligible || !copy) return null;
  return (
    <section aria-labelledby="onboarding-notice" className="dashboard-panel rounded-2xl border p-4 sm:p-6">
      <h2 id="onboarding-notice" className="dashboard-heading text-lg font-semibold">{copy.title}</h2>
      <p className="dashboard-muted mt-1 text-sm leading-relaxed">{copy.body}</p>
      <button type="button" className={`${secondaryButton} mt-4`} onClick={onOpen}>{copy.action}</button>
    </section>
  );
}
