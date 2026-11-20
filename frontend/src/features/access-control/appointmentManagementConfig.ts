/** D-112 UI only. Also needs D-87 route mount and D-110 backend registry gate.
 * A frontend flag is NEVER authority; backend revalidates all requested actions. */
export const APPOINTMENT_MANAGEMENT_ENABLED =
  import.meta.env?.VITE_WORKSPACE_APPOINTMENT_MANAGEMENT_ENABLED === '1';
