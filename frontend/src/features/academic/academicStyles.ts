/** Dashboard class strings (docs/design/COMPONENTS.md §2, §3) shared by the WF-11.01 views. */
export const ring = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]';
export const primaryButton = `dashboard-primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${ring} disabled:cursor-not-allowed disabled:opacity-50`;
export const secondaryButton = `dashboard-outline-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${ring} disabled:cursor-not-allowed disabled:opacity-50`;
export const compactButton = `dashboard-outline-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${ring} disabled:cursor-not-allowed disabled:opacity-50`;
export const destructiveButton = `inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#b91c1c] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#991b1b] ${ring} disabled:cursor-not-allowed disabled:opacity-50`;
export const fieldClass = `dashboard-panel min-h-11 w-full rounded-lg border px-3 py-2 text-sm ${ring} disabled:cursor-not-allowed disabled:opacity-60`;
export const badgeClass = 'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap';

const DATE_FORMAT = new Intl.DateTimeFormat('en-PH', { dateStyle: 'medium', timeZone: 'UTC' });
const DATE_TIME_FORMAT = new Intl.DateTimeFormat('en-PH', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Manila' });

export function formatDate(value: string | null): string {
  return value ? DATE_FORMAT.format(new Date(`${value}T00:00:00Z`)) : 'Not set';
}

export function formatDateTime(value: string): string {
  const moment = new Date(value);
  return Number.isNaN(moment.getTime()) ? 'Not recorded' : DATE_TIME_FORMAT.format(moment);
}
