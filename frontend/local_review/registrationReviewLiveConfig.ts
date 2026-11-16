/** Local dev release only; never load in a production build. */
export const REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT: string | null =
  import.meta.env.DEV && import.meta.env.VITE_CTUG_REVIEW_LOCAL === 'LOCAL_REVIEW_ONLY'
    ? '/api/v1/admin/registration-requests/'
    : null;
