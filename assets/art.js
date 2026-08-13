/* Plectis — the living field, low-power architecture.
   The reference image as living matter behind the landing: crimson spatter
   in three registers, droplets with dark cores and bright vermilion rims,
   deep navy cell-texture, a dust-fine starfield, one thin magenta streak,
   a thin warm breath along the top edge, film grain. No central mass, no
   disc; the drama lives at the frame edges and the text spine stays dark.

   Motion and heat contract:
   - WebGL is a one-shot paint tool, not an ambient process. It renders one
     deliberately soft frame into a 2D canvas, releases its context, and does
     no recurring work while the page is idle. There is no ambient rAF loop to
     leave running, so a backgrounded tab costs exactly nothing.
   - Nothing is compiled or painted while the document is hidden. A prerender
     or a background tab waits for its first visible moment.
   - Scrolling only adjusts the retained still's wrapper opacity once per
     animation frame. It never invokes the shader, and it writes opacity with
     the wrapper's CSS transition disabled so the recession tracks the scroll
     instead of chasing a 240ms transition restarted on every frame.
   - A resize or rotation repaints once, debounced, into the SAME retained
     still, so the field never stretches and never flickers back to the flat
     wash mid-gesture. Sub-threshold height changes (a mobile URL bar) are
     ignored.
   - prefers-reduced-motion keeps the static CSS field and starts no WebGL.
   - The static CSS field in style.css stays authoritative for no-JS,
     no-WebGL, save-data, small-device, and lost-context visitors; this
     file crossfades over it and removes itself cleanly on any failure,
     including a GPU context loss and an evicted 2D backing store.
   - Nothing leaves the page: no fetches, no storage, no third-party code
     (CSP: 'self'). */
(function () {
  'use strict';

  if (!window.matchMedia || !window.requestAnimationFrame) return;
  var doc = document;
  var root = doc.documentElement;

  /* Kindness gates: explicit data saving or a very small device budget means
     the static CSS composition stays in charge and no ambient GPU work starts. */
  try {
    if (navigator.connection && navigator.connection.saveData) return;
    if (navigator.deviceMemory && navigator.deviceMemory <= 4) return;
    if (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4) return;
  } catch (e) {}

  var mqMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var mqDark = window.matchMedia('(prefers-color-scheme: dark)');
  if (mqMotion.matches) return;

  var VERT = [
    'attribute vec2 a;',
    'void main(){ gl_Position = vec4(a, 0.0, 1.0); }'
  ].join('\n');

  /* Design space: x in [0, aspect] left to right, y in [0,1] top to bottom,
     so masses sit where the CSS field puts them and the two layers agree.
     Colour law, earned: spatter is deep crimson through ember vermilion —
     never rose, never pink; rose exists ONLY in the single thin streak, the
     way the reference keeps its one magenta interference line. Blue stays
     navy-deep: saturated hue at low luminance, colour in the dark. */
  var FRAG = [
    '#ifdef GL_FRAGMENT_PRECISION_HIGH',
    'precision highp float;',
    '#else',
    'precision mediump float;',
    '#endif',
    'uniform vec2 u_res;',
    'uniform float u_time;',
    'uniform float u_theme;',     /* 0 dark textured matter, 1 light pigment on paper */
    'uniform vec3 u_ground;',
    'uniform vec3 u_warm;',
    'uniform vec3 u_cool;',
    'uniform vec3 u_rose;',
    'uniform vec3 u_ember;',
    'uniform vec4 u_a;',          /* strengths: warm, cool, rose, ember */
    '',
    'float hash21(vec2 p){',
    '  p = fract(p * vec2(234.34, 435.345));',
    '  p += dot(p, p + 34.23);',
    '  return fract(p.x * p.y);',
    '}',
    'float vnoise(vec2 p){',
    '  vec2 i = floor(p); vec2 f = fract(p);',
    '  vec2 u = f * f * (3.0 - 2.0 * f);',
    '  float a = hash21(i);',
    '  float b = hash21(i + vec2(1.0, 0.0));',
    '  float c = hash21(i + vec2(0.0, 1.0));',
    '  float d = hash21(i + vec2(1.0, 1.0));',
    '  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);',
    '}',
    'const mat2 ROT = mat2(0.8, 0.6, -0.6, 0.8);',
    'float fbm(vec2 p){',
    '  float v = 0.0; float amp = 0.5;',
    '  for (int i = 0; i < 5; i++){',
    '    v += amp * vnoise(p);',
    '    p = ROT * p * 2.03 + vec2(11.7, 7.3);',
    '    amp *= 0.5;',
    '  }',
    '  return v;',
    '}',
    '',
    'void main(){',
    '  float aspect = u_res.x / u_res.y;',
    '  vec2 p = gl_FragCoord.xy / u_res;',
    '  p.y = 1.0 - p.y;',
    '  p.x *= aspect;',
    '  float t = u_time;',
    '',
    /* Domain warp, glacial time: the drift that makes each painted frame a
       slightly different weather than the last. */
    '  vec2 q = vec2(fbm(p * 1.9 + vec2(0.0, 0.0) + 0.018 * t),',
    '                fbm(p * 1.9 + vec2(5.2, 1.3) - 0.014 * t));',
    '  vec2 r = vec2(fbm(p * 1.9 + 1.7 * q + vec2(1.7, 9.2) + 0.006 * t),',
    '                fbm(p * 1.9 + 1.7 * q + vec2(8.3, 2.8) - 0.005 * t));',
    '  float f = fbm(p * 2.6 + 2.2 * r);',
    '',
    /* Reading protection first and absolute: a calm band over the column
       region, deepest where prose sits; only the star dust is exempt. */
    '  float shade = 1.0 - 0.78 * smoothstep(0.16, 0.38, p.y) * smoothstep(1.08, 0.86, p.y);',
    '  vec2 cuv = p - vec2(0.5 * aspect, 0.52);',
    '  float edgew = smoothstep(0.30, 1.0, length(cuv * vec2(1.0, 1.3)));',
    '  float portrait = smoothstep(0.9, 0.55, aspect);',
    '',
    /* Cluster gate: spatter drifts in weather systems, denser toward the
       frame edges, reusing the big warp field for its migration. */
    '  float gate = (0.30 + 0.70 * smoothstep(0.42, 0.66, f)) * (0.35 + 0.65 * edgew);',
    '',
    /* Three registers of spatter in the crimson-vermilion register. */
    '  float h1 = fbm(p * 26.0 + r * 3.0);',
    '  float spray = smoothstep(0.635, 0.675, h1);',
    '  float h2 = fbm(p * 9.5 - r * 2.2 + 4.7);',
    '  float drops = smoothstep(0.655, 0.70, h2);',
    '  float h3 = fbm(p * 4.2 + r * 1.1 + 8.9);',
    '  float blobs = smoothstep(0.665, 0.705, h3);',
    '  float blobRim = smoothstep(0.640, 0.665, h3) * (1.0 - smoothstep(0.678, 0.700, h3));',
    '  float twinkle = 0.72 + 0.28 * sin(t * 0.5 + h1 * 41.0);',
    '  vec3 deepRed = u_ember * vec3(0.92, 0.42, 0.38);',
    '  vec3 sprayCol = mix(deepRed, u_ember, smoothstep(0.71, 0.85, h1));',
    '',
    /* Navy depth: cells breathing on the warp, colour without brightness. */
    '  float water = 0.30 + 0.70 * q.x;',
    '',
    /* The one warm edge: a thin full-width breath along the very top. */
    '  float topglow = exp(-max(p.y, 0.0) * 16.0) * (0.78 + 0.22 * vnoise(vec2(p.x * 2.6, t * 0.02)));',
    '',
    /* The single thin magenta streak, upper-right corner — the only rose. */
    '  float th = 0.50 + 0.07 * sin(t * 0.011);',
    '  vec2 bdir = vec2(cos(th), sin(th));',
    '  vec2 bnrm = vec2(-bdir.y, bdir.x);',
    '  vec2 rel = p - vec2(0.88 * aspect, 0.05);',
    '  float dline = dot(rel, bnrm);',
    '  float along = dot(rel, bdir);',
    '  float beam = exp(-dline * dline * 300.0) * exp(-along * along * 1.4);',
    '  beam *= 0.6 + 0.4 * fbm(vec2(along * 2.5, dline * 10.0) + 0.03 * t);',
    '',
    /* A small vermilion breath low on the left frame edge. */
    '  float demb = distance(p * vec2(1.0, 1.2), vec2(0.06 * aspect, 1.32));',
    '  float lowmass = smoothstep(0.75, 0.08, demb) * (0.5 + 0.5 * f);',
    '',
    '  vec3 col;',
    '  if (u_theme < 0.5) {',
    /* Dark: textured matter over wine-black water, luminance held down. */
    '    float sg2 = gate * shade;',
    '    vec3 add = vec3(0.0);',
    '    add += u_cool * water * u_a.y * 0.7 * mix(shade, 1.0, 0.45);',
    '    add += (u_warm * 0.6 + u_ember * 0.4) * topglow * u_a.x * 0.85;',
    '    add += sprayCol * spray * twinkle * u_a.w * 2.2 * sg2;',
    '    add += mix(deepRed, u_ember, 0.5) * drops * u_a.w * 2.0 * sg2;',
    '    add += deepRed * blobs * u_a.w * 1.0 * sg2;',
    '    add += vec3(0.97, 0.55, 0.22) * blobRim * u_a.w * 2.6 * sg2;',
    '    add += u_rose * beam * u_a.z * 1.1 * shade;',
    '    add += u_ember * lowmass * u_a.w * 1.2;',
    '',
    '    add *= 1.0 + 0.35 * portrait;',
    '    add = add / (1.0 + 0.5 * add);',    /* firm shoulder, text first */
    '',
    /* Dust-fine starfield, unshaded — it is part of the dark itself. */
    '    vec2 sg = p * vec2(120.0, 78.0);',
    '    vec2 cell = floor(sg);',
    '    float sh2 = hash21(cell);',
    '    float sd = length(fract(sg) - 0.5);',
    '    float star = smoothstep(0.30, 0.02, sd) * step(0.984, sh2);',
    '    star *= 0.55 + 0.45 * sin(t * 0.7 + sh2 * 90.0);',
    '    add += mix(vec3(0.78, 0.83, 0.95), u_cool, 0.4) * star * (1.0 - blobs) * 0.5;',
    '',
    '    float vig = smoothstep(1.7, 0.45, length(cuv * vec2(1.0, 1.25)));',
    '    col = u_ground * mix(0.82, 1.0, vig) + add;',
    '  } else {',
    /* Light: pigment specks on warm paper, same geometry, quieter still. */
    '    col = u_ground;',
    '    col *= mix(vec3(1.0), u_warm,  clamp(topglow * u_a.x * 0.8, 0.0, 0.5));',
    '    col *= mix(vec3(1.0), u_cool,  clamp(water * edgew * u_a.y * 0.5, 0.0, 0.4));',
    '    col *= mix(vec3(1.0), u_rose,  clamp(beam * u_a.z * 0.8, 0.0, 0.45));',
    '    col *= mix(vec3(1.0), u_ember, clamp((spray * 0.8 + drops + blobRim) * gate * u_a.w, 0.0, 0.5));',
    '    col = mix(u_ground, col, mix(1.0, shade, 0.7));',
    '  }',
    '',
    /* Film grain per painted frame; doubles as dither against banding. The
       hash must be decorrelated from the pixel axes — an axis-biased hash
       reads as vertical lines. Static within a frame; the crossfade between
       frames is what animates it, gently. */
    '  float gt = floor(t * 8.0) * 7.13;',
    '  float grain = fract(sin(dot(gl_FragCoord.xy + vec2(gt, gt * 1.7), vec2(12.9898, 78.233))) * 43758.5453) - 0.5;',
    '  col += grain * (u_theme < 0.5 ? 0.018 : 0.008);',
    '',
    '  gl_FragColor = vec4(col, 1.0);',
    '}'
  ].join('\n');

  var wrap, glCanvas, still, stillCtx, gl, program;
  var U = {};
  var vt = 47 + Math.random() * 180;
  var scrollRaf = 0;
  /* Set while this file deliberately drops its own context after the single
     paint, so the WEBGL_lose_context event that release fires is not mistaken
     for a real GPU loss. */
  var releasing = false;
  /* Effective darkness of the frame currently on screen; null until first
     paint. Guards the repaint triggers against redrawing an identical frame. */
  var paintedDark = null;
  /* Viewport the current still was composed for. */
  var lastVW = 0, lastVH = 0;
  var resizeTimer = 0;
  var settleTimer = 0;
  var pendingRepaint = false;

  function isDark() {
    var t = root.getAttribute('data-theme');
    if (t === 'dark') return true;
    if (t === 'light') return false;
    return mqDark.matches;
  }

  function token(name) {
    return getComputedStyle(root).getPropertyValue(name).trim();
  }
  function colorOf(name, fb) {
    var v = token(name);
    var m = /^#([0-9a-f]{6})$/i.exec(v);
    if (!m) {
      m = /^#([0-9a-f]{3})$/i.exec(v);
      if (m) {
        var s = m[1];
        v = '#' + s.charAt(0) + s.charAt(0) + s.charAt(1) + s.charAt(1) + s.charAt(2) + s.charAt(2);
        m = /^#([0-9a-f]{6})$/i.exec(v);
      }
    }
    if (!m) return fb;
    var n = parseInt(m[1], 16);
    return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
  }
  function alphaOf(name, fb) {
    var v = parseFloat(token(name));
    return isNaN(v) ? fb : v / 100;
  }

  /* Lift a token's chroma without lifting its light. The stylesheet's washes
     are archival on purpose; the field speaks the same hues, saturated. */
  function ignite(rgb, satMul, lumMul) {
    var r = rgb[0], g = rgb[1], b = rgb[2];
    var mx = Math.max(r, g, b), mn = Math.min(r, g, b);
    var l = (mx + mn) / 2;
    var h = 0, s = 0;
    if (mx !== mn) {
      var d = mx - mn;
      s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
      if (mx === r) h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
      else if (mx === g) h = ((b - r) / d + 2) / 6;
      else h = ((r - g) / d + 4) / 6;
    }
    s = Math.min(1, s * satMul);
    l = Math.min(0.72, l * lumMul);
    if (s === 0) return [l, l, l];
    var q2 = l < 0.5 ? l * (1 + s) : l + s - l * s;
    var p2 = 2 * l - q2;
    function hue(tt) {
      if (tt < 0) tt += 1;
      if (tt > 1) tt -= 1;
      if (tt < 1 / 6) return p2 + (q2 - p2) * 6 * tt;
      if (tt < 1 / 2) return q2;
      if (tt < 2 / 3) return p2 + (q2 - p2) * (2 / 3 - tt) * 6;
      return p2;
    }
    return [hue(h + 1 / 3), hue(h), hue(h - 1 / 3)];
  }

  function applyPalette() {
    if (!gl) return;
    var dark = isDark();
    paintedDark = dark;
    gl.uniform1f(U.u_theme, dark ? 0 : 1);
    gl.uniform3fv(U.u_ground, colorOf('--page', dark ? [0.09, 0.063, 0.125] : [0.973, 0.941, 0.886]));
    gl.uniform3fv(U.u_warm, ignite(colorOf('--wash-warm', [0.878, 0.635, 0.247]), dark ? 1.25 : 1.12, 1.0));
    gl.uniform3fv(U.u_cool, ignite(colorOf('--wash-cool', [0.263, 0.345, 0.733]), dark ? 1.2 : 1.1, 1.0));
    gl.uniform3fv(U.u_rose, ignite(colorOf('--wash-rose', [0.769, 0.314, 0.557]), 1.2, 1.0));
    gl.uniform3fv(U.u_ember, ignite(colorOf('--wash-ember', [0.784, 0.333, 0.180]), dark ? 1.35 : 1.15, 1.0));
    var aw = alphaOf('--wash-warm-a', 0.13);
    var ac = alphaOf('--wash-cool-a', 0.10);
    var ar = alphaOf('--wash-rose-a', 0.06);
    var ae = alphaOf('--wash-ember-a', 0.06);
    if (dark) {
      gl.uniform4f(U.u_a, aw * 3.3, ac * 3.1, ar * 4.2, ae * 3.4);
    } else {
      gl.uniform4f(U.u_a, aw * 4.6, ac * 3.6, ar * 4.4, ae * 3.8);
    }
  }

  var sizeRetry = 0;
  function size() {
    if (!gl) return false;
    /* A detached or not-yet-laid-out viewport reports zero dimensions;
       painting a 2px frame there would stretch to a smear. Wait for real
       dimensions instead. */
    if (window.innerWidth < 4 || window.innerHeight < 4) {
      if (!sizeRetry) {
        sizeRetry = setTimeout(function () {
          sizeRetry = 0;
          if (size()) { applyPalette(); paintStill(); }
        }, 300);
      }
      return false;
    }
    /* The field is intentionally diffuse. More than three quarters of a CSS
       pixel per backing pixel adds heat and memory, not visible detail. */
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var scale = Math.min(0.75, Math.max(0.5, dpr * 0.45));
    var w = Math.max(2, Math.round(window.innerWidth * scale));
    var h = Math.max(2, Math.round(window.innerHeight * scale));
    lastVW = window.innerWidth;
    lastVH = window.innerHeight;
    if (glCanvas.width !== w || glCanvas.height !== h) {
      glCanvas.width = w;
      glCanvas.height = h;
      still.width = w;
      still.height = h;
      gl.viewport(0, 0, w, h);
      gl.uniform2f(U.u_res, w, h);
    }
    return true;
  }

  /* The deliberate drop after one frame. `releasing` stays true until the next
     renderer starts: WEBGL_lose_context dispatches its event in a later task,
     and a flag survives that gap where removeEventListener alone would race. */
  function releaseRenderer() {
    if (!gl) return;
    releasing = true;
    try {
      gl.flush();
      var lose = gl.getExtension('WEBGL_lose_context');
      if (lose) lose.loseContext();
    } catch (e) {}
    if (glCanvas) {
      glCanvas.removeEventListener('webglcontextlost', onGlContextLost, false);
      if (glCanvas.parentNode) glCanvas.parentNode.removeChild(glCanvas);
      glCanvas.width = 1;
      glCanvas.height = 1;
    }
    glCanvas = null;
    gl = null;
    program = null;
    U = {};
  }

  /* A real GPU loss during the single paint. Cancelling the default would ask
     for a restore this file has no ambient loop to use, so hand the room back
     to the CSS field instead — that is the documented fallback. */
  function onGlContextLost() {
    if (releasing) return;
    teardown();
  }

  /* Chrome can evict a 2D backing store under memory pressure. The retained
     still is what the reader is actually looking at, and mc-field-live has
     already faded the CSS wash out behind it, so a lost still would read as a
     void rather than a fallback. Withdraw and let the wash return. */
  function onStillContextLost() {
    teardown();
  }

  function teardown() {
    if (sizeRetry) { clearTimeout(sizeRetry); sizeRetry = 0; }
    if (resizeTimer) { clearTimeout(resizeTimer); resizeTimer = 0; }
    if (settleTimer) { clearTimeout(settleTimer); settleTimer = 0; }
    if (scrollRaf) { cancelAnimationFrame(scrollRaf); scrollRaf = 0; }
    pendingRepaint = false;
    paintedDark = null;
    releaseRenderer();
    root.classList.remove('mc-field-live');
    root.removeAttribute('data-plectis-field-mode');
    if (still) still.removeEventListener('contextlost', onStillContextLost, false);
    if (wrap && wrap.parentNode) wrap.parentNode.removeChild(wrap);
    wrap = null; still = null; stillCtx = null;
  }

  /* Paint once, retain the pixels in an ordinary 2D canvas, then release the
     shader context. Idle Plectis should be indistinguishable from a still. */
  function paintStill() {
    if (!gl || !stillCtx) return;
    gl.uniform1f(U.u_time, vt % 7200);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    try {
      stillCtx.drawImage(glCanvas, 0, 0);
    } catch (e) { teardown(); return; }
    root.setAttribute('data-plectis-field-mode', 'still');
    root.classList.add('mc-field-live');
    applyScrollOpacity();
    settleWrapper();
    releaseRenderer();
  }

  /* The wrapper's entry crossfade is a CSS transition on opacity. Scroll
     recession writes that same property every animation frame, which restarts
     the transition sixty times a second and leaves the field trailing a quarter
     of a second behind the scroll. Once the entry fade has finished, take
     direct control of it. A theme flip tears the wrapper down and mounts a
     fresh one, so the crossfade still introduces every repainted field; a
     resize repaints into the existing wrapper and correctly keeps the
     direct-write behaviour it already has. */
  function settleWrapper() {
    if (settleTimer || !wrap || wrap.style.transition === 'none') return;
    settleTimer = window.setTimeout(function () {
      settleTimer = 0;
      if (wrap) wrap.style.transition = 'none';
    }, 340);
  }

  /* Scroll recession updates at most once per display frame and never touches
     a drawing context. */
  function applyScrollOpacity() {
    scrollRaf = 0;
    if (!wrap) return;
    var vh = Math.max(1, window.innerHeight);
    var sy = (window.pageYOffset || root.scrollTop || 0) / vh;
    var k = Math.min(1, Math.max(0, (sy - 0.12) / 1.25));
    k = k * k * (3 - 2 * k);
    wrap.style.opacity = String(1 - 0.55 * k);
  }
  function onScroll() {
    if (!scrollRaf) scrollRaf = requestAnimationFrame(applyScrollOpacity);
  }

  /* Renderer setup, kept separate from the wrapper mount so a resize can
     repaint into the SAME retained still. size(), applyPalette() and
     paintStill() run in one synchronous task, so the moment where the still is
     resized (and therefore cleared) never reaches a presented frame — the
     reader sees the old field, then the new one, and never the bare wash. */
  function startRenderer() {
    if (!wrap || !still || !stillCtx) return false;
    if (gl) releaseRenderer();
    releasing = false;

    glCanvas = doc.createElement('canvas');
    /* Behind the still, matching the original stacking: both canvases are
       absolutely positioned, so document order decides which is on top. */
    wrap.insertBefore(glCanvas, still);
    glCanvas.addEventListener('webglcontextlost', onGlContextLost, false);

    /* Preserve only long enough to copy the one frame into the retained 2D
       canvas. releaseRenderer() drops the context immediately afterwards. */
    var opts = { alpha: false, depth: false, stencil: false, antialias: false, powerPreference: 'low-power', preserveDrawingBuffer: true };
    try {
      gl = glCanvas.getContext('webgl', opts) || glCanvas.getContext('experimental-webgl', opts);
    } catch (e) { gl = null; }
    if (!gl) return false;

    function shader(type, src) {
      var s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) return null;
      return s;
    }
    var vs = shader(gl.VERTEX_SHADER, VERT);
    var fs = shader(gl.FRAGMENT_SHADER, FRAG);
    if (!vs || !fs) return false;
    program = gl.createProgram();
    gl.attachShader(program, vs);
    gl.attachShader(program, fs);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return false;
    gl.useProgram(program);

    var buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    var loc = gl.getAttribLocation(program, 'a');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

    ['u_res', 'u_time', 'u_theme', 'u_ground', 'u_warm',
     'u_cool', 'u_rose', 'u_ember', 'u_a'].forEach(function (n) {
      U[n] = gl.getUniformLocation(program, n);
    });

    if (!size()) return true;   /* size() schedules its own retry and repaint */
    applyPalette();
    paintStill();
    return true;
  }

  function init() {
    if (!doc.body || retired) return;
    if (!wrap) {
      wrap = doc.createElement('div');
      wrap.className = 'mc-field';
      wrap.setAttribute('aria-hidden', 'true');
      still = doc.createElement('canvas');
      wrap.appendChild(still);
      doc.body.appendChild(wrap);
      stillCtx = still.getContext('2d', { alpha: false });
      still.addEventListener('contextlost', onStillContextLost, false);
    }
    if (!stillCtx || !startRenderer()) { teardown(); return; }
  }

  /* A palette change REPAINTS the field rather than retiring it.
     This used to tear down permanently, on the reasoning that recreating a GPU
     context for a decorative toggle would violate the heat budget. That reading
     of the cost was wrong: paintStill() already draws exactly one frame, copies
     it into the retained 2D canvas and drops the GL context, so there is no
     standing context to preserve and a flip costs precisely what the initial
     load costs — one compile, one frame, then nothing. What the old behaviour
     actually bought was a landing page that fell back to the flat CSS wash on
     the first toggle and stayed there for the rest of the session, including
     after toggling back. That is the part a reader notices.

     Everything below binds ONCE, outside init(), because init() now runs more
     than once and re-registering inside it would stack a fresh observer,
     listener and scroll handler on every flip. */
  var restartTimer = 0;
  var retired = false;

  /* Nothing is compiled or painted for a document the reader cannot see. A
     prerender or a background tab records the intent and spends the work on
     its first visible moment instead. */
  function start() {
    if (retired) return;
    if (doc.hidden) { pendingRepaint = true; return; }
    init();
  }

  function onVisibility() {
    if (doc.hidden || retired || !pendingRepaint) return;
    pendingRepaint = false;
    if (wrap) repaint();
    else init();
  }

  /* Same wrapper, same retained still, new frame. Used for resize and rotation,
     where a full teardown would drop the reader back to the flat CSS wash for
     the length of the restart delay. */
  function repaint() {
    if (retired) return;
    if (!wrap) { start(); return; }
    if (doc.hidden) { pendingRepaint = true; return; }
    if (!startRenderer()) teardown();
  }

  function restart() {
    if (retired) return;
    teardown();
    if (restartTimer) clearTimeout(restartTimer);
    /* One tick of delay: it coalesces a mashed toggle into a single repaint and
       lets the new theme's custom properties settle before applyPalette() reads
       them off the computed style. */
    restartTimer = window.setTimeout(function () {
      restartTimer = 0;
      start();
    }, 60);
  }

  /* Only a change in effective darkness changes the palette: every --wash-*
     value is declared under :root, :root[data-theme="dark"] and the
     prefers-color-scheme mirror of that. A system-scheme flip on a page whose
     theme is pinned, or a data-theme write landing on the value already in
     force, would otherwise recompile a shader to draw the identical frame. */
  function onThemeChange() {
    if (paintedDark !== null && isDark() === paintedDark) return;
    restart();
  }

  /* The composition is aspect-dependent, so a resized viewport was stretching
     the retained still rather than recomposing it. Mobile browsers also fire
     resize when the URL bar slides — height only, and by a little — which is
     not a recomposition and must not cost one. */
  function onResize() {
    if (retired || !wrap || !lastVW) return;
    var w = window.innerWidth;
    var h = window.innerHeight;
    if (w === lastVW && Math.abs(h - lastVH) <= Math.max(90, lastVH * 0.18)) return;
    if (resizeTimer) clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () {
      resizeTimer = 0;
      repaint();
    }, 240);
  }

  /* Reduced motion is the one flip that is meant to be terminal. Guard on the
     query's current state: the old listener retired on ANY change to it, so a
     reader who turned reduced motion off lost the field until a reload. */
  function onMotionChange() {
    if (!mqMotion.matches) return;
    retired = true;
    if (restartTimer) { clearTimeout(restartTimer); restartTimer = 0; }
    teardown();
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onResize, { passive: true });
  window.addEventListener('orientationchange', onResize, { passive: true });
  doc.addEventListener('visibilitychange', onVisibility, false);
  if (window.MutationObserver) {
    new MutationObserver(onThemeChange)
      .observe(root, { attributes: true, attributeFilter: ['data-theme'] });
  }
  if (mqDark.addEventListener) mqDark.addEventListener('change', onThemeChange);
  else if (mqDark.addListener) mqDark.addListener(onThemeChange);
  if (mqMotion.addEventListener) mqMotion.addEventListener('change', onMotionChange);
  else if (mqMotion.addListener) mqMotion.addListener(onMotionChange);

  if (doc.readyState === 'loading') {
    doc.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
