/** WF-03.06 audit read API: bounded parsing, no writes or permission claims. */
import { ApiError, getJSON } from '../../api/client.ts';
import { ACCESS_AUDIT_ENABLED, ACCESS_AUDIT_ROOT } from './accessAuditConfig.ts';

export type AuditFilters = {actor:string; target:string; action:string; from:string; to:string};
export type AuditEvent = {audit_id:number;action:string;occurred_at:string;actor_ctug_id:string;
  target_ctug_id:string|null;role_name:string|null;permission_code:string|null};
export type AuditPage = {page:number;page_size:number;has_next:boolean;events:AuditEvent[]};
export type AuditDetail = AuditEvent & {reason:string|null;old_value:Record<string,unknown>|null;
  new_value:Record<string,unknown>|null;old_redacted:boolean;new_redacted:boolean};
const record = (v:unknown):v is Record<string,unknown> => v !== null && typeof v === 'object' && !Array.isArray(v);
const num = (v:unknown):v is number => typeof v === 'number' && Number.isInteger(v) && v>=1 && v<=2147483647;
const str = (v:unknown,max:number):v is string => typeof v === 'string' && v.length>0 && v.length<=max;
const nullable = (v:unknown,max:number) => v===null || str(v,max);
const fail = (): ApiError => new ApiError('Unexpected audit-history response.',0,'invalid_response');
const ensureOn = () => { if(!ACCESS_AUDIT_ENABLED) throw new ApiError('Audit history is disabled.',503,'review_unavailable'); };
const dateTime = (v:unknown) => str(v,64) && /^\d{4}-\d{2}-\d{2}T/.test(v);

function parseEvent(v:unknown):AuditEvent {
  if(!record(v) || !num(v.audit_id) || !str(v.action,50) || !dateTime(v.occurred_at)
    || !str(v.actor_ctug_id,50) || !nullable(v.target_ctug_id,50)
    || !nullable(v.role_name,50) || !nullable(v.permission_code,150)) throw fail();
  return v as unknown as AuditEvent;
}

export async function getAuditPage(filters:AuditFilters,page:number):Promise<AuditPage> {
  ensureOn();
  if(!Number.isInteger(page)||page<1||page>1000) throw fail();
  const params = new URLSearchParams({page:String(page)});
  for(const key of ['actor','target','action','from','to'] as const){
    const value=filters[key].trim();if(value) params.set(key,value);
  }
  const data = await getJSON(`${ACCESS_AUDIT_ROOT}events/?${params}`);
  if(!record(data)||data.page!==page||data.page_size!==20||typeof data.has_next!=='boolean'
      ||!Array.isArray(data.events)||data.events.length>20) throw fail();
  const seen = new Set<number>();
  const events = data.events.map((entry:unknown)=>{const e=parseEvent(entry);
    if(seen.has(e.audit_id)) throw fail();seen.add(e.audit_id);return e;});
  if(data.has_next && events.length!==20) throw fail();
  return {page,page_size:20,has_next:data.has_next,events};
}

const state = (v:unknown):v is Record<string,unknown>|null => v===null ||
  (record(v) && Object.keys(v).length<=20 && JSON.stringify(v).length<=2048);
export async function getAuditDetail(auditId:number):Promise<AuditDetail> {
  ensureOn();if(!num(auditId)) throw fail();
  const data = await getJSON(`${ACCESS_AUDIT_ROOT}events/${auditId}/`);
  const event = parseEvent(data);
  if(event.audit_id!==auditId || !record(data) || !nullable(data.reason,255)
    || !state(data.old_value) || !state(data.new_value)
    || typeof data.old_redacted!=='boolean' || typeof data.new_redacted!=='boolean') throw fail();
  return data as unknown as AuditDetail;
}
