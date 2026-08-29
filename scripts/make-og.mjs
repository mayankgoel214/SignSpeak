// Render web/og.png, the social preview card. The number on it is read from the
// evaluation output like every other number on the site, so a stale share image
// cannot advertise an accuracy the repository no longer measures.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const ROOT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const results = JSON.parse(fs.readFileSync(path.join(ROOT, "eval", "results.json"), "utf8"));
const si = results.signer_independent;
const rs = results.random_split;

const html = `<!doctype html><meta charset="utf-8">
<link rel="stylesheet" href="./tokens.css">
<style>
  html,body{margin:0}
  body{width:1200px;height:630px;background:var(--n-100);color:var(--n-1000);
       font-family:var(--sans);display:flex;flex-direction:column;justify-content:space-between;
       padding:64px 72px;box-sizing:border-box;position:relative;overflow:hidden}
  .bloom{position:absolute;top:-30%;right:-10%;width:820px;height:820px;
         background:radial-gradient(closest-side,rgb(227 151 36/.22),transparent 70%)}
  .mark{display:flex;align-items:center;gap:12px;font-size:26px;font-weight:640;letter-spacing:-.03em;position:relative}
  h1{margin:0;font-size:76px;font-weight:660;letter-spacing:-.045em;line-height:.98;max-width:16ch;position:relative}
  h1 em{font-style:normal;color:var(--a-300)}
  .row{display:flex;gap:56px;align-items:flex-end;position:relative}
  .fig{font-family:var(--mono);font-variant-numeric:tabular-nums}
  .v{font-size:80px;font-weight:700;letter-spacing:-.05em;line-height:.9;color:var(--a-300)}
  .v.muted{color:var(--n-700);font-size:52px}
  .fig .l{font-family:var(--sans);font-size:19px;color:var(--n-900);margin-top:10px;max-width:22ch;line-height:1.35}
  .l.muted{color:var(--n-700)}
</style>
<div class="bloom"></div>
<div class="mark">
  <svg width="26" height="26" viewBox="0 0 24 24"><g stroke="#f5bb64" stroke-width="2.1" stroke-linecap="round" fill="none">
  <path d="M6 18V10"/><path d="M10 18V5"/><path d="M14 18V7"/><path d="M18 18V12"/></g></svg>
  SignSpeak
</div>
<h1>ASL fingerspelling,<br>read on <em>your</em> device.</h1>
<div class="row">
  <div class="fig"><div class="v">${(si.mean_accuracy * 100).toFixed(1)}%</div>
    <div class="l">on a signer the model has never seen · leave-one-signer-out, ${si.n_test_total.toLocaleString()} samples</div></div>
  <div class="fig"><div class="v muted">${(rs.accuracy * 100).toFixed(1)}%</div>
    <div class="l muted">the same model on a random split — published here as the number not to trust</div></div>
</div>`;

fs.writeFileSync(path.join(ROOT, "web", "_og.html"), html);
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
await page.goto(`file://${path.join(ROOT, "web", "_og.html")}`);
await page.waitForTimeout(600);
await page.screenshot({ path: path.join(ROOT, "web", "og.png") });
await browser.close();
fs.unlinkSync(path.join(ROOT, "web", "_og.html"));
console.log(`wrote web/og.png (${(fs.statSync(path.join(ROOT, "web", "og.png")).size / 1024).toFixed(0)} KB)`);
