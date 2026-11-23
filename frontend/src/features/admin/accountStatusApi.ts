/** WF-02 school-account client: independent directory reads and status mutations (D-69).
 *
 * Read integration uses ACCOUNT_DIRECTORY_ENABLED; POSTs retain ACCOUNT_STATUS_ENABLED.
 * These switches decide whether the dashboard calls the API; Django's own gates, the exact
 * effective permission and the account rules decide everything. The API is mounted only where
 * the owner authorizes it (normal config.urls mounts reads only). GETs are never retried automatically; the status
 * POST is sent once and anything that might have been applied is `outcome_unknown` (D-68).
 */
import { ApiError, initializeCSRF, timeoutSignal } from '../../api/client.ts';
import { notifyAuthenticationRequired } from '../../utils/sessionSignals.ts';
import { parseRegistrationReviewError } from './registrationReviewApiContract.ts';
import {
  buildAccountDetailRequest, buildAccountHistoryRequest, buildAccountsRequest, buildStatusChangeRequest,
  parseAccountDetail, parseAccountPage, parseHistoryPage, parseStatusChange, parseStatusConflict,
} from './accountStatusContract.ts';
import { ACCOUNT_DIRECTORY_ENABLED, ACCOUNT_STATUS_ENABLED, ACCOUNT_STATUS_ROUTE_ROOT } from './accountStatusConfig.ts';
import { availableActions } from './managementAvailability.ts';
import type {
  AccountsQuery, AccountStatusAction, AccountStatusResult, SchoolAccountDetail, SchoolAccountPage, StatusHistoryPage,
} from './accountStatusContract.ts';


const off = () => new ApiError('Account status is not activated.', 503, 'review_unavailable');
const uncertain = () => new ApiError(
  'We could not confirm the change. Reload the account before trying again.', 0, 'outcome_unknown', {}, { outcomeUnknown: true },
);

async function getJSON(path: string, onResponse?: (response: Response) => void): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, { method: 'GET', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json' }, signal: timeoutSignal() });
  } catch {
    throw new ApiError('Unable to connect to the account service.', 0, 'network_error');
  }
  let value: unknown;
  try {
    value = await response.json();
  } catch {
    throw new ApiError('The server returned an unexpected response.', response.status, 'invalid_response');
  }
  if (!response.ok) {
    const { code, message } = parseRegistrationReviewError(response.status, value);
    if (response.status === 401) notifyAuthenticationRequired();
    throw new ApiError(message, response.status, code);
  }
  onResponse?.(response);
  return value;
}

export async function listSchoolAccounts(page = 1, query: AccountsQuery = {}, enabled = ACCOUNT_DIRECTORY_ENABLED): Promise<SchoolAccountPage> {
  if (!enabled) throw off(); // MUST stay first: no request while switched off
  return parseAccountPage(await getJSON(buildAccountsRequest(ACCOUNT_STATUS_ROUTE_ROOT, page, query)));
}

export async function getSchoolAccount(accountId: number, enabled = ACCOUNT_DIRECTORY_ENABLED): Promise<SchoolAccountDetail> {
  if (!enabled) throw off();
  let actions: string[] = [];
  const value = await getJSON(buildAccountDetailRequest(ACCOUNT_STATUS_ROUTE_ROOT, accountId), (response) => { actions = availableActions(response); });
  return { ...parseAccountDetail(value, accountId), available_actions: actions };
}

/** WF-02.06: one page (20, newest first) of the account's permitted status history; read-only. */
export async function getSchoolAccountHistory(accountId: number, page = 1, enabled = ACCOUNT_DIRECTORY_ENABLED): Promise<StatusHistoryPage> {
  if (!enabled) throw off();
  return parseHistoryPage(await getJSON(buildAccountHistoryRequest(ACCOUNT_STATUS_ROUTE_ROOT, accountId, page)), page);
}

/** One confirmed-state POST; never retried. Definite refusals keep their codes. */
export async function changeAccountStatus(
  accountId: number, action: AccountStatusAction, expectedActive: boolean, enabled = ACCOUNT_STATUS_ENABLED,
): Promise<AccountStatusResult> {
  if (!enabled) throw off();
  const plan = buildStatusChangeRequest(ACCOUNT_STATUS_ROUTE_ROOT, accountId, action, expectedActive);
  const csrfToken = await initializeCSRF(); // fails before anything is sent
  let response: Response;
  try {
    response = await fetch(plan.path, {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(plan.body), signal: timeoutSignal(),
    });
  } catch {
    throw uncertain();
  }
  let value: unknown = null;
  try {
    value = await response.json();
  } catch {
    if (response.ok || response.status >= 500) throw uncertain();
  }
  if (response.ok) {
    try {
      return parseStatusChange(value, accountId, action === 'activate');
    } catch {
      throw uncertain();
    }
  }
  if (response.status === 409) {
    throw new ApiError('The account status could not be changed.', 409, parseStatusConflict(value) ?? 'account_status_conflict');
  }
  const { code, message } = parseRegistrationReviewError(response.status, value);
  if (response.status >= 500 && !(response.status === 503 && code === 'review_unavailable')) throw uncertain();
  if (response.status === 401) notifyAuthenticationRequired();
  throw new ApiError(message, response.status, code);
}
