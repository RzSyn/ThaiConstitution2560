# -*- coding: utf-8 -*-
"""Save the current senator list exactly as www.senate.go.th shows it.

The page https://www.senate.go.th/view/1/senator_v2/TH-TH is plain HTML: one
<div class="card-tiles" data-groupid=… data-group=…> per senator with the name, "เลขที่ NNN"
and the occupational group. The page also shows the total ("จำนวนสมาชิก"); the script stops if
the number of cards differs from it or a member number repeats.
Photos on that page are government works (copyrighted) and are NOT saved.

Run: python tools/fetch_senators.py   → data/external/senators.json
"""
import datetime
import html
import io
import json
import os
import re
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'https://www.senate.go.th/view/1/senator_v2/TH-TH'


def text(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def main():
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0 (ThaiConstitution2560)'})
    with urllib.request.urlopen(req, timeout=60) as r:
        page = r.read().decode('utf-8', 'replace')
    total = int(re.search(r'จำนวนสมาชิก</div>\s*</div>\s*<span class="number-dashboard">(\d+)</span>', page).group(1))
    rows = []
    for gid, group, body in re.findall(r'<div class="card-tiles" data-groupid="(\d+)" data-group="([^"]*)">(.*?)</div>\s*</div>', page, re.S):
        name = text(re.search(r'<span class="name-bd">(.*?)</span>', body, re.S).group(1))
        no = re.search(r'เลขที่ (\d+)', body).group(1)
        shown = text(re.search(r'<span class="career"\s*>.*?<span>กลุ่มอาชีพ :</span>\s*<span>(.*?)</span>', body, re.S).group(1))
        assert shown == text(group), (no, shown, group)
        rows.append({'no': no, 'name': name, 'group': shown, 'groupid': int(gid)})
    assert len(rows) == total, 'cards %d != total on page %d' % (len(rows), total)
    assert len({r['no'] for r in rows}) == len(rows), 'a member number repeats'
    title = text(re.search(r'<title>(.*?)</title>', page, re.S).group(1))
    out = {'url': URL, 'title': title, 'retrieved': datetime.date.today().isoformat(),
           'data': {'heading': 'สมาชิกวุฒิสภา', 'total_on_page': total, 'count': len(rows), 'rows': rows}}
    with io.open(os.path.join(ROOT, 'data', 'external', 'senators.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('senators: %d (page total %d), groups: %d' % (len(rows), total, len({r['group'] for r in rows})))


if __name__ == '__main__':
    main()
