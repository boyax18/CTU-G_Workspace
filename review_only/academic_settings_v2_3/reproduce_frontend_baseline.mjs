// Extract immutable Git sources to fresh ignored folders; never check out over the user's work.
import { execFileSync, spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, symlinkSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../../', import.meta.url));
const rows = [];
for (const revision of ['51d0904', '13da643', '2a1bca1']) {
  const folder = mkdtempSync(path.join(root, '.local', `wf11-baseline-${revision}-`));
  const archive = execFileSync('git', ['archive', '--format=tar', revision, 'frontend/src',
    'frontend/tests/dashboard-navigation.test.mjs', 'backend/apps/access_control/catalogue/v2_0.json'],
  { cwd: root, maxBuffer: 30 * 1024 * 1024 });
  const unpack = spawnSync('tar', ['-xf', '-', '-C', folder], { input: archive, windowsHide: true });
  if (unpack.status !== 0) throw new Error('Could not extract baseline sources.');
  writeFileSync(path.join(folder, 'frontend/package.json'), '{"type":"module"}\n');
  symlinkSync(path.join(root, 'frontend/node_modules'), path.join(folder, 'frontend/node_modules'), 'junction');
  const run = spawnSync(process.execPath, ['--test', 'tests/dashboard-navigation.test.mjs'], {
    cwd: path.join(folder, 'frontend'), encoding: 'utf8', windowsHide: true,
  });
  const output = (run.stdout ?? '') + (run.stderr ?? '');
  writeFileSync(path.join(folder, 'result.log'), output);
  const assertion = output.match(/appointment-evidence: access_control\.appointments\.record/);
  if (run.status !== 1 || !assertion) throw new Error(`Unexpected baseline result at ${revision}: ${output}`);
  rows.push({ revision, exit: run.status, failure: assertion[0],
    suite: 'dashboard-navigation.test.mjs', log: path.relative(root, path.join(folder, 'result.log')) });
}
console.log(JSON.stringify(rows, null, 2));
