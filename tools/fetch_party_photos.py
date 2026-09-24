# -*- coding: utf-8 -*-
"""MP photo URLs from the parties' own websites, for MPs whose official HRIS photo we cannot reach.

The owner asked (2026-09-24) for a photo of every MP from any source, as long as it is the right
person. A photo is accepted only when:
  * the name on the party's site, with honorifics stripped (fetch_photos.bare), equals the MP's
    name in data/external/mps.json exactly, and
  * that MP belongs to the same party in mps.json, and
  * exactly one MP of that party has that name.
If the site shows the person more than once (e.g. candidate list and board), the first photo is used.
The URL, the page it came from and the party are written to data/external/mp_photo_party.json;
tools/fetch_official_photos.py downloads small copies (HRIS photos, when present, win).

Run: python tools/fetch_party_photos.py
"""
import html
import io
import json
import os
import re
import time
import urllib.request

from fetch_photos import ROOT, bare

UA = 'Mozilla/5.0 (ThaiConstitution2560; https://github.com/RzSyn/ThaiConstitution2560)'


def get(url, as_json=True):
    for wait in (0, 5, 20):
        time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            return json.loads(data) if as_json else data.decode('utf-8', 'replace')
        except Exception as e:
            last = e
    raise last


# each source yields (name as shown, photo url, page url[, place]); a place ("ตรัง เขต 3") must then
# match the MP's seat in mps.json as well

def peoples_party():
    for pg in range(1, 20):
        try:
            rows = get('https://peoplesparty.or.th/wp-json/wp/v2/personel?per_page=100&page=%d&_embed=wp:featuredmedia' % pg)
        except Exception:
            break
        if not rows:
            break
        for p in rows:
            media = (p.get('_embedded', {}).get('wp:featuredmedia') or [{}])[0]
            if media.get('source_url'):
                yield html.unescape(p['title']['rendered']), media['source_url'], p['link']


def democrat():
    for page in ('https://www.democrat.or.th/party-list-representatives/', 'https://www.democrat.or.th/constituency-representatives/'):
        t = get(page, as_json=False)
        for li in re.findall(r'<li[^>]*>(.*?)</li>', t, re.S):
            img = re.search(r'<img[^>]*src="(https://[^"]+)"', li)
            first = re.search(r'<h3[^>]*>(.*?)</h3>', li, re.S)
            last = re.search(r'<h4[^>]*>(.*?)</h4>', li, re.S)
            if img and first and last:
                h3 = ' '.join(html.unescape(re.sub(r'<[^>]+>', '', first.group(1))).split())
                h4 = ' '.join(html.unescape(re.sub(r'<[^>]+>', '', last.group(1))).split())
                if 'เขต' in h4:     # constituency page: full name, then "จังหวัด เขต N"
                    yield h3, img.group(1), page, h4
                else:               # party-list page: first name, then surname
                    yield '%s %s' % (h3, h4), img.group(1), page


def bhumjaithai():
    base = 'https://admin.bhumjaithai.com/wp-json/api/v1/candidate_2026?page=%d'
    first = get(base % 1)
    posts = list(first['posts'])
    for pg in range(2, first['totalPages'] + 1):
        posts += get(base % pg)['posts']
    for p in posts:
        img = ((p.get('acf') or {}).get('image') or {}).get('url')
        if img:
            yield p['post_title'], img, 'https://bhumjaithai.com/candidate'
    for p in get('https://admin.bhumjaithai.com/wp-json/better-rest-endpoints/v1/board_member?per_page=100'):
        acf = p.get('acf') or {}
        img = acf.get('image') or acf.get('photo') or p.get('media') or {}
        url = img.get('url') if isinstance(img, dict) else img if isinstance(img, str) else None
        if not url and isinstance(p.get('media'), dict):
            url = p['media'].get('full')
        if url:
            yield p['title'], url, 'https://bhumjaithai.com/party/board'


SOURCES = [
    ('พรรคประชาชน', 'เว็บไซต์พรรคประชาชน', peoples_party),
    ('พรรคประชาธิปัตย์', 'เว็บไซต์พรรคประชาธิปัตย์', democrat),
    ('พรรคภูมิใจไทย', 'เว็บไซต์พรรคภูมิใจไทย', bhumjaithai),
]


def seat_key(s):
    """'สมาชิกสภาผู้แทนราษฎรจังหวัดตรัง เขตเลือกตั้งที่ 3' and 'ตรัง เขต 3' → 'ตรัง|3'"""
    m = re.search(r'(?:จังหวัด)?\s*(\S+?)\s*เขต(?:เลือกตั้งที่)?\s*(\d+)', s.replace('สมาชิกสภาผู้แทนราษฎร', ''))
    return '%s|%s' % (m.group(1).replace('จังหวัด', ''), m.group(2)) if m else s


TPBS_DATA = 'https://election69-data.thaipbs.or.th'
TPBS_ASSETS = 'https://election69-assets.thaipbs.or.th'
TPBS_PAGE = 'https://www.thaipbs.or.th/election69/result'


def thaipbs(mps):
    """Thai PBS election-2569 data (the files its results page loads). District MPs: the candidate
    in the same province and district with the same name. Party-list MPs: the same name on the
    list of the MP's party, when Thai PBS has a photo for it."""
    manifest = {d['name']: d['version'] for d in get(TPBS_DATA + '/manifest.json')['data']}
    base = '%s/master-data-th/%s/' % (TPBS_DATA, manifest['master-data-th'])
    common, cands = get(base + 'common-data.json'), get(base + 'candidate-data.json')['candidates']
    parties = {p['code']: p['name'] for p in get(base + 'party-data.json')['parties']}
    prov = {p['code']: p['name'] for p in common['provinces']}
    area = {a['code']: '%s|%d' % (prov[a['provinceCode']], a['number']) for a in common['areas']}
    by_seat = {}
    for c in cands:
        by_seat.setdefault(area[c['areaCode']], {}).setdefault(bare('%s %s' % (c['firstName'], c['lastName'])), []).append(c)
    out = {}
    for r in mps:
        if 'บัญชีรายชื่อ' in r['seat']:
            continue
        hits = by_seat.get(seat_key(r['seat']), {}).get(bare(r['name']), [])
        if not hits:
            # Thai PBS sometimes splits a name wrongly ("จ่าเอกยศ" + "สิงห์"): accept the candidate of the
            # same seat and party with the same surname whose prefix+first name ends with the MP's first name
            first, last = bare(r['name']).rsplit(' ', 1)
            hits = [c for cs in by_seat.get(seat_key(r['seat']), {}).values() for c in cs
                    if c['lastName'].strip() == last and 'พรรค' + parties.get(c['partyCode'], '') == r['party']
                    and (c['prefix'] + c['specialPrefix'] + c['firstName']).replace(' ', '').endswith(first.replace(' ', ''))]
        if len(hits) == 1:
            t = hits[0]['code'][-6:]
            out[r['no']] = '%s/candidate_img/v2/normalized-face-portrait-webp-300x480/%d/%d/%d.webp' % (
                TPBS_ASSETS, int(t[:2]), int(t[2:4]), int(t[4:6]))
    code = {v: k for k, v in parties.items()}
    for r in mps:
        pc = code.get(r['party'].replace('พรรค', '', 1))
        if 'บัญชีรายชื่อ' not in r['seat'] or not pc:
            continue
        try:
            lst = get('%s/partylist-candidates/%s/%s.json' % (TPBS_DATA, manifest['partylist-candidates'], pc))['candidates']
        except Exception:
            continue
        hits = [c for c in lst if bare(c['name']) == bare(r['name']) and c.get('candidatePhotoPath')]
        if len(hits) == 1:
            out[r['no']] = '%s/pl-candidate-photos%s' % (TPBS_ASSETS, hits[0]['candidatePhotoPath'])
    return out


def pptv(mps):
    """PPTV election-2569 party pages (pptvhd36.com/election69/parties/<id>): each party-list
    candidate with an avatar. Party-list MPs only; the name and the party must both match."""
    want = {(bare(r['name']), r['party']): r for r in mps if 'บัญชีรายชื่อ' in r['seat']}
    found, misses = {}, 0
    for pid in range(1, 120):
        page = 'https://www.pptvhd36.com/election69/parties/%d' % pid
        try:
            t = get(page, as_json=False)
        except Exception:
            misses += 1
            if misses > 8:
                break
            continue
        m = re.search(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
        if not m:
            continue
        a = json.loads(m.group(1))
        v = lambda i: a[i] if isinstance(i, int) else i
        for o in a:
            if isinstance(o, dict) and 'f_name' in o and 'avatar' in o and v(o['avatar']):
                key = (bare('%s %s' % (v(o['f_name']), v(o['l_name']))), v(o['party_name']))
                if key in want:
                    found.setdefault(want[key]['no'], (v(o['avatar']), page))
        time.sleep(0.5)
    return found


def add(out, no, name, url, page, credit):
    """first source found is the main photo; later ones are kept as 'alts' in case a host is unreachable"""
    e = {'src': url, 'page': page, 'credit': credit}
    if no not in out:
        out[no] = dict(e, name=name, alts=[])
    elif url != out[no]['src'] and url not in [a['src'] for a in out[no]['alts']]:
        out[no]['alts'].append(e)


def main():
    with io.open(os.path.join(ROOT, 'data', 'external', 'mps.json'), encoding='utf-8') as f:
        mps = json.load(f)['data']['rows']
    out, report = {}, []
    try:
        tp = thaipbs(mps)
    except Exception as e:
        tp = {}
        report.append('Thai PBS: source error %s' % e)
    names = {r['no']: r['name'] for r in mps}
    for no, url in tp.items():
        add(out, no, names[no], url, TPBS_PAGE, 'Thai PBS (ข้อมูลเลือกตั้ง ๒๕๖๙)')
    report.append('Thai PBS: %d MPs (%d district seats)' % (len(tp), sum(1 for r in mps if r['no'] in tp and 'บัญชีรายชื่อ' not in r['seat'])))
    try:
        pp = pptv(mps)
    except Exception as e:
        pp = {}
        report.append('PPTV: source error %s' % e)
    for no, (url, page) in pp.items():
        add(out, no, names[no], url, page, 'PPTV (ข้อมูลเลือกตั้ง ๒๕๖๙)')
    report.append('PPTV: %d party-list MPs' % len(pp))
    for party, credit, fn in SOURCES:
        members = {}
        for r in mps:
            if r['party'] == party:
                members.setdefault(bare(r['name']), []).append(r)
        seen = {}
        try:
            for item in fn():
                name, url, page = item[:3]
                place = item[3] if len(item) > 3 else None
                seen.setdefault(bare(name), {}).setdefault(url, (page, place))   # keeps first-seen order
        except Exception as e:
            report.append('%s: source error %s' % (party, e))
        n = 0
        for key, rows in members.items():
            urls = seen.get(key, {})
            if len(rows) != 1 or not urls:
                continue
            url, (page, place) = next(iter(urls.items()))
            if place and seat_key(place) != seat_key(rows[0]['seat']):
                report.append('%s: %s — place on site "%s" differs from seat, skipped' % (party, rows[0]['name'], place))
                continue
            n += 1
            add(out, rows[0]['no'], rows[0]['name'], url, page, credit)
        report.append('%s: %d of %d MPs (site listed %d names with photos)' % (party, n, sum(map(len, members.values())), len(seen)))
    with io.open(os.path.join(ROOT, 'data', 'external', 'mp_photo_party.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'retrieved': time.strftime('%Y-%m-%d'), 'data': dict(sorted(out.items()))}, f, ensure_ascii=False, indent=1)
    print('\n'.join(report))
    print('total:', len(out))


if __name__ == '__main__':
    main()
