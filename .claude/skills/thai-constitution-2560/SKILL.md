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
8. **Headless profile keeps localStorage between runs:** the mobile screenshot
   came out in the "paper" theme set by the desktop run. Reset state explicitly
   in screenshot specs before judging a theme.
