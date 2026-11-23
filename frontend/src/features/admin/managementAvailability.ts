/** Server-reported request-local hints. Missing/malformed headers fail closed.
 * Django rechecks gates, permissions, role context and target rules on every POST. */
export function availableActions(response: Response): string[] {
  const value = response.headers?.get?.('X-Workspace-Available-Actions');
  if (!value) return [];
  const actions = value.split(',');
  const allowed = new Set(['approve', 'reject', 'bulk-approve', 'bulk-reject', 'suspend', 'activate']);
  return actions.length <= 6 && new Set(actions).size === actions.length && actions.every((action) => allowed.has(action))
    ? actions : [];
}
