import { createContext } from 'react';
import type { AuthenticatedWorkspaceSession } from '../features/auth/session';
import type { DashboardView } from '../features/dashboard/navigation';

/** A page inside the current view (for example one application inside Applicant reviews). */
export interface DashboardSubpage {
  /** Fourth breadcrumb, for example "CTU-G ID 7240001". */
  label: string;
  /** Replaces the view's description in the page header. */
  description?: string;
}

export interface DashboardContextValue {
  session: AuthenticatedWorkspaceSession;
  view: DashboardView;
  navigate: (next: DashboardView) => void;
  /** The current query string, for example "?view=registration-review&applicant=12". */
  search: string;
  /** Pushes the CURRENT view with extra query parameters (null returns to the view itself). */
  openSubpage: (params: Record<string, string> | null) => void;
  subpage: DashboardSubpage | null;
  setSubpage: (subpage: DashboardSubpage | null) => void;
}

export const DashboardContext = createContext<DashboardContextValue | null>(null);
