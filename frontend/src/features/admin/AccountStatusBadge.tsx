/** WF-02.05: account status in words with a non-color mark (never color only). */
const badgeClass = 'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap';

export default function AccountStatusBadge({ active }: { active: boolean }) {
  return active
    ? <span className={`${badgeClass} dashboard-heading`}><span aria-hidden="true">●</span>Active</span>
    : <span className={`${badgeClass} dashboard-muted border-dashed`}><span aria-hidden="true">○</span>Inactive</span>;
}
