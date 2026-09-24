// hris.parliament.go.th/ss_th.php — every current MP as a text block:
//   เลขประจำตัวสมาชิก : 001 / name / "สมาชิกสภาผู้แทนราษฎรจังหวัด… เขตเลือกตั้งที่ …" or "…แบบบัญชีรายชื่อ" / party
const t = document.body.innerText;
const heading = (t.match(/สมาชิกสภาผู้แทนราษฎร ชุดที่ \d+/) || [null])[0];
const blocks = t.split(/เลขประจำตัวสมาชิก\s*:\s*/).slice(1);
const rows = blocks.map(b => {
  const lines = b.split('\n').map(s => s.replace(/\s+/g, ' ').trim()).filter(Boolean);
  return { no: lines[0], name: lines[1], seat: lines[2], party: lines[3] };
});
return { heading, count: rows.length, rows };
