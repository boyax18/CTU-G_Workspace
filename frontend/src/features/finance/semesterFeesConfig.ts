/** Semester organizational fee configuration (School Admin).
 *
 * Off unless the build sets the flags to '1'. They decide only whether the dashboard calls the API
 * and shows controls; Django's own default-off switches and HDAC decide everything. Fee setting needs
 * finance.fee_schedule.manage through a genuine Admin role grant, which the pinned v2.2 catalogue
 * does not provide (Treasurer default; governance pending), so the server refuses it until reviewed.
 * Approval has its own switch; neither enables semester activation.
 */
export const SEMESTER_FEE_CONFIGURATION_ENABLED: boolean =
  import.meta.env?.VITE_WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED === '1';
export const SEMESTER_FEE_APPROVAL_ENABLED: boolean = SEMESTER_FEE_CONFIGURATION_ENABLED
  && import.meta.env?.VITE_WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED === '1';

export const SEMESTER_FEES_ROUTE_ROOT = '/api/v1/finance/semester-fees/';
export const FEE_PERMISSION = 'finance.fee_schedule.manage';
export const MAX_FEE_AMOUNT = '100000.00';
