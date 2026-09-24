# -*- coding: utf-8 -*-
"""Build index.html from data/constitution.json + data/glossary.json.

Official text is only ever copied from constitution.json (which comes from the
OCS dump). Everything written here by hand is page furniture or explanatory
text, and every explanatory block carries the class rc-explain so it is styled
and labelled as "not the official text".

Run: python tools/build.py
"""
import difflib
import hashlib
import html
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT =os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TH_DIGITS = '๐๑๒๓๔๕๖๗๘๙'
TH_MONTHS = ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม',
             'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม']
REPO_URL = 'https://github.com/RzSyn/ThaiConstitution2560'


def repo_live():
    """True once the GitHub repo exists and is public — until then the page must not link to it (404)."""
    import subprocess
    try:
        r = subprocess.run(['git', 'ls-remote', REPO_URL + '.git'], capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:
        return False


def th(n):
    return ''.join(TH_DIGITS[int(c)] if c.isdigit() else c for c in str(n))


def th2int(s):
    return int(''.join(str(TH_DIGITS.index(c)) for c in s))


def th_date(iso):
    y, m, d = (int(x) for x in iso.split('-'))
    return '%s %s %s' % (th(d), TH_MONTHS[m - 1], th(y + 543))


def esc(s):
    return html.escape(s, quote=False)


def attr(s):
    return html.escape(s, quote=True)


def load(name):
    with io.open(os.path.join(ROOT, 'data', name), encoding='utf-8') as f:
        return json.load(f)


def asset_stamp(name):
    with open(os.path.join(ROOT, 'assets', name), 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()[:10]


# ── cross-references ─────────────────────────────────────────────────────
REF_RE = re.compile(r'มาตรา\s*([๐-๙]+)')
OWN_LAW = re.compile(r'\s*ของรัฐธรรมนูญแห่งราชอาณาจักรไทย(?!\s*\(ฉบับชั่วคราว\))')
N_SECTIONS = 279


def linkify(text):
    """Escape text and turn "มาตรา ๘๓" into links, unless it points into another law."""
    s = esc(text)
    out, last = [], 0
    for m in REF_RE.finditer(s):
        n = th2int(m.group(1))
        after = s[m.end():m.end() + 80]
        if re.match(r'\s*(ของ|แห่ง)', after) and not OWN_LAW.match(after):
            continue
        if not 1 <= n <= N_SECTIONS:
            continue
        out.append(s[last:m.start()])
        out.append('<a class="rc-xref" href="#s%d" data-n="%d">%s</a>' % (n, n, m.group(0)))
        last = m.end()
    out.append(s[last:])
    return ''.join(out)


def para_html(paras, link=True):
    out = []
    for i, p in enumerate(paras):
        cls = 'rc-item' if re.match(r'^\([๐-๙]+\)', p) else ('rc-p1' if i == 0 else 'rc-p')
        out.append('<p class="%s">%s</p>' % (cls, linkify(p) if link else esc(p)))
    return ''.join(out)


# ── diff of old vs new wording (explanatory highlighting) ────────────────
CLUSTER = re.compile(r'[^ัิ-ฺ็-๎][ัิ-ฺ็-๎]*')
SEP = ' '


def tokens(paras):
    out = []
    for p in paras:
        out += re.findall(r'\S+|\s+', p) + [SEP]
    return out


def mark_side(a, b):
    """Return [(text, marked)] for old side a and new side b (token lists)."""
    left, right = [], []
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == 'equal':
            left += [(t, False) for t in a[i1:i2]]
            right += [(t, False) for t in b[j1:j2]]
            continue
        sa, sb = ''.join(a[i1:i2]), ''.join(b[j1:j2])
        if op == 'replace' and SEP not in sa and SEP not in sb:
            ca, cb = CLUSTER.findall(sa), CLUSTER.findall(sb)
            sub = difflib.SequenceMatcher(None, ca, cb, autojunk=False)
            if ''.join(ca) == sa and ''.join(cb) == sb and sub.ratio() >= 0.6:
                for op2, k1, k2, l1, l2 in sub.get_opcodes():
                    left.append((''.join(ca[k1:k2]), op2 != 'equal'))
                    right.append((''.join(cb[l1:l2]), op2 != 'equal'))
                continue
        left += [(t, True) for t in a[i1:i2]]
        right += [(t, True) for t in b[j1:j2]]
    return left, right


def render_marked(parts, tag):
    paras, cur = [], []
    for text, marked in parts:
        pieces = text.split(SEP)
        for k, piece in enumerate(pieces):
            if k:
                paras.append(cur)
                cur = []
            if piece:
                cur.append((piece, marked))
    if cur:
        paras.append(cur)
    out = []
    for para in paras:
        buf, run = [], None
        for piece, marked in para:
            if marked and not piece.strip():
                marked = run == 'm'   # keep spaces inside a run, never start one with a space
            state = 'm' if marked else 'p'
            if state != run:
                if run == 'm':
                    buf.append('</%s>' % tag)
                if state == 'm':
                    buf.append('<%s>' % tag)
                run = state
            buf.append(esc(piece))
        if run == 'm':
            buf.append('</%s>' % tag)
        text = ''.join(buf).strip()
        if text:
            cls = 'rc-item' if re.match(r'^(<%s>)?\([๐-๙]+\)' % tag, text) else 'rc-p'
            out.append('<p class="%s">%s</p>' % (cls, text))
    return ''.join(out)


def compare_html(before, after):
    left, right = mark_side(tokens(before), tokens(after))
    return render_marked(left, 'del'), render_marked(right, 'ins')


# ── page parts ───────────────────────────────────────────────────────────
def gazette_label(g):
    """'ราชกิจจานุเบกษา เล่ม ๑๓๔/ตอนที่ ๔๐ ก/หน้า ๑/๖ เมษายน ๒๕๖๐' → readable form (same facts)."""
    m = re.match(r'ราชกิจจานุเบกษา (เล่ม [๐-๙]+)/(ตอนที่ .+?)/(หน้า [๐-๙]+)/(.+)$', g)
    if not m:
        raise SystemExit('unexpected gazette string: ' + g)
    return 'ราชกิจจานุเบกษา %s %s %s วันที่ %s' % m.groups(), m.group(4)


def section_html(sec, amends):
    n = sec['no']
    hist = sec.get('history', [])
    cls = 'rc-sec' + (' is-amended' if hist else '')
    meta, extra = '', ''
    if hist:
        a = amends[hist[-1]['by']]
        meta = ('<div class="rc-sec-meta"><span class="rc-tag">แก้ไขเพิ่มเติมโดยฉบับที่ %s (พ.ศ. %s)</span>'
                '<button class="rc-sec-act" type="button" data-act="compare" aria-expanded="false" '
                'aria-controls="cmp%d">เทียบถ้อยคำเดิม</button></div>') % (a['no'], a['year'], n)
        old, new = compare_html(hist[-1]['before'], sec['paras'])
        extra = ('<div class="rc-compare" id="cmp%d" hidden>'
                 '<div class="rc-pane"><h4>ถ้อยคำเดิม <small>(ฉบับ พ.ศ. ๒๕๖๐ ก่อนแก้ไข)</small></h4>%s</div>'
                 '<div class="rc-pane is-new"><h4>ถ้อยคำปัจจุบัน <small>(แก้ไขโดยฉบับที่ %s พ.ศ. %s)</small></h4>%s</div>'
                 '<p class="rc-explain rc-explain-sm"><b>คำอธิบาย</b> ทั้งสองช่องเป็นตัวบทจริง '
                 'ส่วน<del>ขีดฆ่า</del>และ<ins>ไฮไลต์</ins>เป็นการเทียบความต่างโดยอัตโนมัติของเว็บไซต์นี้ ไม่ใช่ส่วนหนึ่งของตัวบท</p>'
                 '</div>') % (n, old, a['no'], a['year'], new)
    return ('<article class="%s" id="s%d" data-n="%d">'
            '<a class="rc-sec-no" href="#s%d" title="ลิงก์ถาวรของมาตรา %s"><span>มาตรา</span><b>%s</b></a>'
            '<div class="rc-sec-main">%s<div class="rc-sec-body">%s</div>%s</div>'
            '<button class="rc-copy" type="button" data-act="copy" aria-label="คัดลอกลิงก์มาตรา %s" title="คัดลอกลิงก์">'
            '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 14a4 4 0 0 0 5.66 0l3-3a4 4 0 0 0-5.66-5.66l-1 1M14 10a4 4 0 0 0-5.66 0l-3 3a4 4 0 0 0 5.66 5.66l1-1"/></svg>'
            '</button></article>') % (cls, n, n, n, sec['th'], sec['th'], meta, para_html(sec['paras']), extra, sec['th'])


def chapter_id(ch):
    return 'chT' if ch['no'] is None else 'ch%d' % ch['no']


# ── knowledge topics (explanatory panels built from topics/*.html) ───────
TOPIC_HEAD = re.compile(r'^<!--topic\s*(\{.*?\})\s*-->\s*', re.S)


def load_topics():
    tdir = os.path.join(ROOT, 'topics')
    with io.open(os.path.join(tdir, '_groups.json'), encoding='utf-8') as f:
        groups = json.load(f)
    topics = []
    for name in sorted(os.listdir(tdir)):
        if not name.endswith('.html'):
            continue
        with io.open(os.path.join(tdir, name), encoding='utf-8') as f:
            src = f.read()
        m = TOPIC_HEAD.match(src)
        assert m, 'topic header missing in ' + name
        meta = json.loads(m.group(1))
        meta['body'] = src[m.end():]
        meta['file'] = name
        topics.append(meta)
    gids = [g['id'] for g in groups]
    for t in topics:
        assert t['group'] in gids, 'unknown group in ' + t['file']
    assert len({t['id'] for t in topics}) == len(topics), 'duplicate topic id'
    topics.sort(key=lambda t: (gids.index(t['group']), t['order']))
    return groups, topics


def linkify_html(text):
    """linkify() for text that is already HTML (topic sources are hand-written HTML)."""
    return linkify(html.unescape(text))


# ── other laws scraped from the OCS database (data/source-ocs/laws/*.json) ─
_LAWS = {}


def law(name):
    """{'title', 'url', 'secs': {'๕': [paras]}, 'html': {'๕': raw html}} for one scraped law."""
    if name not in _LAWS:
        ldir = os.path.join(ROOT, 'data', 'source-ocs', 'laws')
        with io.open(os.path.join(ldir, '_index.json'), encoding='utf-8') as f:
            meta = json.load(f)[name]
        with io.open(os.path.join(ldir, name + '.json'), encoding='utf-8') as f:
            items = json.load(f)['items']
        secs_, raw = {}, {}
        for it in items:
            # the consolidated dump appends each amending act (with its own มาตรา ๑, ๒ …) after the countersignature
            if it['text'].strip().startswith('ผู้รับสนอง'):
                break
            m = re.match(r'\s*มาตรา\s*([๐-๙]+(?:/[๐-๙]+)?)', it['text'])
            if not m or not it['id'] or m.group(1) in secs_:
                continue
            paras = []
            for chunk in re.split(r'</p\s*>|<br\s*/?>', re.sub(r'<sup[^>]*>\[\d+\]</sup>', '', it['html'])):
                txt = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', chunk))).replace(' ', ' ').strip()
                if txt:
                    paras.append(txt)
            paras[0] = re.sub(r'^มาตรา\s*[๐-๙/]+\s*', '', paras[0])
            if not paras[0]:
                paras = paras[1:]
            secs_[m.group(1)] = paras
            raw[m.group(1)] = it['html']
        _LAWS[name] = dict(meta, secs=secs_, html=raw)
    return _LAWS[name]


def law_key(n):
    return th(n) if re.match(r'^[0-9/]+$', n) else n


def law_quote(name, n, rng=None):
    L = law(name)
    paras = L['secs'][law_key(n)]
    if rng:
        a, _, b = rng.partition('-')
        a, b = int(a), int(b or a)
        assert 1 <= a <= b <= len(paras), 'bad paragraph range for %s ม.%s' % (name, n)
        paras = paras[a - 1:b]
    # never linkify: "มาตรา" inside another law refers to that law, not to the constitution
    return ('<blockquote class="tp-quote is-law"><p class="tp-quote-head"><a href="%s" rel="noopener" target="_blank">%s มาตรา %s</a>'
            '<span>ตัวบททางการ%s</span></p>%s</blockquote>') % (
                attr(L['url']), esc(L['title']), law_key(n), ' (บางวรรค)' if rng else '', para_html(paras, link=False))


def law_items(name, n):
    """Numbered items of a section, leaving out repealed ones — e.g. the list of ministries."""
    items = [p for p in law(name)['secs'][law_key(n)] if re.match(r'^\([๐-๙/]+\)', p) and '(ยกเลิก)' not in p]
    names = [re.sub(r'^\([๐-๙/]+\)\s*', '', p) for p in items]
    return ('<ol class="tp-list">%s</ol><p class="tp-note">รวม %s รายการ ตามมาตรา %s แห่ง%s (ฉบับปรับปรุงล่าสุด ไม่รวมอนุมาตราที่ยกเลิกแล้ว)</p>' % (
        ''.join('<li>%s</li>' % esc(x) for x in names), th(len(names)), law_key(n), esc(law(name)['title'])))


def rank_table(name, n, which=None):
    """Rank tables drawn as HTML tables in the law (พ.ร.บ.ยศทหาร ม.๔). Rows line up only when no cell has blanks."""
    src = law(name)['html'][law_key(n)]
    out = []
    tables = re.findall(r'<table.*?</table>', src, re.S)
    if which:
        tables = [tables[int(which) - 1]]
    for tbl in tables:
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tbl, re.S)
        cells = [[c for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)] for r in rows]
        head = [re.sub(r'<[^>]+>', '', html.unescape(c)).strip() for c in cells[1]]
        cols = []
        for c in cells[2]:
            lines = [re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html.unescape(p))).strip() for p in re.split(r'<br\s*/?>|</p>', c)]
            cols.append(lines)
        clean = [[x for x in col if x] for col in cols]
        # rows are only "equivalent ranks" when every column has the same entries with no leading/inner blanks
        aligned = len({len(c) for c in clean}) == 1 and all(col[:len(cl)] == cl for col, cl in zip(cols, clean))
        if aligned:
            body = ''.join('<tr>%s</tr>' % ''.join('<td>%s</td>' % esc(col[i]) for col in clean) for i in range(len(clean[0])))
            out.append('<table class="tp-table tp-ranks"><thead><tr>%s</tr></thead><tbody>%s</tbody></table>' % (
                ''.join('<th>%s</th>' % esc(h) for h in head), body))
        else:
            out.append('<div class="tp-rank-cols">%s</div>' % ''.join(
                '<div><h5>%s</h5><ol>%s</ol></div>' % (esc(h), ''.join('<li>%s</li>' % esc(x) for x in col))
                for h, col in zip(head, clean)))
    return ''.join(out)


# ── snapshots of official web pages (data/external/*.json, made by tools/scrape_js.mjs) ──
def ext(name):
    with io.open(os.path.join(ROOT, 'data', 'external', name + '.json'), encoding='utf-8') as f:
        return json.load(f)


def ext_cabinet():
    d, pm = ext('cabinet')['data'], ext('pm')['data']
    assert d['complete'], 'cabinet scrape did not reach the site total'
    rows = d['rows']
    people = []
    for r in rows:
        if r['name'] not in people:
            people.append(r['name'])
    photos = ext('cabinet_photos')['photos']
    cards = []
    for name in people:
        posts = [r['position'] for r in rows if r['name'] == name]
        p = photos.get(name)
        if p:
            credit = '<a href="%s" rel="noopener" target="_blank">ภาพ: %s · %s</a>' % (
                attr(p['page']), esc(p['artist'] or 'Wikimedia Commons'), esc(p['license']))
            fig = '<img src="%s" alt="%s" loading="lazy" width="120" height="160">' % (attr(p['src']), attr(name))
        else:
            credit = '<span>ไม่พบภาพที่ใช้ได้โดยเสรี</span>'
            # first consonant of the given name (skip the title and any leading vowel such as เ in เอกนิติ)
            initials = re.search(r'[ก-ฮ]', re.sub(r'^(นางสาว|นาง|นาย|พลตำรวจโท|พลโท)\s*', '', name)).group(0)
            # a personal-use photo may sit in assets/img/private/<full name>.jpg (git-ignored, never published);
            # site.js swaps it in only if the file loads, so the public site keeps the initial
            fig = '<span class="tp-noimg" aria-hidden="true" data-private="assets/img/private/%s.jpg">%s</span>' % (
                attr(name), esc(initials))
        cards.append('<div class="tp-person">%s<div><b>%s</b><ul>%s</ul><small>%s</small></div></div>' % (
            fig, esc(name), ''.join('<li>%s</li>' % esc(x) for x in posts), credit))
    kinds = [('รองนายกรัฐมนตรี', r'^รองนายกรัฐมนตรี'), ('รัฐมนตรีประจำสำนักนายกรัฐมนตรี', r'^รัฐมนตรีประจำสำนักนายกรัฐมนตรี'),
             ('รัฐมนตรีว่าการกระทรวง', r'^รัฐมนตรีว่าการ'), ('รัฐมนตรีช่วยว่าการกระทรวง', r'^รัฐมนตรีช่วยว่าการ')]
    counted = sum(1 for r in rows if any(re.match(p, r['position']) for _, p in kinds)) + sum(1 for r in rows if r['position'] == 'นายกรัฐมนตรี')
    assert counted == len(rows), 'a cabinet position did not fit any kind'
    breakdown = ''.join('<li><b>%s</b> %s ตำแหน่ง</li>' % (esc(k), th(sum(1 for r in rows if re.match(p, r['position'])))) for k, p in kinds)
    body = '<ul class="tp-breakdown">%s</ul><div class="tp-people">%s</div>' % (breakdown, ''.join(cards))
    return ('<div class="tp-stats">'
            '<div class="tp-stat"><b>คนที่ %s</b><span>%s นายกรัฐมนตรี</span><small>ตามเว็บไซต์รัฐบาลไทย</small></div>'
            '<div class="tp-stat"><b>%s</b><span>ตำแหน่งในคณะรัฐมนตรี (บางคนดำรงสองตำแหน่ง)</span><small>ตามเว็บไซต์รัฐบาลไทย</small></div>'
            '<div class="tp-stat"><b>%s คน</b><span>จำนวนบุคคล (นับไม่ซ้ำ)</span><small>คำนวณจากรายชื่อ</small></div>'
            '<div class="tp-stat"><b>%s คน</b><span>มีภาพที่ใช้ได้โดยเสรีจาก Wikimedia Commons</span><small>ภาพดึง %s</small></div></div>'
            '%s') % (th(pm['number']), esc(pm['name']), th(len(rows)), th(len(people)),
                     th(sum(1 for n in people if n in photos)), th_date(ext('cabinet_photos')['retrieved']), body)


def ext_parties():
    d = ext('mps')['data']
    rows = d['rows']
    parties = {}
    for r in rows:
        p = parties.setdefault(r['party'], {'d': 0, 'l': 0})
        p['l' if 'บัญชีรายชื่อ' in r['seat'] else 'd'] += 1
    order = sorted(parties.items(), key=lambda kv: (-(kv[1]['d'] + kv[1]['l']), kv[0]))
    top = order[0][1]['d'] + order[0][1]['l']
    body = ''.join('<tr><td>%s</td><td>%s</td><td>%s</td><td><b>%s</b></td><td class="tp-bar-cell"><i style="width:%.1f%%"></i></td></tr>' % (
        esc(name), th(v['d']), th(v['l']), th(v['d'] + v['l']), 100.0 * (v['d'] + v['l']) / top) for name, v in order)
    nd, nl = sum(v['d'] for v in parties.values()), sum(v['l'] for v in parties.values())
    return ('<div class="tp-stats">'
            '<div class="tp-stat"><b>%s</b><span>สมาชิกที่มีรายชื่อในระบบ (%s)</span><small>ระบบสารสนเทศสมาชิก สภาผู้แทนราษฎร</small></div>'
            '<div class="tp-stat"><b>%s + %s</b><span>แบ่งเขตเลือกตั้ง + บัญชีรายชื่อ</span><small>นับจากรายชื่อ</small></div>'
            '<div class="tp-stat"><b>%s</b><span>พรรคที่มีสมาชิก</span><small>นับจากรายชื่อ</small></div></div>'
            '<table class="tp-table tp-parties"><thead><tr><th>พรรค</th><th>แบ่งเขต</th><th>บัญชีรายชื่อ</th><th>รวม</th><th aria-hidden="true"></th></tr></thead>'
            '<tbody>%s</tbody></table>') % (th(len(rows)), esc(th(d['heading'])), th(nd), th(nl), th(len(parties)), body)


TITLE = re.compile(r'^(นางสาว|นาง|นาย|ว่าที่ร้อยตรีหญิง|ว่าที่ร้อยตรี|ว่าที่ร้อยโท|ว่าที่|พลตำรวจเอก|พลตำรวจโท|พลตำรวจตรี|พันตำรวจเอก|พันตำรวจโท|'
                   r'พลเอก|พลโท|พลตรี|พันเอก|พันโท|พันตรี|ร้อยตำรวจเอก|ร้อยเอก|ร้อยโท|ร้อยตรี|จ่าสิบเอก|หม่อมราชวงศ์|หม่อมหลวง|'
                   r'ศาสตราจารย์|รองศาสตราจารย์|ผู้ช่วยศาสตราจารย์|ดร\.|แพทย์หญิง|นายแพทย์|ทันตแพทย์หญิง|ทันตแพทย์|เภสัชกรหญิง|เภสัชกร)\s*')


def person_fig(name, photos, private):
    """Photo box for a member card: a free Commons photo already vetted for the cabinet list, else the
    initial of the given name with an optional personal-use photo that site.js swaps in on this computer."""
    p = photos.get(name)
    if p:
        fig = '<img src="%s" alt="%s" loading="lazy" width="120" height="160">' % (attr(p['src']), attr(name))
        credit = '<a href="%s" rel="noopener" target="_blank">ภาพ: %s · %s</a>' % (
            attr(p['page']), esc(p['artist'] or 'Wikimedia Commons'), esc(p['license']))
        return fig, credit
    bare, prev = name, None
    while prev != bare:
        prev, bare = bare, TITLE.sub('', bare)
    initial = (re.search(r'[ก-ฮ]', bare) or re.search(r'[ก-ฮ]', name)).group(0)
    return ('<span class="tp-noimg" aria-hidden="true" data-private="%s">%s</span>' % (attr(private), esc(initial)),
            '<span>ไม่พบภาพที่ใช้ได้โดยเสรี</span>')


def member_cards(rows, photos, folder, line2):
    cards = []
    for r in rows:
        fig, credit = person_fig(r['name'], photos, 'assets/img/private/%s/%s.jpg' % (folder, r['name']))
        extra, key = line2(r)
        cards.append('<div class="tp-person tp-member" data-key="%s" data-q="%s">%s<div><b>%s</b><ul>%s</ul><small>%s</small></div></div>' % (
            attr(key), attr((r['name'] + ' ' + ' '.join(extra)).lower()), fig, esc(r['name']),
            ''.join('<li>%s</li>' % esc(x) for x in extra), credit))
    return ''.join(cards)


def member_tools(label, keys, counts):
    opts = ''.join('<option value="%s">%s (%s)</option>' % (attr(k), esc(k), th(counts[k])) for k in keys)
    return ('<div class="tp-mtools"><select class="tp-mkey" aria-label="%s"><option value="">%sทั้งหมด</option>%s</select>'
            '<input class="tp-mq" type="search" placeholder="ค้นหาชื่อ จังหวัด…" aria-label="ค้นหาชื่อ">'
            '<span class="tp-mcount" aria-live="polite"></span></div>') % (attr(label), esc(label), opts)


def ext_members():
    d = ext('mps')['data']
    rows = d['rows']
    photos = dict(ext('cabinet_photos')['photos'])
    if os.path.exists(os.path.join(ROOT, 'data', 'external', 'member_photos.json')):
        photos.update(ext('member_photos')['photos'])
    counts = {}
    for r in rows:
        counts[r['party']] = counts.get(r['party'], 0) + 1
    parties = sorted(counts, key=lambda k: (-counts[k], k))
    mp_cards = member_cards(rows, photos, 'mps', lambda r: ([r['party'], th(r['seat'].replace('สมาชิกสภาผู้แทนราษฎร', '').strip())], r['party']))
    n_photo = sum(1 for r in rows if r['name'] in photos)
    mp = ('<p class="tp-note">%s ตามระบบสารสนเทศสมาชิก สำนักงานเลขาธิการสภาผู้แทนราษฎร ดึงข้อมูลเมื่อ %s มีรายชื่อ <b>%s คน</b> '
          'เรียงตามเลขประจำตัวสมาชิก ชื่อ เขต และพรรคสะกดตามต้นฉบับ มีภาพที่ใช้ได้โดยเสรีจาก Wikimedia Commons %s คน</p>%s'
          '<div class="tp-people tp-members">%s</div>') % (
        esc(th(d['heading'])), th_date(ext('mps')['retrieved']), th(len(rows)), th(n_photo),
        member_tools('พรรค', parties, counts), mp_cards)
    spath = os.path.join(ROOT, 'data', 'external', 'senators.json')
    if os.path.exists(spath):
        s = ext('senators')['data']
        srows = s['rows']
        assert len(srows) == s['total_on_page'], 'senator list shorter than the total the page shows'
        gcount, gid = {}, {}
        for r in srows:
            gcount[r['group']] = gcount.get(r['group'], 0) + 1
            gid[r['group']] = r['groupid']
        groups = sorted(gcount, key=lambda k: gid[k])  # the senate site's own group order
        sw = ('<p class="tp-note">รายชื่อ%sตามเว็บไซต์วุฒิสภา (สำนักงานเลขาธิการวุฒิสภา) ดึงข้อมูลเมื่อ %s มีรายชื่อ <b>%s คน</b> ใน %s กลุ่ม '
              'เรียงตามเลขที่ ชื่อและกลุ่มสะกดตามต้นฉบับ สว. ไม่สังกัดพรรคการเมือง จึงแสดงกลุ่มอาชีพที่ได้รับเลือกแทนพรรค '
              'มีภาพที่ใช้ได้โดยเสรีจาก Wikimedia Commons %s คน</p>'
              '%s<div class="tp-people tp-members">%s</div>') % (
            esc(s['heading']), th_date(ext('senators')['retrieved']), th(len(srows)), th(len(groups)),
            th(sum(1 for r in srows if r['name'] in photos)),
            member_tools('กลุ่ม', groups, gcount),
            member_cards(srows, photos, 'senators', lambda r: ([th(r['group'])], r['group'])))
    else:
        sw = ('<div class="rc-explain"><b>ยังไม่มีรายชื่อสมาชิกวุฒิสภาในหน้านี้</b> รายชื่อต้องดึงจากเว็บไซต์ของรัฐสภาโดยตรง '
              'ซึ่งยังไม่ได้ดึงมา หน้านี้จึงยังไม่แสดงรายชื่อที่พิมพ์ขึ้นเอง</div>')
    return ('<div class="tp-chambers" role="tablist">'
            '<button type="button" role="tab" class="tp-filter is-on" data-chamber="mp" aria-selected="true">สส. · สภาผู้แทนราษฎร (%s)</button>'
            '<button type="button" role="tab" class="tp-filter" data-chamber="sw" aria-selected="false">สว. · วุฒิสภา%s</button></div>'
            '<div class="tp-chamber" data-chamber="mp">%s</div><div class="tp-chamber" data-chamber="sw" hidden>%s</div>') % (
        th(len(rows)), ' (%s)' % th(len(srows)) if os.path.exists(spath) else '', mp, sw)


THMON = ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม']


def wiki_date(s):
    """'28 มิถุนายน พ.ศ. 2475' → '2475-06-28'; 'ปัจจุบัน' → None"""
    m = re.match(r'(\d+) (\S+) (?:พ\.ศ\. )?(\d{4})', s)
    return '%s-%02d-%02d' % (m.group(3), THMON.index(m.group(2)) + 1, int(m.group(1))) if m else None


def days(a, b):
    """days between two B.E. 'YYYY-MM-DD' dates"""
    import datetime
    f = lambda s: datetime.date(int(s[:4]) - 543, int(s[5:7]), int(s[8:10]))
    return (f(b) - f(a)).days


def pm_rows():
    """Official list (E-Museum) joined with terms (Wikipedia, secondary), charters (OCS + 4 from Wikipedia),
    notes (checked against the Wikipedia leads) and photos."""
    hist = sorted(ext('pm_history')['data'], key=lambda x: x['number'])
    assert [x['number'] for x in hist] == list(range(1, len(hist) + 1)), 'PM numbers not continuous'
    assert hist[-1]['number'] == ext('pm')['data']['number'], 'E-Museum list and current-PM page disagree'
    photos = ext('pm_photos')['photos']
    leads = ext('wiki_pm_leads')['data']
    notes = load('pm_notes.json')
    charters = ext('constitutions')['data']
    y, m, d = ext('pm')['retrieved'].split('-')
    today = '%d-%s-%s' % (int(y) + 543, m, d)
    seen, terms = set(), []
    for t in ext('pm_terms')['data']['terms']:
        key = (t['pm'], t['cabinet'], t['start'], t['end'])
        if key not in seen:
            seen.add(key)
            terms.append(dict(t, s=wiki_date(t['start']), e=wiki_date(t['end']) or today,
                              party=re.sub(r'\[[a-z0-9]+\]', '', t['party']).strip()))
    terms.sort(key=lambda t: t['s'])
    rows = []
    for x in hist:
        n = x['number']
        mine = [t for t in terms if t['pm'] == n]
        assert mine, 'no terms for PM %d' % n
        note = notes['notes'][str(n)]
        for phrase in note['check']:
            if phrase not in leads[str(n)]['lead']:
                raise SystemExit('PM %d note: lead does not contain “%s”' % (n, phrase))
        # year spans: a new span starts when someone else held office in between
        spans = []
        for t in mine:
            i = terms.index(t)
            ys, ye = int(t['s'][:4]), int(t['e'][:4])
            if spans and i and terms[i - 1]['pm'] == n:
                spans[-1][1] = max(spans[-1][1], ye)
            else:
                spans.append([ys, ye])
        # charters in force: the one in force at each term's start (unless that one predates a coup
        # that ended the previous term — then none was in force yet) plus any promulgated during the term
        used = []
        for t in mine:
            i = terms.index(t)
            before = [c for c in charters if c['date'] <= t['s']]
            prev = terms[i - 1] if i else None
            pre = before[-1] if before else None
            soon = [c for c in charters if t['s'] < c['date'] <= t['e'] and days(t['s'], c['date']) <= 30]
            # the term began in the gap after a coup that abolished the old charter (e.g. 6 Oct 2519):
            # only then is the charter from before the coup not the one in force
            if pre and prev and 'รัฐประหาร' in prev['end_how'] and pre['date'] < prev['e'] and soon:
                pre = None
            for c in ([pre] if pre else []) + [c for c in charters if t['s'] < c['date'] <= t['e']]:
                if c not in used:
                    used.append(c)
        parties = []
        for t in mine:
            if t['party'] and t['party'] not in parties:
                parties.append(t['party'])
        rows.append(dict(n=n, name=re.sub(r'\s+', ' ', x['name']),
                         link=next((t['href'] for t in x['terms']), 'https://archives.thaigov.go.th/th/history/prime-minister'),
                         photo=photos.get(str(n)), private='assets/img/private/pm/%d.jpg' % n,
                         terms=mine, spans=spans, charters=used, parties=parties, note=note['text'],
                         lead=leads[str(n)], black=n in notes['black'], current=mine[-1]['end'].startswith('ปัจจุบัน'),
                         era=0 if spans[0][0] < 2500 else (1 if spans[0][0] < 2540 else 2)))
    return rows


ERAS = [('era-1', 'พ.ศ. ๒๔๗๕–๒๔๙๙'), ('era-2', 'พ.ศ. ๒๕๐๐–๒๕๓๙'), ('era-3', 'พ.ศ. ๒๕๔๐–ปัจจุบัน')]


def charter_short(c):
    t = c['title']
    if 'แก้ไขเพิ่มเติม' in t:
        return 'รัฐธรรมนูญ ๒๔๗๕ แก้ไข ๒๔๙๕'
    ys = re.findall(r'[๐-๙]{4}', t)
    kind = 'ธรรมนูญการปกครอง' if 'ธรรมนูญการปกครอง' in t else ('รัฐธรรมนูญชั่วคราว' if 'ชั่วคราว' in t else 'รัฐธรรมนูญ')
    return '%s %s' % (kind, ys[-1] if ys else th(c['date'][:4]))


def span_text(r):
    parts = [th(a) if a == b else '%s–%s' % (th(a), th(b)) for a, b in r['spans']]
    if r['current']:
        parts[-1] = th(r['spans'][-1][0]) + '–ปัจจุบัน'
    return parts


def party_cell(name):
    """Logo box like the reference table: a free Commons logo on the public site, the Thai Wikipedia
    logo (fair use) only from the private folder on this computer, otherwise a neutral initial badge."""
    logos = ext('party_logos')['logos']
    private = 'assets/img/private/parties/%s.png' % name
    core = re.sub(r'^(พรรค|คณะ|ขบวนการ)', '', name)
    initial = (re.search(r'[ก-ฮ]', core) or re.search(r'[ก-ฮ]', name)).group(0)
    lg = logos.get(name)
    if lg:
        pic = '<img class="tp-logo" src="%s" data-private="%s" alt="" loading="lazy">' % (attr(lg['src']), attr(private))
        credit = '<a class="tp-credit" href="%s" rel="noopener" target="_blank">%s</a>' % (attr(lg['page']), esc(lg['license']))
    elif name == 'อิสระ':
        pic, credit = '<span class="tp-logo tp-logo-none" aria-hidden="true">–</span>', ''
    else:
        pic = '<span class="tp-logo tp-logo-none" data-private="%s" aria-hidden="true">%s</span>' % (attr(private), esc(initial))
        credit = ''
    return '<div class="tp-party"><div class="tp-party-box">%s</div><span>%s</span>%s</div>' % (pic, esc(name), credit)


def ext_pm_table():
    rows = pm_rows()
    btns = '<button type="button" class="tp-filter is-on" data-era="all">แสดงทั้งหมด</button>' + ''.join(
        '<button type="button" class="tp-filter" data-era="%s">%s</button>' % e for e in ERAS)
    body = []
    for r in rows:
        p = r['photo']
        if p:
            pic = '<img src="%s" data-private="%s" alt="%s" loading="lazy">' % (attr(p['src']), attr(r['private']), attr(r['name']))
            credit = '<a class="tp-credit" href="%s" rel="noopener" target="_blank">ภาพ: %s · %s</a>' % (
                attr(p['page']), esc(p['artist'] or 'Wikimedia Commons'), esc(p['license']))
        else:
            pic = '<span class="tp-noimg" data-private="%s" aria-hidden="true">%s</span>' % (attr(r['private']), th(r['n']))
            credit = '<span class="tp-credit">ไม่พบภาพที่ใช้ได้โดยเสรี</span>'
        cab = ', '.join(dict.fromkeys(t['cabinet'] for t in r['terms']))
        badges = ''.join('<a class="tp-era-badge tp-%s" href="%s"%s title="%s">%s</a>' % (
            ERAS[r['era']][0], attr(c['url']), '' if c['url'].startswith('#') else ' rel="noopener" target="_blank"',
            attr(c['title'] + (' — วันที่จากวิกิพีเดีย' if c['src'] == 'wiki' else ' — ' + c['ref'])), esc(charter_short(c)))
            for c in r['charters'])
        body.append(
            '<tr class="tp-pm-row" data-n="%d" data-era="%s">'
            '<td class="tp-pm-no">%s</td>'
            '<td class="tp-c"><div class="tp-pm-frame%s">%s</div>%s</td>'
            '<td><b class="tp-pm-name">%s</b><span class="tp-pm-sub">คณะรัฐมนตรีคณะที่ %s</span>'
            '<span class="tp-pill">%s คณะรัฐมนตรี</span> <a class="tp-pm-link" href="%s" rel="noopener" target="_blank">ประวัติทางการ ↗</a></td>'
            '<td class="tp-c">%s</td><td class="tp-c tp-years">%s</td><td>%s</td>'
            '<td class="tp-pm-note">%s</td></tr>' % (
                r['n'], ERAS[r['era']][0], th(r['n']), ' is-black' if r['black'] else '', pic, credit,
                esc(r['name']), esc(th(cab)), th(len(dict.fromkeys(t['cabinet'] for t in r['terms']))), attr(r['link']),
                ''.join(party_cell(x) for x in r['parties']) or '–',
                '<br>'.join(span_text(r)), badges, esc(r['note'])))
    return ('<div class="tp-filters" role="group" aria-label="กรองตามช่วงเวลา">%s</div>'
            '<div class="tp-scroll"><table class="tp-table tp-pm"><thead><tr>'
            '<th class="tp-c">ลำดับ</th><th class="tp-c">รูปนายก</th><th>ชื่อของนายก</th><th class="tp-c">พรรคที่อยู่</th>'
            '<th class="tp-c">ปีที่เป็นนายก</th><th>รัฐธรรมนูญฉบับ</th><th>ผลงาน / บทบาทสำคัญ</th></tr></thead>'
            '<tbody>%s</tbody></table></div>') % (btns, ''.join(body))


def ext_pm_hall():
    rows = pm_rows()
    data = {'title': 'นายกรัฐมนตรีแห่งราชอาณาจักรไทย', 'rail': 'นายกรัฐมนตรีคนที่ ๑–%s' % th(len(rows)),
            'items': [{'label': 'นายกรัฐมนตรีคนที่ %s' % th(r['n']), 'name': r['name'], 'note': ' · '.join(span_text(r)),
                       'frame': 'black' if r['black'] else 'wood',
                       'src': r['photo']['src'] if r['photo'] else None, 'private': r['private']} for r in rows]}
    return ('<script type="application/json" id="hallData">%s</script>'
            '<portrait-hall class="tp-hall" data-src="hallData" aria-label="หอภาพเหมือนนายกรัฐมนตรี"></portrait-hall>') % (
                json.dumps(data, ensure_ascii=False).replace('</', '<\\/'))


EXT = {'cabinet': ext_cabinet, 'parties': ext_parties, 'pm_table': ext_pm_table, 'pm_hall': ext_pm_hall, 'members': ext_members}


def flag_img(name):
    f = ext('flag_images')['files'][name]
    return ('<img src="%s" alt="" loading="lazy" width="150" height="100">'
            '<a class="tp-credit" href="%s" rel="noopener" target="_blank">ภาพ: Wikimedia Commons · %s</a>') % (
                attr(f['src']), attr(f['page']), esc(f['license']))


def render_topic(t, secs):
    body = t['body']

    # 1. every data-check="N:phrase;law:NAME:N:phrase" must be literally in that section, then the attribute is dropped
    def check(m):
        for pair in m.group(1).split(';'):
            if pair.startswith('ext:'):   # phrase must appear in a saved snapshot of a web page
                _, name, phrase = pair.split(':', 2)
                text, where = json.dumps(ext(name)['data'], ensure_ascii=False), 'snapshot ' + name
                if name.startswith('wiki_'):   # compare with the wiki markup removed: [[a|b]] → b, [[a]] → a, ''' → nothing
                    text = re.sub(r"'{2,}", '', re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', ext(name)['data']['wikitext']))
            elif pair.startswith('law:'):
                _, name, n, phrase = pair.split(':', 3)
                text, where = ' '.join(law(name)['secs'][law_key(n)]), '%s ม.%s' % (name, n)
            else:
                n, phrase = pair.split(':', 1)
                text, where = ' '.join(secs[int(n)]['paras']), 'section %s' % n
            if phrase not in text:
                raise SystemExit('topic %s: %s does not contain “%s”' % (t['id'], where, phrase))
        return ''
    body = re.sub(r'\s*data-check="([^"]*)"', check, body)
    # 2. numbers copied from a source in Arabic digits → Thai digits, so they are never retyped
    body = re.sub(r'\{\{th:([0-9,.]+)\}\}', lambda m: th(m.group(1)), body)
    # 3. "มาตรา ๘๓" in the explanatory text → link (text between tags only)
    body = re.sub(r'>([^<]+)<', lambda m: '>' + linkify_html(m.group(1)) + '<', body)

    # 4. official quotes are copied from the data, never typed
    def quote(m):
        n = int(m.group(1))
        paras = secs[n]['paras']
        part = bool(m.group(2))
        if part:
            a, _, b = m.group(2).partition('-')
            a, b = int(a), int(b or a)
            assert 1 <= a <= b <= len(paras), 'bad paragraph range in ' + m.group(0)
            paras = paras[a - 1:b]
        return ('<blockquote class="tp-quote"><p class="tp-quote-head"><a class="rc-xref" href="#s%d" data-n="%d">มาตรา %s</a>'
                '<span>ตัวบททางการ%s</span></p>%s</blockquote>') % (
                    n, n, secs[n]['th'], ' (บางวรรค)' if part else '', para_html(paras))
    body = re.sub(r'\{\{sec:(\d+)(?::(\d+(?:-\d+)?))?\}\}', quote, body)
    body = re.sub(r'\{\{law:([\w-]+):([0-9๐-๙/]+)(?::(\d+(?:-\d+)?))?\}\}', lambda m: law_quote(m.group(1), m.group(2), m.group(3)), body)
    body = re.sub(r'\{\{lawitems:([\w-]+):([0-9๐-๙/]+)\}\}', lambda m: law_items(m.group(1), m.group(2)), body)
    body = re.sub(r'\{\{ranktable:([\w-]+):([0-9๐-๙/]+)(?::(\d))?\}\}', lambda m: rank_table(m.group(1), m.group(2), m.group(3)), body)
    body = re.sub(r'\{\{lawtitle:([\w-]+)\}\}', lambda m: esc(law(m.group(1))['title']), body)
    body = re.sub(r'\{\{lawurl:([\w-]+)\}\}', lambda m: attr(law(m.group(1))['url']), body)
    body = re.sub(r'\{\{ext:([\w-]+)\}\}', lambda m: EXT[m.group(1)](), body)
    body = re.sub(r'\{\{flagimg:([^}]+)\}\}', lambda m: flag_img(m.group(1)), body)
    left = re.findall(r'\{\{[^}]*\}\}', body)
    assert not left, 'unknown placeholder in %s: %s' % (t['id'], left)

    for s in t['sources']:
        if s.get('ext'):   # {"ext": "cabinet", "t": "…"} → the snapshot's own URL and retrieval date
            E = ext(s['ext'])
            s['t'] = '%s — ดึงข้อมูล %s' % (s['t'], th_date(E['retrieved']))
            s['u'] = E['url']
        if s.get('law'):   # {"law": "flag"} → the scraped law's own title and OCS link
            L = law(s['law'])
            s['t'] = '%s (ฉบับปรับปรุงล่าสุด) — ระบบฐานข้อมูลกฎหมาย สำนักงานคณะกรรมการกฤษฎีกา ดึงข้อมูล %s' % (L['title'], th_date(L['retrieved']))
            s['u'] = L['url']
    srcs = ''.join('<li>%s</li>' % (
        '<a href="%s"%s>%s</a>' % (attr(s['u']), '' if s['u'].startswith('#') else ' rel="noopener" target="_blank"', esc(s['t']))
        if s.get('u') else esc(s['t'])) for s in t['sources'])
    return ('<section class="tp-panel" id="t-%s" data-topic="%s" aria-labelledby="t-%s-h">'
            '<header class="tp-head"><span class="tp-ic" aria-hidden="true">%s</span><div><h3 id="t-%s-h">%s</h3>'
            '<p class="tp-kind">คำอธิบายโดยผู้จัดทำ ไม่ใช่ตัวบทกฎหมาย · กรอบ “ตัวบททางการ” คัดจากตัวบทตามแหล่งอ้างอิงท้ายหัวข้อ · ข้อมูล ณ %s</p></div></header>'
            '<div class="tp-body">%s</div>'
            '<footer class="tp-src"><b>แหล่งอ้างอิง</b><ul>%s</ul></footer></section>') % (
                t['id'], t['id'], t['id'], t['icon'], t['id'], esc(t['title']), th_date(t['asof']), body, srcs)


def topics_html(groups, topics, secs):
    hub, panels, k = [], [], 0
    for g in groups:
        mine = [t for t in topics if t['group'] == g['id']]
        if not mine:
            continue
        k += 1
        btns = ''.join('<button type="button" class="tp-btn" data-topic="%s" aria-controls="t-%s" style="--i:%d">'
                       '<span class="tp-btn-ic" aria-hidden="true">%s</span><span>%s</span></button>' % (
                           t['id'], t['id'], i, t['icon'], esc(t['title'])) for i, t in enumerate(mine))
        hub.append('<details class="tp-group" open><summary><span class="tp-group-ic" aria-hidden="true">%s</span>'
                   '<span class="tp-group-no">%s</span><span class="tp-group-name">%s</span>'
                   '<span class="tp-group-count">%s หัวข้อ</span></summary><div class="tp-btns">%s</div></details>' % (
                       g['icon'], th('%02d' % k), esc(g['name']), th(len(mine)), btns))
        panels += [render_topic(t, secs) for t in mine]
    return ''.join(hub), ''.join(panels)


def build():
    d = load('constitution.json')
    g = load('glossary.json')
    secs = {s['no']: s for s in d['sections']}
    amends = {a['id']: a for a in d['amendments']}
    chapters = d['chapters']
    numbered = [c for c in chapters if c['no'] is not None]
    amended_secs = [s['no'] for s in d['sections'] if s.get('history')]
    meta = d['meta']
    gz_label, gz_date = gazette_label(meta['gazette'])
    enacted = re.search(r'ตราไว้ ณ วันที่ (.+)$', ' '.join(meta['royal'])).group(1)
    retrieved = th_date(meta['source']['retrieved'])
    css_v, js_v = asset_stamp('site.css'), asset_stamp('site.js')

    # ── TOC and hub ──
    toc, hub = [], []
    toc.append('<a class="rc-toc-link" href="#preamble"><span class="rc-toc-name">คำปรารภ</span></a>')
    for c in chapters:
        cid = chapter_id(c)
        rng = 'ม. %s–%s' % (th(c['first']), th(c['last'])) if c['first'] != c['last'] else 'ม. %s' % th(c['first'])
        label = c['label'] if c['no'] is not None else 'บทเฉพาะกาล'
        name = c['title'] if c['no'] is not None else ''
        toc.append('<a class="rc-toc-link" href="#%s" data-ch="%s"><span class="rc-toc-no">%s</span>'
                   '<span class="rc-toc-range">%s</span>%s</a>' % (
                       cid, cid, esc(label), rng, '<span class="rc-toc-name">%s</span>' % esc(name) if name else ''))
        if c['parts']:
            toc.append('<div class="rc-toc-parts">' + ''.join(
                '<a href="#%s-p%d">%s %s</a>' % (cid, p['no'], esc(p['label']), esc(p['title'])) for p in c['parts']) + '</div>')
        count = c['last'] - c['first'] + 1
        am_here = [n for n in amended_secs if c['first'] <= n <= c['last']]
        hub.append('<a class="rc-card%s" href="#%s"><span class="rc-card-no">%s</span>'
                   '<span class="rc-card-name">%s</span><span class="rc-card-meta">%s · %s มาตรา%s%s</span></a>' % (
                       ' is-amended' if am_here else '', cid,
                       esc('หมวด ' + th(c['no'])) if c['no'] is not None else 'บทเฉพาะกาล',
                       esc(c['title']) if c['no'] is not None else 'บทบัญญัติช่วงเปลี่ยนผ่าน',
                       rng, th(count), ' · %s ส่วน' % th(len(c['parts'])) if c['parts'] else '',
                       ' · <b>มีมาตราที่แก้ไข</b>' if am_here else ''))

    # ── document body ──
    body = []
    for c in chapters:
        cid = chapter_id(c)
        head = ('<header class="rc-ch-head"><div class="rc-ch-no">%s</div><h2>%s</h2></header>' % (
            esc(c['label']), esc(c['title'])) if c['no'] is not None else
            '<header class="rc-ch-head is-trans"><h2>บทเฉพาะกาล</h2></header>')
        parts_by_first = {p['first']: p for p in c['parts']}
        inner = []
        for n in range(c['first'], c['last'] + 1):
            if n in parts_by_first:
                p = parts_by_first[n]
                inner.append('<h3 class="rc-part" id="%s-p%d"><span>%s</span> %s</h3>' % (cid, p['no'], esc(p['label']), esc(p['title'])))
            inner.append(section_html(secs[n], amends))
        body.append('<section class="rc-chapter" id="%s" data-ch="%s" data-label="%s">%s%s</section>' % (
            cid, cid, attr(c['label'] + ('' if c['no'] is None else ' ' + c['title'])), head, ''.join(inner)))

    preamble = ''.join('<p>%s</p>' % esc(p) for p in d['preamble'])
    royal = ''.join('<p>%s</p>' % esc(p) for p in meta['royal'])
    countersign = ''.join('<p>%s</p>' % esc(p) for p in d['countersign'])

    # ── amendment history ──
    hist = []
    for a in d['amendments']:
        a_gz, a_date = gazette_label(a['gazette'])
        given = re.sub(r'^ให้ไว้ ณ วันที่ ', '', a['given'])
        changes = ' '.join('<a class="rc-xref" href="#s%d" data-n="%d">มาตรา %s</a>' % (n, n, th(n)) for n in a['changes'])
        act = []
        act.append('<div class="rc-act-title">%s</div>' % esc(a['title']))
        act.append('<div class="rc-act-royal">%s</div>' % ''.join('<p>%s</p>' % esc(p) for p in a['royal']))
        act.append(''.join('<p class="rc-p">%s</p>' % esc(p) for p in a['enacting']))
        for s in a['sections']:
            act.append('<div class="rc-act-sec"><b>มาตรา %s</b> %s</div>' % (s['th'], para_html(s['paras'])))
        act.append('<div class="rc-act-sign">%s</div>' % ''.join('<p>%s</p>' % esc(p) for p in a['countersign']))
        act.append('<p class="rc-act-note">%s</p>' % esc(a['note']))
        rows = []
        for n in a['changes']:
            s = secs[n]
            old, new = compare_html(s['history'][-1]['before'], s['paras'])
            rows.append('<div class="rc-h-cmp"><h4><a class="rc-xref" href="#s%d" data-n="%d">มาตรา %s</a></h4>'
                        '<div class="rc-compare"><div class="rc-pane"><h5>ถ้อยคำเดิม</h5>%s</div>'
                        '<div class="rc-pane is-new"><h5>ถ้อยคำใหม่</h5>%s</div></div></div>' % (n, n, s['th'], old, new))
        hist.append(
            '<li class="rc-tl-item"><div class="rc-tl-dot"></div><div class="rc-tl-body">'
            '<p class="rc-tl-date">ให้ไว้ ณ วันที่ %s · ประกาศในราชกิจจานุเบกษา %s</p>'
            '<h3>%s</h3><p class="rc-tl-src">%s</p>'
            '<p class="rc-tl-changes">มาตราที่แก้ไข: %s</p>'
            '<div class="rc-explain"><b>สรุปสาระ (คำอธิบายโดยผู้จัดทำ ไม่ใช่ตัวบท)</b>'
            '<ul><li>มาตรา ๘๓ สภาผู้แทนราษฎรยังมีสมาชิกห้าร้อยคน แต่เปลี่ยนจากแบบแบ่งเขตเลือกตั้งสามร้อยห้าสิบคนกับบัญชีรายชื่อหนึ่งร้อยห้าสิบคน '
            'เป็นแบบแบ่งเขตเลือกตั้งสี่ร้อยคนกับแบบบัญชีรายชื่อหนึ่งร้อยคน และเพิ่มวรรคให้ใช้บัตรเลือกตั้งแบบละหนึ่งใบ</li>'
            '<li>มาตรา ๘๖ ใช้จำนวนสี่ร้อยคน (แทนสามร้อยห้าสิบคน) เป็นฐานคำนวณจำนวนสมาชิกที่แต่ละจังหวัดพึงมี</li>'
            '<li>มาตรา ๙๑ ยกเลิกวิธีคำนวณเดิม (๕ อนุมาตรา) และกำหนดให้คำนวณผู้ได้รับเลือกแบบบัญชีรายชื่อเป็นสัดส่วนโดยตรงกับคะแนนที่แต่ละพรรคได้รับรวมกันทั้งประเทศ '
            'รายละเอียดให้เป็นไปตามพระราชบัญญัติประกอบรัฐธรรมนูญว่าด้วยการเลือกตั้งสมาชิกสภาผู้แทนราษฎร</li>'
            '<li>มาตรา ๖ ของฉบับแก้ไข (บทเฉพาะกาล) กำหนดว่ามาตราทั้งสามที่แก้ไขยังไม่ใช้บังคับจนกว่าจะมีการเลือกตั้งสมาชิกสภาผู้แทนราษฎรเป็นการทั่วไปครั้งแรกภายหลังประกาศใช้</li></ul>'
            '<p>เหตุผลอย่างเป็นทางการอยู่ใน “หมายเหตุ” ท้ายตัวบทฉบับแก้ไขด้านล่าง</p></div>'
            '%s'
            '<details class="rc-act"><summary>ตัวบทฉบับแก้ไขเพิ่มเติมทั้งฉบับ (ตัวบททางการ)</summary><div class="rc-act-in">%s</div></details>'
            '</div></li>' % (esc(given), esc(a_date), esc(a['title']), esc(a_gz), changes, ''.join(rows), ''.join(act)))

    # ── glossary ──
    indep = [p['title'] for p in next(c for c in chapters if c['no'] == 12)['parts'] if p['title'] != 'บททั่วไป']
    fill = {'{sections}': th(len(d['sections'])), '{chapters}': th(len(numbered)),
            '{independent}': ' '.join(indep[:-1]) + ' และ' + indep[-1]}
    gl = []
    for t in g['terms']:
        text = t['def']
        for k, v in fill.items():
            text = text.replace(k, v)
        found = []
        for s in d['sections']:
            if any(f in p for f in t['find'] for p in s['paras']):
                found.append(s['no'])
        if t['find']:
            assert found, 'glossary term not found in text: ' + t['term']
        where = ''
        if 'chapter' in t:
            c = next(c for c in chapters if (c['no'] if c['no'] is not None else 'T') == t['chapter'])
            where = '<a href="#%s">%s</a>' % (chapter_id(c), esc(c['label'] if c['no'] is not None else 'บทเฉพาะกาล'))
        if found:
            shown = ' '.join('<a class="rc-xref" href="#s%d" data-n="%d">%s</a>' % (n, n, th(n)) for n in found[:8])
            more = ' และอีก %s มาตรา' % th(len(found) - 8) if len(found) > 8 else ''
            where += ('%sพบในมาตรา %s%s' % (' · ' if where else '', shown, more))
        gl.append('<div class="rc-g-item" data-term="%s"><dt>%s</dt><dd><p>%s</p>%s</dd></div>' % (
            attr(t['term']), esc(t['term']), linkify(text), '<p class="rc-g-where">%s</p>' % where if where else ''))

    tl_steps = ' → '.join(esc(x) for x in meta['source']['timeline'])
    n_am = len(d['amendments'])
    am_sources = ''.join('<li>ฉบับแก้ไขเพิ่มเติม %s: %s</li>' % (esc(a['short']), esc(gazette_label(a['gazette'])[0])) for a in d['amendments'])
    changed = ' '.join('<a class="rc-xref" href="#s%d" data-n="%d">มาตรา %s</a>' % (n, n, th(n)) for n in amended_secs)

    # the Royal Gazette comparison is re-run on every build, so the claim on the page is always current
    import verify_gazette
    a_txt, b_txt = verify_gazette.norm(verify_gazette.ocs_original()), verify_gazette.norm(verify_gazette.gazette_text())
    if a_txt == b_txt:
        verify_msg = ('ตรวจเทียบฉบับหลัก (พ.ศ. ๒๕๖๐) กับไฟล์ PDF จากราชกิจจานุเบกษาด้วยโปรแกรมแล้ว ตรงกันทุกตัวอักษร '
                      '(%s ตัวอักษร ไม่นับช่องว่างและการขึ้นบรรทัด)' % th('{:,}'.format(len(a_txt))))
    else:
        raise SystemExit('OCS original text differs from the Royal Gazette PDF — run tools/verify_gazette.py')

    t_groups, topics = load_topics()
    t_hub, t_panels = topics_html(t_groups, topics, secs)

    live = repo_live()
    print('GitHub repo reachable:', live, '(links to it are %s)' % ('included' if live else 'left out'))
    page = TEMPLATE
    repl = {
        '{{CSS_V}}': css_v, '{{JS_V}}': js_v, '{{HALL_V}}': asset_stamp('portrait-hall.js'),
        '{{N_CH}}': th(len(numbered)), '{{N_SEC}}': th(len(d['sections'])),
        '{{N_AM}}': th(n_am), '{{N_AMSEC}}': th(len(amended_secs)),
        '{{ENACTED}}': esc(enacted), '{{GAZETTE}}': esc(gz_label), '{{GZ_DATE}}': esc(gz_date),
        '{{RETRIEVED}}': retrieved, '{{SRC_URL}}': attr(meta['source']['url']), '{{SRC_NAME}}': esc(meta['source']['name']),
        '{{TL_STEPS}}': tl_steps, '{{LATEST}}': esc(d['amendments'][-1]['short']),
        '{{TOC}}': ''.join(toc), '{{HUB}}': ''.join(hub), '{{ROYAL}}': royal, '{{PREAMBLE}}': preamble,
        '{{BODY}}': ''.join(body), '{{COUNTERSIGN}}': countersign, '{{HISTORY}}': ''.join(hist),
        '{{GLOSSARY}}': ''.join(gl), '{{N_GLOSS}}': th(len(g['terms'])), '{{REPO}}': REPO_URL,
        '{{REPO_ABOUT}}': ' ดูได้ที่ <a href="%s" rel="noopener" target="_blank">GitHub</a>' % REPO_URL if live else '',
        '{{REPO_FOOT}}': ' · <a href="%s" rel="noopener" target="_blank">ซอร์สโค้ด</a>' % REPO_URL if live else '',
        '{{REPO_REPORT}}': 'หากพบข้อผิดพลาด โปรดแจ้งผ่าน <a href="%s/issues" rel="noopener" target="_blank">GitHub</a> ' % REPO_URL if live else '',
        '{{AM_SOURCES}}': am_sources, '{{CHANGED}}': changed, '{{VERIFY_GAZETTE}}': verify_msg,
        '{{TOPIC_HUB}}': t_hub, '{{TOPIC_PANELS}}': t_panels, '{{N_TOPICS}}': th(len(topics)),
    }
    for k, v in repl.items():
        page = page.replace(k, v)
    left = re.findall(r'\{\{[A-Z_]+\}\}', page)
    assert not left, left
    with io.open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(page)
    print('index.html', len(page.encode('utf-8')) // 1024, 'KB')


with io.open(os.path.join(ROOT, 'tools', 'template.html'), encoding='utf-8') as _f:
    TEMPLATE = _f.read()

if __name__ == '__main__':
    build()
