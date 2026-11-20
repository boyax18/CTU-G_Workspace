import { useContext } from 'react';
import { DashboardContext } from '../contexts/DashboardContext';

export function useDashboardContext() {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error('useDashboardContext must be used inside DashboardLayout');
  }
  return context;
}
