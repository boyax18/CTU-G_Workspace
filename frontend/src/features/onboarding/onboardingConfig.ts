/** Student Semester Onboarding (WF-05.05), in-person CTU verification (WF-05.04 minimum) and the
 * evidenced historical participation correction (WF11-D14).
 *
 * Every switch is off unless the build sets it to '1'. They only decide whether the dashboard calls
 * the API and shows controls; Django's own default-off switches, the selected Student (or School
 * Admin) role context, the exact effective permission and every rule are enforced on each request.
 * Finalization (participation, clearance and fee obligation) has its own switch.
 */
const flag = (value: string | undefined) => value === '1';

export const STUDENT_ONBOARDING_ENABLED: boolean = flag(import.meta.env?.VITE_WORKSPACE_STUDENT_ONBOARDING_ENABLED);
export const STUDENT_ONBOARDING_FINALIZATION_ENABLED: boolean = STUDENT_ONBOARDING_ENABLED
  && flag(import.meta.env?.VITE_WORKSPACE_STUDENT_ONBOARDING_FINALIZATION_ENABLED);
export const ENROLLMENT_VERIFICATION_ENABLED: boolean = flag(import.meta.env?.VITE_WORKSPACE_ENROLLMENT_VERIFICATION_ENABLED);
export const HISTORICAL_PARTICIPATION_CORRECTION_ENABLED: boolean = ENROLLMENT_VERIFICATION_ENABLED
  && flag(import.meta.env?.VITE_WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED);

export const ONBOARDING_ROUTE_ROOT = '/api/v1/academic/onboarding/';
export const VERIFICATION_ROUTE_ROOT = '/api/v1/academic/verification/';

/** Exact catalogue codes (presentation hints only; the server decides). */
export const ONBOARDING_READ_CODE = 'academic.profile.self.read';
export const ONBOARDING_WRITE_CODE = 'clearance.requests.self.submit';
export const VERIFICATION_CODE = 'academic.profiles.manage';
