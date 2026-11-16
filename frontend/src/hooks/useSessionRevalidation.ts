import { useEffect, useRef } from 'react';
import { subscribeSessionSignals } from '../utils/sessionSignals';

/** Re-run `recheck` on every session signal (see utils/sessionSignals.ts). */
export function useSessionRevalidation(recheck: () => void): void {
  const latest = useRef(recheck);
  useEffect(() => { latest.current = recheck; }, [recheck]);
  useEffect(() => subscribeSessionSignals(() => latest.current()), []);
}
