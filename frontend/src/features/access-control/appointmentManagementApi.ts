/** WF-03.01 D-112. Gated, non-retrying appointment registry HTTP contract. */
import { ApiError, initializeCSRF, timeoutSignal } from '../../api/client.ts';
import { notifyAuthenticationRequired } from '../../utils/sessionSignals.ts';
import { parseRegistrationReviewError } from '../admin/registrationReviewApiContract.ts';
import { ROLE_ASSIGNMENT_ROUTE_ROOT } from './roleAssignmentConfig.ts';
import { APPOINTMENT_MANAGEMENT_ENABLED } from './appointmentManagementConfig.ts';

export type AppointmentRole = 'Treasurer' | 'SSG Advisor';
export type AppointmentStatus = 'Submitted' | 'Verified' | 'Rejected' | 'Revoked';
export type AppointmentDecision = 'verify' | 'reject' | 'revoke';
export interface AppointmentCandidate { account_id: number; ctug_id: string; role_name: AppointmentRole }
export interface AppointmentRow {
  appointment_id: number;
  account_id: number;
  role_name: AppointmentRole;
  valid_from: string;
  valid_until: string;
  status?: AppointmentStatus;
}
export interface AppointmentPage { page: number; has_next: boolean; results: AppointmentRow[] }
const root = `${ROLE_ASSIGNMENT_ROUTE_ROOT}appointments/`;
const rec = (value: unknown): value is Record<string, unknown> =>
  !!value && typeof value === 'object' && !Array.isArray(value);
const id = (n: unknown): n is number => typeof n === 'number' && Number.isInteger(n) && n > 0 && n <= 2_147_483_647;
const role = (x: unknown): x is AppointmentRole => x === 'Treasurer' || x === 'SSG Advisor';
function unavailable(): never { throw new ApiError('Appointment management is not activated.', 503, 'review_unavailable'); }
function invalid(): never { throw new ApiError('Unexpected appointment response.', 0, 'invalid_response'); }
function unknown(): never { throw new ApiError('Result unknown. Reload before trying another action.', 0, 'outcome_unknown'); }
function ensureEnabled() { if (!APPOINTMENT_MANAGEMENT_ENABLED) unavailable(); }
function pageNumber(n: number) { if (!Number.isInteger(n) || n < 1 || n > 10000) throw new Error('Invalid page.'); }

async function decode(response: Response): Promise<unknown> {
  let data: unknown;
  try { data = await response.json(); } catch { invalid(); }
  if (response.ok) return data;
  if (response.status === 409 && rec(data) && rec(data.error)
      && data.error.code === 'appointment_conflict' && typeof data.error.reason === 'string') {
    throw new ApiError('Appointment changed or is no longer eligible. Reload the list.', 409, data.error.reason);
  }
  const { code, message } = parseRegistrationReviewError(response.status, data);
  if (response.status === 401) notifyAuthenticationRequired();
  throw new ApiError(message, response.status, code);
}
async function read(url: string): Promise<unknown> {
  ensureEnabled();
  let response: Response;
  try { response = await fetch(url, { method: 'GET', credentials: 'same-origin', cache: 'no-store',
    headers: { Accept: 'application/json' }, signal: timeoutSignal() }); }
  catch { throw new ApiError('Unable to load appointments.', 0, 'network_error'); }
  return decode(response);
}
async function write(url: string, body: object): Promise<unknown> {
  ensureEnabled();
  // CSRF acquisition failing cannot mutate state; only a request with uncertain delivery is ambiguous.
  const csrf = await initializeCSRF();
  let response: Response;
  try { response = await fetch(url, { method: 'POST', credentials: 'same-origin', cache: 'no-store',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify(body), signal: timeoutSignal() }); }
  catch { unknown(); }
  try { return await decode(response); } catch (e: unknown) {
    if (e instanceof ApiError && (e.code === 'invalid_response' || e.status >= 500 && e.code !== 'review_unavailable')) unknown();
    throw e;
  }
}
function parseRow(value: unknown, statusRequired: boolean): AppointmentRow {
  if (!rec(value) || !id(value.appointment_id) || !id(value.account_id) || !role(value.role_name)
    || typeof value.valid_from !== 'string' || !Number.isFinite(Date.parse(value.valid_from))
    || typeof value.valid_until !== 'string' || !Number.isFinite(Date.parse(value.valid_until))) invalid();
  if (statusRequired && !['Submitted', 'Verified', 'Rejected', 'Revoked'].includes(String(value.status))) invalid();
  if (!statusRequired && 'status' in value) invalid();
  return value as unknown as AppointmentRow;
}
function parsePage(value: unknown, withStatus = false): AppointmentPage {
  if (!rec(value) || !id(value.page) || value.page > 10000 || typeof value.has_next !== 'boolean'
    || !Array.isArray(value.results) || value.results.length > 20 || (value.has_next && value.results.length !== 20)) invalid();
  const results = (value.results as unknown[]).map(row => parseRow(row, withStatus));
  if (new Set(results.map(r => r.appointment_id)).size !== results.length) invalid();
  return { page: value.page as number, has_next: value.has_next as boolean, results };
}
export async function findCandidate(ctugId: string, kind: AppointmentRole): Promise<AppointmentCandidate> {
  if (!role(kind) || ctugId.length < 1 || ctugId.length > 50 || ctugId !== ctugId.trim())
    throw new Error('Enter an exact CTU-G ID.');
  const q = new URLSearchParams({ ctug_id: ctugId, role: kind });
  const v = await read(`${root}candidate/?${q}`);
  if (!rec(v) || !id(v.account_id) || v.ctug_id !== ctugId || v.role_name !== kind) invalid();
  return v as unknown as AppointmentCandidate;
}
export async function listAppointments(kind: 'mine' | 'submitted' | 'verified', page = 1): Promise<AppointmentPage> {
  pageNumber(page);
  const endpoint = kind === 'mine' ? 'my-submissions/' : kind === 'submitted' ? 'review-queue/' : 'verified/';
  return parsePage(await read(`${root}${endpoint}?page=${page}`), kind === 'mine');
}
export async function fingerprintOfficialFile(file: File): Promise<string> {
  if (!file || file.size < 1 || file.size > 25 * 1024 * 1024) throw new Error('Choose a file between 1 byte and 25 MB.');
  if (!globalThis.crypto?.subtle) throw new Error('Local file fingerprinting requires a secure browser context.');
  const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer());
  return Array.from(new Uint8Array(digest), x => x.toString(16).padStart(2, '0')).join('');
}
export async function submitAppointment(data: {
  candidate: AppointmentCandidate; document_sha256: string; valid_from: string; valid_until: string;
}): Promise<{appointment_id: number; status: 'Submitted'}> {
  if (!id(data.candidate.account_id) || !role(data.candidate.role_name) || !/^[a-f0-9]{64}$/.test(data.document_sha256))
    throw new Error('Appointment information is incomplete.');
  const v = await write(root, { account_id: data.candidate.account_id, role_name: data.candidate.role_name,
    document_sha256: data.document_sha256, valid_from: data.valid_from, valid_until: data.valid_until });
  if (!rec(v) || !id(v.appointment_id) || v.status !== 'Submitted') unknown();
  return v as {appointment_id: number; status: 'Submitted'};
}
export async function decideAppointment(row: AppointmentRow, action: AppointmentDecision, digest?: string): Promise<AppointmentStatus> {
  if (!id(row.appointment_id) || !['verify', 'reject', 'revoke'].includes(action)
    || (action === 'verify' && !/^[a-f0-9]{64}$/.test(digest ?? ''))) throw new Error('Invalid appointment decision.');
  const body = action === 'verify' ? {confirmed_document_sha256: digest} : {};
  const v = await write(`${root}${row.appointment_id}/${action}/`, body);
  const expected = action === 'verify' ? 'Verified' : action === 'reject' ? 'Rejected' : 'Revoked';
  if (!rec(v) || v.appointment_id !== row.appointment_id || v.status !== expected) unknown();
  return expected;
}
