# -*- coding: utf-8 -*-
"""Free photos for every MP and senator, with the same rules as fetch_photos.py but one bulk query.

fetch_photos.py searches Wikidata one name at a time; for ~700 names Wikidata answers 429 (too
many requests). This script asks the Wikidata query service once for every human who is a Thai
citizen (P27 = Q869) and has an image (P18), with their Thai labels and aliases, then:
  1. strips the honorific/rank from each member's name (fetch_photos.bare);
  2. accepts an item only if its Thai label or an alias, stripped the same way, equals the name
     exactly; if two items match, takes none;
  3. reads the file's licence from the Commons API and keeps it only if it is free (fetch_photos.FREE);
  4. saves a thumbnail to assets/img/people/<QID>.jpg and the credit to data/external/member_photos.json.
Names already in cabinet_photos.json are skipped (the build uses that file first).

Run: python tools/fetch_member_photos.py
"""
import io
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from fetch_photos import FREE, ROOT, UA, bare, file_info

QUERY = '''SELECT ?item ?img ?name WHERE {
  ?item wdt:P31 wd:Q5; wdt:P27 wd:Q869; wdt:P18 ?img.
  { ?item rdfs:label ?name } UNION { ?item skos:altLabel ?name }
  FILTER(LANG(?name) = "th")
}'''


def retry(fn, *a):
    for wait in (0, 5, 15, 45, 90):
        time.sleep(wait)
        try:
            return fn(*a)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                raise
            last = e
    raise last


def sparql():
    url = 'https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': QUERY, 'format': 'json'})
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/sparql-results+json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)['results']['bindings']


def download(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def ext(name):
    with io.open(os.path.join(ROOT, 'data', 'external', name + '.json'), encoding='utf-8') as f:
        return json.load(f)


def main():
    have = ext('cabinet_photos')['photos']
    names = []
    for r in ext('mps')['data']['rows'] + ext('senators')['data']['rows']:
        if r['name'] not in have and r['name'] not in names:
            names.append(r['name'])
    index = {}   # stripped Thai name → {qid: first image file}
    rows = retry(sparql)
    for b in rows:
        qid = b['item']['value'].rsplit('/', 1)[1]
        img = urllib.parse.unquote(b['img']['value'].rsplit('/', 1)[1]).replace('_', ' ')
        index.setdefault(bare(b['name']['value']), {}).setdefault(qid, img)
    print('Wikidata: %d label rows, %d distinct names' % (len(rows), len(index)))
    out_dir = os.path.join(ROOT, 'assets', 'img', 'people')
    os.makedirs(out_dir, exist_ok=True)
    photos, report = {}, []
    old = ext('member_photos')['photos'] if os.path.exists(os.path.join(ROOT, 'data', 'external', 'member_photos.json')) else {}
    for full in names:
        hits = index.get(bare(full), {})
        if len(hits) != 1:
            report.append((full, 'no unique match (%d)' % len(hits)))
            continue
        qid, filename = next(iter(hits.items()))
        dest = os.path.join(out_dir, qid + '.jpg')
        if full in old and old[full]['qid'] == qid and old[full]['file'] == filename and os.path.exists(dest):
            photos[full] = old[full]     # same match as the last run, file already saved
            report.append((full, 'ok %s %s (kept)' % (qid, old[full]['license'])))
            continue
        try:
            info = retry(file_info, filename)
        except urllib.error.HTTPError as e:
            report.append((full, 'commons error %s — run again later' % e))
            continue
        if not FREE.match(info['license']):
            report.append((full, 'licence not free: %s' % info['license']))
            continue
        try:
            data = retry(download, info['thumb'])
        except urllib.error.HTTPError as e:
            report.append((full, 'download error %s — run again later' % e))
            continue
        assert not data[:15].lower().startswith(b'<!doctype html'), 'got an HTML page instead of an image'
        with open(dest, 'wb') as f:
            f.write(data)
        photos[full] = dict(info, qid=qid, src='assets/img/people/%s.jpg' % qid)
        report.append((full, 'ok %s %s' % (qid, info['license'])))
        time.sleep(1)
    with io.open(os.path.join(ROOT, 'data', 'external', 'member_photos.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'retrieved': time.strftime('%Y-%m-%d'), 'photos': photos}, f, ensure_ascii=False, indent=1)
    for full, msg in report:
        if not msg.startswith('no unique match (0)'):
            print(msg, '|', full)
    print('photos:', len(photos), 'of', len(names))


if __name__ == '__main__':
    main()
