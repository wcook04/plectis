/* The map explorers' shared frame (maths/universe.html, docs/system-map.html).

   Both maps open as one full-window explorer: the site header, one reading
   panel on the left, and the drawing in the rest of the window. Each map's
   own engine (maths/assets/universe.js, assets/system-map.js) draws, fits and
   selects; this file only wires the frame they share:

   - [data-explorer-fullscreen] asks the browser for full screen on the
     explorer and keeps the button's label and aria-pressed true to the
     browser's actual state. Where native full screen is unavailable, the
     same button expands the explorer within the window and Escape exits.
   - [data-explorer-fit] and [data-explorer-zoom="in"|"out"] dispatch
     "explorer:fit" and "explorer:zoom" (detail.direction = 1 | -1) on the
     [data-explorer] element, which the engine handles.
   - [data-explorer-view="map"|"details"] switches the narrow layout between
     the drawing and the panel; the explorer carries the choice as
     data-explorer-shown so CSS decides what shows.
   - The explorer's stage size is published to CSS as --explorer-stage-h, and
     "explorer:resize" fires (once per frame) when the stage changes size, so
     an engine can refit without its own observer. */
(function () {
  "use strict";
  var root = document.querySelector("[data-explorer]");
  if (!root) return;

  function fire(name, detail) {
    root.dispatchEvent(new CustomEvent(name, { bubbles: true, detail: detail || {} }));
  }

  // Full screen ------------------------------------------------------------
  var fsButtons = Array.prototype.slice.call(root.querySelectorAll("[data-explorer-fullscreen]"));
  var fsEnabled = !!(document.fullscreenEnabled || document.webkitFullscreenEnabled);
  var windowMode = false;
  // Keep the drawing in its existing ancestor/compositing tree. Promoting
  // only the nested SVG/canvas frame can produce a black native surface.
  var fullscreenHost = document.documentElement;
  function fsElement() { return document.fullscreenElement || document.webkitFullscreenElement || null; }
  function syncFs() {
    var on = windowMode || fsElement() === fullscreenHost || fsElement() === root;
    document.documentElement.classList.toggle("is-map-fullscreen", on);
    root.classList.toggle("is-fullscreen", on);
    fsButtons.forEach(function (b) {
      b.setAttribute("aria-pressed", on ? "true" : "false");
      var label = b.querySelector("[data-explorer-fullscreen-label]");
      var text = on ? "Exit full screen" : "Full screen";
      if (label) label.textContent = text; else b.setAttribute("aria-label", text);
      b.title = on ? "Exit full screen (Esc)" : "Full screen";
    });
    requestAnimationFrame(function () { fire("explorer:resize"); });
  }
  fsButtons.forEach(function (b) {
    b.hidden = false;
    b.addEventListener("click", function () {
      if (windowMode) { windowMode = false; syncFs(); return; }
      if (fsElement()) {
        var exit = document.exitFullscreen || document.webkitExitFullscreen;
        try {
          var done = exit.call(document);
          if (done && done.catch) done.catch(syncFs);
        } catch (err) { syncFs(); }
        return;
      }
      function expandWindow() { windowMode = true; syncFs(); }
      var req = fullscreenHost.requestFullscreen || fullscreenHost.webkitRequestFullscreen;
      if (!fsEnabled || !req) { expandWindow(); return; }
      try {
        var p = req.call(fullscreenHost);
        if (p && typeof p.catch === "function") p.catch(expandWindow);
      } catch (err) { expandWindow(); }
    });
  });
  document.addEventListener("fullscreenchange", syncFs);
  document.addEventListener("webkitfullscreenchange", syncFs);
  syncFs();
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && windowMode) {
      windowMode = false;
      syncFs();
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);

  // Fit and zoom -------------------------------------------------------------
  root.addEventListener("click", function (ev) {
    var t = ev.target instanceof Element ? ev.target : null;
    if (!t) return;
    var fit = t.closest("[data-explorer-fit]");
    if (fit && root.contains(fit)) { ev.preventDefault(); fire("explorer:fit"); return; }
    var zoom = t.closest("[data-explorer-zoom]");
    if (zoom && root.contains(zoom)) {
      ev.preventDefault();
      fire("explorer:zoom", { direction: zoom.getAttribute("data-explorer-zoom") === "out" ? -1 : 1 });
      return;
    }
    var view = t.closest("[data-explorer-view]");
    if (view && root.contains(view)) {
      ev.preventDefault();
      showView(view.getAttribute("data-explorer-view"));
    }
  });

  // Narrow layout: map or details --------------------------------------------
  var viewButtons = Array.prototype.slice.call(root.querySelectorAll("[data-explorer-view]"));
  function showView(which) {
    if (which !== "map" && which !== "details") return;
    root.setAttribute("data-explorer-shown", which);
    viewButtons.forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-explorer-view") === which ? "true" : "false");
    });
    if (which === "map") fire("explorer:resize");
  }
  // A selection made on the map, on a phone, brings its reading forward; the
  // engines fire this when the reader chooses something.
  root.addEventListener("explorer:selected", function () {
    if (window.matchMedia("(max-width: 899px)").matches) showView("details");
  });
  // An exact result URL already chooses its reading. Show the panel before
  // deferred graph data arrives, so return focus and new input can resolve.
  var exactResult = root.getAttribute("data-explorer") === "universe" && /^#o=.+/.test(location.hash);
  showView(root.getAttribute("data-explorer-shown") || (exactResult ? "details" : "map"));

  // Stage size ----------------------------------------------------------------
  var stage = root.querySelector(".explorer__stage");
  if (stage && "ResizeObserver" in window) {
    var queued = false;
    new ResizeObserver(function () {
      root.style.setProperty("--explorer-stage-h", stage.clientHeight + "px");
      if (queued) return;
      queued = true;
      requestAnimationFrame(function () { queued = false; fire("explorer:resize"); });
    }).observe(stage);
  }
})();
