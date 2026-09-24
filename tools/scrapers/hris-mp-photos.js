// hris.parliament.go.th/ss_th.php — photo URL of every current MP, keyed by member number.
// For each photo, walk up to the smallest box that holds a "เลขประจำตัวสมาชิก : NNN"; keep the photo
// only if that box holds exactly one number and one photo. Numbers match data/external/mps.json.
// HRIS refuses connections from outside Thailand, so run this on a computer in Thailand:
//   node tools/scrape_js.mjs https://hris.parliament.go.th/ss_th.php tools/scrapers/hris-mp-photos.js data/external/mp_photo_urls.json
//   python tools/fetch_official_photos.py
const sleep = ms => new Promise(r => setTimeout(r, ms));
for (let y = 0; y < document.body.scrollHeight; y += 800) { window.scrollTo(0, y); await sleep(120); }  // wake lazy images
await sleep(1500);
const NUM = /เลขประจำตัวสมาชิก\s*:\s*(\d+)/g;
const url = i => i.currentSrc || i.getAttribute('data-src') || i.src || '';
const isPhoto = i => url(i) && !/logo|icon|banner|blank|spacer/i.test(url(i));
const out = {};
for (const img of [...document.images].filter(isPhoto)) {
  let box = img.parentElement;
  while (box && ![...box.innerText.matchAll(NUM)].length) box = box.parentElement;
  if (!box) continue;
  const nums = [...box.innerText.matchAll(NUM)].map(m => m[1]);
  const photos = [...box.querySelectorAll('img')].filter(isPhoto);
  if (nums.length === 1 && photos.length === 1 && !out[nums[0]]) out[nums[0]] = { src: new URL(url(img), location.href).href, alt: img.alt || '' };
}
return out;
