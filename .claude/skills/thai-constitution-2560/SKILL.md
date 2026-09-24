---
name: thai-constitution-2560
description: Working rules for the ThaiConstitution2560 site — the REAL Thai constitution of 2560 (2017) with every promulgated amendment, one static index.html built from official text. Load before any edit to this project (text, data, build scripts, CSS/JS), before adding an amendment, and whenever a mistake happens so the lesson is written down. Covers the official-text rule, the data pipeline and its checks, where the sources are and how to reach them, and a running log of mistakes.
---

# ThaiConstitution2560

Real law, so **accuracy is the whole point**. This project is separate from the
fictional รัฐธรรมนุญจำลอง site (RzSyn/Politic): nothing from that canon —
invented people, parties, articles, dates, "คณะประชาราษฎร", the ๑,๑๖๐-article
charter — may appear here. Only the *visual style* was borrowed (the user asked
for the look of `website_new.html`: charcoal + gold/jade, Taviraj headings,
Sarabun body, section cards with a number column).

## Where it lives

- Repo: https://github.com/RzSyn/ThaiConstitution2560 (public), branch `main`.
- Site: https://rzsyn.github.io/ThaiConstitution2560/ (GitHub Pages from `main` /root, `.nojekyll`).
- `gh` is installed at `C:/Program Files/GitHub CLI/gh.exe`, logged in as RzSyn (not on the Bash PATH).
- Commit and push after every finished change.

## The official-text rule

- Constitutional text comes **only** from official sources: the Office of the
  Council of State database (searchlaw.ocs.go.th) and the Royal Gazette
  (ratchakitcha.soc.go.th). Never type a section, a date, a gazette reference
  or a number from memory — derive it from `data/constitution.json` or the
  source dump, and read the rendered string back.
- Hand-written text is explanatory and must look different: wrap it in
  `.rc-explain` (dashed border) or put it in `data/glossary.json`, and label it
  "คำอธิบาย … ไม่ใช่ตัวบท". Glossary "พบในมาตรา" lists are computed by the build.
- Every section number cited in an explanation must be one you checked in the
  data (print the section and read it before citing).

## Pipeline (run all of it after any data or build change)

```
python tools/parse_ocs.py        # asserts: 1..279 in order; changed sections == sections the amendment replaces;
                                 #          amendment's quoted wording == consolidated wording
python tools/verify_gazette.py   # original 2560 text vs Royal Gazette PDF, whitespace-free, sara am normalised
python tools/build.py            # index.html; re-runs the gazette check and fails if it no longer matches
python tools/verify_site.py      # reads index.html back and compares every section with the RAW OCS dump
python ~/.claude/skills/safe-web-editing/scripts/div_stack_check.py index.html
node ~/.claude/skills/safe-web-editing/scripts/layout_check.mjs file:///…/index.html 390   # and 320, 1366
```

Assets carry `?v=<sha1>` stamps written by build.py — always rebuild after
editing `assets/site.css` or `assets/site.js`.

## Knowledge topics (`topics/*.html` → hub + stage in index.html)

Each file starts with `<!--topic {json} -->` (id, group from `topics/_groups.json`,
order, icon, title, asof, sources) followed by hand-written HTML. The whole
panel is labelled as explanation; build.py enforces the facts:

- `data-check="83:สี่ร้อยคน;99:คราวละสี่ปี"` on any element: the build fails
  unless each phrase is literally in that section. Put one on every tile, card,
  row or step that states a number or rule from the constitution.
- `{{sec:79}}`, `{{sec:83:1-2}}`: official quote copied from the data. Never
  paste constitutional text into a topic by hand.
- `{{th:2540}}`: numbers taken from an Arabic-digit source, converted to Thai digits.
- "มาตรา ๘๓" in topic text becomes a cross-reference link automatically.
- Facts from outside the constitution (law titles, people, dates) must come
  from an official page you actually read this session. Name it in `sources`.

### Other sources inside topics

- **Other laws:** `tools/scrape_ocs.mjs <docId> <dir> latest` → `data/source-ocs/laws/<name>.json`
  (+ `_index.json`). Use `{{law:NAME:N[:a-b]}}`, `{{lawitems:NAME:N}}`,
  `{{ranktable:NAME:N:k}}`, `{{lawtitle:NAME}}`, check with `law:NAME:N:phrase`.
- **Official web pages:** `node tools/scrape_js.mjs URL tools/scrapers/X.js data/external/NAME.json`
  saves exactly what the page shows (thaigov cabinet/PM/news, hris MP list).
  Render with `{{ext:NAME}}` (renderer in build.py `EXT`). Check with
  `ext:NAME:phrase`. Cite with `{"ext": "NAME", "t": "…"}` in sources.
- **Secondary sources** (Wikipedia, only when no official page is reachable):
  snapshot a fixed revision (`data/external/wiki_*.json`, url with `oldid`).
  Check with `ext:wiki_…:phrase` (wiki markup is stripped first) and label each
  such item `<span class="tp-src-tag">ทุติยภูมิ</span>`.
- **Photos:** `tools/fetch_photos.py` matches each cabinet name to a Wikidata item
  by exact Thai label or alias, Thai citizen, with P18, and keeps it only under
  a free Commons licence; the credit goes under the photo. `tools/fetch_flags.py`
  does the same for flag SVGs. Government works are copyrighted
  (พ.ร.บ.ลิขสิทธิ์ ม.๑๔; ม.๗ exempts only laws, news facts, orders and similar).
  **The owner decided on 2026-09-24, after being told this, to publish official
  photos of people anyway** (see lesson 20): `tools/fetch_official_photos.py`
  saves ≤240×320 copies to `assets/img/official/<set>/` and
  `data/external/official_photos.json`; the build prefers them over Commons
  (cabinet, สส./สว., PM table and hall). Credit the source office under every
  photo. Photo URLs come from saved official pages (senators.json `photo`,
  pm_portraits.json, mp_photo_urls.json), never typed by hand.
- **สส./สว. tab** (`topics/members.html`, `ext:members`): MPs from mps.json (HRIS),
  senators from `tools/fetch_senators.py` (www.senate.go.th plain HTML, checked
  against the page total).
- **MP photos** (HRIS unreachable from the cloud): `tools/fetch_party_photos.py`
  → `mp_photo_party.json`, in this order: Thai PBS election-69 data (district
  MPs: name + province + district must match), PPTV election-69 party pages
  (party-list: name + party), then the party sites (ประชาชน WP API `personel`,
  ประชาธิปัตย์ pages, ภูมิใจไทย `admin.bhumjaithai.com/wp-json/api/v1/candidate_2026`).
  Every match is kept as `alts`, so the download falls through when a host
  fails (PPTV's supabase host is blocked here). The 8 party-list MPs who moved up
  later had no photo anywhere reachable, so `mp_photo_manual.json` holds news
  photos picked by hand (lead image of an article about that MP, looked at,
  cropped to that one person, reason written in `why`). Wikipedia article HTML
  loads even when the API gives 429, but those 8 articles had no image. klathamparty.com is a
  **gambling spam site, not the party**; never use it. ptp.or.th returns 403.
- **Personal-use photos** (the user's choice for people with no free photo, e.g.
  saved from Facebook): the user saves them as
  `assets/img/private/<full name as on thaigov>.jpg`. The folder is git-ignored,
  and site.js swaps a photo in only on `file:` pages when the file exists. Never
  commit or push anything from that folder, and never fetch Facebook images
  yourself.
- soc.go.th (Cabinet Secretariat) is behind the same Cloudflare check as
  ratchakitcha. thaigov.go.th and parliament.go.th / hris.parliament.go.th work
  from the owner's computer. **From a cloud session** (outside Thailand):
  hris.parliament.go.th resets the connection, parliament.go.th/view/1 answers
  401, thaigov.go.th pages show a Cloudflare check; www.senate.go.th and
  media.thaigov.go.th images work. Headless Chromium there fails on the proxy
  certificate, so use curl/Python for static pages.

## Adding a new amendment (ฉบับที่ ๒ …)

1. Find it on OCS: `https://www.ocs.go.th/searchlaw-law?q=รัฐธรรมนูญแห่งราชอาณาจักรไทย`,
   run `tableSearch('law1')` in the page; the current constitution's doc id is
   `VG9mbS9RRXZhdjNGYy9Xcm5LTjd1Zz09`. Its timeline ("ผังแสดงการแก้ไข") lists every version.
2. `node tools/scrape_ocs.mjs <docId> <outDir>` saves every timeline version.
3. Extend `parse_ocs.py` to load all amendment dumps (it currently handles one),
   keep `history` as a list per section, and keep all the asserts.
4. Ask the user to download the Royal Gazette PDF of the amendment
   (ratchakitcha blocks automated access) and add a check like verify_gazette.
5. Update `meta.source.retrieved`, rebuild, run the whole pipeline.

## Reaching the sources

- ratchakitcha.soc.go.th sits behind a Cloudflare bot check: curl gets 403 and
  the browser pane stops at "Just a moment…". **Do not try to get past it** —
  ask the user to download the PDF (they are happy to) into `sources/gazette/`.
- krisdika.go.th no longer answers; the OCS lives at ocs.go.th. The law search
  page is `https://www.ocs.go.th/searchlaw-law?q=…`; documents open at
  `https://searchlaw.ocs.go.th/council-of-state/#/public/doc/<encTimelineID>`
  (an Angular app; its API requests are encrypted, so scrape the rendered DOM:
  `div.in-a4 > div.preview-html` blocks, footnotes in the last block).
- The in-app browser pane is usually hidden: `read_page` returns an empty page
  (viewport 0×0). Use `javascript_tool` / `get_page_text`, or headless Chrome.

## Mistakes and lessons (append every new one — what happened, and the rule)

1. **Gazette reference from memory was wrong (near-miss).** While planning I
   "remembered" the 2564 amendment as published in September 2021, ตอนที่ ๖๑ ก.
   The OCS footnote says ราชกิจจานุเบกษา เล่ม ๑๓๘/ตอนที่ ๗๖ ก/หน้า ๑/๒๑ พฤศจิกายน ๒๕๖๔
   (given ๗ พฤศจิกายน ๒๕๖๔). Nothing was written from memory, which is why it
   did not reach the site. Rule: every date/reference comes from the source.
2. **Typed a wrong Thai digit in a chat message:** wrote "พุทธศักราช ๒๕๖๴"
   (a non-digit character) instead of ๒๕๖๔ when telling the user which PDF to
   download. Rule: copy Thai numerals from the data/tool output, never retype.
3. **Redundant labels from composing strings blindly:** the tag read
   "แก้ไขเพิ่มเติมโดยแก้ไขเพิ่มเติม (ฉบับที่ ๑) พ.ศ. ๒๕๖๔" and the hero
   "รวมการแก้ไขเพิ่มเติมถึงแก้ไขเพิ่มเติม (ฉบับที่ ๑)". Fix: store `no`/`year`
   (derived from the act's title) and compose each label for its sentence.
   Rule: after building, grep the rendered labels and read them.
4. **String comparison of ids:** verify_site filtered `id < 'sec-content-11430'`,
   but `'sec-content-4992' < 'sec-content-11430'` is False (character order), so
   no sections were collected. Rule: compare numbers numerically, or stop at a
   structural marker (the countersign block) as the script now does.
5. **Sticky bar covered section tops on phones:** a fixed `scroll-padding-top`
   assumed a one-row reader bar; at 390 px it wraps to two rows. Now JS sets
   scroll-padding from the bar's real height (ResizeObserver). Rule: check an
   anchor jump at phone width (section top must be below the bar bottom).
6. **Print ran the section number into the text** ("มาตรา ๒๗๘ให้…") because
   the number is inline in print CSS. Added margin. Rule: check print output
   with `Page.printToPDF` and read a page's text, not only the screen.
7. **Environment:** WebSearch returned a model error; DuckDuckGo HTML gave a
   202 challenge; `grep -oE '.{0,220}pattern'` on a 1.5 MB minified bundle ran
   past 120 s — use Python for that. The Gazette PDF text layer writes sara am
   as U+0E4D U+0E32 and breaks lines mid-word; compare whitespace-free.
8. **Headless profile keeps localStorage between runs:** the mobile screenshot
   came out in the "paper" theme set by the desktop run. Reset state explicitly
   in screenshot specs before judging a theme.
9. **Garuda emblem request (2026-09-24).** The user wrote "ตราครุฑสิ". I checked
   the OCS text first: พระราชบัญญัติเครื่องหมายราชการ พุทธศักราช ๒๔๘๒ ม.๖ forbids
   using a เครื่องหมายราชการ without permission, ม.๗ forbids imitating one, and
   ม.๘ sets the penalty. A Garuda would also make this unofficial site look like
   a government one. I advised against it. The user replied "มันครุฑอยู่แล้ว
   ไม่ต้องเปลี่ยน". I first recorded this as "the icon is really the พาน", which
   was **wrong**: the user had already replaced `assets/icon.svg` with a Garuda
   SVG of 532 KB, and `git status` showed it modified. I asserted what the file
   contained without looking at the working tree. Rules: (a) run `git status`
   and look at any file the user mentions before saying what it contains;
   (b) the Garuda icon is the user's informed choice, so keep it and never swap
   it back; (c) because of it, the "ไม่ใช่เว็บไซต์ของหน่วยงานรัฐ" disclaimers on
   the page must stay prominent. (Near-miss: from memory I had the Act as
   พ.ศ. ๒๕๑๑; the OCS title says ๒๔๘๒.)
10. **Linked to a repo that did not exist yet (user found the 404).** The footer's
    "ซอร์สโค้ด" and the about cards linked to github.com/RzSyn/ThaiConstitution2560
    before the user had created it. The fix: build.py now runs `git ls-remote`
    on the repo and leaves the GitHub links out until it answers. **Rebuild after
    the repo is created and pushed** so the links come back. Rule: every link
    must point to something that exists at the moment of the build. Check
    external links, not only in-page anchors.
15. **Said "เสร็จแล้ว" when nothing had changed on the user's screen (user
    correction).** I built the private-photo swap, tested it with a dummy image,
    and opened my reply with "เสร็จแล้วครับ". But no photo can appear until the
    user saves files into `assets/img/private/`, and the folder was empty. The
    user replied "ไม่ขึ้นอยู่ดี" and reminded me that SKILL.md is for learning
    from mistakes, not for adding things. Rules: (a) report done only when the
    user will *see* the result; if it needs their action, lead with
    "ยังไม่ขึ้น จนกว่าคุณจะ…" and say exactly what to do; (b) before
    replying, check the real state (the folder listing), not the dummy test;
    (c) lessons in this file are mistakes and corrections only; procedures go
    in the sections above.
16. **Portrait hall stuttered (user: "โคตรกระตุก").** The canvas hall drew each
    full-size portrait (official files up to 1–2 MP) in up to 44 perspective
    strips, twice per portrait (the "soft" and "sharp" copies were the same
    file), on every frame. My headless test only checked that it rendered, not
    how smoothly it moved. Fix: shrink each portrait once into a ≤420 px canvas
    when it loads, and draw it once. Rule: anything drawn per frame must use
    pre-scaled bitmaps; judge animation by moving it, not by one screenshot.
17. **"รูปแบบเหมือน website_new.html" was not followed (user correction).** For
    the PM list I built my own simpler table: number, photo, name. The
    reference table has ลำดับ · รูปนายก (220×275 gold frame) · ชื่อ (+ second
    line) · พรรค · ปีที่เป็นนายก · รัฐธรรมนูญฉบับ (era badge) · ผลงาน, plus
    era filter buttons. Rule: when the user says "รูปแบบเหมือน X", open X,
    list its columns and parts, and reproduce every one of them (with real,
    sourced data). If a part cannot be filled truthfully, say which one before
    building. Do not quietly drop it.
18. **A rule for "which constitution was in force" left one PM blank.** First
    rule: drop the earlier charter if a coup ended the previous term. That was
    right for Thanin (1976: the 2517 charter was abolished on 6 Oct, and his
    term began before the 2519 charter). It was wrong for Pote Sarasin (1957:
    the coup kept the 2495 charter), whose row came out empty. Rule: print every
    row after writing such a rule and read the edge cases. The rule now also
    requires a new charter within 30 days of the term's start.
19. **Heredoc with a large Thai Python payload failed** ("unexpected EOF").
    Write big scripts with the Write tool, then run them.
20. **Photo rule overridden by the owner; my Wikidata calls got rate-limited
    (2026-09-24).** For the สส./สว. tab I searched Wikidata one name at a time
    (~700 calls) and got HTTP 429 on almost all of them; Commons then refused me
    too. For bulk matching, use one SPARQL query (`tools/fetch_member_photos.py`).
    Only ~110 of ~700 members had a free photo. The user asked to "ignore
    free or not". I explained ม.๑๔ and offered the private folder. The user
    replied that local-only photos are useless for the public site, that they
    accept the risk, and asked for official photos for everyone, earlier photos
    included. Rules: (a) this is the owner's informed choice, like the Garuda
    icon; do not switch back to free-only photos; (b) never hotlink the
    full-size files (senate photos are ~600 KB each), store small copies;
    (c) `pkill -f <name>` also kills the shell running it, so use `pgrep` and
    then `kill <pid>`.
11. **Pages status said "errored" but the site was live.** Two pushes in quick
    succession started two Pages runs, and the first was cancelled. After that
    `gh api repos/…/pages` kept reporting `status: errored` even though the
    second run deployed fine and the URL returned 200. Rule: judge a deploy by
    `gh run watch <id> --exit-status` and by fetching the live URL, not by
    the Pages status field.
12. **Amending acts overwrote the law's own sections.** An OCS "ฉบับปรับปรุงล่าสุด"
    dump appends every amending act, with its own มาตรา ๑, ๒, ๓…, after the
    countersignature. The first law parser kept the *last* "มาตรา ๕", which came
    from an amending act. A data-check on the ministries topic failed and caught
    it. The parser now stops at the first "ผู้รับสนอง…" block and keeps the
    first occurrence. Rule: never key sections by number across a whole dump.
13. **Token waste when peeking at law text:** a loose filter printed 44 KB and
    then 32 KB of Thai text. Rule: first print section numbers and lengths only,
    then print exactly the sections you need. Also edit big files with the Edit
    tool rather than sed/python rewrites, which echo the whole file back as a
    change notice.
14. **Law references inside topics:** "มาตรา N" in topic text is auto-linked to
    the *constitution*. For other laws, write "ม. ๕" (the linker ignores it), and
    law quotes are rendered with `link=False`.
