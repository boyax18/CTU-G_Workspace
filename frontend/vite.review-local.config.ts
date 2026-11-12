/** AR-6C7E.4 opt-in loopback development server for the REAL local database.
 * WARNING: authenticated approvals/rejections CHANGE ctug_workspace data.
 * Normal Vite configuration and production frontend gates stay untouched.
 */
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

if (process.env.CTUG_REVIEW_LOCAL_ACK !== 'LOCAL_REVIEW_ONLY') {
  throw new Error('Local review Vite configuration requires explicit release marker.');
}

const cwd = process.cwd();
const gate = resolve(cwd, 'local_review/registrationReviewApiGate.ts');
const route = resolve(cwd, 'local_review/registrationReviewLiveConfig.ts');
if (![gate, route, resolve(cwd, 'src/features/admin/registrationReviewApiGate.ts')].every(existsSync)) {
  throw new Error('Run only from the CTU-G Workspace frontend/ directory.');
}

export default defineConfig(({ command }) => {
  if (command !== 'serve') {
    throw new Error('The opt-in local review overlay must NEVER build a deployable artifact.');
  }
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: [
        { find: /^(?:\.{1,2}\/)+(?:[^/]+\/)*registrationReviewApiGate(?:\.ts)?$/, replacement: gate },
        { find: /^(?:\.{1,2}\/)+(?:[^/]+\/)*registrationReviewLiveConfig(?:\.ts)?$/, replacement: route },
      ],
    },
    server: {
      host: '127.0.0.1',
      port: 5176,
      strictPort: true,
      proxy: {
        '/api': { target: 'http://127.0.0.1:8002', changeOrigin: false },
      },
    },
  };
});
