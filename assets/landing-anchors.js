/* The site root sends every reader on (Will, 29 October 2026).

   The root address opens Will's home page, which lists every website and
   film. The maths front door (the plait and its five routes, the eight
   programmes with their map, the papers) is at map/. Old links into the root
   landing carried fragments, from other pages, the agent files and outside:
   a band that lives on map/ opens there; a film or the films opens the home
   page's list; a band that left the site with its own page (the contact
   routes, the credit ledger, the coding-agent page, a result's problem page)
   opens that page; anything else opens the home page. Loaded in the root's
   <head>, before its no-script refresh. */
(function () {
  "use strict";
  var HOME = "https://wcook04.github.io/";
  var HOME_VIDEOS = HOME + "#videos";
  // Ids that stand on map/index.html.
  var ON_MAP = ["top", "main", "mathematics", "maths-slide", "maths-title", "problems", "result",
                "boundaries", "system", "system-title", "papers", "papers-title"];
  var EXACT = {
    atlas: "https://wcook04.github.io/plectis-atlas/",
    "atlas-title": "https://wcook04.github.io/plectis-atlas/",
    "take-part": "docs/contact.html",
    contribute: "docs/contact.html",
    "contribute-title": "docs/contact.html",
    contact: "docs/contact.html",
    help: "docs/contact.html",
    "decision-routes": "docs/contact.html#audience-routes",
    credit: "docs/credit-ledger.html",
    "credit-title": "docs/credit-ledger.html",
    "credit-list": "docs/credit-ledger.html",
    check: "docs/coding-agents.html",
    "browser-assistant": "docs/coding-agents.html",
    "research-question": "docs/coding-agents.html",
    "ai-handoff": "docs/coding-agents.html",
    "earlier-software": "docs/index.html",
    "how-it-fits": "docs/index.html"
  };
  var VIDEO_PREFIXES = ["videos", "demo-", "film-", "project-", "video-", "transcript-", "chapters"];
  function target(id) {
    if (!id) return HOME;
    if (ON_MAP.indexOf(id) !== -1) return "map/#" + encodeURIComponent(id);
    if (Object.prototype.hasOwnProperty.call(EXACT, id)) return EXACT[id];
    // A result slide (result-257-weighted and its old aliases) opens its
    // problem's page, which leads with the same plate.
    var result = /^result-(\d+)(?:-|$)/.exec(id);
    if (result) return "maths/problems/erdos_" + result[1] + ".html";
    for (var i = 0; i < VIDEO_PREFIXES.length; i++) {
      if (id.indexOf(VIDEO_PREFIXES[i]) === 0) return HOME_VIDEOS;
    }
    return HOME + "#" + encodeURIComponent(id);
  }
  var id = "";
  try { id = decodeURIComponent(location.hash.slice(1)); } catch (e) { id = ""; }
  location.replace(target(id));
})();
