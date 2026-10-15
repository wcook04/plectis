# Why I am building this

This homepage component shows one Erdős #257 result in four existing forms.
The curated HTML stays in `../../index.html`; prose is projected from
`../../film-programme.json::home` through `data-home-copy` slots. The film
programme also owns project resources and exact released video identities.

- `why-section.css` and `why-section.js` adapt the existing landing band,
  typography and `../art.js` plait. Tabs progressively enhance four paragraphs;
  with JavaScript disabled all paragraphs and links remain available. There
  is no looping animation or third-party fetch.
- `why-257-paper-{light,dark}.webp` are actual captures of
  `maths/papers/erdos-257-mersenne-support-subseries.html#res:reciprocal-support`.
- `why-257-map-{light,dark}.webp` capture that same statement in the maths map.
- The code view quotes the statement recorded in
  `maths/assets/statement-details/erdos-257-mersenne-support-subseries.json`,
  pinned to `plectis-erdos-lean@cc7e541cf2081c6fef5a5e377d52e365e33b01eb`,
  `Solutions/PalomarCorpus/E257_47/PaperStatementsAV.lean#L52`.
- The video view uses the existing released #257 thumbnail and `#film-mathematics`.
  Its example uses base two; the paper and Lean statement allow every integer
  base at least two. The unrestricted problem remains open.

Desktop Opus implemented this component; the parent supplied the words and
verified the source correspondence. Retained creation captures, integration
notes and tools are recorded in `work/film-map-20261015/README.md` in the
private generator repository. When refreshing the screenshots, capture the
actual linked statement in both themes and retain its source identity.

Validation uses the native film publication/runtime suite and a full assembled
site audit at laptop and phone sizes, including no script, keyboard tabs, theme
switching, reduced motion and the four actual destinations.
