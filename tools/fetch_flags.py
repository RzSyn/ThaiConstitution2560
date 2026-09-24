# -*- coding: utf-8 -*-
"""Download the historical flag drawings used in the flag topic from Wikimedia Commons.

Each file is kept only if Commons reports a free licence; the original SVG goes to
assets/img/flags/ and the credit to data/external/flag_images.json.

Run: python tools/fetch_flags.py
"""
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = 'ThaiConstitution2560/1.0 (https://github.com/RzSyn/ThaiConstitution2560)'
FILES = ['Flag of Thailand (Ayutthaya period).svg', 'Flag of Thailand (1782).svg', 'Flag of Thailand (1817).svg',
         'Flag of Thailand 1855.svg', 'Flag of Thailand (1916).svg']
FREE = re.compile(r'^(CC BY(-SA)? [0-9.]+( [A-Za-z]+)?|CC0|Public domain|PD.*)$', re.I)


def main():
    out_dir = os.path.join(ROOT, 'assets', 'img', 'flags')
    os.makedirs(out_dir, exist_ok=True)
    meta = {}
    for name in FILES:
        q = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({
            'action': 'query', 'titles': 'File:' + name, 'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'format': 'json'})
        with urllib.request.urlopen(urllib.request.Request(q, headers={'User-Agent': UA}), timeout=30) as r:
            page = next(iter(json.load(r)['query']['pages'].values()))
        ii = page['imageinfo'][0]
        em = ii.get('extmetadata', {})
        strip = lambda s: re.sub(r'<[^>]+>', '', s or '').strip()
        lic = strip(em.get('LicenseShortName', {}).get('value'))
        if not FREE.match(lic):
            print('skip (licence %s): %s' % (lic, name))
            continue
        with urllib.request.urlopen(urllib.request.Request(ii['url'], headers={'User-Agent': UA}), timeout=60) as r:
            data = r.read()
        assert data.lstrip()[:5] in (b'<?xml', b'<svg ') or b'<svg' in data[:400], 'not an SVG: ' + name
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower().replace('.svg', '')).strip('-') + '.svg'
        with open(os.path.join(out_dir, slug), 'wb') as f:
            f.write(data)
        meta[name] = {'src': 'assets/img/flags/' + slug, 'page': ii['descriptionurl'], 'license': lic,
                      'artist': strip(em.get('Artist', {}).get('value'))}
        print('ok', lic, name, len(data) // 1024, 'KB')
        time.sleep(0.5)
    with io.open(os.path.join(ROOT, 'data', 'external', 'flag_images.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'retrieved': time.strftime('%Y-%m-%d'), 'files': meta}, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
