/* Plectis — MathJax configuration for public paper and document pages.
   Loaded whenever the page's fragment still carries exact-TeX math
   (`class="math inline|display"`). Native MathML remains a generated
   fallback artifact, not the reader-facing route: Chromium MathML plus
   `display: inline-block` on `<math>` flattened the corpus, and Pandoc's
   MathML path drops `\eqref`/`\ref`.
   The macro table mirrors _normalise_tex_for_mathml in
   tools/meta/dissemination/build_plectis_lean_experience.py: the manuscript
   house style defines these compact aliases, the exact-TeX stream keeps the
   manuscript unmodified, so the renderer must know the same vocabulary. */
window.MathJax = {
  tex: {
    inlineMath: [['\\(', '\\)']],
    displayMath: [['\\[', '\\]']],
    tags: 'ams',
    tagSide: 'right',
    tagIndent: '0em',
    processEscapes: true,
    processRefs: false,
    macros: {
      Npos: '\\mathbb{N}_{>0}',
      Nzero: '\\mathbb{N}_{0}',
      ph: '\\varphi',
      N: '\\mathbb{N}',
      Z: '\\mathbb{Z}',
      Q: '\\mathbb{Q}',
      R: '\\mathbb{R}',
      C: '\\mathbb{C}',
      lcm: '\\operatorname{lcm}',
      emph: ['\\mathit{#1}', 1],
      leanlink: ['\\mathtt{#1}', 1],
      small: ''
    }
  },
  chtml: {
    displayAlign: 'center',
    displayIndent: '0',
    /* Resolve against the vendored runtime, not the page URL. A relative
       path on window.location is only accidentally correct on depth-1
       paper/problem pages and 404s from maths/index.html. The tex-chtml
       script tag is already in the document when this file runs. */
    fontURL: (function () {
      var script = document.querySelector('script[src*="tex-chtml.js"]');
      if (script && script.src) {
        return new URL('output/chtml/fonts/woff-v2', script.src).href;
      }
      return new URL(
        '../assets/vendor/mathjax-3.2.2/output/chtml/fonts/woff-v2',
        document.baseURI
      ).href;
    })()
  },
  options: {
    enableMenu: false
  },
  startup: {
    typeset: false,
    pageReady: function () {
      return MathJax.startup.defaultPageReady().then(function () {
        if (typeof window.__plectisTypesetPage === 'function') {
          return window.__plectisTypesetPage(MathJax);
        }
        return MathJax.typesetPromise();
      });
    }
  }
};
