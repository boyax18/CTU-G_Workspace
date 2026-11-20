/** WF-03.01 D-112: independently authorized appointment registry UI, default OFF.
 * Never uploads official file bytes; only a local SHA-256 digest is submitted.
 * Appointments do not assign roles. School Admin has no role-management controls.
 */
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Modal from '../../components/common/Modal';
import {
  decideAppointment, findCandidate, fingerprintOfficialFile, listAppointments, submitAppointment,
} from './appointmentManagementApi.ts';
import type { AppointmentCandidate, AppointmentDecision, AppointmentPage, AppointmentRole, AppointmentRow } from './appointmentManagementApi.ts';

const RECORD = 'access_control.appointments.record';
const VERIFY = 'access_control.appointments.verify';
const field = 'dashboard-panel w-full min-h-11 rounded-lg border px-3 py-2 text-sm';
const button = 'dashboard-outline-button inline-flex min-h-11 items-center justify-center rounded-lg border px-4 py-2 text-sm font-medium disabled:opacity-50';
const primary = 'dashboard-primary-link inline-flex min-h-11 items-center justify-center rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-50';
const errorCode = (e: unknown) => e && typeof e === 'object' && 'code' in e ? String((e as {code: unknown}).code) : '';
function explain(e: unknown) {
  const code = errorCode(e);
  if (code === 'outcome_unknown') return 'The outcome is uncertain. Reload the relevant list before taking another action.';
  if (code === 'access_denied') return 'Your account does not have the required appointment permission.';
  if (code === 'review_unavailable') return 'Appointment services are not enabled or are temporarily unavailable.';
  if (code === 'request_unavailable') return 'No eligible account or appointment was found.';
  if (code === 'not_eligible' || code === 'state_changed' || code === 'role_still_assigned' || code === 'already_verified')
    return 'The appointment is no longer eligible for that decision. Refresh the list. If a role remains assigned, ask the Super Admin to revoke the role first.';
  return e instanceof Error ? e.message : 'The appointment request could not be completed.';
}

function Queue({ kind, label, onDecision }: {kind: 'submitted' | 'verified'; label: string;
  onDecision: (row: AppointmentRow, action: AppointmentDecision) => void}) {
  const [page, setPage] = useState(1);
  const [tick, setTick] = useState(0);
  const [state, setState] = useState<{loading: boolean; data?: AppointmentPage; error?: string}>({loading: true});
  useEffect(() => {
    let active = true;
    listAppointments(kind, page).then(data => { if (active) setState({loading: false, data}); })
      .catch((e: unknown) => { if (active) setState({loading: false, error: explain(e)}); });
    return () => { active = false; };
  }, [kind, page, tick]);
  return <div className="dashboard-panel rounded-xl border p-4">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 className="dashboard-heading font-semibold">{label}</h3>
      <button type="button" className={button} onClick={() => { setState({loading: true}); setTick(t => t + 1); }}>Refresh</button>
    </div>
    {state.loading && <p role="status" className="dashboard-muted mt-3 text-sm">Loading appointments…</p>}
    {state.error && <p role="alert" className="dashboard-error mt-3 text-sm">{state.error}</p>}
    {!state.loading && state.data?.results.length === 0 && <p className="dashboard-muted mt-3 text-sm">No appointments in this list.</p>}
    <ul className="mt-3 divide-y" aria-label={label}>{state.data?.results.map(row => <li key={row.appointment_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
      <div className="text-sm">
        <p className="dashboard-heading font-semibold">{row.role_name} · Appointment #{row.appointment_id}</p>
        <p className="dashboard-muted text-xs">Account #{row.account_id} · Valid {new Date(row.valid_from).toLocaleDateString()} to {new Date(row.valid_until).toLocaleDateString()}</p>
      </div>
      <div className="flex gap-2">{kind === 'submitted' ? <>
        <button type="button" className={primary} onClick={() => onDecision(row, 'verify')}>Verify</button>
        <button type="button" className={button} onClick={() => onDecision(row, 'reject')}>Reject</button>
      </> : <button type="button" className={button} onClick={() => onDecision(row, 'revoke')}>Revoke evidence</button>}</div>
    </li>)}</ul>
    {state.data && (page > 1 || state.data.has_next) && <nav aria-label={`${label} pages`} className="mt-3 flex items-center justify-between gap-2">
      <button type="button" className={button} disabled={page <= 1} onClick={() => {setState({loading:true}); setPage(p => p - 1);}}>Previous</button>
      <span className="dashboard-muted text-xs">Page {page}</span>
      <button type="button" className={button} disabled={!state.data.has_next} onClick={() => {setState({loading:true}); setPage(p => p + 1);}}>Next</button>
    </nav>}
  </div>;
}

export default function AppointmentManagementPanel({ permissions }: {permissions: readonly string[]}) {
  const canRecord = permissions.includes(RECORD);
  const canVerify = permissions.includes(VERIFY);
  const [ctugId, setCtugId] = useState('');
  const [role, setRole] = useState<AppointmentRole>('Treasurer');
  const [candidate, setCandidate] = useState<AppointmentCandidate | null>(null);
  const [start, setStart] = useState('');
  const [until, setUntil] = useState('');
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const recordFile = useRef<HTMLInputElement>(null);
  const reviewFile = useRef<HTMLInputElement>(null);
  const [decision, setDecision] = useState<{row: AppointmentRow; action: AppointmentDecision} | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);
  const [history, setHistory] = useState<AppointmentPage | null>(null);
  const [historyError, setHistoryError] = useState('');
  const [historyPage, setHistoryPage] = useState(1);
  const [historyTick, setHistoryTick] = useState(0);
  useEffect(() => {
    if (!canRecord) return;
    let active = true;
    listAppointments('mine', historyPage).then(value => { if (active) {setHistory(value);setHistoryError('');} })
      .catch((e: unknown) => { if (active) setHistoryError(explain(e)); });
    return () => {active = false;};
  }, [canRecord, historyPage, historyTick, reload]);
  const changeCandidate = () => { setCandidate(null); setMessage(''); setError(''); };
  async function find(e: FormEvent) {
    e.preventDefault(); if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setError(''); setMessage(''); setCandidate(null);
    try { setCandidate(await findCandidate(ctugId, role)); }
    catch (err: unknown) {setError(explain(err));}
    finally { inFlight.current = false; setBusy(false); }
  }
  async function record(e: FormEvent) {
    e.preventDefault(); if (!candidate || !recordFile.current?.files?.[0] || inFlight.current) return;
    if (!start || !until || !(Date.parse(start) < Date.parse(until))) {
      setError('Provide valid start and end dates, with the end after the start.'); return;
    }
    inFlight.current = true; setBusy(true); setError(''); setMessage('');
    try {
      const hash = await fingerprintOfficialFile(recordFile.current.files[0]);
      const result = await submitAppointment({ candidate, document_sha256: hash,
        valid_from: new Date(start).toISOString(), valid_until: new Date(until).toISOString() });
      setMessage(`Appointment #${result.appointment_id} submitted for independent review. This has NOT assigned any role.`);
      setCandidate(null); setStart(''); setUntil('');
      if (recordFile.current) recordFile.current.value = '';
      setHistoryPage(1);setHistoryTick(t => t + 1);
    } catch (err: unknown) { setError(explain(err)); }
    finally { inFlight.current = false; setBusy(false); }
  }
  async function confirmDecision() {
    if (!decision || inFlight.current) return;
    inFlight.current = true; setBusy(true); setMessage(''); setError('');
    const current = decision;
    try {
      const digest = current.action === 'verify'
        ? await fingerprintOfficialFile(reviewFile.current?.files?.[0] as File) : undefined;
      await decideAppointment(current.row, current.action, digest);
      setMessage(`Appointment #${current.row.appointment_id} marked ${current.action === 'verify' ? 'Verified' : current.action === 'reject' ? 'Rejected' : 'Revoked'}. No system role was assigned.`);
      setDecision(null); setReload(v => v + 1);setHistoryTick(t => t + 1);
    } catch (err: unknown) {setError(explain(err));setDecision(null);setReload(v => v + 1);}
    finally { inFlight.current = false; setBusy(false); }
  }
  return <div className="space-y-5">
    <section className="dashboard-panel rounded-2xl border p-4 sm:p-6">
      <h2 className="dashboard-heading text-lg font-semibold">Official appointment evidence</h2>
      <p className="dashboard-muted mt-1 text-sm">Recorders and independent reviewers have different permissions. Neither action grants a Treasurer or SSG Advisor role. A separate authorized Super Admin assigns roles after verification.</p>
      {(error || message) && <p role={error ? 'alert' : 'status'} className={`${error ? 'dashboard-error' : 'dashboard-success'} mt-3 rounded-lg border p-3 text-sm`}>{error || message}</p>}
    </section>
    {canRecord && <section className="dashboard-panel rounded-2xl border p-4 sm:p-6" aria-labelledby="appt-record-title">
      <h2 id="appt-record-title" className="dashboard-heading text-lg font-semibold">Record an appointment</h2>
      <p className="dashboard-muted mt-1 text-sm">Use an approved official appointment document. Only its SHA-256 fingerprint is submitted; the file stays on this device.</p>
      <form onSubmit={find} className="mt-4 grid gap-3 sm:grid-cols-3">
        <label className="dashboard-muted text-xs">CTU-G ID<input className={field} value={ctugId} onChange={e => {setCtugId(e.target.value);changeCandidate();}} required maxLength={50}/></label>
        <label className="dashboard-muted text-xs">Proposed responsibility<select className={field} value={role} onChange={e => {setRole(e.target.value as AppointmentRole);changeCandidate();}}><option>Treasurer</option><option>SSG Advisor</option></select></label>
        <button type="submit" className={button} disabled={busy}>Find eligible account</button>
      </form>
      {candidate && <form onSubmit={record} className="mt-4 grid gap-3 border-t pt-4 sm:grid-cols-2">
        <p className="dashboard-heading sm:col-span-2 text-sm font-semibold">Confirm: CTU-G ID {candidate.ctug_id} · {candidate.role_name}</p>
        <label className="dashboard-muted text-xs">Valid from (your local time)<input className={field} type="datetime-local" value={start} required onChange={e => setStart(e.target.value)}/></label>
        <label className="dashboard-muted text-xs">Valid until (your local time)<input className={field} type="datetime-local" value={until} required onChange={e => setUntil(e.target.value)}/></label>
        <label className="dashboard-muted text-xs sm:col-span-2">Official appointment document (local fingerprint only)<input ref={recordFile} className={field} type="file" required/></label>
        <p className="dashboard-muted text-xs sm:col-span-2">Recording creates a Submitted item. A different, independently authorized official must verify it using the institution's original source.</p>
        <button type="submit" className={primary} disabled={busy}>Submit for independent review</button>
      </form>}
    </section>}
    {canRecord && <section className="dashboard-panel rounded-2xl border p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="dashboard-heading font-semibold">My submissions</h2><button type="button" className={button} onClick={() => setHistoryTick(t => t + 1)}>Refresh</button></div>
      {historyError && <p role="alert" className="dashboard-error mt-2 text-sm">{historyError}</p>}
      <ul className="mt-3 divide-y">{history?.results.map(row => <li key={row.appointment_id} className="py-2 text-sm"><strong>#{row.appointment_id} · {row.role_name}</strong> · Account #{row.account_id} · {row.status}</li>)}</ul>
      {history && (historyPage > 1 || history.has_next) && <div className="mt-3 flex items-center gap-3"><button type="button" className={button} disabled={historyPage === 1} onClick={() => setHistoryPage(p=>p-1)}>Previous</button><span>Page {historyPage}</span><button type="button" className={button} disabled={!history.has_next} onClick={() => setHistoryPage(p=>p+1)}>Next</button></div>}
    </section>}
    {canVerify && <section className="space-y-4" aria-label="Independent appointment review">
      <p className="dashboard-muted text-sm">Reviewer: obtain the official appointment from an independent institutional source. Do not rely on a recorder's copy or fingerprint. Verification is not a role assignment.</p>
      <Queue key={`submitted-${reload}`} kind="submitted" label="Awaiting independent review" onDecision={(row, action) => {setError('');setDecision({row, action});}}/>
      <Queue key={`verified-${reload}`} kind="verified" label="Verified evidence (eligible for revocation review)" onDecision={(row, action) => {setError('');setDecision({row, action});}}/>
      <p className="dashboard-muted text-xs">An appointment cannot be revoked while its role is still assigned. An authorized Super Admin must revoke the role first; this screen cannot change roles.</p>
    </section>}
    <Modal open={!!decision} busy={busy} onClose={() => setDecision(null)} title={decision ? `${decision.action === 'verify' ? 'Verify' : decision.action === 'reject' ? 'Reject' : 'Revoke'} appointment #${decision.row.appointment_id}?` : 'Review appointment'}
      actions={<><button type="button" className={button} disabled={busy} onClick={() => setDecision(null)}>Cancel</button><button type="button" className={primary} disabled={busy} onClick={confirmDecision}>Confirm decision</button></>}>
      {decision && <div className="space-y-3 text-sm">
        <p>{decision.row.role_name}, account #{decision.row.account_id}. Verify the current official authority and validity dates independently before making a decision.</p>
        {decision.action === 'verify' && <label className="dashboard-muted block text-xs">Select the independently obtained official document. Its fingerprint is calculated here, never uploaded.<input key={decision.row.appointment_id} ref={reviewFile} type="file" className={`${field} mt-2`}/></label>}
        {decision.action === 'revoke' && <p className="dashboard-muted">If the ordinary role is still assigned, this request will be refused. Revoke the role separately first.</p>}
      </div>}
    </Modal>
  </div>;
}
