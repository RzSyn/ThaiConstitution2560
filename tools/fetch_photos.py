# -*- coding: utf-8 -*-
"""Find a freely licensed photo on Wikimedia Commons for each person in the cabinet snapshot.

For every unique name in data/external/cabinet.json:
  1. strip the honorific/rank, search Wikidata (Thai labels and aliases);
  2. accept a candidate only if its Thai label or an alias equals the name exactly, it is a Thai
     citizen (P27 = Q869) and it has an image (P18); if two candidates pass, take none;
  3. read the file's licence from the Commons API and keep it only if it is a free licence;
  4. save a small thumbnail to assets/img/people/<QID>.jpg and the credit to
     data/external/cabinet_photos.json.
People with no safe match get no photo (the page shows initials). Nothing is guessed.

Run: python tools/fetch_photos.py
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = 'ThaiConstitution2560/1.0 (https://github.com/RzSyn/ThaiConstitution2560)'
PREFIX = re.compile(r'^(นางสาว|นาง|นาย|ว่าที่ร้อยตรีหญิง|ว่าที่ร้อยตรี|ว่าที่ร้อยโท|ว่าที่|พลตำรวจเอก|พลตำรวจโท|พลตำรวจตรี|พันตำรวจเอก|พันตำรวจโท|'
                    r'พลเอก|พลโท|พลตรี|พลเรือเอก|พลเรือโท|พลอากาศเอก|พลอากาศโท|พันเอก|พันโท|พันตรี|ร้อยตำรวจเอก|ร้อยเอก|ร้อยโท|ร้อยตรี|'
                    r'จ่าสิบเอก|หม่อมราชวงศ์|หม่อมหลวง|ศาสตราจารย์|รองศาสตราจารย์|ผู้ช่วยศาสตราจารย์|ดร\.|แพทย์หญิง|นายแพทย์|'
                    r'ทันตแพทย์หญิง|ทันตแพทย์|เภสัชกรหญิง|เภสัชกร)\s*')
FREE = re.compile(r'^(CC BY(-SA)? [0-9.]+( [A-Za-z]+)?|CC0|Public domain|PD.*|Attribution)$', re.I)


def get(url, params):
    q = url + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(q, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def bare(name):
    prev = None
    while prev != name:
        prev, name = name, PREFIX.sub('', name).strip()
    return re.sub(r'\s+', ' ', name)


def candidates(name):
    res = get('https://www.wikidata.org/w/api.php', {'action': 'wbsearchentities', 'search': name, 'language': 'th',
                                                      'uselang': 'th', 'type': 'item', 'limit': 7, 'format': 'json'})
    ids = [r['id'] for r in res.get('search', [])]
    if not ids:
        return []
    ents = get('https://www.wikidata.org/w/api.php', {'action': 'wbgetentities', 'ids': '|'.join(ids),
                                                       'props': 'labels|aliases|claims', 'languages': 'th', 'format': 'json'})['entities']
    out = []
    for qid, e in ents.items():
        labels = [e.get('labels', {}).get('th', {}).get('value', '')] + [a['value'] for a in e.get('aliases', {}).get('th', [])]
        if name not in [re.sub(r'\s+', ' ', bare(l)) for l in labels if l]:
            continue
        claims = e.get('claims', {})
        thai = any(c['mainsnak'].get('datavalue', {}).get('value', {}).get('id') == 'Q869' for c in claims.get('P27', []))
        imgs = [c['mainsnak']['datavalue']['value'] for c in claims.get('P18', []) if 'datavalue' in c['mainsnak']]
        if thai and imgs:
            out.append((qid, imgs[0]))
    return out


def file_info(filename):
    res = get('https://commons.wikimedia.org/w/api.php', {'action': 'query', 'titles': 'File:' + filename, 'prop': 'imageinfo',
                                                          'iiprop': 'url|extmetadata', 'iiurlwidth': 240, 'format': 'json'})
    page = next(iter(res['query']['pages'].values()))
    ii = page['imageinfo'][0]
    meta = ii.get('extmetadata', {})
    strip = lambda s: re.sub(r'<[^>]+>', '', s or '').strip()
    return {'thumb': ii['thumburl'], 'page': ii['descriptionurl'], 'license': strip(meta.get('LicenseShortName', {}).get('value')),
            'license_url': strip(meta.get('LicenseUrl', {}).get('value')), 'artist': strip(meta.get('Artist', {}).get('value')),
            'file': filename}


def main():
    with io.open(os.path.join(ROOT, 'data', 'external', 'cabinet.json'), encoding='utf-8') as f:
        rows = json.load(f)['data']['rows']
    names = []
    for r in rows:
        if r['name'] not in names:
            names.append(r['name'])
    out_dir = os.path.join(ROOT, 'assets', 'img', 'people')
    os.makedirs(out_dir, exist_ok=True)
    photos, report = {}, []
    for full in names:
        name = bare(full)
        try:
            c = candidates(name)
        except Exception as e:
            report.append((full, 'search error %s' % e))
            continue
        if len(c) != 1:
            report.append((full, 'no unique match (%d)' % len(c)))
            continue
        qid, filename = c[0]
        info = file_info(filename)
        if not FREE.match(info['license']):
            report.append((full, 'licence not free: %s' % info['license']))
            continue
        dest = os.path.join(out_dir, qid + '.jpg')
        req = urllib.request.Request(info['thumb'], headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        assert not data[:15].lower().startswith(b'<!doctype html'), 'got an HTML page instead of an image'
        with open(dest, 'wb') as f:
            f.write(data)
        photos[full] = dict(info, qid=qid, src='assets/img/people/%s.jpg' % qid)
        report.append((full, 'ok %s %s' % (qid, info['license'])))
        time.sleep(0.5)
    with io.open(os.path.join(ROOT, 'data', 'external', 'cabinet_photos.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'retrieved': time.strftime('%Y-%m-%d'), 'photos': photos}, f, ensure_ascii=False, indent=1)
    for full, msg in report:
        print(msg, '|', full)
    print('photos:', len(photos), 'of', len(names))


if __name__ == '__main__':
    main()
