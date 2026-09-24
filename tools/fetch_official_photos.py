# -*- coding: utf-8 -*-
"""Small copies of the official photos, published on the site by the owner's decision (2026-09-24).

The photos belong to the offices that took them (government works, พ.ร.บ.ลิขสิทธิ์ ม.๑๔). The site
owner chose to show them anyway, with the source credited under every photo. The build prefers
these over the Wikimedia Commons photos.

Sources (each URL was saved from the official page by another script, never typed by hand):
  senators  data/external/senators.json        rows[].photo   (www.senate.go.th, tools/fetch_senators.py)
  mps       data/external/mp_photo_urls.json   data[no].src   (hris.parliament.go.th, tools/scrapers/hris-mp-photos.js,
                                                               run on a computer in Thailand: HRIS refuses others)
            data/external/mp_photo_manual.json data[no]       (news photos picked and checked by hand, with a crop box)
            data/external/mp_photo_party.json  data[no]       (Thai PBS election data / party websites,
                                                               tools/fetch_party_photos.py; used when HRIS has none)
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
import urllib.parse
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
    names = {r['no']: r['name'] for r in ext('mps')['data']['rows']}
    m = (ext('mp_photo_urls') or {}).get('data', {})
    party = (ext('mp_photo_party') or {}).get('data', {})
    manual = (ext('mp_photo_manual') or {}).get('data', {})
    for no in sorted(names):
        if m.get(no, {}).get('src'):          # official HRIS photo first
            yield 'mps', names[no], no, m[no]['src'], ext('mp_photo_urls')['url'], 'สำนักงานเลขาธิการสภาผู้แทนราษฎร'
        elif no in manual:                    # a news photo picked and checked by hand (crop box)
            e = manual[no]
            yield 'mps', names[no], no, [(e['src'], e['page'], e['credit'], e['crop'])], None, None
        elif no in party:                     # else Thai PBS / PPTV / the MP's party website
            e = party[no]
            yield 'mps', names[no], no, [(x['src'], x['page'], x['credit']) for x in [e] + e.get('alts', [])], None, None
    p = ext('pm_portraits')
    for n, v in sorted(p['data'].items(), key=lambda kv: int(kv[0])):
        yield 'pm', n, n, v['src'], p['url'], 'สำนักเลขาธิการนายกรัฐมนตรี'


def download(url):
    for wait in (0, 5, 20):
        time.sleep(wait)
        try:
            safe = urllib.parse.quote(url, safe=":/?&=%#+@,;~!$'()*[]")   # Thai file names
            req = urllib.request.Request(safe, headers={'User-Agent': UA})
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
        options = url if isinstance(url, list) else [(url, page, who)]   # tried in order until one downloads
        kept = [o for o in options if prev and prev.get('url') == o[0]]
        if kept and os.path.exists(dest):
            url, page, who = kept[0][:3]
        else:
            errors = []
            for opt in options:
                url, page, who = opt[:3]
                try:
                    data = download(url)
                    im = Image.open(io.BytesIO(data))
                    im = im.convert('RGB')
                    if len(opt) > 3 and opt[3]:
                        im = im.crop(tuple(opt[3]))
                    im.thumbnail(BOX, Image.LANCZOS)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    im.save(dest, 'JPEG', quality=80, optimize=True, progressive=True)
                    break
                except Exception as e:
                    errors.append('%s' % e)
            else:
                failed.append((kind, key, ' / '.join(errors)))
                continue
            time.sleep(0.2)
        lic = 'ภาพจากเว็บไซต์ทางการ' if who.startswith('สำนัก') else 'ภาพจากเว็บไซต์'
        sets.setdefault(kind, {})[key] = {'src': rel, 'url': url, 'page': page, 'artist': who, 'license': lic}
    with io.open(os.path.join(ROOT, 'data', 'external', 'official_photos.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'retrieved': time.strftime('%Y-%m-%d'), 'sets': sets}, f, ensure_ascii=False, indent=1)
    for k, v in sets.items():
        print('%s: %d photos' % (k, len(v)))
    for f in failed:
        print('FAILED', *f)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
