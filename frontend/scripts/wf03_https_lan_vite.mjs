/**
 * CTU-G Workspace WF-03.01 HTTPS dev frontends (Vite 8).
 * HTTPS terminates here; only this trusted loopback proxy may reach Django.
 * Never use Vite/DEBUG as an institutional production server.
 */
import { readFileSync, realpathSync } from 'node:fs';
import { isIP } from 'node:net';
import { X509Certificate } from 'node:crypto';
import { resolve, relative, isAbsolute } from 'node:path';
import { createServer } from 'vite';

const frontendRoot = realpathSync(process.cwd());
function privateIP(ip) {
  if (isIP(ip) !== 4) return false;
  const [a, b] = ip.split('.').map(Number);
  return a === 10 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168);
}
const raw = process.env.CTUG_ROLE_CONTEXT_HTTPS_LAN_IPS ?? '';
const ips = raw.split(',').map(x => x.trim());
if (!raw || ips.length > 4 || ips.some(ip => !privateIP(ip)) || new Set(ips).size !== ips.length) {
  throw new Error('Expected 1–4 explicit, distinct RFC1918 IPv4 server addresses.');
}
if (process.env.CTUG_ROLE_CONTEXT_HTTPS_LAN_DEV_ACK !== 'LAN_HTTPS_DEV_SYNTHETIC_WF0301_B' ||
    process.env.CTUG_API_TARGET !== 'http://127.0.0.1:8000') {
  throw new Error('HTTPS development acknowledgment or loopback API target is missing.');
}
if (process.env.CTUG_ROLE_CONTEXT_LAN_DEV_ACK || process.env.CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK) {
  throw new Error('HTTP LAN/localhost acknowledgments cannot be combined with HTTPS LAN.');
}
const certFile = process.env.CTUG_HTTPS_LAN_CERT;
const keyFile = process.env.CTUG_HTTPS_LAN_KEY;
if (!certFile || !keyFile || !isAbsolute(certFile) || !isAbsolute(keyFile)) {
  throw new Error('Both certificate and key must be absolute paths outside the repository.');
}
function insideRepo(path) {
  const relativeToRepo = relative(frontendRoot, resolve(path));
  return relativeToRepo === '' || (!relativeToRepo.startsWith('..') && !isAbsolute(relativeToRepo));
}
if (insideRepo(certFile) || insideRepo(keyFile)) {
  throw new Error('Do not store TLS private keys or certificates in the frontend repository.');
}
const cert = readFileSync(certFile);
const key = readFileSync(keyFile);
const x509 = new X509Certificate(cert);
const now = Date.now();
if (Date.parse(x509.validFrom) > now || Date.parse(x509.validTo) < now) {
  throw new Error('The local HTTPS certificate is expired or not yet valid.');
}
for (const ip of ips) {
  if (!x509.checkIP(ip)) throw new Error(`TLS certificate is missing IP SAN: ${ip}`);
}
// The TLS socket is terminated by Vite. Trusting an arbitrary forwarded header
// from the client would be unsafe: overwrite it here on every proxied request.
function installProxyTlsHeader(proxy) {
  proxy.on('proxyReq', (proxyReq) => {
    proxyReq.setHeader('X-Forwarded-Proto', 'https');
    proxyReq.setHeader('X-Forwarded-Port', '5173');
    proxyReq.removeHeader('Forwarded');
  });
}

const servers = [];
try {
  for (const ip of ips) {
    const server = await createServer({
      server: {
        host: ip,
        port: 5173,
        strictPort: true,
        https: { cert, key },
        // Override ONLY /api, keeping the project's React, Tailwind and other
        // plugins; prevent user-injected X-Forwarded-Proto from being trusted.
        proxy: {
          '/api': {
            target: 'http://127.0.0.1:8000',
            changeOrigin: false,
            configure: installProxyTlsHeader,
          },
        },
      },
      cacheDir: `node_modules/.vite-ctug-https-${ip.replaceAll('.', '-')}`,
    });
    await server.listen();
    servers.push(server);
    console.log(`CTU-G HTTPS development: https://${ip}:5173/`);
  }
} catch (err) {
  await Promise.allSettled(servers.map(server => server.close()));
  throw err;
}
console.log('Django must remain bound to 127.0.0.1:8000. Certificate must be trusted on each test device.');
let closing = false;
async function shutdown() {
  if (closing) return;
  closing = true;
  await Promise.allSettled(servers.map(server => server.close()));
  process.exit(0);
}
process.once('SIGINT', shutdown);
process.once('SIGTERM', shutdown);
