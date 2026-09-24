# -*- coding: utf-8 -*-
"""Small copies of the official photos, published on the site by the owner's decision (2026-09-24).

The photos belong to the offices that took them (government works, พ.ร.บ.ลิขสิทธิ์ ม.๑๔). The site
owner chose to show them anyway, with the source credited under every photo. The build prefers
these over the Wikimedia Commons photos.

Sources (each URL was saved from the official page by another script, never typed by hand):
  senators  data/external/senators.json        rows[].photo   (www.senate.go.th, tools/fetch_senators.py)
  mps       data/external/mp_photo_urls.json   data[no].src   (hris.parliament.go.th, tools/scrapers/hris-mp-photos.js,
                                                               run on a computer in Thailand: HRIS refuses others)
  pm        data/external/pm_portraits.json    data[n].src    (archives.thaigov.go.th E-Museum)

Each photo is shrunk to at most 240×320 and saved as assets/img/official/<set>/<key>.jpg; the list
goes to data/external/official_photos.json in the same shape as the Commons photo files
(src, page, artist, license). A photo whose source URL has not changed is not downloaded again.

Run: python tools/fetch_official_photos.py
"""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = 'Mozilla/5.0 (ThaiConstitution2560; https://github.com/RzSyn/ThaiConstitution2560)'
BOX = (240, 320)


def ext(name):
    path = os.path.join(ROOT, 'data', 'external', name + '.json')
    if not os.path.exists(path):
        return None
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def jobs():
    """(set, key, url, page, credit) for every photo we have a URL for"""
    s = ext('senators')
    for r in s['data']['rows']:
        if r.get('photo'):
            yield 'senators', r['name'], r['no'], r['photo'], s['url'], 'สำนักงานเลขาธิการวุฒิสภา'
    m = ext('mp_photo_urls')
    if m:
        names = {r['no']: r['name'] for r in ext('mps')['data']['rows']}
        for no, v in sorted(m['data'].items()):
            if no in names and v.get('src'):
                yield 'mps', names[no], no, v['src'], m['url'], 'สำนักงานเลขาธิการสภาผู้แทนราษฎร'
    p = ext('pm_portraits')
    for n, v in sorted(p['data'].items(), key=lambda kv: int(kv[0])):
        yield 'pm', n, n, v['src'], p['url'], 'สำนักเลขาธิการนายกรัฐมนตรี'


def download(url):
    for wait in (0, 5, 20):
        time.sleep(wait)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.URLError as e:
            last = e
    raise last


def main():
    old = (ext('official_photos') or {}).get('sets', {})
    sets, failed = {}, []
    for kind, key, fname, url, page, who in jobs():
        rel = 'assets/img/official/%s/%s.jpg' % (kind, fname)
        dest = os.path.join(ROOT, rel)
        prev = old.get(kind, {}).get(key)
        if not (prev and prev.get('url') == url and os.path.exists(dest)):
            try:
                data = download(url)
                im = Image.open(io.BytesIO(data))
                im = im.convert('RGB')
                im.thumbnail(BOX, Image.LANCZOS)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                im.save(dest, 'JPEG', quality=80, optimize=True, progressive=True)
            except Exception as e:
                failed.append((kind, key, '%s' % e))
                continue
            time.sleep(0.2)
        sets.setdefault(kind, {})[key] = {'src': rel, 'url': url, 'page': page, 'artist': who, 'license': 'ภาพจากเว็บไซต์ทางการ'}
    with io.open(os.path.join(ROOT, 'data', 'external', 'official_photos.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'retrieved': time.strftime('%Y-%m-%d'), 'sets': sets}, f, ensure_ascii=False, indent=1)
    for k, v in sets.items():
        print('%s: %d photos' % (k, len(v)))
    for f in failed:
        print('FAILED', *f)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
