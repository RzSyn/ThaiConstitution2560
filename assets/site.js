/* ThaiConstitution2560 — interactions. The page is fully readable without this
   file; everything here is progressive enhancement. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var TH = '๐๑๒๓๔๕๖๗๘๙';
  var toTh = function (s) { return String(s).replace(/[0-9]/g, function (d) { return TH[+d]; }); };
  var toAr = function (s) { return String(s).replace(/[๐-๙]/g, function (d) { return TH.indexOf(d); }); };
  var store = {
    get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };
  var root = document.documentElement;
  var N_MAX = $$('.rc-sec').length;

  /* ── theme ─────────────────────────────────────────────────────────── */
  function setTheme(t) {
    root.dataset.theme = t;
    $$('.rc-theme button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.theme === t)); });
    var meta = $('meta[name="theme-color"]');
    if (meta) meta.content = getComputedStyle(root).getPropertyValue('--bg-2').trim() || '#0b0a08';
  }
  $$('.rc-theme button').forEach(function (b) {
    b.addEventListener('click', function () { setTheme(b.dataset.theme); store.set('rc-theme', b.dataset.theme); });
  });
  setTheme(root.dataset.theme || 'gold');

  /* ── font size ─────────────────────────────────────────────────────── */
  $$('[data-fs]').forEach(function (b) {
    b.addEventListener('click', function () {
      var cur = parseFloat(getComputedStyle(root).getPropertyValue('--rc-fs')) || 17;
      var next = Math.min(24, Math.max(14, cur + (+b.dataset.fs)));
      root.style.setProperty('--rc-fs', next + 'px');
      store.set('rc-fs', String(next));
    });
  });

  /* ── toast ─────────────────────────────────────────────────────────── */
  var toastTimer;
  function toast(msg) {
    var t = $('#toast');
    t.textContent = msg; t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.hidden = true; }, 1800);
  }

  /* ── going to a section ────────────────────────────────────────────── */
  function flash(el) {
    el.classList.remove('is-flash'); void el.offsetWidth; el.classList.add('is-flash');
  }
  function goSection(n, push) {
    var el = document.getElementById('s' + n);
    if (!el) { toast('ไม่มีมาตรา ' + toTh(n) + ' (มีมาตรา ๑–' + toTh(N_MAX) + ')'); return false; }
    if (el.offsetParent === null) clearSearch();
    closePopup();
    if (push !== false && location.hash !== '#s' + n) history.pushState(null, '', '#s' + n);
    el.scrollIntoView({ block: 'start' });
    flash(el);
    return true;
  }
  $('#jumpForm').addEventListener('submit', function (e) {
    e.preventDefault();
    var v = parseInt(toAr($('#jump').value).replace(/\D/g, ''), 10);
    if (v) { goSection(v); $('#jump').blur(); }
  });
  window.addEventListener('hashchange', function () {
    var m = /^#s(\d+)$/.exec(location.hash);
    if (m) goSection(+m[1], false);
  });

  /* ── compare old / new wording ─────────────────────────────────────── */
  function setCompare(btn, open) {
    var box = document.getElementById(btn.getAttribute('aria-controls'));
    if (!box) return;
    box.hidden = !open;
    btn.setAttribute('aria-expanded', String(open));
    btn.textContent = open ? 'ซ่อนถ้อยคำเดิม' : 'เทียบถ้อยคำเดิม';
  }
  $('#cmpAll').addEventListener('click', function () {
    var on = this.getAttribute('aria-pressed') !== 'true';
    this.setAttribute('aria-pressed', String(on));
    $$('.rc-sec-act[data-act="compare"]').forEach(function (b) { setCompare(b, on); });
    if (on) { var first = $('.rc-sec.is-amended'); if (first) { first.scrollIntoView({ block: 'start' }); flash(first); } }
  });

  /* ── clicks inside the document ────────────────────────────────────── */
  document.addEventListener('click', function (e) {
    var t = e.target.closest ? e.target : e.target.parentElement;
    var act = t.closest('[data-act]');
    if (act && act.dataset.act === 'compare') { setCompare(act, act.getAttribute('aria-expanded') !== 'true'); return; }
    if (act && act.dataset.act === 'copy') {
      var sec = act.closest('.rc-sec');
      var url = location.href.split('#')[0] + '#' + sec.id;
      var done = function () { toast('คัดลอกลิงก์มาตรา ' + toTh(sec.dataset.n) + ' แล้ว'); };
      if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, function () { prompt('คัดลอกลิงก์', url); });
      else prompt('คัดลอกลิงก์', url);
      return;
    }
    var x = t.closest('a.rc-xref');
    if (x && !e.ctrlKey && !e.metaKey && !e.shiftKey && e.button === 0) {
      e.preventDefault();
      openPopup(x);
      return;
    }
    if (!t.closest('#popup')) closePopup();
  });

  /* ── cross-reference popup ─────────────────────────────────────────── */
  var popup = $('#popup'), popupFrom = null;
  function openPopup(link) {
    var n = +link.dataset.n, sec = document.getElementById('s' + n);
    if (!sec) return;
    if (popupFrom === link && !popup.hidden) { closePopup(); return; }
    var body = sec.querySelector('.rc-sec-body').cloneNode(true);
    $$('mark', body).forEach(function (m) { m.replaceWith(document.createTextNode(m.textContent)); });
    popup.innerHTML = '';
    var head = document.createElement('div');
    head.className = 'rc-popup-head';
    head.innerHTML = '<b>มาตรา ' + toTh(n) + '</b><span><a href="#s' + n + '">ไปที่มาตรา ' + toTh(n) + ' →</a>' +
      '<button type="button" aria-label="ปิด">×</button></span>';
    popup.appendChild(head);
    if (sec.classList.contains('is-amended')) {
      var tag = sec.querySelector('.rc-tag').cloneNode(true);
      popup.appendChild(tag);
    }
    popup.appendChild(body);
    popup.hidden = false;
    popupFrom = link;
    var r = link.getBoundingClientRect(), w = popup.offsetWidth;
    var left = Math.max(12, Math.min(window.scrollX + r.left, window.scrollX + document.documentElement.clientWidth - w - 12));
    var top = window.scrollY + r.bottom + 8;
    if (r.bottom + popup.offsetHeight + 16 > window.innerHeight && r.top > popup.offsetHeight + 16) top = window.scrollY + r.top - popup.offsetHeight - 8;
    popup.style.left = left + 'px';
    popup.style.top = top + 'px';
    head.querySelector('button').addEventListener('click', closePopup);
    head.querySelector('a').addEventListener('click', function (ev) { ev.preventDefault(); goSection(n); });
  }
  function closePopup() { popup.hidden = true; popupFrom = null; }
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { closePopup(); closeToc(); } });

  /* ── table of contents drawer (small screens) ──────────────────────── */
  var toc = $('#toc'), scrim = $('#tocScrim'), tocBtn = $('#tocToggle');
  function closeToc() { toc.classList.remove('is-open'); scrim.hidden = true; tocBtn.setAttribute('aria-expanded', 'false'); }
  tocBtn.addEventListener('click', function () {
    var open = !toc.classList.contains('is-open');
    toc.classList.toggle('is-open', open); scrim.hidden = !open; tocBtn.setAttribute('aria-expanded', String(open));
  });
  scrim.addEventListener('click', closeToc);
  toc.addEventListener('click', function (e) { if (e.target.closest('a')) closeToc(); });

  /* ── mobile search toggle ──────────────────────────────────────────── */
  $('#searchToggle').addEventListener('click', function () {
    var f = $('#searchForm'); f.classList.toggle('is-open');
    if (f.classList.contains('is-open')) $('#q').focus();
  });

  /* ── search ────────────────────────────────────────────────────────── */
  var secs = $$('.rc-sec'), chapters = $$('.rc-chapter'), parts = $$('.rc-part'), preamble = $('#preamble');
  var result = $('#result'), searchTimer, lastQ = '';
  function unmark() {
    $$('mark.rc-hit').forEach(function (m) { var p = m.parentNode; p.replaceChild(document.createTextNode(m.textContent), m); p.normalize(); });
  }
  function markIn(el, terms) {
    var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null), nodes = [], n;
    while ((n = walker.nextNode())) nodes.push(n);
    nodes.forEach(function (node) {
      var text = node.nodeValue, spans = [];
      terms.forEach(function (t) { var i = 0; while ((i = text.indexOf(t, i)) !== -1) { spans.push([i, i + t.length]); i += t.length; } });
      if (!spans.length) return;
      spans.sort(function (a, b) { return a[0] - b[0]; });
      var frag = document.createDocumentFragment(), pos = 0;
      spans.forEach(function (s) {
        if (s[0] < pos) return;
        frag.appendChild(document.createTextNode(text.slice(pos, s[0])));
        var m = document.createElement('mark'); m.className = 'rc-hit'; m.textContent = text.slice(s[0], s[1]);
        frag.appendChild(m); pos = s[1];
      });
      frag.appendChild(document.createTextNode(text.slice(pos)));
      node.parentNode.replaceChild(frag, node);
    });
  }
  function clearSearch() {
    unmark();
    secs.concat(chapters, parts, [preamble]).forEach(function (el) { el.hidden = false; });
    result.hidden = true; lastQ = ''; $('#q').value = '';
  }
  function runSearch(raw) {
    var q = raw.trim().replace(/\s+/g, ' ');
    if (q === lastQ) return;
    lastQ = q;
    unmark();
    if (!q) { clearSearch(); return; }
    var m = /^(?:มาตรา|ม\.?)?\s*([0-9๐-๙]+)$/.exec(q);
    if (m) { var n = +toAr(m[1]); secs.concat(chapters, parts, [preamble]).forEach(function (el) { el.hidden = false; }); result.hidden = true; goSection(n); return; }
    var terms = q.split(' ').map(toTh).filter(Boolean);
    if (terms.join('').length < 2) return;
    var hits = 0;
    secs.forEach(function (s) {
      var text = s.querySelector('.rc-sec-body').textContent;
      var ok = terms.every(function (t) { return text.indexOf(t) !== -1; });
      s.hidden = !ok;
      if (ok) { hits++; markIn(s.querySelector('.rc-sec-body'), terms); }
    });
    var pre = terms.every(function (t) { return preamble.textContent.indexOf(t) !== -1; });
    preamble.hidden = !pre;
    if (pre) markIn(preamble, terms);
    parts.forEach(function (p) {
      var el = p.nextElementSibling, any = false;
      while (el && el.classList.contains('rc-sec')) { if (!el.hidden) any = true; el = el.nextElementSibling; }
      p.hidden = !any;
    });
    chapters.forEach(function (c) { c.hidden = !$$('.rc-sec', c).some(function (s) { return !s.hidden; }); });
    result.hidden = false;
    result.innerHTML = '';
    var span = document.createElement('span');
    span.textContent = hits ? 'พบ “' + terms.join(' ') + '” ใน ' + toTh(hits) + ' มาตรา' + (pre ? ' และคำปรารภ' : '')
                            : 'ไม่พบ “' + terms.join(' ') + '” ในตัวบท' + (pre ? ' (พบในคำปรารภ)' : '');
    var btn = document.createElement('button'); btn.type = 'button'; btn.textContent = 'ล้างการค้นหา';
    btn.addEventListener('click', clearSearch);
    result.appendChild(span); result.appendChild(btn);
    var reader = $('#reader');
    if (reader.getBoundingClientRect().top > window.innerHeight * 0.5 || reader.getBoundingClientRect().bottom < 0) reader.scrollIntoView({ block: 'start' });
  }
  $('#q').addEventListener('input', function () { var v = this.value; clearTimeout(searchTimer); if (!/^\s*(?:มาตรา|ม\.?)?\s*[0-9๐-๙]+\s*$/.test(v)) searchTimer = setTimeout(function () { runSearch(v); }, 300); else if (!v.trim()) clearSearch(); });
  $('#searchForm').addEventListener('submit', function (e) { e.preventDefault(); clearTimeout(searchTimer); lastQ = ''; runSearch($('#q').value); });

  /* ── glossary filter ───────────────────────────────────────────────── */
  var gl = $('#glFilter');
  if (gl) gl.addEventListener('input', function () {
    var q = toTh(gl.value.trim());
    $$('.rc-g-item').forEach(function (it) { it.hidden = !!q && it.textContent.indexOf(q) === -1; });
  });

  /* ── print ─────────────────────────────────────────────────────────── */
  $('#printBtn').addEventListener('click', function () { clearSearch(); closePopup(); window.print(); });
  window.addEventListener('beforeprint', function () { closePopup(); $$('.rc-act').forEach(function (d) { d.open = true; }); });

  /* ── scroll: progress, scrollspy, crumb, back-to-top ───────────────── */
  var bar = $('.rc-progress i'), top = $('#toTop'), crumbCh = $('#crumbCh'), crumbSec = $('#crumbSec');
  var tocLinks = {};
  $$('.rc-toc-link[data-ch]').forEach(function (a) { tocLinks[a.dataset.ch] = a; });
  var navLinks = $$('.rc-nav a');
  var blocks = [preamble].concat(chapters);
  var ticking = false, readerBar = $('#readerBar');
  /* where the sticky reader bar ends; anchors must land below it (it wraps to two rows on phones) */
  function readLine() {
    return (parseFloat(getComputedStyle(root).getPropertyValue('--mast-h')) || 64) + readerBar.offsetHeight + 12;
  }
  function fitPadding() { root.style.scrollPaddingTop = readLine() + 'px'; }
  function onScroll() {
    ticking = false;
    var h = document.documentElement, max = h.scrollHeight - h.clientHeight;
    bar.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + '%';
    top.hidden = h.scrollTop < 900;
    var line = readLine() + 4;
    var cur = null;
    for (var i = 0; i < blocks.length; i++) { if (!blocks[i].hidden && blocks[i].getBoundingClientRect().top <= line) cur = blocks[i]; }
    var key = cur ? cur.dataset.ch : 'preamble';
    Object.keys(tocLinks).forEach(function (k) { tocLinks[k].classList.toggle('is-here', k === key); });
    crumbCh.textContent = cur ? cur.dataset.label : 'คำปรารภ';
    var sec = null;
    if (cur && cur !== preamble) {
      var list = $$('.rc-sec', cur);
      for (var j = 0; j < list.length; j++) { if (!list[j].hidden && list[j].getBoundingClientRect().top <= line) sec = list[j]; }
    }
    crumbSec.textContent = sec ? 'มาตรา ' + toTh(sec.dataset.n) : '';
    var here = null;
    ['about', 'glossary', 'history', 'reader', 'topics'].some(function (id) {
      var el = document.getElementById(id);
      if (el.getBoundingClientRect().top <= line) { here = id; return true; }
      return false;
    });
    navLinks.forEach(function (a) { a.classList.toggle('is-on', a.getAttribute('href') === '#' + here); });
  }
  window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  window.addEventListener('resize', function () { fitPadding(); onScroll(); });
  if (window.ResizeObserver) new ResizeObserver(fitPadding).observe(readerBar);
  top.addEventListener('click', function () { window.scrollTo({ top: 0 }); });
  fitPadding();
  onScroll();

  /* ── personal-use photos: only when a local file exists (the folder is never published) ── */
  if (location.protocol === 'file:') {
    $$('.tp-logo[data-private]').forEach(function (el) {          // party logos: swap only the picture
      var probe = new Image();
      probe.onload = function () {
        if (el.tagName === 'IMG') { el.src = probe.src; }
        else { var im = document.createElement('img'); im.className = 'tp-logo'; im.alt = ''; im.src = probe.src; el.replaceWith(im); }
      };
      probe.src = el.getAttribute('data-private');
    });
    $$('img[data-private]:not(.tp-logo)').forEach(function (im) {
      var probe = new Image();
      probe.onload = function () {
        im.src = probe.src;
        var row = im.closest('.tp-pm-row, .tp-person'), credit = row && row.querySelector('.tp-credit, small');
        if (credit) credit.outerHTML = '<span class="tp-credit">ภาพส่วนตัวในเครื่องนี้ (ไม่ได้เผยแพร่)</span>';
      };
      probe.src = im.getAttribute('data-private');
    });
    $$('.tp-noimg[data-private]:not(.tp-logo)').forEach(function (span) {
      var img = new Image();
      img.onload = function () {
        img.className = 'is-private'; img.alt = ''; img.width = 120; img.height = 160;
        var card = span.closest('.tp-person, .tp-pm-row'), note = card && card.querySelector('small, .tp-credit');
        span.replaceWith(img);
        if (note) note.textContent = 'ภาพส่วนตัวในเครื่องนี้ (ไม่ได้เผยแพร่)';
      };
      img.src = span.getAttribute('data-private');
    });
  }

  /* ── filter buttons (ทำเนียบนายกรัฐมนตรี) ─────────────────────────────── */
  $$('.tp-filters').forEach(function (bar) {
    bar.addEventListener('click', function (e) {
      var b = e.target.closest('.tp-filter'); if (!b) return;
      $$('.tp-filter', bar).forEach(function (x) { x.classList.toggle('is-on', x === b); });
      var era = b.dataset.era;
      $$('.tp-pm-row', bar.parentNode).forEach(function (r) { r.hidden = era !== 'all' && r.dataset.era !== era; });
    });
  });

  /* ── knowledge topics: one panel at a time in the stage ────────────── */
  var tpBtns = $$('.tp-btn'), tpPanels = $$('.tp-panel');
  var tpOrder = tpBtns.map(function (b) { return b.dataset.topic; });
  var tpPrev = $('#tpPrev'), tpNext = $('#tpNext');
  function showTopic(id, push, scroll) {
    var panel = document.getElementById('t-' + id);
    if (!panel) return false;
    tpPanels.forEach(function (p) { p.classList.toggle('is-on', p === panel); });
    tpBtns.forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.topic === id)); });
    var btn = tpBtns.filter(function (b) { return b.dataset.topic === id; })[0];
    var group = btn.closest('.tp-group');
    group.open = true;
    $('#stageTitle').textContent = panel.querySelector('h3').textContent;
    $('#stageGroup').textContent = group.querySelector('.tp-group-name').textContent;
    var i = tpOrder.indexOf(id);
    tpPrev.disabled = i <= 0; tpNext.disabled = i >= tpOrder.length - 1;
    if (push && location.hash !== '#t-' + id) history.pushState(null, '', '#t-' + id);
    if (scroll) $('#stage').scrollIntoView({ block: 'start' });
    return true;
  }
  tpBtns.forEach(function (b) { b.addEventListener('click', function () { showTopic(b.dataset.topic, true, true); }); });
  tpPrev.addEventListener('click', function () { var i = tpOrder.indexOf($('.tp-btn[aria-pressed="true"]').dataset.topic); if (i > 0) showTopic(tpOrder[i - 1], true, true); });
  tpNext.addEventListener('click', function () { var i = tpOrder.indexOf($('.tp-btn[aria-pressed="true"]').dataset.topic); if (i < tpOrder.length - 1) showTopic(tpOrder[i + 1], true, true); });
  window.addEventListener('hashchange', function () {
    var m = /^#t-([\w-]+)$/.exec(location.hash);
    if (m) showTopic(m[1], false, true);
  });
  var mt = /^#t-([\w-]+)$/.exec(location.hash);
  if (!(mt && showTopic(mt[1], false, false)) && tpOrder.length) showTopic(tpOrder[0], false, false);
  if (mt) setTimeout(function () { $('#stage').scrollIntoView({ block: 'start' }); }, 60);

  /* ── arriving with #sN ─────────────────────────────────────────────── */
  var m0 = /^#s(\d+)$/.exec(location.hash);
  if (m0) setTimeout(function () { goSection(+m0[1], false); }, 60);
})();
