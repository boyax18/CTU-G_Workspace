import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { ThemeContext } from './themeContext';
import type { ResolvedTheme, ThemePreference } from './themeContext';

const STORAGE_KEY = 'ctug-theme';
const DARK_QUERY = '(prefers-color-scheme: dark)';

function readPreference(): ThemePreference {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  } catch {
    /* storage unavailable: fall back to system */
  }
  return 'system';
}

function readSystemTheme(): ResolvedTheme {
  return window.matchMedia(DARK_QUERY).matches ? 'dark' : 'light';
}

export default function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<ThemePreference>(readPreference);
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>(readSystemTheme);
  const resolved: ResolvedTheme = preference === 'system' ? systemTheme : preference;

  // Follow the operating system while the preference is "system".
  useEffect(() => {
    const query = window.matchMedia(DARK_QUERY);
    const onChange = () => setSystemTheme(query.matches ? 'dark' : 'light');
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('dark', resolved === 'dark');
    // Explicit "Dark" is pure black; "System" on a dark device keeps the softer green dark theme.
    root.classList.toggle('theme-black', preference === 'dark');
    root.style.colorScheme = resolved;
  }, [resolved, preference]);

  const setPreference = useCallback((next: ThemePreference) => {
    // Fade colors only while switching, so normal hover states stay snappy.
    const root = document.documentElement;
    root.classList.add('theme-transition');
    window.setTimeout(() => root.classList.remove('theme-transition'), 450);
    setPreferenceState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next); // theme choice only, never credentials
    } catch {
      /* ignore */
    }
  }, []);

  const value = useMemo(() => ({ preference, resolved, setPreference }), [preference, resolved, setPreference]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
