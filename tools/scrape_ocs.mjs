// node scrape.mjs <encTimelineId> <outDir>
// Loads the OCS public law page in headless Chrome, then for each timeline version
// (ฉบับหลัก / ฉบับแก้ไข / ฉบับปรับปรุงล่าสุด) clicks its view button and saves the
// children of div.in-a4 (id, class, innerHTML, innerText) as JSON. Nothing is edited.
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { tmpdir } from 'node:os';

const docId = process.argv[2];
const out = resolve(process.argv[3] || '.');
mkdirSync(out, { recursive: true });
const CH = process.env.CHROME || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const port = 9300 + Math.floor(Math.random() * 500);
const prof = join(tmpdir(), 'cdp-ocs-profile');
mkdirSync(prof, { recursive: true });
const chrome = spawn(CH, ['--headless=new', '--disable-gpu', `--remote-debugging-port=${port}`,
  `--user-data-dir=${prof}`, '--no-first-run', 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));

let pages;
for (let i = 0; i < 60; i++) {
  try { pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); if (pages.length) break; } catch {}
  await sleep(250);
}
const ws = new WebSocket(pages.find(p => p.type === 'page').webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r));
let id = 0; const waiting = new Map();
ws.addEventListener('message', m => {
  const msg = JSON.parse(m.data);
  if (msg.id && waiting.has(msg.id)) { waiting.get(msg.id)(msg); waiting.delete(msg.id); }
});
const send = (method, params = {}) => new Promise(r => { const k = ++id; waiting.set(k, r); ws.send(JSON.stringify({ id: k, method, params })); });
const ev = async expr => {
  const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 400));
  return r.result.result.value;
};

await send('Page.enable');
await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1400, height: 1000, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url: `https://searchlaw.ocs.go.th/council-of-state/#/public/doc/${docId}` });

const waitDoc = async (prevSig) => {
  for (let i = 0; i < 120; i++) {
    const sig = await ev(`(()=>{const b=document.querySelector('div.in-a4');if(!b)return '';return b.children.length+':'+(b.innerText||'').length})()`);
    if (sig && +sig.split(':')[0] > 5 && sig !== prevSig) { await sleep(2500);
      const sig2 = await ev(`(()=>{const b=document.querySelector('div.in-a4');return b.children.length+':'+(b.innerText||'').length})()`);
      if (sig2 === sig) return sig; }
    await sleep(500);
  }
  throw new Error('doc did not load');
};

const grab = `(()=>{const b=document.querySelector('div.in-a4');
  return [...b.children].map(k=>({id:k.id, cls:k.className, html:k.innerHTML, text:k.innerText}));})()`;
const timeline = `(()=>[...document.querySelectorAll('.app-timeline > div[id^=timeline-]')].map(t=>({id:t.id, text:t.innerText.trim().replace(/\\s+/g,' '),
  view: !!t.querySelector('button.timeline-button')})))()`;

let sig = await waitDoc('');
const tl = await ev(timeline);
console.log('timeline', JSON.stringify(tl));
const title = await ev(`document.querySelector('div.in-a4').innerText.slice(0,80)`);
writeFileSync(join(out, 'default.json'), JSON.stringify({ timeline: tl, title, items: await ev(grab) }, null, 1));
console.log('saved default', sig);

for (const t of tl) {
  if (!t.view) continue;
  await ev(`document.querySelector('#${t.id} button.timeline-button').click()`);
  try { sig = await waitDoc(sig); } catch (e) { console.log(t.id, 'no change after click'); }
  writeFileSync(join(out, `${t.id}.json`), JSON.stringify({ timeline: t, items: await ev(grab) }, null, 1));
  console.log('saved', t.id, sig);
}
ws.close(); chrome.kill(); process.exit(0);
