# -*- coding: utf-8 -*-
"""Parse the prime-minister table of a fixed Thai Wikipedia revision into data/external/pm_terms.json.

Uses the rendered HTML of that revision (action=parse&oldid=…), expands rowspan/colspan into a grid,
and keeps per term: PM number, cabinet number, start and end (with the reason the source gives),
party and reign. SECONDARY source — the site labels every value taken from it.
Run: python tools/parse_wiki_pms.py
"""
import html
import io
import json
import os
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = 'ThaiConstitution2560/1.0 (https://github.com/RzSyn/ThaiConstitution2560)'


class Tables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables, self.stack = [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'table':
            self.stack.append({'rows': [], 'cls': a.get('class', '')})
        elif not self.stack:
            return
        elif tag == 'tr':
            self.stack[-1]['rows'].append([])
        elif tag in ('td', 'th') and self.stack[-1]['rows']:
            self.stack[-1]['rows'][-1].append({'rs': int(re.sub(r'\D', '', a.get('rowspan', '1')) or 1),
                                               'cs': int(re.sub(r'\D', '', a.get('colspan', '1')) or 1), 'text': ''})
        elif tag == 'br' and self.stack[-1]['rows'] and self.stack[-1]['rows'][-1]:
            self.stack[-1]['rows'][-1][-1]['text'] += '\n'

    def handle_endtag(self, tag):
        if tag == 'table' and self.stack:
            self.tables.append(self.stack.pop())

    def handle_data(self, data):
        if self.stack and self.stack[-1]['rows'] and self.stack[-1]['rows'][-1]:
            self.stack[-1]['rows'][-1][-1]['text'] += data


def grid(rows):
    out, pending = [], {}
    for r in rows:
        line, col, cells = [], 0, list(r)
        while cells or col in pending:
            if col in pending:
                n, text = pending[col]
                line.append(text)
                if n <= 1:
                    del pending[col]
                else:
                    pending[col] = (n - 1, text)
                col += 1
                continue
            c = cells.pop(0)
            for _ in range(c['cs']):
                line.append(c['text'])
                if c['rs'] > 1:
                    pending[col] = (c['rs'] - 1, c['text'])
                col += 1
        out.append(line)
    return out


def clean(s):
    s = re.sub(r'\[\d+\]', '', html.unescape(s))
    return '\n'.join(re.sub(r'\s+', ' ', x).strip() for x in s.split('\n') if x.strip())


def main():
    with io.open(os.path.join(ROOT, 'data', 'external', 'wiki_pm_list.json'), encoding='utf-8') as f:
        snap = json.load(f)
    u = 'https://th.wikipedia.org/w/api.php?' + urllib.parse.urlencode(
        {'action': 'parse', 'oldid': snap['revid'], 'prop': 'text', 'format': 'json', 'formatversion': 2})
    with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=60) as r:
        page = json.load(r)['parse']['text']
    p = Tables()
    p.feed(page)
    table = max((t for t in p.tables if 'wikitable' in t['cls']), key=lambda t: len(t['rows']))
    g = grid(table['rows'])
    terms = []
    for line in g:
        if len(line) < 10:
            continue
        m = re.match(r'\s*(\d+)', clean(line[0]))
        if not m:
            continue
        start, end = clean(line[4]).split('\n'), clean(line[5]).split('\n')
        terms.append({'pm': int(m.group(1)), 'name': clean(line[2]).split('\n')[0], 'cabinet': clean(line[3]),
                      'start': start[0], 'start_how': ' '.join(start[1:]).strip('() '),
                      'end': end[0], 'end_how': ' '.join(end[1:]).strip('() '),
                      'party': clean(line[8]), 'reign': clean(line[9]).split('\n')[-1]})
    out = {'url': snap['url'], 'title': snap['title'], 'retrieved': snap['retrieved'], 'data': {'terms': terms}}
    with io.open(os.path.join(ROOT, 'data', 'external', 'pm_terms.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(len(terms), 'terms,', len({t['pm'] for t in terms}), 'PMs', sorted({t['pm'] for t in terms}) [-5:])


if __name__ == '__main__':
    main()
