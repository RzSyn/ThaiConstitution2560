# -*- coding: utf-8 -*-
"""Second pass for cabinet members still without a photo: search Wikimedia Commons files directly.

A file is a candidate only if its title or description contains the person's full name (without
the title/rank) and its licence is free. Candidates are written to data/external/commons_candidates.json
with thumbnails in the scratch folder given on the command line, so a human can look at them before
anything is accepted. Nothing is added to the site by this script.

Run: python tools/search_commons.py <scratch-dir>
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_photos import bare, FREE, UA  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def api(params):
    q = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(dict(params, format='json'))
    with urllib.request.urlopen(urllib.request.Request(q, headers={'User-Agent': UA}), timeout=30) as r:
        return json.load(r)


def main(scratch):
    os.makedirs(scratch, exist_ok=True)
    with io.open(os.path.join(ROOT, 'data', 'external', 'cabinet.json'), encoding='utf-8') as f:
        rows = json.load(f)['data']['rows']
    with io.open(os.path.join(ROOT, 'data', 'external', 'cabinet_photos.json'), encoding='utf-8') as f:
        have = json.load(f)['photos']
    names = []
    for r in rows:
        if r['name'] not in names and r['name'] not in have:
            names.append(r['name'])
    out = {}
    for full in names:
        name = bare(full)
        res = api({'action': 'query', 'list': 'search', 'srsearch': name, 'srnamespace': 6, 'srlimit': 10})
        cands = []
        for hit in res['query']['search']:
            title = hit['title']
            if not re.search(r'\.(jpe?g|png|webp)$', title, re.I):
                continue
            info = api({'action': 'query', 'titles': title, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiurlwidth': 240})
            page = next(iter(info['query']['pages'].values()))
            ii = page['imageinfo'][0]
            em = ii.get('extmetadata', {})
            strip = lambda s: re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s or '')).strip()
            desc = strip(em.get('ImageDescription', {}).get('value'))
            lic = strip(em.get('LicenseShortName', {}).get('value'))
            if name not in title.replace('_', ' ') and name not in desc:
                continue
            if not FREE.match(lic):
                continue
            k = len(cands)
            thumb = os.path.join(scratch, '%s_%d.jpg' % (re.sub(r'\W+', '', name)[:20] or 'x', k))
            with urllib.request.urlopen(urllib.request.Request(ii['thumburl'], headers={'User-Agent': UA}), timeout=60) as r:
                open(thumb, 'wb').write(r.read())
            cands.append({'file': title[5:], 'thumb_url': ii['thumburl'], 'page': ii['descriptionurl'], 'license': lic,
                          'artist': strip(em.get('Artist', {}).get('value')), 'desc': desc[:300], 'local': thumb})
            time.sleep(0.3)
        out[full] = cands
        print(len(cands), 'candidates |', full)
    with io.open(os.path.join(ROOT, 'data', 'external', 'commons_candidates.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main(sys.argv[1])
