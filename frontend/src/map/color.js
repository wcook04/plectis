// Colour, mixed as the stylesheet mixes it.
//
// Harvested from the Plectis universe map (ai_workflow
// tools/meta/dissemination/maths_site_assets/universe.js, parseColor,
// rgbToOklab, oklabToRgb, mixOklab, overGround, groundIsDark and the glow
// sprite, lines 160-232 and 825-883). A mark that drops back is mixed toward
// the ground's line tone in Oklab, as color-mix(in oklab, ...) does, so it
// stays faded ink of its own hue rather than turning grey. Canvas cannot
// evaluate color-mix, so the map reads plain colours from CSS and mixes here.

const parsed = new Map();

export function parseColor(text) {
  const key = String(text == null ? '' : text).trim();
  if (parsed.has(key)) return parsed.get(key);
  let out = null;
  let m;
  if ((m = /^#([0-9a-f]{3,8})$/i.exec(key))) {
    let hex = m[1];
    if (hex.length === 3 || hex.length === 4) hex = hex.replace(/(.)/g, '$1$1');
    if (hex.length === 6 || hex.length === 8) {
      out = [parseInt(hex.slice(0, 2), 16) / 255, parseInt(hex.slice(2, 4), 16) / 255,
        parseInt(hex.slice(4, 6), 16) / 255, hex.length === 8 ? parseInt(hex.slice(6, 8), 16) / 255 : 1];
    }
  } else if ((m = /^rgba?\(\s*([\d.]+%?)[\s,]+([\d.]+%?)[\s,]+([\d.]+%?)(?:[\s,/]+([\d.]+%?))?\s*\)$/i.exec(key))) {
    const channel = (v) => (/%$/.test(v) ? parseFloat(v) / 100 : parseFloat(v) / 255);
    out = [channel(m[1]), channel(m[2]), channel(m[3]),
      m[4] == null ? 1 : /%$/.test(m[4]) ? parseFloat(m[4]) / 100 : parseFloat(m[4])];
  } else if ((m = /^color\(\s*srgb\s+([-\d.e]+)\s+([-\d.e]+)\s+([-\d.e]+)(?:\s*\/\s*([\d.]+%?))?\s*\)$/i.exec(key))) {
    out = [+m[1], +m[2], +m[3], m[4] == null ? 1 : /%$/.test(m[4]) ? parseFloat(m[4]) / 100 : +m[4]];
  }
  if (out && !out.every((v) => Number.isFinite(v))) out = null;
  parsed.set(key, out);
  return out;
}

const toLinear = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const toGamma = (c) => (c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055);

function rgbToOklab(c) {
  const r = toLinear(c[0]); const g = toLinear(c[1]); const b = toLinear(c[2]);
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
}

function oklabToRgb(c) {
  let l = c[0] + 0.3963377774 * c[1] + 0.2158037573 * c[2];
  let m = c[0] - 0.1055613458 * c[1] - 0.0638541728 * c[2];
  let s = c[0] - 0.0894841775 * c[1] - 1.2914855480 * c[2];
  l = l * l * l; m = m * m * m; s = s * s * s;
  return [toGamma(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
    toGamma(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
    toGamma(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)];
}

export function rgbText(c) {
  const v = (x) => Math.round(Math.max(0, Math.min(1, x)) * 255);
  return `rgb(${v(c[0])}, ${v(c[1])}, ${v(c[2])})`;
}

/** What a translucent colour shows over an opaque ground. */
export function overGround(c, ground) {
  if (c[3] >= 0.999) return c;
  return [c[0] * c[3] + ground[0] * (1 - c[3]), c[1] * c[3] + ground[1] * (1 - c[3]),
    c[2] * c[3] + ground[2] * (1 - c[3]), 1];
}

/** color-mix(in oklab, a, b t), or null when either colour cannot be read. */
export function mixOklab(a, b, t, ground) {
  let ca = parseColor(a); let cb = parseColor(b);
  if (!ca || !cb) return null;
  if (ground) { ca = overGround(ca, ground); cb = overGround(cb, ground); }
  const la = rgbToOklab(ca); const lb = rgbToOklab(cb);
  return rgbText(oklabToRgb([la[0] + (lb[0] - la[0]) * t, la[1] + (lb[1] - la[1]) * t, la[2] + (lb[2] - la[2]) * t]));
}

export function isDark(color) {
  const c = parseColor(color);
  return !!c && (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) < 0.35;
}

/* One soft disc per colour, drawn once: white light masked to the colour, so
   its edge fades to nothing rather than through grey. */
const sprites = new Map();
export function glowSprite(color) {
  if (sprites.has(color)) return sprites.get(color);
  let sprite = typeof document !== 'undefined' ? document.createElement('canvas') : null;
  const g = sprite && sprite.getContext ? sprite.getContext('2d') : null;
  if (g && g.createRadialGradient) {
    sprite.width = sprite.height = 64;
    const light = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    light.addColorStop(0, 'rgba(255,255,255,1)');
    light.addColorStop(0.28, 'rgba(255,255,255,0.55)');
    light.addColorStop(0.62, 'rgba(255,255,255,0.13)');
    light.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = light;
    g.fillRect(0, 0, 64, 64);
    g.globalCompositeOperation = 'source-in';
    g.fillStyle = color;
    g.fillRect(0, 0, 64, 64);
  } else {
    sprite = null;
  }
  sprites.set(color, sprite);
  return sprite;
}
