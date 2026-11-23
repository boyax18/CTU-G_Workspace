/** WF-02.05 Activate or deactivate an existing account: typed contract for the school-account API.
 *
 * Minimized fields only (no email, credentials, review data, sessions or permission detail).
 * Every parser refuses extra or inconsistent fields. Plans never send a role or status other than
 * the confirmed `expected_active` (D-68).
 */
export type AccountStatusFilter = 'active' | 'inactive';
export type AccountStatusAction = 'suspend' | 'activate';
export type AccountStatusConflictReason = 'state_changed' | 'protected_account' | 'no_operational_role';

export interface SchoolAccountItem {
  account_id: number;
  school_id: string;
  id_label: 'CTU-G ID';
  full_name: string | null;
  roles: string[];
  is_active: boolean;
}

export interface SchoolAccountPage {
  results: SchoolAccountItem[];
  page: number;
  page_size: 20;
  has_next: boolean;
}

/** WF-02.06 D-74: the only history events, each with its fixed description. */
export type StatusHistoryEvent = 'registration_approved' | 'account_deactivated' | 'account_reactivated';
/** WF-02.06 D-73: made by Django from the trusted session; never a name or ID. */
export type HistoryActor = 'You' | 'An administrator';

export interface StatusHistoryEntry {
  event: StatusHistoryEvent;
  description: string;
  occurred_at: string;
  actor: HistoryActor;
  /** Only for activation/deactivation events; null when the audit did not record a matching state. */
  previous_is_active?: boolean | null;
  new_is_active?: boolean | null;
}

export interface StatusHistoryPage {
  results: StatusHistoryEntry[];
  page: number;
  page_size: 20;
  has_next: boolean;
}

export interface SchoolAccountDetail extends SchoolAccountItem {
  name: { first: string | null; middle: string | null; last: string | null; suffix: string | null };
  request_status: 'Approved';
  created_at: string;
  /** A hint only; Django re-checks it inside the lock. */
  can_reactivate: boolean;
  /** WF-02.06 D-75: null means "Not recorded"; never inferred. */
  approved_at: string | null;
  last_status_change: StatusHistoryEntry | null;
}

export interface AccountStatusResult { account_id: number; is_active: boolean }

export interface AccountsQuery { q?: string; status?: AccountStatusFilter }

const MAX_ID = 2_147_483_647;
const INVALID = 'The account service returned an unexpected response.';
export const ACCOUNT_SEARCH_MAX = 50;

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const exactKeys = (v: Record<string, unknown>, keys: readonly string[]) =>
  Object.keys(v).length === keys.length && keys.every((k) => Object.prototype.hasOwnProperty.call(v, k));
export const isAccountId = (v: unknown): v is number => typeof v === 'number' && Number.isInteger(v) && v >= 1 && v <= MAX_ID;
const optionalText = (v: unknown, max: number) => v === null || (typeof v === 'string' && v.length >= 1 && v.length <= max);
const isTimestamp = (v: unknown) => typeof v === 'string'
  && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(v) && Number.isFinite(Date.parse(v));
const fail = (): never => { throw new Error(INVALID); };

function validateRoot(root: string): string {
  if (typeof root !== 'string' || !/^\/api\/(?:[A-Za-z0-9_-]+\/)+$/.test(root)) {
    throw new Error('An approved, same-origin API route prefix is required.');
  }
  return root;
}

/** `?account=` value as an ID, or null. */
export function parseAccountParam(raw: string | null): number | null {
  if (typeof raw !== 'string' || !/^[1-9][0-9]{0,9}$/.test(raw)) return null;
  const id = Number(raw);
  return isAccountId(id) ? id : null;
}

/** Trimmed printable-ASCII search, or '' for none; throws for anything the server refuses. */
export function normalizeAccountSearch(value: string): string {
  const term = typeof value === 'string' ? value.trim() : '';
  if (!term) return '';
  if (term.length > ACCOUNT_SEARCH_MAX || !/^[\x20-\x7E]+$/.test(term) || term.split(/\s+/).length > 5) {
    throw new Error(`Use up to ${ACCOUNT_SEARCH_MAX} letters, digits or punctuation (no accents), in at most 5 words.`);
  }
  return term;
}

export function buildAccountsRequest(root: string, page = 1, query: AccountsQuery = {}): string {
  const base = validateRoot(root);
  if (!Number.isInteger(page) || page < 1 || page > 10_000) throw new Error('Invalid page.');
  const raw: unknown = query;
  if (!isRecord(raw) || Object.keys(raw).some((k) => k !== 'q' && k !== 'status')) throw new Error('Unsupported query.');
  const params = new URLSearchParams({ page: String(page) });
  if (query.q !== undefined) {
    const term = normalizeAccountSearch(query.q);
    if (term) params.set('q', term);
  }
  if (query.status !== undefined) {
    if (query.status !== 'active' && query.status !== 'inactive') throw new Error('Unsupported status.');
    params.set('status', query.status);
  }
  return `${base}?${params.toString().replace(/\+/g, '%20')}`;
}

export function buildAccountDetailRequest(root: string, accountId: number): string {
  if (!isAccountId(accountId)) throw new Error('Invalid account ID.');
  return `${validateRoot(root)}${accountId}/`;
}

/** WF-02.06: GET only; the page is the only query field the server accepts. */
export function buildAccountHistoryRequest(root: string, accountId: number, page = 1): string {
  if (!isAccountId(accountId)) throw new Error('Invalid account ID.');
  if (!Number.isInteger(page) || page < 1 || page > 10_000) throw new Error('Invalid page.');
  return `${validateRoot(root)}${accountId}/history/?page=${page}`;
}

const HISTORY_DESCRIPTIONS: Record<StatusHistoryEvent, string> = {
  registration_approved: 'Registration approved',
  account_deactivated: 'Account deactivated',
  account_reactivated: 'Account reactivated',
};
const STATUS_STATES: Partial<Record<StatusHistoryEvent, readonly [boolean, boolean]>> = {
  account_deactivated: [true, false],
  account_reactivated: [false, true],
};

/** Exact D-74 shape: refuses extra fields, unknown events, other actor labels or inconsistent states. */
export function parseHistoryEntry(value: unknown): StatusHistoryEntry {
  if (!isRecord(value)) fail();
  const v = value as Record<string, unknown>;
  const event = v.event as StatusHistoryEvent;
  if (!Object.prototype.hasOwnProperty.call(HISTORY_DESCRIPTIONS, event)) fail();
  const states = STATUS_STATES[event];
  const keys = ['event', 'description', 'occurred_at', 'actor', ...(states ? ['previous_is_active', 'new_is_active'] : [])];
  if (!exactKeys(v, keys) || v.description !== HISTORY_DESCRIPTIONS[event] || !isTimestamp(v.occurred_at)
    || (v.actor !== 'You' && v.actor !== 'An administrator')) fail();
  const entry: StatusHistoryEntry = {
    event, description: HISTORY_DESCRIPTIONS[event], occurred_at: v.occurred_at as string, actor: v.actor as HistoryActor,
  };
  if (states) {
    const recorded = v.previous_is_active === null && v.new_is_active === null;
    if (!recorded && (v.previous_is_active !== states[0] || v.new_is_active !== states[1])) fail();
    entry.previous_is_active = v.previous_is_active as boolean | null;
    entry.new_is_active = v.new_is_active as boolean | null;
  }
  return entry;
}

export function parseHistoryPage(value: unknown, expectedPage: number): StatusHistoryPage {
  if (!isRecord(value) || !exactKeys(value, ['results', 'page', 'page_size', 'has_next'])) fail();
  const v = value as Record<string, unknown>;
  if (!Array.isArray(v.results) || v.results.length > 20 || v.page_size !== 20 || typeof v.has_next !== 'boolean'
    || v.page !== expectedPage || (v.has_next && v.results.length !== 20)) fail();
  // Kept in Django's order (newest first by the append-only audit key); never re-sorted here.
  const results = (v.results as unknown[]).map(parseHistoryEntry);
  return { results, page: expectedPage, page_size: 20, has_next: v.has_next as boolean };
}

export function buildStatusChangeRequest(root: string, accountId: number, action: AccountStatusAction, expectedActive: boolean) {
  if (!isAccountId(accountId)) throw new Error('Invalid account ID.');
  if (action !== 'suspend' && action !== 'activate') throw new Error('Unsupported action.');
  // Suspension confirms an active account; reactivation confirms an inactive one.
  if (typeof expectedActive !== 'boolean' || expectedActive !== (action === 'suspend')) throw new Error('Inconsistent confirmation.');
  return { method: 'POST' as const, path: `${validateRoot(root)}${accountId}/${action}/`, body: { expected_active: expectedActive } };
}

function parseItem(item: unknown, detail = false): SchoolAccountItem {
  const keys = ['account_id', 'school_id', 'id_label', 'full_name', 'roles', 'is_active'];
  const all = detail
    ? [...keys, 'name', 'request_status', 'created_at', 'can_reactivate', 'approved_at', 'last_status_change'] : keys;
  if (!isRecord(item) || !exactKeys(item, all)) fail();
  const v = item as Record<string, unknown>;
  if (!isAccountId(v.account_id) || typeof v.school_id !== 'string' || v.school_id.length < 1 || v.school_id.length > 50
    || v.id_label !== 'CTU-G ID' || !optionalText(v.full_name, 400)
    || !Array.isArray(v.roles) || v.roles.length > 20
    || v.roles.some((r) => typeof r !== 'string' || r.length < 1 || r.length > 50)
    || new Set(v.roles).size !== v.roles.length || typeof v.is_active !== 'boolean') fail();
  return {
    account_id: v.account_id as number, school_id: v.school_id as string, id_label: v.id_label as SchoolAccountItem['id_label'],
    full_name: v.full_name as string | null, roles: [...(v.roles as string[])], is_active: v.is_active as boolean,
  };
}

export function parseAccountPage(value: unknown): SchoolAccountPage {
  if (!isRecord(value) || !exactKeys(value, ['results', 'page', 'page_size', 'has_next'])) fail();
  const v = value as Record<string, unknown>;
  if (!Array.isArray(v.results) || v.results.length > 20 || v.page_size !== 20 || typeof v.has_next !== 'boolean'
    || !Number.isInteger(v.page) || (v.page as number) < 1 || (v.has_next && v.results.length !== 20)) fail();
  const results = (v.results as unknown[]).map((item) => parseItem(item));
  if (new Set(results.map((r) => r.account_id)).size !== results.length) fail();
  return { results, page: v.page as number, page_size: 20, has_next: v.has_next as boolean };
}

export function parseAccountDetail(value: unknown, expectedId: number): SchoolAccountDetail {
  const base = parseItem(value, true);
  const v = value as Record<string, unknown>;
  const name = v.name;
  if (base.account_id !== expectedId || v.request_status !== 'Approved' || !isTimestamp(v.created_at)
    || typeof v.can_reactivate !== 'boolean' || !isRecord(name) || !exactKeys(name, ['first', 'middle', 'last', 'suffix'])
    || !optionalText(name.first, 100) || !optionalText(name.middle, 100) || !optionalText(name.last, 100)
    || !optionalText(name.suffix, 20) || (v.approved_at !== null && !isTimestamp(v.approved_at))) fail();
  const last = v.last_status_change === null ? null : parseHistoryEntry(v.last_status_change);
  if (last && !STATUS_STATES[last.event]) fail(); // only an activation/deactivation is a status change
  const n = name as Record<string, string | null>;
  return {
    ...base, name: { first: n.first, middle: n.middle, last: n.last, suffix: n.suffix }, request_status: 'Approved',
    created_at: v.created_at as string, can_reactivate: v.can_reactivate as boolean,
    approved_at: v.approved_at as string | null, last_status_change: last,
  };
}

/** The server must confirm exactly this account and the new state. */
export function parseStatusChange(value: unknown, expectedId: number, expectedActive: boolean): AccountStatusResult {
  if (!isRecord(value) || !exactKeys(value, ['account_id', 'is_active'])
    || value.account_id !== expectedId || value.is_active !== expectedActive) fail();
  return { account_id: expectedId, is_active: expectedActive };
}

export function parseStatusConflict(value: unknown): AccountStatusConflictReason | null {
  if (!isRecord(value) || !exactKeys(value, ['error']) || !isRecord(value.error)) return null;
  const { code, reason } = value.error;
  if (code !== 'account_status_conflict') return null;
  return reason === 'state_changed' || reason === 'protected_account' || reason === 'no_operational_role' ? reason : null;
}
