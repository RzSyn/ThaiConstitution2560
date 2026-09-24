// node tools/scrape_js.mjs <url> <scraper.js> <out.json>
// Opens an official page in headless Chrome, runs the scraper expression (it may be async and must
// return JSON-serialisable data) and writes {url, retrieved, data} to out.json — so facts reach the
// repo exactly as the page shows them, never retyped by hand.
import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { tmpdir } from 'node:os';

const [url, jsFile, outFile] = process.argv.slice(2);
const expr = readFileSync(resolve(jsFile), 'utf8');
const CH = process.env.CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const port = 9300 + Math.floor(Math.random() * 500);
const prof = join(tmpdir(), 'cdp-scrape-profile');
mkdirSync(prof, { recursive: true });
const chrome = spawn(CH, ['--headless=new', '--disable-gpu', `--remote-debugging-port=${port}`, `--user-data-dir=${prof}`,
  '--no-first-run', '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36',
  'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let pages;
for (let i = 0; i < 60; i++) {
  try { pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); if (pages.length) break; } catch {}
  await sleep(250);
}
const ws = new WebSocket(pages.find(p => p.type === 'page').webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const waiting = new Map(); const events = [];
ws.addEventListener('message', m => {
  const msg = JSON.parse(m.data);
  if (msg.id && waiting.has(msg.id)) { waiting.get(msg.id)(msg); waiting.delete(msg.id); } else if (msg.method) events.push(msg.method);
});
const send = (method, params = {}) => new Promise(r => { const k = ++id; waiting.set(k, r); ws.send(JSON.stringify({ id: k, method, params })); });
await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1400, height: 1000, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url });
for (let i = 0; i < 160 && !events.includes('Page.loadEventFired'); i++) await sleep(250);
await sleep(3500);
const r = await send('Runtime.evaluate', { expression: `(async () => { ${expr} })()`, awaitPromise: true, returnByValue: true });
if (r.result.exceptionDetails) { console.error('scraper error:', JSON.stringify(r.result.exceptionDetails).slice(0, 500)); process.exit(1); }
const title = (await send('Runtime.evaluate', { expression: 'document.title', returnByValue: true })).result.result.value;
mkdirSync(dirname(resolve(outFile)), { recursive: true });
writeFileSync(resolve(outFile), JSON.stringify({ url, title, retrieved: new Date().toISOString().slice(0, 10), data: r.result.result.value }, null, 1));
console.log('saved', outFile, '|', title);
ws.close(); chrome.kill(); process.exit(0);
