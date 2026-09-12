/**
 * Next `output: "standalone"` does not copy `.next/static` or `public`
 * next to `server.js`. The frontend Dockerfile does:
 *   COPY public ./public
 *   COPY .next/standalone ./
 *   COPY .next/static ./.next/static
 * Playwright starts `node .next/standalone/server.js` without that copy,
 * so `/_next/static/*` 404s, the client never hydrates, and browser tests
 * that need the workspace chrome stay on SSR "Restoring session…".
 */
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const standalone = path.join(root, ".next", "standalone");
const serverJs = path.join(standalone, "server.js");
const staticSrc = path.join(root, ".next", "static");
const staticDest = path.join(standalone, ".next", "static");
const publicSrc = path.join(root, "public");
const publicDest = path.join(standalone, "public");

if (!fs.existsSync(serverJs)) {
  console.error(`Missing ${serverJs}`);
  process.exit(1);
}
if (!fs.existsSync(staticSrc)) {
  console.error(`Missing ${staticSrc}`);
  process.exit(1);
}

fs.cpSync(staticSrc, staticDest, { recursive: true });
fs.mkdirSync(publicDest, { recursive: true });
if (fs.existsSync(publicSrc)) {
  fs.cpSync(publicSrc, publicDest, { recursive: true });
}
