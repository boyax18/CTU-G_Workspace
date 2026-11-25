/** Non-component helpers shared by the Academic settings tabs. */
import { ConfigApiError } from '../academicConfigurationApi.ts';

export function fieldErrors(error: unknown): Record<string, string> {
  return error instanceof ConfigApiError ? error.detail.fields : {};
}

export const YEAR_LEVEL_OPTIONS = [1, 2, 3, 4, 5, 6].map((n) => ({ value: String(n), label: `Year ${n}` }));
export const TERM_OPTIONS = [{ value: 'first', label: 'First semester' }, { value: 'second', label: 'Second semester' }];

/** "" -> null; "3" -> "3"; trimmed. Units stay strings so the server parses them exactly. */
export const blankToNull = (value: string | undefined) => (value && value.trim() ? value.trim() : null);
export const toInt = (value: string | undefined) => (value && /^\d+$/.test(value.trim()) ? Number(value.trim()) : NaN);
