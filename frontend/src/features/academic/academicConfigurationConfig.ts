/** Academic configuration foundation (courses, subjects, sections, curricula, offerings, instructors).
 *
 * Every switch is off unless the build sets it to '1'. They only decide whether the dashboard calls
 * the API and shows write controls; Django's own default-off switches, the exact effective permission
 * of each area, the Admin role context and every rule are enforced on each request.
 *
 * Curriculum and offering writes have no approved exact permission yet (proposed mapping only), and
 * instructor assignments have their own switch. None of these enables semester transitions.
 */
const flag = (value: string | undefined) => value === '1';

export const ACADEMIC_CONFIGURATION_ENABLED: boolean = flag(import.meta.env?.VITE_WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED);
export const ACADEMIC_CURRICULUM_WRITES_ENABLED: boolean = ACADEMIC_CONFIGURATION_ENABLED
  && flag(import.meta.env?.VITE_WORKSPACE_ACADEMIC_CURRICULUM_WRITES_ENABLED);
export const ACADEMIC_OFFERING_WRITES_ENABLED: boolean = ACADEMIC_CONFIGURATION_ENABLED
  && flag(import.meta.env?.VITE_WORKSPACE_ACADEMIC_OFFERING_WRITES_ENABLED);
export const ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED: boolean = ACADEMIC_CONFIGURATION_ENABLED
  && flag(import.meta.env?.VITE_WORKSPACE_ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED);

export const ACADEMIC_CONFIGURATION_ROUTE_ROOT = '/api/v1/academic/config/';

/** Exact catalogue code per area (presentation hints only; the server decides). */
export const AREA_CODES = {
  courses: 'academic.courses.manage',
  subjects: 'clearance.subjects.manage',
  sections: 'academic.sections.manage',
  curricula: 'academic.courses.manage',
  offerings: 'academic.periods.manage',
  teaching: 'clearance.teaching_assignments.manage',
} as const;
