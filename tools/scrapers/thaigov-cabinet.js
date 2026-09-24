// thaigov.go.th/th/cabinet/minister — the list is paginated by JS and the Prime Minister's card is
// repeated at the top of every page. Collect every (name, position) pair in page order and drop exact
// repeats; the count must then equal the site's own "แสดง … จาก N รายการ".
const grab = () => {
  const t = document.body.innerText;
  const a = t.indexOf('ชุดปัจจุบัน') + 'ชุดปัจจุบัน'.length;
  const b = t.indexOf('‹', a);
  return t.slice(a, b).split('\n').map(s => s.trim()).filter(s => s && s !== 'ประวัตินายกรัฐมนตรี');
};
const rows = [], seen = new Set();
let total = null, pages = 0;
for (let k = 0; k < 15; k++) {
  const lines = grab();
  for (let i = 0; i + 1 < lines.length; i += 2) {
    const key = lines[i] + '|' + lines[i + 1];
    if (!seen.has(key)) { seen.add(key); rows.push({ name: lines[i], position: lines[i + 1] }); }
  }
  pages++;
  const st = document.body.innerText.match(/แสดง (\d+) ถึง (\d+) จาก (\d+)/);
  if (!st) break;
  total = +st[3];
  if (+st[2] >= total) break;
  const btn = [...document.querySelectorAll('a,button')].find(e => /Next/.test(e.innerText || ''));
  if (!btn) break;
  btn.click();
  await new Promise(r => setTimeout(r, 2000));
}
return { total, pages, rows, complete: rows.length === total };
