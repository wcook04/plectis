// Where the explorer is mounted, and whether it reads a static export.
//
// The development server mounts the explorer at the origin root, so every
// page path is written as an absolute path such as "/components/<id>". A
// static export can be hosted under a subpath, for example GitHub Pages at
// /practical-formal-verification/explorer/. BASE is the directory above
// src/, read from this module's own URL, so the same code works in both
// places without configuration: at() maps a page path onto the mount point,
// and routePath() maps a location back to the page path.

export const BASE = new URL('../', import.meta.url).pathname;

/** A root-relative page path ("/catalogue") as a URL path under BASE. */
export function at(path) {
  if (typeof path !== 'string' || !path.startsWith('/') || path.startsWith('//')) return path;
  return BASE + path.slice(1);
}

/** The page path ("/", "/components/x") for a location's pathname. */
export function routePath(pathname) {
  let path = pathname.startsWith(BASE) ? `/${pathname.slice(BASE.length)}` : pathname;
  // Static exports name each page as a file: "/catalogue" is catalogue.html.
  path = path.replace(/\/index\.html$/, '/').replace(/\.html$/, '');
  return path.replace(/\/+$/, '') || '/';
}

/**
 * The static export's own record, or null under the development server. The
 * exporter writes it into every page as
 * <meta name="plectis-static-export" content="{...}">: the snapshot revision
 * it copied, the commit it was exported from and when.
 */
export const STATIC_EXPORT = (() => {
  if (typeof document === 'undefined') return null;
  const meta = document.querySelector('meta[name="plectis-static-export"]');
  if (!meta) return null;
  try { return JSON.parse(meta.getAttribute('content') || '{}'); } catch { return {}; }
})();
