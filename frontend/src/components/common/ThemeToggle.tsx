import type { KeyboardEvent } from 'react';
import { useTheme } from '../../hooks/useTheme';
import type { ThemePreference } from '../../contexts/themeContext';
import { MonitorIcon, MoonIcon, SunIcon } from './Icons';

const OPTIONS: { value: ThemePreference; label: string; Icon: typeof SunIcon }[] = [
  { value: 'light', label: 'Light', Icon: SunIcon },
  { value: 'system', label: 'System default', Icon: MonitorIcon },
  { value: 'dark', label: 'Dark', Icon: MoonIcon },
];

export default function ThemeToggle() {
  const { preference, setPreference } = useTheme();
  const index = OPTIONS.findIndex((o) => o.value === preference);

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    let next = index;
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') next = (index + 1) % OPTIONS.length;
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') next = (index - 1 + OPTIONS.length) % OPTIONS.length;
    else return;
    e.preventDefault();
    setPreference(OPTIONS[next].value);
    e.currentTarget.querySelectorAll<HTMLButtonElement>('button')[next]?.focus();
  };

  return (
    <div
      role="radiogroup"
      aria-label="Color theme"
      onKeyDown={onKeyDown}
      className="theme-toggle relative grid grid-cols-3 rounded-full p-0.5"
    >
      <span aria-hidden className="theme-thumb" style={{ transform: `translateX(${index * 100}%)` }} />
      {OPTIONS.map(({ value, label, Icon }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={preference === value}
          aria-label={label}
          title={label}
          tabIndex={preference === value ? 0 : -1}
          onClick={() => setPreference(value)}
          className="theme-opt relative z-10 flex h-7 w-8 items-center justify-center rounded-full"
        >
          <Icon width={15} height={15} />
        </button>
      ))}
    </div>
  );
}
