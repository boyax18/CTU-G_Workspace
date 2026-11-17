/** Real production gate remains false. Only local Vite serve aliases this module. */
export const REGISTRATION_REVIEW_LIVE_API_ENABLED: boolean =
  import.meta.env.DEV && import.meta.env.VITE_CTUG_REVIEW_LOCAL === 'LOCAL_REVIEW_ONLY';
