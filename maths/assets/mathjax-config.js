/* Plectis — MathJax configuration for the exact-TeX paper variants.
   Loaded only by the two papers whose MathML conversion is incomplete
   (render_contract.preferred == "html_exact_tex"); every other paper and
   document ships browser-native MathML and needs no math runtime at all.
   The macro table mirrors _normalise_tex_for_mathml in
   tools/meta/dissemination/build_plectis_lean_experience.py: the manuscript
   house style defines these compact aliases, the exact-TeX stream keeps the
   manuscript unmodified, so the renderer must know the same vocabulary. */
window.MathJax = {
  tex: {
    inlineMath: [['\\(', '\\)']],
    displayMath: [['\\[', '\\]']],
    tags: 'ams',
    processEscapes: true,
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
    fontURL: new URL(
      '../../assets/vendor/mathjax-3.2.2/output/chtml/fonts/woff-v2',
      window.location.href
    ).href
  },
  options: {
    enableMenu: false
  }
};
