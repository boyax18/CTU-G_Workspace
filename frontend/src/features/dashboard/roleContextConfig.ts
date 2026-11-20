/** D-113: frontend presentation gate. Backend is separately gated and authoritative. */
export const ROLE_CONTEXT_SWITCHING_ENABLED =
  import.meta.env?.VITE_WORKSPACE_ROLE_CONTEXT_SWITCHING_ENABLED === '1';
