import type { RegistrationData } from './registration';

export default function RegistrationSchoolInformation({ role }: { role: RegistrationData['requested_role'] }) {
  return (
    <fieldset className="min-w-0">
      <legend className="fg-strong mb-4 w-full border-b border-emerald-500/20 pb-3 text-sm font-semibold">03 — School Information</legend>
      <div aria-live="polite" aria-atomic="true" className="rounded-xl bg-emerald-500/5 p-4">
        {role === 'Student' ? (
          <>
            <p className="fg-muted text-xs leading-relaxed">Your academic details will be configured later as part of your academic profile. These details are not collected during registration.</p>
            <dl className="mt-4 grid gap-4 sm:grid-cols-3">
              {['Course', 'Year Level', 'Section'].map((label) => (
                <div key={label}>
                  <dt className="fg-body text-xs font-medium">{label}</dt>
                  <dd className="fg-muted mt-1 text-xs">Configured later</dd>
                </div>
              ))}
            </dl>
          </>
        ) : (
          <p className="fg-muted text-sm leading-relaxed">Instructor academic and teaching assignments will be configured after account approval.</p>
        )}
      </div>
    </fieldset>
  );
}
