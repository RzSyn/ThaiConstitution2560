# -*- coding: utf-8 -*-
"""Compare the ORIGINAL 2560 text in data/constitution.json (from the OCS database)
with the Royal Gazette PDF in sources/gazette/.

The PDF text layer breaks lines mid-paragraph (sometimes mid-word) and writes
sara am as nikhahit + sara aa, so both sides are compared with all whitespace
removed and sara am normalised. Any difference is printed with context and the
script exits non-zero.

Run: python tools/verify_gazette.py [pdf]
"""
import difflib
import io
import json
import os
import re
import sys

import fitz  # PyMuPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'sources', 'gazette', '2560-constitution-rg134-40a.pdf')


def norm(s):
    s = s.replace('ํา', 'ำ')
    return re.sub(r'\s+', '', s)


def gazette_text():
    doc = fitz.open(PDF)
    pages = []
    for p in doc:
        t = p.get_text()
        # running head: หน้า ๑ / เล่ม ๑๓๔ ตอนที่ ๔๐ ก / ราชกิจจานุเบกษา / ๖ เมษายน ๒๕๖๐
        t2 = re.sub(r'^\s*หน้า\s+[๐-๙]+\s+เล่ม\s+[๐-๙]+\s+ตอนที่\s+[๐-๙]+\s+ก\s+ราชกิจจานุเบกษา\s+[๐-๙]+\s+\S+\s+[๐-๙]+\s*', '', t)
        assert t2 != t, 'running head not found on page %d' % (p.number + 1)
        pages.append(t2)
    return '\n'.join(pages)


def ocs_original():
    with io.open(os.path.join(ROOT, 'data', 'constitution.json'), encoding='utf-8') as f:
        d = json.load(f)
    parts = ['รัฐธรรมนูญแห่งราชอาณาจักรไทย'] + d['meta']['royal'] + d['preamble']
    secs = {s['no']: s for s in d['sections']}
    for c in d['chapters']:
        parts.append(c['label'] if c['no'] is None else c['label'] + c['title'])
        firsts = {p['first']: p for p in c['parts']}
        for n in range(c['first'], c['last'] + 1):
            if n in firsts:
                parts.append(firsts[n]['label'] + firsts[n]['title'])
            s = secs[n]
            paras = s['history'][0]['before'] if s.get('history') else s['paras']
            parts.append('มาตรา' + s['th'] + ''.join(paras))
    parts += d['countersign']
    return ''.join(parts)


def main():
    a, b = norm(ocs_original()), norm(gazette_text())
    print('OCS original: %d chars, gazette: %d chars (whitespace removed)' % (len(a), len(b)))
    if a == b:
        print('IDENTICAL: every character of the original text matches the Royal Gazette PDF')
        return
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    bad = 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            continue
        bad += 1
        print('--- %s  OCS[%d:%d]=%r  GAZETTE[%d:%d]=%r' % (op, i1, i2, a[i1:i2][:80], j1, j2, b[j1:j2][:80]))
        print('    context OCS    : …%s…' % a[max(0, i1 - 40):i2 + 40])
        print('    context gazette: …%s…' % b[max(0, j1 - 40):j2 + 40])
    print('differences:', bad)
    sys.exit(1)


if __name__ == '__main__':
    main()
