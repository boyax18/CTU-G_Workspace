// Real HTTP demonstration using the same client as RegisterPage. Requires the
// disposable backend helper; refuses to submit to a normal development server.
import assert from 'node:assert/strict';
import { submitRegistration } from '../src/features/auth/registration.ts';

const base = 'http://127.0.0.1:5174';
const originalFetch = globalThis.fetch;
const probe = await originalFetch(`${base}/api/v1/auth/csrf/`);
const database = probe.headers.get('X-Registration-Demo-Database');
assert.match(database || '', /^test_ctug_registration_[0-9a-f]{16}$/, 'Refusing submission: disposable demo backend is not running.');
let cookie = '';
globalThis.fetch = async (path, options = {}) => {
  const headers = new Headers(options.headers);
  if (cookie) headers.set('Cookie', cookie);
  if (options.method === 'POST') headers.set('Origin', base);
  const response = await originalFetch(new URL(path, base), { ...options, headers });
  const setCookie = response.headers.get('set-cookie');
  if (setCookie) cookie = setCookie.split(';', 1)[0];
  assert.equal(response.headers.get('X-Registration-Demo-Database'), database);
  return response;
};

try {
  for (const role of ['Student', 'Instructor']) {
    await submitRegistration({
      school_id: `DEMO-${role}-${Date.now()}`, email: '', first_name: 'Demo', middle_name: '',
      last_name: 'Registrant', suffix: '', requested_role: role,
      password: 'Copper!River7392', password_confirmation: 'Copper!River7392',
    });
    console.log(`${role}: real frontend client -> Vite proxy -> CSRF-protected Django API -> HTTP 202`);
  }
  console.log(`Isolated database: ${database}. See the backend terminal for persisted account/profile evidence.`);
} finally {
  globalThis.fetch = originalFetch;
}
