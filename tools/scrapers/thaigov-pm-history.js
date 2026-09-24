// archives.thaigov.go.th/th/history/prime-minister — E-Museum ทำเนียบนายกรัฐมนตรี (สำนักเลขาธิการนายกรัฐมนตรี).
// 4 cards per page, paginated by JS. For each card: number, name, portrait, term links; the "ดูประวัติ"
// button opens the biography, which is appended to the page — read it by diffing the page text.
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = [];
for (let pg = 0; pg < 15; pg++) {
  const btns = [...document.querySelectorAll('button')].filter(b => /ดูประวัติ/.test(b.innerText));
  for (const b of btns) {
    let card = b.parentElement;
    while (card && !/นายกรัฐมนตรีคนที่/.test(card.innerText)) card = card.parentElement;
    const text = card.innerText;
    const m = text.match(/นายกรัฐมนตรีคนที่ (\d+)\s*\n\s*(.+)/);
    const img = card.querySelector('img:not([alt="thg-icon"])');
    const terms = [...card.querySelectorAll('a')].filter(a => /\/th\/t\//.test(a.getAttribute('href') || ''))
      .map(a => ({ label: a.innerText.trim(), href: a.href }));
    const before = document.body.innerText;
    b.click();
    await sleep(1500);
    const after = document.body.innerText;
    const bio = after.startsWith(before.slice(0, 200)) ? after.slice(before.length).trim() : after;
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    const close = [...document.querySelectorAll('button')].find(x => /ปิด|close|×/i.test(x.innerText || x.getAttribute('aria-label') || ''));
    if (close) close.click();
    await sleep(600);
    out.push({ number: m && +m[1], name: m && m[2].trim(), img: img && img.src, img_alt: img && img.alt, terms, bio });
  }
  const st = [...document.querySelectorAll('a,button')].find(e => /Next/.test(e.innerText || ''));
  const cur = document.body.innerText.match(/(\d+)\s*\n\(current\)/);
  if (!st || out.length >= 32 || (cur && +cur[1] >= 8)) break;
  st.click();
  await sleep(2500);
}
return out;
