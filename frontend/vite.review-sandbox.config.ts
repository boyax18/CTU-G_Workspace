/** AR-6C7E.3: Vite sandbox-only overlay. NEVER use for deployment.
 * It substitutes only the hard-disabled frontend gate/route modules while
 * leaving the real files untouched. Production builds remain disabled.
 */
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

if (process.env.CTUG_REVIEW_SANDBOX_ACK !== 'SANDBOX_ONLY') {
  throw new Error('Sandbox Vite config requires CTUG_REVIEW_SANDBOX_ACK=SANDBOX_ONLY.');
}

const frontendRoot = process.cwd();
const gate = resolve(frontendRoot, 'sandbox/registrationReviewApiGate.ts');
const route = resolve(frontendRoot, 'sandbox/registrationReviewLiveConfig.ts');
if (!existsSync(gate) || !existsSync(route)
    || !existsSync(resolve(frontendRoot, 'src/features/admin/registrationReviewApiGate.ts'))) {
  throw new Error('Run this Vite config only from the CTU-G Workspace frontend directory.');
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: [
      { find: /^(?:\.{1,2}\/)+(?:[^/]+\/)*registrationReviewApiGate(?:\.ts)?$/, replacement: gate },
      { find: /^(?:\.{1,2}\/)+(?:[^/]+\/)*registrationReviewLiveConfig(?:\.ts)?$/, replacement: route },
    ],
  },
  server: {
    host: '127.0.0.1',
    port: 5175,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: false,
      },
    },
  },
  // Never build a deployable artifact with the sandbox overlay.
  build: { outDir: 'dist-review-sandbox-DO-NOT-DEPLOY' },
});
