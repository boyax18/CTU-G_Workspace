// Deferred until consolidated WF-03 testing: inspect-gate and read-only UX.
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const read=p=>readFileSync(new URL(p,import.meta.url),'utf8');

test('effective access inspection has an explicit frontend gate',()=>{
 const config=read('../src/features/access-control/effectiveAccessConfig.ts');
 assert.match(config,/VITE_WORKSPACE_WF0305_EFFECTIVE_ACCESS_INSPECT_ENABLED/);
 assert.match(config,/=== '1'/);
});
test('effective access inspector does not mutate roles, services or grants',()=>{
 const client=read('../src/features/access-control/effectiveAccessApi.ts');
 assert.match(client,/getJSON/);
 assert.doesNotMatch(client,/postJSON|putJSON|deleteJSON/);
 const panel=read('../src/features/access-control/EffectiveAccessPanel.tsx');
 assert.match(panel,/Service states/);
 assert.match(panel,/selected role/);
});
