# -*- coding: utf-8 -*-
"""Read the built index.html back and check that the text shown for every section
is exactly the OCS text — compared with the raw OCS page dump (innerText), not
with the parsed JSON, so a bug in parse_ocs.py or build.py cannot hide itself.

Run: python tools/verify_site.py
"""
import html
import io
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def norm(s):
    s = html.unescape(s).replace(' ', ' ')
    s = re.sub(r'\[\d+\]', '', s)          # OCS footnote markers
    return re.sub(r'\s+', '', s)


class SecText(HTMLParser):
    """Collect the text inside <article class="rc-sec" id="sN"> … <div class="rc-sec-body"> … </div>."""

    def __init__(self):
        super().__init__()
        self.stack, self.cur, self.depth_body, self.out, self.pre, self.in_pre = [], None, 0, {}, [], 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'article' and 'rc-sec' in (a.get('class') or '').split():
            self.cur = int(a['data-n'])
            self.out[self.cur] = []
        if self.depth_body:
            self.depth_body += tag == 'div'
        elif tag == 'div' and a.get('class') == 'rc-sec-body' and self.cur:
            self.depth_body = 1
        if self.in_pre:
            self.in_pre += tag == 'section'
        elif tag == 'section' and a.get('id') == 'preamble':
            self.in_pre = 1

    def handle_endtag(self, tag):
        if self.depth_body and tag == 'div':
            self.depth_body -= 1
            if not self.depth_body:
                self.cur = None
        if self.in_pre and tag == 'section':
            self.in_pre -= 1

    def handle_data(self, data):
        if self.depth_body:
            self.out[self.cur].append(data)
        if self.in_pre:
            self.pre.append(data)


def main():
    with io.open(os.path.join(ROOT, 'index.html'), encoding='utf-8') as f:
        page = f.read()
    p = SecText()
    p.feed(page)
    with io.open(os.path.join(ROOT, 'data', 'source-ocs', 'consolidated.json'), encoding='utf-8') as f:
        raw = json.load(f)
    ocs = {}
    pre = None
    for it in raw['items']:
        if 'preview-html' not in it['cls'] or not it['id']:
            continue
        t = it['text'].strip()
        if t.startswith('ผู้รับสนองพระราชโองการ'):
            break                          # after this come the amending act's own sections
        m = re.match(r'มาตรา\s*([๐-๙]+)', t)
        if t.startswith('ศุภมัสดุ'):
            pre = t
        if m:
            n = int(''.join(str('๐๑๒๓๔๕๖๗๘๙'.index(c)) for c in m.group(1)))
            ocs[n] = t[m.end():]
    bad = 0
    assert sorted(p.out) == list(range(1, 280)), 'page does not show sections 1..279'
    assert sorted(ocs) == list(range(1, 280)), 'OCS dump parse for verification failed'
    for n in range(1, 280):
        shown, source = norm(''.join(p.out[n])), norm(ocs[n])
        if shown != source:
            bad += 1
            i = next(k for k in range(min(len(shown), len(source))) if shown[k] != source[k]) if shown[:len(source)] != source[:len(shown)] else min(len(shown), len(source))
            print('section %d differs at %d: page …%s… / OCS …%s…' % (n, i, shown[max(0, i - 30):i + 30], source[max(0, i - 30):i + 30]))
    shown_pre = norm(''.join(p.pre))
    assert shown_pre.startswith('คำปรารภ')    # the visually hidden <h2> of the section, not official text
    if shown_pre[len('คำปรารภ'):] != norm(pre):
        bad += 1
        print('preamble differs')
    print('sections checked: 279, preamble checked, differences:', bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
