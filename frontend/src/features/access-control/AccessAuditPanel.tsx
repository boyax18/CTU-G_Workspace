/** WF-03.06 read-only governance audit history. No mutations in this screen. */
import { useRef, useState } from 'react';
import { ApiError } from '../../api/client.ts';
import { getAuditDetail, getAuditPage } from './accessAuditApi.ts';
import type { AuditDetail, AuditFilters, AuditPage } from './accessAuditApi.ts';

const input = 'dashboard-panel mt-1 block min-h-11 w-full rounded-lg border px-3 py-2 text-sm';
const button = 'dashboard-panel min-h-11 rounded-lg border px-4 py-2 text-sm font-medium disabled:opacity-50';
const primary = 'dashboard-primary-link min-h-11 rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50';
const empty:AuditFilters = {actor:'',target:'',action:'',from:'',to:''};
function explain(error:unknown):string {
  if(error instanceof ApiError){
    if(error.status===401)return 'Your session ended; sign in again.';
    if(error.status===403)return 'Your active role is not authorized to read audit history.';
    if(error.status===404)return 'This audit entry is no longer available.';
    if(error.status===503)return 'Audit history is unavailable in this configuration.';
    return error.message;
  }
  return 'Could not load audit records. Try again.';
}
function formatTime(raw:string):string {
  const instant=new Date(raw);return Number.isNaN(instant.getTime())?raw:instant.toLocaleString();
}
function snapshot(value:Record<string,unknown>|null,redacted:boolean):string {
  if(redacted)return 'Redacted: legacy or unsupported audit snapshot.';
  return value===null?'No snapshot recorded.':JSON.stringify(value,null,2);
}

export default function AccessAuditPanel({permissions}:{permissions:readonly string[]}) {
  const [filters,setFilters]=useState<AuditFilters>(empty);
  const [page,setPage]=useState<AuditPage|null>(null);
  const [detail,setDetail]=useState<AuditDetail|null>(null);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState('');
  const version=useRef(0);
  async function load(number:number) {
    const current=++version.current;setLoading(true);setError('');setDetail(null);
    try {const next=await getAuditPage(filters,number);if(current===version.current)setPage(next);}
    catch(err){if(current===version.current){setError(explain(err));setPage(null);}}
    finally{if(current===version.current)setLoading(false);}
  }
  async function inspect(id:number) {
    const current=++version.current;setLoading(true);setError('');setDetail(null);
    try {const next=await getAuditDetail(id);if(current===version.current)setDetail(next);}
    catch(err){if(current===version.current)setError(explain(err));}
    finally{if(current===version.current)setLoading(false);}
  }
  if(!permissions.includes('access_control.audit.read'))
    return <p role="alert" className="dashboard-muted text-sm">Audit history is not available in this role context.</p>;
  return <div className="space-y-5">
    <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
      <h2 className="dashboard-heading text-lg font-bold">Access-control audit history</h2>
      <p className="dashboard-muted mt-2 text-sm">Read-only history of access-control changes. Filters use exact CTU-G IDs and action codes. Original records cannot be edited from this page.</p>
      <form className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3" onSubmit={e=>{e.preventDefault();void load(1);}}>
        <label className="dashboard-muted text-sm">Actor CTU-G ID<input className={input} maxLength={50} value={filters.actor} onChange={e=>setFilters(s=>({...s,actor:e.target.value}))}/></label>
        <label className="dashboard-muted text-sm">Target CTU-G ID<input className={input} maxLength={50} value={filters.target} onChange={e=>setFilters(s=>({...s,target:e.target.value}))}/></label>
        <label className="dashboard-muted text-sm">Exact action code<input className={input} maxLength={50} value={filters.action} onChange={e=>setFilters(s=>({...s,action:e.target.value}))} placeholder="account.role.assign"/></label>
        <label className="dashboard-muted text-sm">From date (UTC)<input type="date" className={input} value={filters.from} onChange={e=>setFilters(s=>({...s,from:e.target.value}))}/></label>
        <label className="dashboard-muted text-sm">To date (UTC)<input type="date" className={input} value={filters.to} onChange={e=>setFilters(s=>({...s,to:e.target.value}))}/></label>
        <div className="flex items-end gap-2"><button type="submit" disabled={loading} className={primary}>Search audit</button>
          <button type="button" disabled={loading} className={button} onClick={()=>{setFilters(empty);setPage(null);setDetail(null);setError('');version.current++;}}>Clear</button></div>
      </form>
    </section>
    {loading && <p className="dashboard-muted text-sm" role="status">Loading audit history…</p>}
    {error && <p className="dashboard-error-block rounded-xl border p-4 text-sm" role="alert">{error}</p>}
    {page && <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
      <div className="flex items-center justify-between gap-3"><h3 className="dashboard-heading text-lg font-bold">Audit entries</h3><span className="dashboard-muted text-xs">Page {page.page}</span></div>
      <div className="mt-4 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="dashboard-muted border-b">
        <th className="p-2">Recorded (local time)</th><th className="p-2">Action</th><th className="p-2">Actor</th><th className="p-2">Target</th><th className="p-2">Details</th>
      </tr></thead><tbody>{page.events.map(entry=><tr className="border-b" key={entry.audit_id}>
        <td className="p-2 whitespace-nowrap">{formatTime(entry.occurred_at)}</td><td className="p-2 break-all">{entry.action}</td>
        <td className="p-2">{entry.actor_ctug_id}</td><td className="p-2">{entry.target_ctug_id??'—'}</td>
        <td className="p-2"><button type="button" className={button} disabled={loading} onClick={()=>void inspect(entry.audit_id)}>View</button></td>
      </tr>)}</tbody></table></div>
      {page.events.length===0 && <p className="dashboard-muted mt-4 text-sm">No matching audit entries.</p>}
      <div className="mt-4 flex items-center justify-end gap-2">
        <button type="button" className={button} disabled={loading||page.page<=1} onClick={()=>void load(page.page-1)}>Previous</button>
        <button type="button" className={button} disabled={loading||!page.has_next||page.page>=1000} onClick={()=>void load(page.page+1)}>Next</button>
      </div>
    </section>}
    {detail && <section className="dashboard-panel rounded-2xl border p-5 sm:p-6" aria-labelledby="audit-detail-heading">
      <div className="flex items-center justify-between"><h3 className="dashboard-heading text-lg font-bold" id="audit-detail-heading">Event #{detail.audit_id}</h3>
        <button type="button" className={button} onClick={()=>setDetail(null)}>Close</button></div>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <div><dt className="dashboard-muted">Action</dt><dd className="dashboard-heading break-all">{detail.action}</dd></div>
        <div><dt className="dashboard-muted">Recorded</dt><dd>{formatTime(detail.occurred_at)}</dd></div>
        <div><dt className="dashboard-muted">Actor CTU-G ID</dt><dd>{detail.actor_ctug_id}</dd></div>
        <div><dt className="dashboard-muted">Target CTU-G ID</dt><dd>{detail.target_ctug_id??'None'}</dd></div>
        <div><dt className="dashboard-muted">Role</dt><dd>{detail.role_name??'None'}</dd></div>
        <div><dt className="dashboard-muted">Permission</dt><dd className="break-all">{detail.permission_code??'None'}</dd></div>
        <div><dt className="dashboard-muted">Reason code</dt><dd>{detail.reason??'Not recorded'}</dd></div>
      </dl>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div><h4 className="dashboard-heading text-sm font-semibold">Before</h4><pre className="dashboard-muted mt-2 max-h-64 overflow-auto rounded-xl border p-3 text-xs whitespace-pre-wrap break-all">{snapshot(detail.old_value,detail.old_redacted)}</pre></div>
        <div><h4 className="dashboard-heading text-sm font-semibold">After</h4><pre className="dashboard-muted mt-2 max-h-64 overflow-auto rounded-xl border p-3 text-xs whitespace-pre-wrap break-all">{snapshot(detail.new_value,detail.new_redacted)}</pre></div>
      </div>
      <p className="dashboard-muted mt-4 border-t pt-3 text-xs">Recorded values are controlled audit-state fields. This history is informational and never substitutes for current permission checks.</p>
    </section>}
  </div>;
}
