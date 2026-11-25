import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError } from '../../api/client';
import { getSettings, updateSettings } from './api';
import type { AccountSettings } from './api';

const empty: AccountSettings = { first_name: '', middle_name: '', last_name: '', suffix: '', email: '' };

export default function SettingsPage() {
  const [settings, setSettings] = useState<AccountSettings>(empty);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    let cancelled = false;
    getSettings()
      .then((result) => { if (!cancelled) setSettings(result); })
      .catch((caught) => {
        if (!cancelled) setError(caught instanceof ApiError ? caught.message : 'Unable to load settings.');
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      setSettings(await updateSettings(settings));
      setSuccess('Account settings saved.');
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to save settings.');
    } finally {
      setSaving(false);
    }
  };

  const change = (field: keyof AccountSettings, value: string) =>
    setSettings((current) => ({ ...current, [field]: value }));

  if (loading) return <p className="dashboard-muted" role="status">Loading settings...</p>;

  return (
    <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
      <h2 className="dashboard-heading text-lg font-semibold">Account settings</h2>
      {error && <p className="mt-4 text-sm" role="alert">{error}</p>}
      {success && <p className="mt-4 text-sm" role="status">{success}</p>}
      <form className="mt-5 grid gap-4 sm:grid-cols-2" onSubmit={save}>
        {([
          ['first_name', 'First name'],
          ['middle_name', 'Middle name'],
          ['last_name', 'Last name'],
          ['suffix', 'Suffix'],
          ['email', 'Email'],
        ] as [keyof AccountSettings, string][]).map(([field, label]) => (
          <label key={field} className="dashboard-heading text-sm font-medium">
            {label}
            <input
              type={field === 'email' ? 'email' : 'text'}
              className="mt-2 w-full rounded-lg border px-3 py-2"
              value={settings[field]}
              onChange={(event) => change(field, event.target.value)}
            />
          </label>
        ))}
        <button type="submit" disabled={saving} className="mt-2 min-h-11 w-fit rounded-lg bg-green-700 px-5 py-2 text-sm font-semibold text-white disabled:opacity-50 sm:col-span-2">
          {saving ? 'Saving...' : 'Save settings'}
        </button>
      </form>
    </section>
  );
}
