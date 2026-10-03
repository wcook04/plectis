/* Plectis — the universe companion.
   On the landing the eight problems sit beside a small drawing of the
   universe map. This turns that column into a reading companion for the
   drawing. Point at a problem's row, or at any dot in its sector, and the
   problem rises to the head of the column: its number and title travel up
   from the row into the place of the band's heading, and under them come
   the question, the tally of its results, its short paper and, for a dot
   under the pointer, that result's evidence (how Lean states it, whether
   Comparator has replayed it, the declaration, and the note on how the Lean
   form gives the printed statement). The map lights the problem's sector
   while the column reads it. Leaving the band sets the list back.

   It is a pointer enhancement over an ordinary list of links. universe.js
   loads it only on a fine pointer and only where the list stands beside the
   drawing; a row's link in focus opens it too, Escape closes it, and with
   reduced motion it changes without travelling. Nothing in the column moves
   in layout: the companion lies over the column, and only opacity and
   transform animate. */
(function () {
  'use strict';

  var DWELL = 140;      // a row must hold the pointer this long before the column turns
  var LEAVE = 360;      // after the pointer leaves the band, before the column turns back
  var LINGER = 900;     // a result's card stays this long after the pointer leaves its dot
  var EASE = 'cubic-bezier(0.2, 0.75, 0.25, 1)';

  var CLAIM_TIER = {
    'proved here': 'proved', 'formalised here': 'proved', 'verified finite instance': 'proved',
    'unconditional progress': 'progress', 'conditional reduction': 'conditional',
    'open': 'open', 'cited only': 'open'
  };

  function esc(text) {
    return String(text == null ? '' : text).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  function capital(text) {
    text = String(text || '');
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  function count(n, one, many) {
    return n + ' ' + (n === 1 ? one : (many || one + 's'));
  }

  function attach(api) {
    var host = api.host;
    if (!host || host.querySelector('.uc')) return;
    var section = host.closest('section') || host.parentNode;
    var figure = section.querySelector('.home-split__figure') || api.stage;
    var rows = {};
    var order = [];
    var titleHtml = {};
    var hrefOf = {};
    Array.prototype.forEach.call(host.querySelectorAll('li.home-problem[data-problem-id]'), function (li) {
      var pid = li.getAttribute('data-problem-id');
      var link = li.querySelector('a[href]');
      var title = li.querySelector('.home-problem__title');
      rows[pid] = li;
      order.push(pid);
      hrefOf[pid] = link ? link.getAttribute('href') : '#';
      // The row's own title, glossary marks and all: the companion's title
      // carries them, so a term in it still previews its definition.
      titleHtml[pid] = title ? title.innerHTML : '';
    });
    if (!order.length) return;

    var data = null;
    var detail = null;
    var detailAsked = false;
    // focusKey starts unset, so the first card (even "nothing in focus") is drawn.
    var state = { open: false, problem: null, focusKey: undefined, focus: null, overPanel: false, keyboard: false };
    var timers = { dwell: 0, leave: 0, linger: 0 };
    var motion = !api.reduceMotion && typeof Element !== 'undefined' && !!Element.prototype.animate;

    /* ---- The panel ---------------------------------------------------- */

    var root = document.createElement('div');
    root.className = 'uc';
    root.setAttribute('role', 'region');
    root.setAttribute('aria-label', 'Problem in focus');
    root.setAttribute('data-term-auto', 'off');
    root.setAttribute('aria-hidden', 'true');
    root.inert = true;
    /* Three fixed slots: the eight problems as a quiet row of tabs (at the
       top, so they stay on screen whenever the title is), the problem
       (rebuilt whole for each problem), and the card for what the pointer is
       on, a slot that fills the rest of the column so a card never moves
       anything. A slot's contents are replaced, never pushed. */
    root.innerHTML =
      '<nav class="uc__switch" aria-label="The eight problems"></nav>' +
      '<div class="uc__problem"></div>' +
      '<div class="uc__focus" aria-live="polite"></div>';
    host.classList.add('uc-host');
    host.appendChild(root);
    var el = {
      problem: root.querySelector('.uc__problem'),
      focus: root.querySelector('.uc__focus'),
      sw: root.querySelector('.uc__switch'),
      kicker: null, title: null, question: null, tally: null, paper: null
    };
    el.sw.innerHTML = order.map(function (pid) {
      var num = rows[pid].querySelector('.home-problem__num');
      return '<a class="uc__chip" data-problem="' + esc(pid) + '" href="' + esc(hrefOf[pid]) + '">' +
        esc(num ? num.textContent : pid) + '</a>';
    }).join('');

    /* A row's title carries glossary marks that open a definition on hover.
       Where the companion can open, the row is about to lie under it, so the
       row's marks rest and the companion's title (the same words, marks and
       all) offers them instead. Where it cannot, the row keeps them. */
    var rowMarks = host.querySelectorAll('li.home-problem span[data-term-preview-only]');
    function restRowMarks(rest) {
      Array.prototype.forEach.call(rowMarks, function (span) {
        if (rest) {
          span.removeAttribute('data-term-preview-only');
          span.setAttribute('data-uc-preview-rests', '');
        } else if (span.hasAttribute('data-uc-preview-rests')) {
          span.setAttribute('data-term-preview-only', '');
          span.removeAttribute('data-uc-preview-rests');
        }
      });
    }

    fetch(api.dataUrl).then(function (r) { return r.json(); }).then(function (payload) {
      data = payload;
    }).catch(function () {});

    function needDetail() {
      if (detailAsked || !data || !data.detail) return;
      detailAsked = true;
      fetch(api.route(data.detail)).then(function (r) { return r.json(); }).then(function (payload) {
        detail = payload;
        // The note for the card on show arrives with the file.
        if (state.focus && state.focus.kind === 'paper_statement') {
          el.focus.innerHTML = focusHtml(state.focus);
        }
      }).catch(function () {});
    }

    /* ---- What the panel says ------------------------------------------ */

    function tallyHtml(problem, t) {
      var parts = [];
      if (problem.status && problem.status !== 'open') {
        parts.push('<span class="uc__status">' + esc(capital(problem.status)) + '</span>');
      }
      if (t && t.results) {
        var line = '<span class="uc-mark uc-mark--replayed" aria-hidden="true"></span>' +
          esc(t.replayed + ' of ' + count(t.results, 'result') + ' in its papers replayed by Comparator');
        var rest = [];
        if (t.lean) rest.push(t.lean + ' exact in Lean with the replay queued');
        if (t.modulo) rest.push(t.modulo + ' in Lean under named inputs');
        if (t.none) rest.push(count(t.none, 'without a Lean statement', 'without a Lean statement'));
        if (rest.length) line += esc('; ' + rest.join(', '));
        parts.push('<span class="uc__tally-line">' + line + '.</span>');
      }
      return parts.join('');
    }

    function paperHtml(problem) {
      var papers = problem.papers || [];
      var short = papers.filter(function (p) { return p.label === 'Short paper'; })[0] || papers[0];
      if (!short) return '';
      var long = papers.filter(function (p) { return p !== short && p.page; })[0];
      var links = [];
      if (short.page) links.push('<a href="' + esc(api.route(short.page)) + '">Read it</a>');
      if (short.pdf) {
        links.push('<a href="' + esc(api.route(short.pdf)) + '">PDF' +
          (short.pages ? ', ' + esc(count(short.pages, 'page')).replace(' ', '&nbsp;') : '') + '</a>');
      }
      if (long) links.push('<a href="' + esc(api.route(long.page)) + '">The long record</a>');
      var title = short.page
        ? '<a class="uc__paper-title" href="' + esc(api.route(short.page)) + '">' + short.title_html + '</a>'
        : '<span class="uc__paper-title">' + short.title_html + '</span>';
      return '<p class="uc__label">' + esc(short.label === 'Short paper' ? 'The short paper' : short.label) + '</p>' +
        title +
        (short.precis_html ? '<p class="uc__precis">' + short.precis_html + '</p>' : '') +
        (links.length ? '<p class="uc__links">' + links.join('') + '</p>' : '');
    }

    function leanSentence(s) {
      var how = s.lean_status === 'exact_or_stronger' ? 'Lean states it or something stronger' : 'Lean states it exactly';
      if (s.tier === 'replayed') return how + ', and Comparator has replayed it.';
      if (s.tier === 'lean') {
        return how + '; its Comparator replay is queued' + (s.comparator_queued_at ? ' since ' + s.comparator_queued_at : '') + '.';
      }
      if (s.tier === 'modulo') return 'Lean states it under named inputs.';
      return 'No Lean statement is recorded for it yet.';
    }

    function linksHtml(s, readLabel) {
      var links = [];
      if (s.href) links.push('<a href="' + esc(s.href) + '">' + esc(readLabel) + '</a>');
      if (s.mapHref) links.push('<a href="' + esc(s.mapHref) + '">Open it in the map</a>');
      return links.length ? '<p class="uc__links">' + links.join('') + '</p>' : '';
    }

    function focusHtml(s) {
      if (!s || s.kind === 'problem') {
        return '<p class="uc__hint">Point at a dot on the map to read that result here.</p>';
      }
      if (s.kind === 'paper_statement') {
        var d = detail && detail.statements ? detail.statements[s.id] : null;
        var note = (d && d.html_mathml && d.html_mathml.relation_note) || s.leanReasonHtml || '';
        var decl = s.decls && s.decls[0];
        // A declaration's last two segments name it; the full name is its title.
        var parts = decl ? String(decl.name).split('.') : [];
        var shortName = parts.length > 2 ? '…' + parts.slice(-2).join('.') : (decl ? decl.name : '');
        return '<p class="uc__label">' + (s.side === 'long' ? 'In the long record' : 'In the short paper') + '</p>' +
          '<p class="uc__focus-title"><span class="uc-mark uc-mark--' + esc(s.tier || 'none') + '" aria-hidden="true"></span>' +
          '<span>' + esc(s.label) + '</span></p>' +
          '<p class="uc__focus-meta">' + esc(leanSentence(s)) + '</p>' +
          (decl ? '<p class="uc__decl"><code title="' + esc(decl.name) + '">' +
            esc(shortName).replace(/([._])(?=[^._])/g, '$1<wbr>') + '</code>' +
            (s.declCount > 1 ? esc(' and ' + count(s.declCount - 1, 'more declaration', 'more declarations')) : '') + '</p>' : '') +
          (note ? '<p class="uc__note">' + note + '</p>' : '') +
          linksHtml(s, 'Read it in the paper');
      }
      if (s.kind === 'public_claim') {
        var tier = CLAIM_TIER[s.status] || 'proved';
        return '<p class="uc__label">Checked claim</p>' +
          '<p class="uc__focus-title"><span class="uc-mark uc-mark--' + tier + '" aria-hidden="true"></span>' +
          '<span>' + esc(s.label) + '</span></p>' +
          (s.status ? '<p class="uc__focus-meta">' + esc(capital(s.status)) + '.</p>' : '') +
          (s.statement ? '<p class="uc__note">' + esc(s.statement) + '</p>' : '') +
          linksHtml(s, 'Read it');
      }
      if (s.kind === 'paper') {
        return '<p class="uc__label">Paper</p><p class="uc__focus-title"><span>' + esc(s.label) + '</span></p>' +
          linksHtml(s, 'Read the paper');
      }
      return '<p class="uc__hint">Point at a dot on the map to read that result here.</p>';
    }

    function fillProblem(pid) {
      var problem = data.problems[pid];
      el.problem.innerHTML =
        '<p class="uc__kicker">Erdős problem #' + esc(problem.number) + '</p>' +
        '<p class="uc__title" role="heading" aria-level="3"><a href="' + esc(hrefOf[pid]) + '">' +
          (titleHtml[pid] || esc(problem.title)) + '</a></p>' +
        '<p class="uc__question">' + problem.question_html + '</p>' +
        '<p class="uc__tally">' + tallyHtml(problem, api.tallies[pid]) + '</p>' +
        '<div class="uc__paper">' + paperHtml(problem) + '</div>';
      el.kicker = el.problem.querySelector('.uc__kicker');
      el.title = el.problem.querySelector('.uc__title');
      el.question = el.problem.querySelector('.uc__question');
      el.tally = el.problem.querySelector('.uc__tally');
      el.paper = el.problem.querySelector('.uc__paper');
      // A new problem block can be taller or shorter than the last, so the
      // card slot under it is a new slot too: a node that appears is not a
      // node that moved, and the page records no shift.
      var slot = el.focus.cloneNode(false);
      el.focus.parentNode.replaceChild(slot, el.focus);
      el.focus = slot;
      state.focusKey = undefined;
      Array.prototype.forEach.call(el.sw.querySelectorAll('.uc__chip'), function (chip) {
        var on = chip.getAttribute('data-problem') === pid;
        if (on) chip.setAttribute('aria-current', 'true'); else chip.removeAttribute('aria-current');
        chip.classList.toggle('is-focus-proxy', on && state.keyboard);
      });
    }

    function setFocus(s, quiet) {
      var key = s ? s.id : null;
      if (key === state.focusKey) return;
      state.focusKey = key;
      state.focus = s;
      el.focus.innerHTML = focusHtml(s);
      if (s && s.kind === 'paper_statement') needDetail();
      if (motion && !quiet) {
        el.focus.animate([{ opacity: 0.2, transform: 'translateY(3px)' }, { opacity: 1, transform: 'none' }],
          { duration: 180, easing: EASE });
      }
    }

    /* ---- Motion -------------------------------------------------------- */

    // A target set in its final place starts where the source stands, at the
    // source's size, and travels home: the row's number and title become the
    // head of the column.
    function travel(target, source, back) {
      if (!motion || !source) return null;
      var a = source.getBoundingClientRect();
      var b = target.getBoundingClientRect();
      if (!a.width || !b.width) return null;
      var scale = parseFloat(getComputedStyle(source).fontSize) / parseFloat(getComputedStyle(target).fontSize) || 1;
      var away = { transform: 'translate(' + (a.left - b.left) + 'px,' + (a.top - b.top) + 'px) scale(' + scale + ')', opacity: 0.3 };
      var home = { transform: 'none', opacity: 1 };
      return target.animate(back ? [home, away] : [away, home],
        { duration: back ? 340 : 560, easing: back ? 'cubic-bezier(0.4, 0, 0.7, 0.2)' : EASE });
    }

    function rise(nodes, delay) {
      if (!motion) return;
      nodes.forEach(function (node, at) {
        node.animate([{ opacity: 0, transform: 'translateY(12px)' }, { opacity: 1, transform: 'none' }],
          { duration: 420, delay: delay + at * 55, easing: EASE, fill: 'backwards' });
      });
    }

    function open(pid) {
      state.open = true;
      root.inert = false;
      root.removeAttribute('aria-hidden');
      root.classList.add('is-open');
      host.classList.add('uc-host--open');
      var row = rows[pid];
      travel(el.kicker, row.querySelector('.home-problem__num'));
      travel(el.title, row.querySelector('.home-problem__title'));
      rise([el.sw], 60);
      rise([el.question, el.tally, el.paper, el.focus], 140);
    }

    function close() {
      if (!state.open) return;
      var pid = state.problem;
      state.open = false;
      state.problem = null;
      state.focusKey = undefined;
      state.focus = null;
      clearTimeout(timers.linger);
      api.light(null);
      host.classList.remove('uc-host--open');
      root.classList.remove('is-open');
      root.setAttribute('aria-hidden', 'true');
      root.inert = true;
      var row = rows[pid];
      if (row) {
        travel(el.title, row.querySelector('.home-problem__title'), true);
        travel(el.kicker, row.querySelector('.home-problem__num'), true);
      }
    }

    // Another problem while the column is already turned: the head and the
    // body are set again and rise a little, without the long travel.
    function swap(pid) {
      fillProblem(pid);
      rise([el.kicker, el.title], 0);
      rise([el.question, el.tally, el.paper], 60);
    }

    /* ---- When ---------------------------------------------------------- */

    function sideBySide() {
      if (!figure) return false;
      var a = host.getBoundingClientRect();
      var b = figure.getBoundingClientRect();
      return a.width > 0 && a.right <= b.left + 2;
    }

    function show(pid, s) {
      if (!data || !data.problems || !data.problems[pid] || !rows[pid] || !sideBySide()) return;
      clearTimeout(timers.leave);
      if (!state.open) {
        state.problem = pid;
        fillProblem(pid);
        setFocus(s || null, true);
        open(pid);
        return;
      }
      if (state.problem !== pid) {
        state.problem = pid;
        swap(pid);
        state.focusKey = undefined;
      }
      setFocus(s || null);
    }

    function later(name, fn, ms) {
      clearTimeout(timers[name]);
      timers[name] = window.setTimeout(fn, ms);
    }

    // The rows: a held pointer, or a link in focus, turns the column.
    order.forEach(function (pid) {
      var li = rows[pid];
      li.addEventListener('pointerenter', function () {
        later('dwell', function () {
          state.keyboard = false;
          show(pid, null);
          api.light(pid);
        }, state.open ? 0 : DWELL);
      });
      li.addEventListener('pointerleave', function () { clearTimeout(timers.dwell); });
    });
    host.addEventListener('focusin', function (event) {
      var li = event.target.closest ? event.target.closest('li.home-problem[data-problem-id]') : null;
      if (!li) return;
      var pid = li.getAttribute('data-problem-id');
      state.keyboard = true;
      show(pid, null);
      if (state.open) fillProblem(pid);
      api.light(pid);
    });
    host.addEventListener('focusout', function (event) {
      if (event.relatedTarget && host.contains(event.relatedTarget)) return;
      state.keyboard = false;
      if (!section.matches(':hover')) close();
    });

    // The chips: the column moves between problems without the list.
    el.sw.addEventListener('pointerover', function (event) {
      var chip = event.target.closest ? event.target.closest('.uc__chip') : null;
      if (!chip) return;
      var pid = chip.getAttribute('data-problem');
      show(pid, null);
      api.light(pid);
    });

    // The drawing: every dot of a problem's sector turns the column to it,
    // and its card follows the pointer from dot to dot.
    api.stage.addEventListener('universe:hover', function (event) {
      var s = event.detail;
      if (!s) {
        if (state.open && !state.overPanel) later('linger', function () { setFocus(null); }, LINGER);
        return;
      }
      clearTimeout(timers.linger);
      if (!s.sector || !rows[s.sector]) return;
      if (state.open) {
        show(s.sector, s);
      } else {
        later('dwell', function () { show(s.sector, s); }, DWELL);
      }
    });

    root.addEventListener('pointerenter', function () {
      state.overPanel = true;
      clearTimeout(timers.linger);
    });
    root.addEventListener('pointerleave', function () { state.overPanel = false; });

    // The band as a whole: leaving it sets the list back.
    section.addEventListener('pointerleave', function () {
      clearTimeout(timers.dwell);
      if (state.keyboard) return;
      later('leave', close, LEAVE);
    });
    section.addEventListener('pointerenter', function () { clearTimeout(timers.leave); });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && state.open) close();
    });
    // A layout that stacks the list over the drawing has no companion: the
    // rows keep their definitions and an open companion closes.
    function syncLayout() {
      var beside = sideBySide();
      restRowMarks(beside);
      if (!beside && state.open) close();
    }
    window.addEventListener('resize', syncLayout);
    syncLayout();
  }

  window.PlectisUniverseCompanion = { attach: attach };
})();
