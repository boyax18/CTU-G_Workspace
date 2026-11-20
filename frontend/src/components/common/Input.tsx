import { forwardRef } from 'react';
import type { InputHTMLAttributes, ReactNode } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  id: string;
  error?: string;
  rightAdornment?: ReactNode;
  /**
   * Announce the field error as its own alert. Forms that already show an
   * assertive error summary pass false, so screen readers hear one announcement;
   * the field error stays linked through aria-describedby.
   */
  announceError?: boolean;
}

const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, id, error, rightAdornment, className = '', announceError = true, 'aria-describedby': describedBy, ...rest },
  ref,
) {
  const descriptions = [describedBy, error ? `${id}-error` : undefined].filter(Boolean).join(' ') || undefined;
  return (
    <div>
      <label htmlFor={id} className="fg-body mb-1.5 block text-xs font-medium">
        {label}
      </label>
      <div className="relative">
        <input
          ref={ref}
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={descriptions}
          className={`field w-full rounded-lg px-3 py-2.5 text-sm ${error ? 'field-error' : ''} ${rightAdornment ? 'pr-10' : ''} ${className}`}
          {...rest}
        />
        {rightAdornment && <div className="absolute inset-y-0 right-0 flex items-center pr-2">{rightAdornment}</div>}
      </div>
      {error && (
        <p id={`${id}-error`} role={announceError ? 'alert' : undefined} className="fg-error mt-1 text-xs">
          {error}
        </p>
      )}
    </div>
  );
});

export default Input;
