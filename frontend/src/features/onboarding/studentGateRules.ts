/** Shared Student dashboard boundary rules and context (see StudentDashboardGate.tsx). */
import { createContext, useContext } from 'react';
import { getVisibleNavGroups } from '../dashboard/navigation.ts';
import type { DashboardView } from '../dashboard/navigation.ts';
import type { DashboardRoute, OnboardingState, Status } from './onboardingApi.ts';

/** Views whose content depends on the finalized current-semester participation. */
export const STUDENT_SEMESTER_VIEWS: readonly DashboardView[] = ['my-subjects'];
/** Where a blocked Student is routed; it renders every non-completed state. */
export const GATE_TARGET: DashboardView = 'semester-onboarding';
/** Groups of a Student-only dashboard (account, profile, campus and own finance/academic records). */
const STUDENT_GROUPS = new Set(['overview', 'academic', 'finance', 'campus']);
export const CHANNEL = 'ctug-student-onboarding';

export type GateStatus = 'inactive' | 'checking' | 'error' | 'ready';
export interface StudentGate {
  status: GateStatus;
  route: DashboardRoute | null;
  state: OnboardingState | null;
  /** True when the session is a Student-only context, so the ordinary dashboard home is gated too. */
  exclusive: boolean;
  justCompleted: boolean;
  refresh: () => void;
  /** Apply a status the server just returned (a step, the review or the finalization). */
  apply: (status: Status) => void;
  clearCompleted: () => void;
}

export const INACTIVE: StudentGate = { status: 'inactive', route: null, state: null, exclusive: false, justCompleted: false,
  refresh: () => undefined, apply: () => undefined, clearCompleted: () => undefined };
export const GateContext = createContext<StudentGate>(INACTIVE);

export function useStudentGate(): StudentGate {
  return useContext(GateContext);
}

/** Role context on: permissions are already scoped to the selected role. Off: decide from the visible modules. */
export function exclusiveStudentSession(permissions: readonly string[], roleContextEnabled: boolean): boolean {
  return roleContextEnabled || getVisibleNavGroups(permissions, 'main').every((group) => STUDENT_GROUPS.has(group.id));
}

export function isProtectedStudentView(view: DashboardView, exclusive: boolean): boolean {
  return STUDENT_SEMESTER_VIEWS.includes(view) || (exclusive && view === 'overview');
}

export type Guard = 'allow' | 'wait' | 'redirect' | 'error';
export function guardFor(view: DashboardView, gate: Pick<StudentGate, 'status' | 'route' | 'exclusive'>): Guard {
  if (gate.status === 'inactive' || !isProtectedStudentView(view, gate.exclusive)) return 'allow';
  if (gate.status === 'checking') return 'wait';
  if (gate.status === 'error') return 'error';
  return gate.route === 'dashboard' ? 'allow' : 'redirect';
}

