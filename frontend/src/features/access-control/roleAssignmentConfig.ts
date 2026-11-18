/** WF-03.01 (D-86, D-87): Access control → Role assignments. Off unless the build sets
 * VITE_WORKSPACE_ROLE_ASSIGNMENT_ENABLED=1. Django's own default-off WORKSPACE_ROLE_ASSIGNMENT_ENABLED
 * gate, the composite Technical Super Admin profile and the exact effective permission decide. */
export const ROLE_ASSIGNMENT_ENABLED: boolean =
  import.meta.env?.VITE_WORKSPACE_ROLE_ASSIGNMENT_ENABLED === '1';

/** Proposed local-review/sandbox mount; mounting it is a separately authorized change (never config.urls). */
export const ROLE_ASSIGNMENT_ROUTE_ROOT = '/api/v1/admin/role-assignments/';
