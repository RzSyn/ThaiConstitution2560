# -*- coding: utf-8 -*-
"""Find a freely licensed logo for each party/group in the PM table.

For each name: search Wikidata (Thai), accept an item only if its Thai label or alias equals the name
(with or without "พรรค"), and it has a logo (P154) or, failing that, an image (P18) that is the group's
emblem/flag. Keep the Commons file only under a free licence (logos of text only are usually public
domain). Thumbnails go to assets/img/parties/, credits to data/external/party_logos.json.
Names with no safe match get no logo; the page then shows a neutral initials badge.

Run: python tools/fetch_party_logos.py
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
import build  # noqa: E402
from fetch_photos import FREE, UA  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get(url, params):
    with urllib.request.urlopen(urllib.request.Request(url + '?' + urllib.parse.urlencode(params), headers={'User-Agent': UA}), timeout=40) as r:
        return json.load(r)


def main():
    names = []
    for r in build.pm_rows():
        for p in r['parties']:
            if p not in names:
                names.append(p)
    out_dir = os.path.join(ROOT, 'assets', 'img', 'parties')
    os.makedirs(out_dir, exist_ok=True)
    logos = {}
    for name in names:
        if name == 'อิสระ':
            print('skip (not a group):', name)
            continue
        want = {name, re.sub(r'^พรรค', '', name)}
        res = get('https://www.wikidata.org/w/api.php', {'action': 'wbsearchentities', 'search': name, 'language': 'th',
                                                         'uselang': 'th', 'type': 'item', 'limit': 7, 'format': 'json'})
        ids = [x['id'] for x in res.get('search', [])]
        if not ids:
            print('no search result:', name)
            continue
        ents = get('https://www.wikidata.org/w/api.php', {'action': 'wbgetentities', 'ids': '|'.join(ids),
                                                          'props': 'labels|aliases|claims', 'languages': 'th', 'format': 'json'})['entities']
        cands = []
        for qid, e in ents.items():
            labels = [e.get('labels', {}).get('th', {}).get('value', '')] + [a['value'] for a in e.get('aliases', {}).get('th', [])]
            if not want & set(labels):
                continue
            cl = e.get('claims', {})
            files = [c['mainsnak']['datavalue']['value'] for c in cl.get('P154', []) + cl.get('P41', []) if 'datavalue' in c['mainsnak']]
            if files:
                cands.append((qid, files[0]))
        if len(cands) != 1:
            print('no unique match (%d):' % len(cands), name)
            continue
        qid, fname = cands[0]
        ii = next(iter(get('https://commons.wikimedia.org/w/api.php', {'action': 'query', 'titles': 'File:' + fname, 'prop': 'imageinfo',
                                                                      'iiprop': 'url|extmetadata', 'iiurlwidth': 300, 'format': 'json'})['query']['pages'].values()))
        if 'imageinfo' not in ii:
            print('file not on Commons (local fair-use?):', name, fname)
            continue
        ii = ii['imageinfo'][0]
        em = ii.get('extmetadata', {})
        strip = lambda s: re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s or '')).strip()
        lic = strip(em.get('LicenseShortName', {}).get('value'))
        if not FREE.match(lic):
            print('licence not free (%s):' % lic, name)
            continue
        with urllib.request.urlopen(urllib.request.Request(ii['thumburl'], headers={'User-Agent': UA}), timeout=60) as r:
            data = r.read()
        assert not data[:15].lower().startswith(b'<!doctype html')
        dest = 'assets/img/parties/%s.png' % qid
        open(os.path.join(ROOT, dest), 'wb').write(data)
        logos[name] = {'qid': qid, 'src': dest, 'page': ii['descriptionurl'], 'license': lic, 'file': fname,
                       'artist': strip(em.get('Artist', {}).get('value'))}
        print('ok', lic, name, fname)
        time.sleep(0.4)
    with io.open(os.path.join(ROOT, 'data', 'external', 'party_logos.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'retrieved': time.strftime('%Y-%m-%d'), 'logos': logos}, f, ensure_ascii=False, indent=1)
    print('logos:', len(logos), 'of', len(names))


if __name__ == '__main__':
    main()
