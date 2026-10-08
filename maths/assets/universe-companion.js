/* Plectis — the universe companion.
   On the landing the eight problems sit beside a small drawing of the
   universe map. This turns that column into a reading companion for the
   drawing. Point at a problem's row, or at any dot in its sector, and the
   problem rises to the head of the column: its number and title travel up
   from the row into the place of the band's heading, and under them come
   the question, the tally of its results, its short paper and, for a dot
   under the pointer, that result in its paper's own words (the excerpt the
   map quotes) with how far it has been checked: how Lean states it and
   whether Comparator has replayed it. The map lights the problem's sector
   while the column reads it. Taking the pointer off the column and the
   drawing, or resting it on empty ground in the drawing, sets the list
   back, so the next row can be read.

   It is a pointer enhancement over an ordinary list of links. universe.js
   loads it only on a fine pointer and only where the list stands beside the
   drawing; a row's link in focus opens it too, Escape closes it, and with
   reduced motion it changes without travelling. Nothing in the column moves
   in layout: the companion lies over the column, and only opacity and
   transform animate. */
(function () {
  'use strict';

  var DWELL = 140;      // a row must hold the pointer this long before the column turns
  var LEAVE = 260;      // after the pointer leaves the column and the drawing, before the list returns
  var LINGER = 900;     // after the pointer leaves a dot for empty ground, before the list returns
  // The list and the panel never show at once. Opening, the list steps out
  // in OUT and only then does the problem's title travel up from its row;
  // closing, the panel fades out in AWAY and only then does the list come
  // back (universe-companion.css holds both beats; the drawing lets its
  // dimming go on AWAY too). Arrivals ease out hard.
  var OUT = 90, AWAY = 160;
  var EASE = 'cubic-bezier(0.16, 1, 0.3, 1)';

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
    // focusKey starts unset, so the first card (even "nothing in focus") is drawn.
    var state = { open: false, problem: null, focusKey: undefined, focus: null, overPanel: false, keyboard: false,
                  card: { shape: null, tier: null, lines: {} }, pinned: null };
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
      // The drawing names a result on its plate by the paper's number alone
      // where this column reads it whole; from now on it can.
      if (typeof api.redraw === 'function') api.redraw();
      restoreRequestedProblem();
    }).catch(function () { host.dispatchEvent(new CustomEvent('plectis:companion-failed')); });

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
        if (t.lean) rest.push(t.lean + ' exact in Lean with no replay recorded');
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
      // The précis folds away while a result is in the card (the fold
      // gives the result's own words the room).
      return '<p class="uc__label">' + esc(short.label === 'Short paper' ? 'The short paper' : short.label) + '</p>' +
        title +
        (short.precis_html ? '<div class="uc__fold"><p class="uc__precis">' + short.precis_html + '</p></div>' : '') +
        (links.length ? '<p class="uc__links">' + links.join('') + '</p>' : '');
    }

    function leanSentence(s) {
      var how = s.lean_status === 'exact_or_stronger' ? 'Lean states it or something stronger' : 'Lean states it exactly';
      if (s.tier === 'replayed') return how + ', and Comparator has replayed it.';
      if (s.tier === 'lean') {
        return how + (s.comparator_status === 'pending' && s.comparator_queued_at
          ? '; its Comparator replay is queued since ' + s.comparator_queued_at + '.'
          : '; no Comparator replay is recorded for this paper result.');
      }
      if (s.tier === 'modulo') return 'Lean states it under named inputs.';
      return 'No Lean statement is recorded for it yet.';
    }

    // The card's ways out, as buttons: its place in the paper first, then its
    // Lean source on GitHub (in a new tab) and the full map.
    function linksInner(s, readLabel) {
      var links = [];
      if (s.href) links.push('<a class="uc__go uc__go--first" href="' + esc(s.href) + '">' + esc(readLabel) + '</a>');
      // A result's other places, each named for what it opens: the paper's
      // PDF, its TeX source at the line, the Lean on GitHub, the full map.
      var pdf = s.kind === 'paper_statement' ? paperPdf(s) : null;
      if (pdf) links.push('<a class="uc__go" href="' + esc(pdf) + '">PDF</a>');
      if (s.tex) links.push(outLink(s.tex, 'TeX source'));
      if (s.github) links.push(outLink(s.github, 'Lean on GitHub'));
      if (s.mapHref) links.push('<a class="uc__go" href="' + esc(s.mapHref) + '">In the map</a>');
      return links.join('');
    }
    function outLink(href, text) {
      return '<a class="uc__go" href="' + esc(href) + '" data-link-kind="exogenous" rel="external noopener" target="_blank">' +
        esc(text) + '</a>';
    }
    function paperPdf(s) {
      var problem = data && data.problems && s.sector ? data.problems[s.sector] : null;
      var paper = problem ? (problem.papers || []).filter(function (row) { return row.id === s.paperId; })[0] : null;
      return paper && paper.pdf ? api.route(paper.pdf) : null;
    }

    /* ---- The card ------------------------------------------------------ */
    /* A card is a fixed set of lines for its kind. As the pointer moves
       along a band the problem above holds still and so does every line
       that reads the same ("In the long record", the Lean sentence, the
       links); only a line whose words changed is set again, and it settles
       in a tenth of a second. The mark ripples only when the evidence it
       shows is new. A card of another kind is drawn whole. */
    // A kept (pinned) card says so in its head, in plain words: the reader
    // chose it, and Esc is how it is let go. The words show only while the
    // card is kept (.uc.is-pinned).
    var KEPT = '<span class="uc__kept">Kept. Esc lets it go</span>';
    var CARD_SHAPES = {
      // A result: its name, its own words from the paper, how far it is
      // checked, the ways out. A claim keeps its statement as the note.
      result: '<p class="uc__label uc__head"><span data-line="label"></span>' + KEPT + '</p>' +
        '<p class="uc__focus-title"><span class="uc-mark" aria-hidden="true"><span class="uc-mark__ring"></span></span>' +
        '<span data-line="name"></span></p>' +
        '<div class="uc__quote" data-line="quote"></div>' +
        '<p class="uc__focus-meta" data-line="meta"></p><p class="uc__links" data-line="links"></p>' +
        '<p class="uc__note" data-line="note"></p>',
      paper: '<p class="uc__label uc__head"><span data-line="label"></span>' + KEPT + '</p>' +
        '<p class="uc__focus-title"><span data-line="name"></span></p>' +
        '<p class="uc__links" data-line="links"></p>',
      hint: '<p class="uc__hint" data-line="hint"></p>'
    };

    function problemNumber(s) {
      var problem = data && data.problems && s.sector ? data.problems[s.sector] : null;
      return problem ? problem.number : null;
    }

    function cardOf(s) {
      if (s && s.kind === 'paper_statement') {
        // The paper's own words, from the map's excerpt file (typeset as
        // MathML at build time); the Lean code stays on the map's card.
        return { shape: 'result', tier: s.tier || 'none', lines: {
          // Which problem and which paper, so the card reads on its own.
          label: esc((s.side === 'long' ? 'In the long record' : 'In the short paper') +
            (problemNumber(s) ? ' on Erdős #' + problemNumber(s) : '')),
          name: esc(s.label),
          quote: s.quote || '',
          meta: esc(leanSentence(s)),
          note: '',
          links: linksInner(s, 'Read it on this site') } };
      }
      if (s && s.kind === 'public_claim') {
        return { shape: 'result', tier: CLAIM_TIER[s.status] || 'proved', lines: {
          // The map sets a claim's ASCII notation (indices, ≤, ∑) as it does on its own cards.
          label: 'Claim', name: api.notation ? api.notation(s.label) : esc(s.label), quote: '',
          meta: s.status ? esc(capital(s.status)) + '.' : '',
          note: s.statement ? (api.notation ? api.notation(s.statement) : esc(s.statement)) : '',
          links: linksInner(s, 'Read it') } };
      }
      if (s && s.kind === 'paper') {
        return { shape: 'paper', tier: null, lines: { label: 'Paper', name: esc(s.label),
          links: linksInner(s, 'Read the paper') } };
      }
      return { shape: 'hint', tier: null,
               lines: { hint: 'Point at a dot on the map to read that result here; click it to keep it.' } };
    }


    function drawCard(card, quiet) {
      var whole = card.shape !== state.card.shape;
      if (whole) {
        el.focus.innerHTML = CARD_SHAPES[card.shape];
        state.card = { shape: card.shape, tier: null, lines: {} };
      }
      // A result takes the room its words need: the question and the
      // précis fold away while it is in the card.
      root.classList.toggle('has-result', card.shape === 'result');
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
      // A quote shows whole, however long: where it needs more room than
      // the column has, the column scrolls inside its own box (5 October
      // 2026; the cut at the last line that fitted stopped a statement
      // mid-thought above empty space).
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
        '<div class="uc__fold"><p class="uc__question">' + problem.question_html + '</p></div>' +
        '<p class="uc__tally">' + tallyHtml(problem, api.tallies[pid]) + '</p>' +
        '<div class="uc__paper">' + paperHtml(problem) + '</div>';
      el.kicker = el.problem.querySelector('.uc__kicker');
      el.title = el.problem.querySelector('.uc__title');
      el.question = el.problem.querySelector('.uc__fold');
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
      // The same result sent again with its words is a new card to draw;
      // only the quote line, which changed, moves.
      var key = s ? s.id + (s.quote ? '+quote' : '') : null;
      if (key === state.focusKey) return;
      state.focusKey = key;
      state.focus = s;
      if (s && s.id) root.setAttribute('data-uc-selection', s.id);
      else root.removeAttribute('data-uc-selection');
      drawCard(cardOf(s), quiet);
    }

    /* ---- Motion -------------------------------------------------------- */

    // A target set in its final place starts where the source stands, at the
    // source's size, and travels home: the row's number and title become the
    // head of the column.
    function travel(target, source) {
      if (!motion || !source) return null;
      var a = source.getBoundingClientRect();
      var b = target.getBoundingClientRect();
      if (!a.width || !b.width) return null;
      var scale = parseFloat(getComputedStyle(source).fontSize) / parseFloat(getComputedStyle(target).fontSize) || 1;
      var away = { transform: 'translate(' + (a.left - b.left) + 'px,' + (a.top - b.top) + 'px) scale(' + scale + ')', opacity: 0.3 };
      var home = { transform: 'none', opacity: 1 };
      // A third of a second home, leaving only once the list has stepped
      // out (OUT): at 338ms the title used to cross the intro still on its
      // way out.
      return target.animate([away, home], { duration: 320, delay: OUT, easing: EASE, fill: 'backwards' });
    }

    // The slots arrive behind the title, a little apart (40ms), each in a
    // fifth of a second.
    function rise(nodes, delay) {
      if (!motion) return;
      nodes.forEach(function (node, at) {
        node.animate([{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'none' }],
          { duration: 220, delay: delay + at * 40, easing: EASE, fill: 'backwards' });
      });
    }

    function open(pid) {
      state.open = true;
      root.inert = false;
      root.removeAttribute('aria-hidden');
      root.classList.add('is-open');
      host.classList.add('uc-host--open');
      // While the column reads the object, the drawing's own one-line
      // caption would only repeat it.
      api.stage.classList.add('uc-reading');
      var row = rows[pid];
      travel(el.kicker, row.querySelector('.home-problem__num'));
      travel(el.title, row.querySelector('.home-problem__title'));
      // The tabs and the slots rise once the title, which leaves at OUT
      // (90ms) and eases out hard, is nearly home, so it never passes over
      // them: 150ms and 210ms after it leaves.
      rise([el.sw], 240);
      rise([el.question, el.tally, el.paper, el.focus], 300);
    }

    // A pin is let go with the column, or for another problem.
    function unpin() {
      if (!state.pinned) return;
      state.pinned = null;
      root.classList.remove('is-pinned');
      if (api.release) api.release();
    }

    function close() {
      if (!state.open) return;
      unpin();
      state.open = false;
      state.problem = null;
      state.focusKey = undefined;
      state.focus = null;
      root.removeAttribute('data-uc-selection');
      clearTimeout(timers.linger);
      api.light(null);
      host.classList.remove('uc-host--open');
      api.stage.classList.remove('uc-reading');
      root.classList.remove('is-open');
      root.setAttribute('aria-hidden', 'true');
      root.inert = true;
      // The panel fades through in place (AWAY) and the list follows it.
      // The title used to travel back down to its row as it went, and
      // crossed the problem's own question on the way.
    }

    // Another problem while the column is already turned: the new problem
    // crossfades in place. Replaying the opening stagger blanked the column
    // for a beat on every chip; the stagger belongs to the first open only.
    function swap(pid) {
      fillProblem(pid);
      if (!motion) return;
      el.problem.animate([{ opacity: 0.35 }, { opacity: 1 }], { duration: 160, easing: EASE });
    }

    /* ---- When ---------------------------------------------------------- */

    function sideBySide() {
      if (!figure) return false;
      var a = host.getBoundingClientRect();
      var b = figure.getBoundingClientRect();
      return a.width > 0 && a.right <= b.left + 2;
    }

    // The map consumes a click only where this optional panel can be shown.
    // Share the same live layout predicate used by show and syncLayout.
    api.sideBySide = sideBySide;
    // Whether this column reads an object of a problem's sector in full
    // (its title, its words), so the drawing need not repeat them.
    api.reads = function (sector) {
      return !!(data && data.problems && sector && data.problems[sector] && rows[sector] && sideBySide());
    };

    function rowHasFocus() {
      var active = document.activeElement;
      return !!(active && active.closest && active.closest('li.home-problem[data-problem-id]') && host.contains(active));
    }

    function show(pid, s) {
      // A delayed pointer dwell must never cover the native link in focus.
      if (rowHasFocus()) return;
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

    // Only the docs return owner may publish this DOM-local request. Recheck
    // fresh input/focus/exact URL immediately before changing the live panel.
    function restoreRequestedProblem() {
      var request = host.mcLandingProblemRestore;
      if (!request || request.applied || typeof request.allowed !== 'function' ||
          !request.allowed() || !data || !data.problems || !rows[request.problem] ||
          !data.problems[request.problem] || !sideBySide() || state.open) return;
      var previousKeyboard = state.keyboard;
      state.keyboard = true;
      if (request.selection) {
        // Resolve the saved identity through the current map, which owns both
        // the pin and the excerpt. Never replay saved HTML or a stale quote.
        if (typeof api.restoreSelection !== 'function' ||
            !api.restoreSelection(request.selection, request.problem)) {
          state.keyboard = previousKeyboard;
          return;
        }
      } else show(request.problem, null);
      if (!state.open || state.problem !== request.problem) return;
      request.applied = true;
      api.light(request.problem);
      host.dispatchEvent(new CustomEvent('plectis:companion-ready'));
    }
    host.addEventListener('plectis:companion-restore', restoreRequestedProblem);

    function later(name, fn, ms) {
      clearTimeout(timers[name]);
      timers[name] = window.setTimeout(fn, ms);
    }

    // The rows: a held pointer, or a link in focus, turns the column.
    order.forEach(function (pid) {
      var li = rows[pid];
      li.addEventListener('pointerenter', function () {
        // After Escape the row under a resting pointer does not turn the
        // column straight back; the next row the pointer enters does.
        if (state.hushed) return;
        later('dwell', function () {
          state.keyboard = false;
          show(pid, null);
          api.light(pid);
        }, state.open ? 0 : DWELL);
      });
      li.addEventListener('pointerleave', function () {
        clearTimeout(timers.dwell);
        state.hushed = false;
      });
    });
    host.addEventListener('focusin', function (event) {
      var li = event.target.closest ? event.target.closest('li.home-problem[data-problem-id]') : null;
      if (!li) return;
      var pid = li.getAttribute('data-problem-id');
      clearTimeout(timers.dwell);
      clearTimeout(timers.leave);
      close();
      state.keyboard = true;
      api.light(pid);
    });
    host.addEventListener('focusout', function (event) {
      if (event.relatedTarget && host.contains(event.relatedTarget)) return;
      state.keyboard = false;
      if (!host.matches(':hover') && !figure.matches(':hover')) close();
    });

    // The chips: the column moves between problems without the list.
    el.sw.addEventListener('pointerover', function (event) {
      var chip = event.target.closest ? event.target.closest('.uc__chip') : null;
      if (!chip) return;
      var pid = chip.getAttribute('data-problem');
      if (state.pinned && pid === state.problem) return;
      unpin();
      show(pid, null);
      api.light(pid);
    });

    // A click on the drawing pins a result: the card holds it while the
    // pointer travels to its buttons, and other dots light only the map.
    api.stage.addEventListener('universe:select', function (event) {
      var s = event.detail;
      clearTimeout(timers.dwell);
      clearTimeout(timers.linger);
      state.pinned = s && s.sector && rows[s.sector] ? s : null;
      root.classList.toggle('is-pinned', !!state.pinned);
      if (state.pinned) show(s.sector, s);
      else if (state.open && !state.overPanel) setFocus(null);
    });

    // The drawing: every dot of a problem's sector turns the column to it,
    // and its card follows the pointer from dot to dot.
    api.stage.addEventListener('universe:hover', function (event) {
      var s = event.detail;
      if (state.pinned) return;
      if (!s) {
        // Resting on empty ground lets the problem go, as leaving its row does.
        if (state.open && !state.overPanel && !state.keyboard) later('linger', close, LINGER);
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

    // The column and the drawing read together; taking the pointer off both
    // (to the margin, the gap between them, the next band) sets the list
    // back. Crossing the gap from one to the other is quicker than LEAVE.
    // A pinned result stays put when the pointer wanders off: the reader
    // chose it, and only a choice lets it go (Escape, empty ground, its dot
    // again, another problem's chip, or a click elsewhere on the page).
    function pointerOff() {
      clearTimeout(timers.dwell);
      state.hushed = false;
      if (state.keyboard || state.pinned) return;
      later('leave', close, LEAVE);
    }
    document.addEventListener('pointerdown', function (event) {
      if (!state.pinned || !event.target || !event.target.closest) return;
      if (host.contains(event.target) || figure.contains(event.target)) return;
      close();
    });
    function pointerOn() { clearTimeout(timers.leave); }
    [host, figure].forEach(function (area) {
      area.addEventListener('pointerleave', pointerOff);
      area.addEventListener('pointerenter', pointerOn);
    });
    // Arriving on the drawing away from any dot counts as resting on empty
    // ground; the first dot under the pointer keeps the column.
    figure.addEventListener('pointerenter', function () {
      if (state.open && !state.pinned && !state.keyboard) later('linger', close, LINGER);
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && state.open) {
        state.hushed = true;
        clearTimeout(timers.dwell);
        close();
      }
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
    restoreRequestedProblem();
  }

  window.PlectisUniverseCompanion = { attach: attach };
})();
