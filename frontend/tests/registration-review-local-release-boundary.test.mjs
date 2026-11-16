import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (name) => readFileSync(new URL(name, import.meta.url), 'utf8');

test('normal review API flag remains compile-time false', () => {
  assert.match(read('../src/features/admin/registrationReviewApiGate.ts'), /REGISTRATION_REVIEW_LIVE_API_ENABLED: boolean = false/);
});
test('normal review API root remains null', () => {
  assert.match(read('../src/features/admin/registrationReviewLiveConfig.ts'), /REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT: string \| null = null/);
});
test('local frontend requires both DEV and explicit marker', () => {
  const gate = read('../local_review/registrationReviewApiGate.ts');
  const route = read('../local_review/registrationReviewLiveConfig.ts');
  for (const file of [gate, route]) {
    assert.match(file, /import\.meta\.env\.DEV/);
    assert.match(file, /LOCAL_REVIEW_ONLY/);
  }
});
test('local overlay targets exclusively 127.0.0.1 sandbox-independent ports', () => {
  const config = read('../vite.review-local.config.ts');
  assert.match(config, /host: '127\.0\.0\.1'/);
  assert.match(config, /port: 5176/);
  assert.match(config, /127\.0\.0\.1:8002/);
  assert.match(config, /command !== 'serve'/);
  assert.match(config, /CTUG_REVIEW_LOCAL_ACK/);
});
test('full-path Vite aliases match extensionless and explicit ts imports', () => {
  const gate = /^(?:\.{1,2}\/)+(?:[^/]+\/)*registrationReviewApiGate(?:\.ts)?$/;
  const route = /^(?:\.{1,2}\/)+(?:[^/]+\/)*registrationReviewLiveConfig(?:\.ts)?$/;
  for (const candidate of ['../admin/registrationReviewApiGate', './registrationReviewApiGate.ts']) {
    assert.ok(gate.test(candidate), candidate);
    assert.equal(candidate.replace(gate, '/local_review/registrationReviewApiGate.ts'), '/local_review/registrationReviewApiGate.ts');
  }
  assert.ok(route.test('./registrationReviewLiveConfig.ts'));
  assert.ok(!gate.test('./registrationReviewPreviewGate.ts'));
});
test('local overlay has no normal production build switch', () => {
  const config = read('../vite.review-local.config.ts');
  assert.match(config, /throw new Error\('The opt-in local review overlay must NEVER build/);
});
