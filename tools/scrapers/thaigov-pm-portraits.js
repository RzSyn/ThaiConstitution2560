// archives.thaigov.go.th/th/history/prime-minister — portrait URL for each PM number.
// Walk up from each "ดูประวัติ" button to the smallest box that holds exactly one portrait.
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = {};
for (let pg = 0; pg < 15; pg++) {
  for (const b of [...document.querySelectorAll('button')].filter(b => /ดูประวัติ/.test(b.innerText))) {
    let box = b.parentElement;
    while (box && box.querySelectorAll('img:not([alt="thg-icon"])').length < 1) box = box.parentElement;
    const m = (box.innerText.match(/นายกรัฐมนตรีคนที่ (\d+)/) || [])[1];
    const imgs = box.querySelectorAll('img:not([alt="thg-icon"])');
    if (m && imgs.length === 1) out[m] = { src: imgs[0].currentSrc || imgs[0].src, alt: imgs[0].alt };
  }
  if (Object.keys(out).length >= 32) break;
  const nx = [...document.querySelectorAll('a,button')].find(e => /Next/.test(e.innerText || ''));
  if (!nx) break;
  nx.click();
  await sleep(2500);
}
return out;
