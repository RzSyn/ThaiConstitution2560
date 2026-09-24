// thaigov.go.th news article — keep the headline, date line and body text
const t = document.body.innerText;
const a = t.indexOf('วันที่ :');
const b = t.indexOf('สำนักเลขาธิการนายกรัฐมนตรี', a);
return { title: document.title.replace(/^รัฐบาลไทย \| /, ''), text: t.slice(a, b).trim() };
