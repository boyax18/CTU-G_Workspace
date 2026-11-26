/** Read-only record summaries shared by Semester onboarding, My semester and the history list. */
import { useId } from 'react';
import { badgeClass } from '../academic/academicStyles.ts';
import { peso } from './onboardingApi.ts';
import type { Clearance, Result } from './onboardingApi.ts';

const REQUIREMENT_TEXT = { subject_instructor: 'Subject instructor', treasurer_fee: 'SSG Treasurer · organizational fee',
  school_admin_final: 'School Admin · final approval' } as const;

export function ClearanceList({ clearance, title, level = 4 }: { clearance: Clearance | null; title: string; level?: 3 | 4 }) {
  const ids = useId();
  const Heading = level === 3 ? 'h3' : 'h4';
  if (!clearance) return <p className="dashboard-muted text-sm">No clearance record exists for this semester.</p>;
  return (
    <section aria-labelledby={ids} className="space-y-2">
      <Heading id={ids} className="dashboard-heading font-semibold">{title}{' '}
        <span className={`${badgeClass} ${clearance.status === 'Cleared' ? 'dashboard-accent' : 'dashboard-heading'}`}>
          <span aria-hidden="true">{clearance.status === 'Cleared' ? '●' : '○'}</span>{clearance.status}</span></Heading>
      <p className="dashboard-muted text-sm">{clearance.pending_count === 0 ? 'Every requirement is signed.'
        : `${clearance.pending_count} requirement${clearance.pending_count === 1 ? '' : 's'} still pending.`}</p>
      <ul className="space-y-2">
        {clearance.requirements.map((r, index) => (
          <li key={`${r.kind}-${r.subject?.code ?? index}`} className="flex flex-wrap items-baseline justify-between gap-2 rounded-xl border p-3 text-sm">
            <span className="dashboard-heading min-w-0">
              {r.subject ? `${r.subject.code} · ${r.subject.title}` : REQUIREMENT_TEXT[r.kind]}
              {r.signatory && <span className="dashboard-muted block text-xs">Instructor: {r.signatory}</span>}
            </span>
            <span className={`${badgeClass} ${r.status === 'Signed' ? 'dashboard-accent' : 'dashboard-muted border-dashed'}`}>
              <span aria-hidden="true">{r.status === 'Signed' ? '✓' : '○'}</span>{r.status}</span>
          </li>))}
      </ul>
    </section>
  );
}

export function ResultSummary({ result, level = 4 }: { result: Result; level?: 3 | 4 }) {
  return (
    <div className="space-y-5">
      <dl className="grid gap-4 text-sm sm:grid-cols-2">
        <div><dt className="dashboard-muted text-xs">Student type</dt><dd className="dashboard-heading font-semibold">{result.student_type}</dd></div>
        <div><dt className="dashboard-muted text-xs">Course and year level</dt>
          <dd className="dashboard-heading font-semibold">{result.course.code} · Year {result.year_level}</dd></div>
        <div><dt className="dashboard-muted text-xs">Organizational fee</dt>
          <dd className="dashboard-heading font-semibold tabular-nums">{result.fee ? `${peso(result.fee.amount)} · ${result.fee.status}` : 'Not assessed'}</dd></div>
        <div><dt className="dashboard-muted text-xs">Clearance</dt><dd className="dashboard-heading font-semibold">{result.clearance?.status ?? 'None'}</dd></div>
      </dl>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[580px] text-left text-sm">
          <caption className="sr-only">Confirmed subjects</caption>
          <thead><tr className="dashboard-muted border-b text-xs uppercase tracking-wide">
            <th scope="col" className="px-2 py-3">Subject</th><th scope="col" className="px-2 py-3">Section</th>
            <th scope="col" className="px-2 py-3">Instructor</th></tr></thead>
          <tbody>{result.subjects.map((s) => (
            <tr key={s.subject_id} className="border-b last:border-0">
              <td className="dashboard-heading px-2 py-3 font-semibold">{s.code} · {s.title}</td>
              <td className="dashboard-muted px-2 py-3">{s.section}</td>
              <td className="dashboard-muted px-2 py-3">{s.instructor ?? 'Not recorded'}</td></tr>))}</tbody>
        </table>
      </div>
      <ClearanceList clearance={result.clearance} title="Clearance requirements" level={level} />
      <p className="dashboard-muted text-xs">Cleared means every required signature plus the School Admin final approval, not only a paid
        fee. Payments are recorded separately by the SSG Treasurer.</p>
    </div>
  );
}
