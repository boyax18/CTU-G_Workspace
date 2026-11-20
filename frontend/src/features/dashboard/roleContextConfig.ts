/** UI presentation only. Server session capability is the authorization source.
 * VITE_WORKSPACE_ROLE_CONTEXT_SWITCHING_ENABLED=0 can hide the selector;
 * omitting this variable never enables backend role switching on its own. */
export const ROLE_CONTEXT_SWITCHING_ENABLED =
  import.meta.env?.VITE_WORKSPACE_ROLE_CONTEXT_SWITCHING_ENABLED !== '0';
