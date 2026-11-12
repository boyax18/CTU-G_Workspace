/** Only the explicit Vite sandbox configuration aliases imports here.
 * The normal frontend keeps its approved route root null.
 */
export const REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT: string | null =
  import.meta.env.DEV && import.meta.env.VITE_CTUG_REVIEW_SANDBOX === 'SANDBOX_ONLY'
    ? '/api/v1/admin/registration-requests/'
    : null;
