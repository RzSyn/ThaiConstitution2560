# -*- coding: utf-8 -*-
"""Turn the raw OCS page dumps (data/source-ocs/*.json, made by tools/scrape_ocs.mjs)
into one structured file, data/constitution.json.

Nothing here writes constitutional text by hand: every string comes from the
OCS dump. The script only splits it into paragraphs, recognises headings
(หมวด / ส่วนที่ / บทเฉพาะกาล / มาตรา), strips footnote markers, and compares
the original 2560 text with the consolidated one so every changed section is
accounted for.

Run: python tools/parse_ocs.py
"""
import html
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'source-ocs')
OUT = os.path.join(ROOT, 'data', 'constitution.json')

TH_DIGITS = '๐๑๒๓๔๕๖๗๘๙'


def th2int(s):
    return int(''.join(str(TH_DIGITS.index(c)) for c in s))


def int2th(n):
    return ''.join(TH_DIGITS[int(c)] for c in str(n))


def load(name):
    with io.open(os.path.join(SRC, name), encoding='utf-8') as f:
        return json.load(f)


def clean(s):
    s = html.unescape(s).replace(' ', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


FOOT_RE = re.compile(r'\[(\d+)\]')


def paras_of(item):
    """Paragraphs of one OCS block, footnote markers removed, plus the markers found."""
    out, notes = [], []
    for chunk in re.split(r'</p\s*>', item['html']):
        # footnote references look like <a href="#foot-..."><sup ...>[3]</sup></a>
        notes += [int(n) for n in re.findall(r'<sup[^>]*>\[(\d+)\]</sup>', chunk)]
        chunk = re.sub(r'<sup[^>]*>\[\d+\]</sup>', '', chunk)
        text = clean(re.sub(r'<[^>]+>', '', chunk))
        if text:
            out.append(text)
    return out, notes


def footnotes_of(items):
    """The last block (no id) holds the footnote list: <p id="foot-…"><a><sup>[n]</sup></a> text</p>."""
    notes = {}
    for it in items:
        if 'foot-' in it['html'] and not it['id']:
            for n, body in re.findall(r'<sup>\[(\d+)\]</sup></a>(.*?)</p>', it['html'], re.S):
                notes[int(n)] = clean(re.sub(r'<[^>]+>', '', body))
    return notes


SEC_RE = re.compile(r'^มาตรา\s*([๐-๙]+)\s*(.*)$')
CH_RE = re.compile(r'^หมวด\s*([๐-๙]+)$')
PART_RE = re.compile(r'^ส่วนที่\s*([๐-๙]+)$')


def parse_charter(items, stop_at_countersign=True):
    """Parse the body of the 2560 constitution (original or consolidated)."""
    blocks = [it for it in items if 'preview-html' in it['cls'] and it['id']]
    doc = {'title': None, 'royal': [], 'preamble': [], 'chapters': [], 'sections': [],
           'countersign': [], 'rest': []}
    chapter = part = None
    stage = 'head'
    for it in blocks:
        ps, notes = paras_of(it)
        if not ps:
            continue
        first = ps[0]
        if stage == 'tail':
            doc['rest'].append({'paras': ps, 'notes': notes})
            continue
        if doc['title'] is None:
            doc['title'] = {'text': ' '.join(ps), 'notes': notes}
            continue
        if stage == 'head' and first.startswith('สมเด็จพระเจ้าอยู่หัว') and len(ps) <= 4:
            doc['royal'] = ps
            continue
        if stage == 'head' and first.startswith('ศุภมัสดุ'):
            doc['preamble'] = ps
            stage = 'body'
            continue
        m = CH_RE.match(first)
        if m and len(ps) == 2:
            chapter = {'no': th2int(m.group(1)), 'label': first, 'title': ps[1], 'parts': [], 'sections': []}
            doc['chapters'].append(chapter)
            part = None
            continue
        if first == 'บทเฉพาะกาล' and len(ps) == 1:
            chapter = {'no': None, 'label': 'บทเฉพาะกาล', 'title': 'บทเฉพาะกาล', 'parts': [], 'sections': []}
            doc['chapters'].append(chapter)
            part = None
            continue
        m = PART_RE.match(first)
        if m and len(ps) == 2:
            part = {'no': th2int(m.group(1)), 'label': first, 'title': ps[1], 'sections': []}
            chapter['parts'].append(part)
            continue
        m = SEC_RE.match(first)
        if m and stage == 'body':
            n = th2int(m.group(1))
            body = [m.group(2)] + ps[1:] if m.group(2) else ps[1:]
            sec = {'no': n, 'th': m.group(1), 'paras': body, 'notes': notes,
                   'chapter': chapter['no'] if chapter['no'] is not None else 'T',
                   'part': part['no'] if part else None}
            doc['sections'].append(sec)
            chapter['sections'].append(n)
            if part:
                part['sections'].append(n)
            continue
        if first.startswith('ผู้รับสนองพระราชโองการ'):
            doc['countersign'] = ps
            if stop_at_countersign:
                stage = 'tail'
            continue
        raise SystemExit('unrecognised block %s: %s' % (it['id'], first[:80]))
    return doc


def parse_amendment(items):
    blocks = [it for it in items if 'preview-html' in it['cls'] and it['id']]
    am = {'title': [], 'royal': [], 'enacting': [], 'sections': [], 'countersign': [], 'note': None}
    for it in blocks:
        ps, notes = paras_of(it)
        if not ps:
            continue
        first = ps[0]
        if not am['title']:
            am['title'] = ps
        elif first.startswith('พระบาทสมเด็จ') and 'ให้ไว้ ณ วันที่' in ' '.join(ps):
            am['royal'] = ps
        elif first.startswith('พระบาทสมเด็จ'):
            am['enacting'] = ps
        elif SEC_RE.match(first):
            m = SEC_RE.match(first)
            am['sections'].append({'no': th2int(m.group(1)), 'th': m.group(1),
                                   'paras': [m.group(2)] + ps[1:], 'notes': notes})
        elif first.startswith('ผู้รับสนอง'):
            am['countersign'] = ps
        elif first.startswith('หมายเหตุ'):
            am['note'] = ' '.join(ps)
        else:
            raise SystemExit('unrecognised amendment block: ' + first[:80])
    return am


def main():
    cons_raw = load('consolidated.json')
    orig_raw = load('original-2560.json')
    am_raw = load('amendment-1-2564.json')

    cons = parse_charter(cons_raw['items'])
    orig = parse_charter(orig_raw['items'])
    am1 = parse_amendment(am_raw['items'])
    cons_notes = footnotes_of(cons_raw['items'])
    am_notes = footnotes_of(am_raw['items'])

    # ── checks ────────────────────────────────────────────────────────────
    nums = [s['no'] for s in cons['sections']]
    assert nums == list(range(1, 280)), 'consolidated sections are not 1..279 in order'
    assert [s['no'] for s in orig['sections']] == nums, 'original sections differ in numbering'
    assert len(cons['chapters']) == 17, 'expected 16 chapters + บทเฉพาะกาล'
    assert cons['preamble'] == orig['preamble'], 'preamble differs between versions'

    changed = [s['no'] for s, o in zip(cons['sections'], orig['sections']) if s['paras'] != o['paras']]
    # sections the amendment act says it replaces, read from its own text
    replaced = {}
    for s in am1['sections']:
        m = re.match(r'ให้ยกเลิกความในมาตรา ([๐-๙]+) ของรัฐธรรมนูญแห่งราชอาณาจักรไทย และให้ใช้ความต่อไปนี้แทน', s['paras'][0])
        if m:
            replaced[th2int(m.group(1))] = s
    print('changed between original and consolidated:', changed)
    print('replaced by amendment 1:', sorted(replaced))
    assert changed == sorted(replaced), 'changed sections do not match the amendment act'

    # the new wording quoted in the amendment act must equal the consolidated text
    for n, s in replaced.items():
        quoted = s['paras'][1:]
        quoted[0] = re.sub(r'^“มาตรา [๐-๙]+ ', '', quoted[0])
        quoted[-1] = re.sub(r'”$', '', quoted[-1])
        cur = cons['sections'][n - 1]['paras']
        assert quoted == cur, 'amendment wording != consolidated wording for section %d' % n

    # footnotes on amended sections must name amendment 1
    for s in cons['sections']:
        for k in s['notes']:
            assert 'แก้ไขเพิ่มเติมโดยรัฐธรรมนูญแห่งราชอาณาจักรไทย แก้ไขเพิ่มเติม (ฉบับที่ ๑) พุทธศักราช ๒๕๖๔' in cons_notes[k], cons_notes[k]
            assert s['no'] in replaced

    gazette_2560 = cons_notes[cons['title']['notes'][0]]
    gazette_am1 = am_notes[1]
    assert gazette_am1 == cons_notes[5]

    sections = []
    for s, o in zip(cons['sections'], orig['sections']):
        rec = {'no': s['no'], 'th': s['th'], 'chapter': s['chapter'], 'part': s['part'], 'paras': s['paras']}
        if s['no'] in replaced:
            rec['history'] = [{'by': 'a1', 'before': o['paras']}]
        sections.append(rec)

    chapters = [{'no': c['no'], 'label': c['label'], 'title': c['title'],
                 'parts': [{'no': p['no'], 'label': p['label'], 'title': p['title'],
                            'first': p['sections'][0], 'last': p['sections'][-1]} for p in c['parts']],
                 'first': c['sections'][0], 'last': c['sections'][-1]} for c in cons['chapters']]

    date_line = next(p for p in am1['royal'] if p.startswith('ให้ไว้ ณ วันที่'))
    am_no, am_year = re.search(r'\(ฉบับที่ ([๐-๙]+)\) พุทธศักราช ([๐-๙]+)$', ' '.join(am1['title'])).groups()
    data = {
        'meta': {
            'title': cons['title']['text'],
            'royal': cons['royal'],
            'gazette': gazette_2560,
            'source': {
                'name': 'สำนักงานคณะกรรมการกฤษฎีกา — ระบบฐานข้อมูลกฎหมาย (ฉบับปรับปรุงล่าสุด)',
                'url': 'https://searchlaw.ocs.go.th/council-of-state/#/public/doc/VG9mbS9RRXZhdjNGYy9Xcm5LTjd1Zz09',
                'retrieved': '2026-09-24',
                'timeline': [t['text'] for t in cons_raw['timeline']],
            },
        },
        'preamble': cons['preamble'],
        'chapters': chapters,
        'sections': sections,
        'countersign': cons['countersign'],
        'amendments': [{
            'id': 'a1',
            'title': ' '.join(am1['title']),
            'no': am_no, 'year': am_year,
            'short': 'ฉบับที่ %s (พ.ศ. %s)' % (am_no, am_year),
            'royal': am1['royal'],
            'given': date_line,
            'gazette': gazette_am1,
            'enacting': am1['enacting'],
            'sections': [{'no': s['no'], 'th': s['th'], 'paras': s['paras']} for s in am1['sections']],
            'countersign': am1['countersign'],
            'note': am1['note'],
            'changes': sorted(replaced),
        }],
    }
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print('wrote', OUT, '| sections', len(sections), '| chapters', len(chapters))
    print('2560 gazette:', gazette_2560)
    print('amendment 1 gazette:', gazette_am1, '|', date_line)


if __name__ == '__main__':
    main()
