// thaigov.go.th/th/cabinet/prime-minister — the page title names the current PM and their number
const m = document.title.match(/นายกรัฐมนตรีคนที่ (\d+) - (.+)$/);
return m ? { number: +m[1], name: m[2].trim() } : null;
