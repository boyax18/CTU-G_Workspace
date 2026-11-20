// WF-01.01/WF-01.02 audit corrections (owner-approved 16 Nov 2026):
// R-05 resumed notice flag, R-06 neutral no-session wording, R-09 pasted codes,
// R-10 timeout fallback, OD-3 configured code-lifetime guidance.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { postJSON, timeoutSignal } from '../src/api/client.ts';
import { getRegistrationVerification, markRegistrationResumed, takeRegistrationResumed, verificationPath } from '../src/features/auth/registration.ts';
import { codeGuidance, NO_SAVED_ATTEMPT, normalizeCode } from '../src/features/auth/registrationFeedback.ts';

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const summary = { status: 'verification_required', delivery_sent: true, expires_in: 1800, retry_after: 60, resends_remaining: 3, attempts_remaining: 5 };

async function withFetch(mock, action) {
  const original = globalThis.fetch;
  globalThis.fetch = mock;
  try { await action(); } finally { globalThis.fetch = original; }
}

function withStorage(storage, action) {
  const original = globalThis.window;
  globalThis.window = { sessionStorage: storage };
  try { return action(); } finally { globalThis.window = original; }
}

test('R-10: requests still carry a timeout signal when AbortSignal.timeout is unavailable', async () => {
  const original = AbortSignal.timeout;
  try {
    AbortSignal.timeout = undefined;
    const signal = timeoutSignal(50);
    assert.ok(signal instanceof AbortSignal);
    assert.equal(signal.aborted, false);
    await new Promise(resolve => setTimeout(resolve, 80));
    assert.equal(signal.aborted, true);
    let seen;
    await withFetch(async (path, options) => { seen = options.signal; return path.endsWith('/csrf/') ? json({ csrfToken: 't' }) : json({ ok: true }); },
      () => postJSON('/api/v1/auth/register/cancel/', {}));
    assert.ok(seen instanceof AbortSignal);
  } finally {
    AbortSignal.timeout = original;
  }
});

test('R-10: native AbortSignal.timeout is used when present', () => {
  assert.ok(timeoutSignal() instanceof AbortSignal);
});

test('OD-3: configured code lifetime is parsed from success summaries only when valid', async () => {
  await withFetch(async () => json({ ...summary, code_valid_seconds: 600 }, 202), async () => {
    assert.equal((await getRegistrationVerification()).code_valid_seconds, 600);
  });
  for (const bad of [0, -5, 1.5, '600', 999999]) {
    await withFetch(async () => json({ ...summary, code_valid_seconds: bad }, 202), async () => {
      assert.equal('code_valid_seconds' in (await getRegistrationVerification()), false);
    });
  }
  await withFetch(async () => json(summary, 202), async () => {
    assert.equal('code_valid_seconds' in (await getRegistrationVerification()), false);
  });
});

test('OD-3: guidance states the configured minutes and the spam-folder hint', () => {
  assert.equal(codeGuidance(600), "The code is valid for 10 minutes. If you don't see the email, check your spam or junk folder.");
  assert.equal(codeGuidance(60), "The code is valid for 1 minute. If you don't see the email, check your spam or junk folder.");
  assert.equal(codeGuidance(30), "The code is valid for 1 minute. If you don't see the email, check your spam or junk folder.");
  assert.equal(codeGuidance(undefined), "If you don't see the email, check your spam or junk folder.");
});

test('R-09: pasted codes with separators keep exactly six digits', () => {
  assert.equal(normalizeCode('123-456'), '123456');
  assert.equal(normalizeCode(' 123 456 '), '123456');
  assert.equal(normalizeCode('1234567'), '123456');
  assert.equal(normalizeCode('abc'), '');
});

test('R-05: resumed flag is one-shot, non-identifying and safe without storage', () => {
  const values = new Map();
  const storage = { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
  withStorage(storage, () => {
    assert.equal(takeRegistrationResumed(), false);
    markRegistrationResumed();
    assert.deepEqual([...values.values()], ['1']);
    assert.equal(takeRegistrationResumed(), true);
    assert.equal(takeRegistrationResumed(), false);
  });
  const broken = { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); }, removeItem() { throw new Error('blocked'); } };
  withStorage(broken, () => {
    assert.doesNotThrow(() => markRegistrationResumed());
    assert.equal(takeRegistrationResumed(), false);
  });
});

test('verification path keeps the role-only query and adds no identity', () => {
  assert.equal(verificationPath('Student'), '/register/verify');
  assert.equal(verificationPath('Instructor'), '/register/verify?requested_role=Instructor');
});

test('R-06: no-session wording does not claim the attempt expired', () => {
  assert.doesNotMatch(NO_SAVED_ATTEMPT, /has expired/);
  assert.match(NO_SAVED_ATTEMPT, /may have expired, been cancelled, or already been submitted for review/);
});
