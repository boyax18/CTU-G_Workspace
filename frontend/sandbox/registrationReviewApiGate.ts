/** Only the explicit Vite sandbox configuration aliases imports here.
 * Production's real registrationReviewApiGate.ts stays hard-disabled.
 */
export const REGISTRATION_REVIEW_LIVE_API_ENABLED: boolean =
  import.meta.env.DEV && import.meta.env.VITE_CTUG_REVIEW_SANDBOX === 'SANDBOX_ONLY';
