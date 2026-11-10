import { createContext } from 'react';
import type { AuthenticatedWorkspaceSession } from '../features/auth/session';
import type { DashboardView } from '../features/dashboard/navigation';

export interface DashboardContextValue {
  session: AuthenticatedWorkspaceSession;
  view: DashboardView;
  navigate: (next: DashboardView) => void;
}

export const DashboardContext = createContext<DashboardContextValue | null>(null);
