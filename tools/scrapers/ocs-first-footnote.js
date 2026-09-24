// OCS law page — title and the first footnote (the Royal Gazette reference with its date)
for (let i = 0; i < 60; i++) { const b = document.querySelector('div.in-a4'); if (b && b.children.length > 3) break; await new Promise(r => setTimeout(r, 500)); }
await new Promise(r => setTimeout(r, 1500));
const b = document.querySelector('div.in-a4');
const title = (b.children[1] || b.children[0]).innerText.replace(/\s+/g, ' ').replace(/\[\d+\]/g, '').trim();
const foot = [...b.querySelectorAll('p[id^="foot-"]')].map(p => p.innerText.replace(/\s+/g, ' ').trim());
return { title, foot1: foot[0] || null };
