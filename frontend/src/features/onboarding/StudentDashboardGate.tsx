/** WF11-D17 Student dashboard boundary (shared routing; the server stays authoritative).
 *
 * While the session operates as a Student (the switch is on, the session reports the exact read code
 * and the server answers the onboarding status in the Student context), semester-dependent views open
 * only after the server reports a finalized onboarding for the CURRENT Active semester. Otherwise the
 * Student is routed (history *replaced*, so Back never loops) to Semester onboarding, which shows the
 * no-active-semester, onboarding, Pending Verification, Clearance Required or verification-needed state.
 *
 * Nothing is stored in the browser: the status is re-read on every mount, role switch, window focus,
 * page show and when another tab of the same browser reports a change (a BroadcastChannel ping that
 * carries no data). A refusal of the Student context (another role is selected) or a server whose
 * onboarding switch is off leaves the dashboard as it was; any other failure blocks only the
 * semester-dependent views (fail closed) with a retry. The backend gates the data independently.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { AuthenticatedWorkspaceSession } from '../auth/session';
import { OnboardingApiError, getStatus } from './onboardingApi';
import type { DashboardRoute, OnboardingState, Status } from './onboardingApi';
import { ONBOARDING_READ_CODE, STUDENT_ONBOARDING_ENABLED } from './onboardingConfig';
import { CHANNEL, GateContext, INACTIVE, exclusiveStudentSession } from './studentGateRules';
import type { StudentGate } from './studentGateRules';

type Result = { key: string; status: 'checking' | 'error' | 'inactive' | 'ready'; route: DashboardRoute | null;
  state: OnboardingState | null };

export function StudentDashboardGateProvider({ session, children }: { session: AuthenticatedWorkspaceSession; children: ReactNode }) {
  const eligible = STUDENT_ONBOARDING_ENABLED && session.permissions.includes(ONBOARDING_READ_CODE);
  const roleContext = session.role_context?.enabled === true;
  // A new account, role or permission set is a new context: never reuse an earlier answer for it.
  const key = `${session.account.school_id}|${session.role_context?.active_role_id ?? ''}|${session.permissions.join(',')}`;
  const [result, setResult] = useState<Result>({ key: '', status: 'checking', route: null, state: null });
  const [justCompleted, setJustCompleted] = useState(false);
  const sequence = useRef(0);
  const channel = useRef<BroadcastChannel | null>(null);
  const lastRoute = useRef<DashboardRoute | null>(null);

  const settle = useCallback((next: Result) => {
    setResult(next);
    if (next.route === 'dashboard' && lastRoute.current !== null && lastRoute.current !== 'dashboard') channel.current?.postMessage('changed');
    lastRoute.current = next.route;
  }, []);

  const load = useCallback(() => {
    if (!eligible) return;
    const mine = ++sequence.current;
    getStatus().then((s) => {
      if (mine === sequence.current) settle({ key, status: 'ready', route: s.dashboard_route, state: s.state });
    }).catch((error: unknown) => {
      if (mine !== sequence.current) return;
      const code = error instanceof OnboardingApiError ? error.detail.code : '';
      // Another selected role, or the server switch off: the Student boundary does not apply.
      const inactive = code === 'access_denied' || code === 'student_onboarding_unavailable' || code === 'feature_disabled';
      if (code === 'authentication_required') return; // the shell handles the ended session
      settle({ key, status: inactive ? 'inactive' : 'error', route: null, state: null });
    });
  }, [eligible, key, settle]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!eligible) return undefined;
    const onFocus = () => load();
    const onVisible = () => { if (document.visibilityState === 'visible') load(); };
    window.addEventListener('focus', onFocus);
    window.addEventListener('pageshow', onFocus);
    document.addEventListener('visibilitychange', onVisible);
    let bc: BroadcastChannel | null = null;
    if (typeof BroadcastChannel !== 'undefined') {
      bc = new BroadcastChannel(CHANNEL);
      bc.onmessage = () => load(); // the ping carries no data; the server answers
      channel.current = bc;
    }
    return () => {
      window.removeEventListener('focus', onFocus);
      window.removeEventListener('pageshow', onFocus);
      document.removeEventListener('visibilitychange', onVisible);
      bc?.close();
      channel.current = null;
    };
  }, [eligible, load]);

  const clearCompleted = useCallback(() => setJustCompleted(false), []);
  const apply = useCallback((s: Status) => {
    sequence.current++; // a server answer newer than any request still in flight
    if (s.dashboard_route === 'dashboard' && lastRoute.current !== null && lastRoute.current !== 'dashboard') setJustCompleted(true);
    settle({ key, status: 'ready', route: s.dashboard_route, state: s.state });
  }, [key, settle]);

  const value = useMemo<StudentGate>(() => {
    if (!eligible) return INACTIVE;
    const current = result.key === key ? result : { key, status: 'checking' as const, route: null, state: null };
    return { status: current.status, route: current.route, state: current.state,
      exclusive: exclusiveStudentSession(session.permissions, roleContext), justCompleted, refresh: load, apply,
      clearCompleted };
  }, [eligible, result, key, session.permissions, roleContext, justCompleted, load, apply, clearCompleted]);

  return <GateContext.Provider value={value}>{children}</GateContext.Provider>;
}
