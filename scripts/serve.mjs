// A local static server that sends the same headers vercel.json declares.
//
// The point is that the content security policy is enforced in development and
// in CI, not only in production. A policy that is only applied on the deployed
// site is a policy nobody tests: the first sign it is wrong is a blank page for
// a visitor. Serving it here means a change that breaks it fails the suite.
//
// Usage:  node scripts/serve.mjs [port]
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const WEB = path.join(ROOT, "web");
const PORT = Number(process.argv[2] || process.env.PORT || 8099);

const config = JSON.parse(fs.readFileSync(path.join(ROOT, "vercel.json"), "utf8"));
const rules = (config.headers || []).map((rule) => ({
  // vercel.json sources are path patterns; the two used here translate directly.
  test: new RegExp("^" + rule.source.replace("/(.*)", "/(.*)$").replace(/\/\(\.\*\)\$$/, "/.*") + "$"),
  headers: rule.headers,
}));

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".wasm": "application/wasm",
  ".woff2": "font/woff2",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".task": "application/octet-stream",
};

http
  .createServer((req, res) => {
    const url = decodeURIComponent((req.url || "/").split("?")[0]);
    const file = path.join(WEB, url === "/" ? "index.html" : url);
    const inside = file.startsWith(WEB);
    const exists = inside && fs.existsSync(file) && fs.statSync(file).isFile();

    for (const rule of rules) {
      if (rule.test.test(url)) for (const h of rule.headers) res.setHeader(h.key, h.value);
    }

    if (!exists) {
      const notFound = path.join(WEB, "404.html");
      res.setHeader("Content-Type", TYPES[".html"]);
      res.writeHead(404);
      return res.end(fs.existsSync(notFound) ? fs.readFileSync(notFound) : "not found");
    }

    res.setHeader("Content-Type", TYPES[path.extname(file)] || "application/octet-stream");
    res.end(fs.readFileSync(file));
  })
  .listen(PORT, () => console.log(`serving web/ with production headers on ${PORT}`));
