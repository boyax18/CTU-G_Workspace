/**
 * WF-03.01 Option A development-only Vite listeners.
 * Each explicitly approved private LAN IP receives its own Vite listener.
 * Never listen on 0.0.0.0, ::, or VPN/virtual/public interfaces.
 * The Windows launcher must validate local physical interfaces first.
 */
import { isIP } from 'node:net';
import { createServer } from 'vite';

function isRfc1918IPv4(ip) {
  if (isIP(ip) !== 4) return false;
  const [a,b] = ip.split('.').map(Number);
  return a === 10 || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168);
}

const raw = process.env.CTUG_ROLE_CONTEXT_LAN_DEV_IPS ?? '';
const ips = raw.split(',').map(s => s.trim());
if (!raw || ips.length > 4 || ips.some(ip => !isRfc1918IPv4(ip)) ||
    new Set(ips).size !== ips.length) {
  throw new Error('Refusing to start: expected 1–4 distinct explicit RFC1918 LAN IPv4 addresses.');
}
if (process.env.CTUG_ROLE_CONTEXT_LAN_DEV_ACK !== 'LAN_HTTP_SYNTHETIC_ONLY_WF0301_A' ||
    process.env.CTUG_API_TARGET !== 'http://127.0.0.1:8000') {
  throw new Error('Refusing to start: Option A acknowledgment or loopback API target missing.');
}

const servers = [];
try {
  for (const ip of ips) {
    const server = await createServer({
      // Vite merges this with frontend/vite.config.ts, retaining the API proxy.
      server: { host: ip, port: 5173, strictPort: true },
      // Prevent multiple optimizer processes from writing the same cache.
      cacheDir: `node_modules/.vite-option-a-${ip.replaceAll('.', '-')}`,
    });
    await server.listen();
    servers.push(server);
    console.log(`Option A synthetic-only LAN: http://${ip}:5173/`);
  }
} catch (err) {
  await Promise.allSettled(servers.map(server => server.close()));
  throw err;
}

console.log('Django must remain on 127.0.0.1:8000. Use only synthetic accounts and test data.');
console.log('Press Ctrl+C to stop these LAN listeners.');
let closing = false;
async function stop() {
  if (closing) return;
  closing = true;
  await Promise.allSettled(servers.map(server => server.close()));
  process.exit(0);
}
process.once('SIGINT', stop);
process.once('SIGTERM', stop);
