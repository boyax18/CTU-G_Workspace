import { forwardRef } from 'react';
import type { InputHTMLAttributes, ReactNode } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  id: string;
  error?: string;
  rightAdornment?: ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, id, error, rightAdornment, className = '', ...rest },
  ref,
) {
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
          aria-describedby={error ? `${id}-error` : undefined}
          className={`field w-full rounded-lg px-3 py-2.5 text-sm ${error ? 'field-error' : ''} ${rightAdornment ? 'pr-10' : ''} ${className}`}
          {...rest}
        />
        {rightAdornment && <div className="absolute inset-y-0 right-0 flex items-center pr-2">{rightAdornment}</div>}
      </div>
      {error && (
        <p id={`${id}-error`} role="alert" className="fg-error mt-1 text-xs">
          {error}
        </p>
      )}
    </div>
  );
});

export default Input;
