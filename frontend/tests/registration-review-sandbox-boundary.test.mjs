import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const file = (name) => readFileSync(new URL(name, import.meta.url), 'utf8');

test('real production review API gate remains hard-disabled', () => {
  assert.match(file('../src/features/admin/registrationReviewApiGate.ts'), /REGISTRATION_REVIEW_LIVE_API_ENABLED: boolean = false/);
});

test('real production review route remains null', () => {
  assert.match(file('../src/features/admin/registrationReviewLiveConfig.ts'), /REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT: string \| null = null/);
});

test('sandbox substitutions require development build and explicit marker', () => {
  assert.match(file('../sandbox/registrationReviewApiGate.ts'), /import\.meta\.env\.DEV/);
  assert.match(file('../sandbox/registrationReviewApiGate.ts'), /SANDBOX_ONLY/);
  assert.match(file('../sandbox/registrationReviewLiveConfig.ts'), /import\.meta\.env\.DEV/);
  assert.match(file('../sandbox/registrationReviewLiveConfig.ts'), /api\/v1\/admin\/registration-requests\//);
});

test('dedicated Vite config proxies exclusively to local sandbox backend', () => {
  const config = file('../vite.review-sandbox.config.ts');
  assert.match(config, /CTUG_REVIEW_SANDBOX_ACK/);
  assert.match(config, /127\.0\.0\.1:8001/);
  assert.match(config, /host: '127\.0\.0\.1'/);
  assert.match(config, /registrationReviewApiGate/);
  assert.match(config, /registrationReviewLiveConfig/);
});


test('sandbox Vite aliases resolve both extensionless and .ts review imports only', () => {
  const gate = /^(?:\.{1,2}\/)+(?:[^/]+\/)*registrationReviewApiGate(?:\.ts)?$/;
  const root = /^(?:\.{1,2}\/)+(?:[^/]+\/)*registrationReviewLiveConfig(?:\.ts)?$/;
  assert.ok(gate.test('../admin/registrationReviewApiGate'));
  assert.ok(gate.test('./registrationReviewApiGate.ts'));
  assert.ok(root.test('./registrationReviewLiveConfig.ts'));
  assert.equal('../admin/registrationReviewApiGate'.replace(gate, '/sandbox/gate.ts'), '/sandbox/gate.ts');
  assert.equal('./registrationReviewLiveConfig.ts'.replace(root, '/sandbox/route.ts'), '/sandbox/route.ts');
  assert.ok(!gate.test('./registrationReviewPreviewGate.ts'));
});
