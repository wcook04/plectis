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
    var state = { open: false, problem: null, focusKey: undefined, focus: null, overPanel: false, keyboard: false,
                  card: { shape: null, tier: null, lines: {} } };
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
        if (state.focus && state.focus.kind === 'paper_statement') drawCard(cardOf(state.focus), true);
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

    function linksInner(s, readLabel) {
      var links = [];
      if (s.href) links.push('<a href="' + esc(s.href) + '">' + esc(readLabel) + '</a>');
      if (s.mapHref) links.push('<a href="' + esc(s.mapHref) + '">Open it in the map</a>');
      return links.join('');
    }

    /* ---- The card ------------------------------------------------------ */
    /* A card is a fixed set of lines for its kind. As the pointer moves
       along a band the problem above holds still and so does every line
       that reads the same ("In the long record", the Lean sentence, the
       links); only a line whose words changed is set again, and it settles
       in a tenth of a second. The mark ripples only when the evidence it
       shows is new. A card of another kind is drawn whole. */
    var CARD_SHAPES = {
      result: '<p class="uc__label" data-line="label"></p>' +
        '<p class="uc__focus-title"><span class="uc-mark" aria-hidden="true"><span class="uc-mark__ring"></span></span>' +
        '<span data-line="name"></span></p>' +
        '<p class="uc__focus-meta" data-line="meta"></p><p class="uc__decl" data-line="decl"></p>' +
        '<p class="uc__note" data-line="note"></p><p class="uc__links" data-line="links"></p>',
      paper: '<p class="uc__label" data-line="label"></p><p class="uc__focus-title"><span data-line="name"></span></p>' +
        '<p class="uc__links" data-line="links"></p>',
      hint: '<p class="uc__hint" data-line="hint"></p>'
    };

    function cardOf(s) {
      if (s && s.kind === 'paper_statement') {
        var d = detail && detail.statements ? detail.statements[s.id] : null;
        var decl = s.decls && s.decls[0];
        // A declaration's last two segments name it; the full name is its title.
        var parts = decl ? String(decl.name).split('.') : [];
        var shortName = parts.length > 2 ? '…' + parts.slice(-2).join('.') : (decl ? decl.name : '');
        return { shape: 'result', tier: s.tier || 'none', lines: {
          label: s.side === 'long' ? 'In the long record' : 'In the short paper',
          name: esc(s.label),
          meta: esc(leanSentence(s)),
          decl: decl ? '<code title="' + esc(decl.name) + '">' +
            esc(shortName).replace(/([._])(?=[^._])/g, '$1<wbr>') + '</code>' +
            (s.declCount > 1 ? esc(' and ' + count(s.declCount - 1, 'more declaration', 'more declarations')) : '') : '',
          note: (d && d.html_mathml && d.html_mathml.relation_note) || s.leanReasonHtml || '',
          links: linksInner(s, 'Read it in the paper') } };
      }
      if (s && s.kind === 'public_claim') {
        return { shape: 'result', tier: CLAIM_TIER[s.status] || 'proved', lines: {
          label: 'Checked claim', name: esc(s.label),
          meta: s.status ? esc(capital(s.status)) + '.' : '', decl: '',
          note: s.statement ? esc(s.statement) : '',
          links: linksInner(s, 'Read it') } };
      }
      if (s && s.kind === 'paper') {
        return { shape: 'paper', tier: null, lines: { label: 'Paper', name: esc(s.label),
          links: linksInner(s, 'Read the paper') } };
      }
      return { shape: 'hint', tier: null, lines: { hint: 'Point at a dot on the map to read that result here.' } };
    }

    function drawCard(card, quiet) {
      var whole = card.shape !== state.card.shape;
      if (whole) {
        el.focus.innerHTML = CARD_SHAPES[card.shape];
        state.card = { shape: card.shape, tier: null, lines: {} };
      }
      var moved = [];
      Object.keys(card.lines).forEach(function (name) {
        var html = card.lines[name];
        var was = state.card.lines[name];
        if (was === html) return;
        state.card.lines[name] = html;
        var node = el.focus.querySelector('[data-line="' + name + '"]');
        if (!node) return;
        node.innerHTML = html;
        // An empty line takes no room; the name always has one.
        if (name !== 'name') node.hidden = !html;
        // What the reader sees decides the motion: the links keep their
        // words from one result to the next while their addresses change,
        // and a line whose words are the same holds still.
        var words = function (text) { return String(text || '').replace(/<[^>]*>/g, ''); };
        if (html && words(html) !== words(was)) moved.push(node);
      });
      var mark = el.focus.querySelector('.uc-mark');
      var newEvidence = !!mark && card.tier !== state.card.tier;
      if (newEvidence) {
        mark.className = 'uc-mark uc-mark--' + card.tier;
        state.card.tier = card.tier;
      }
      if (!motion) return;
      if (whole) {
        if (!quiet) {
          el.focus.animate([{ opacity: 0.2, transform: 'translateY(3px)' }, { opacity: 1, transform: 'none' }],
            { duration: 140, easing: EASE });
        }
      } else {
        moved.forEach(function (node) {
          node.animate([{ opacity: 0.3 }, { opacity: 1 }], { duration: 100, easing: EASE });
        });
      }
      // The mark answers the map's ripple on the same beat (the map waits a
      // tenth of a second before its own).
      if (newEvidence) {
        mark.firstChild.animate([{ transform: 'scale(1)', opacity: 0 },
                                 { transform: 'scale(1.3)', opacity: 0.8, offset: 0.12 },
                                 { transform: 'scale(3.6)', opacity: 0 }],
          { duration: 720, delay: 110, easing: 'cubic-bezier(0.22, 0.61, 0.36, 1)', fill: 'backwards' });
      }
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
      state.card = { shape: null, tier: null, lines: {} };
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
      if (s && s.kind === 'paper_statement') needDetail();
      drawCard(cardOf(s), quiet);
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
