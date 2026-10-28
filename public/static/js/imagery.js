// Real imagery (NASA GIBS) loaded from /static/img/real, resampled onto a SatelliteTexture.
// Everything here is optional: when the manifest says nothing is available the page keeps its procedural look.
import { getJSON } from './api.js';

const BASE = '/static/img/real/';
const cache = new Map();

export const getImagery = () => getJSON('/api/imagery').catch(() => ({ available: false }));

export function decodeImage(url, keep = true) {
  if (keep && cache.has(url)) return cache.get(url);
  const p = new Promise((res, rej) => {
    const im = new Image();
    im.onload = () => {
      const c = document.createElement('canvas');
      c.width = im.naturalWidth; c.height = im.naturalHeight;
      const x = c.getContext('2d', { willReadFrequently: true });
      x.drawImage(im, 0, 0);
      res({ w: c.width, h: c.height, data: x.getImageData(0, 0, c.width, c.height).data });
    };
    im.onerror = () => rej(new Error(`could not load ${url}`));
    im.src = url;
  });
  if (keep) { cache.set(url, p); p.catch(() => cache.delete(url)); }
  return p;
}

/** Twelve monthly images -> blend by fractional month position (0..12, 0 = 1 Jan). */
export class MonthSet {
  constructor(tex, entry) {
    this.tex = tex; this.entry = entry; this.bbox = entry.bbox;
    this.arr = new Array(12).fill(null); this.busy = new Set();
    this.file = new Array(12).fill(null);
    entry.files.forEach((f, k) => { const m = entry.months[k]; if (m >= 1 && m <= 12) this.file[m - 1] = f; });
    this.static = entry.files.length === 1 && !entry.months[0];
  }
  _want(m) {
    const f = this.static ? this.entry.files[0] : this.file[m];
    if (!f || this.arr[m] || this.busy.has(m)) return;
    this.busy.add(m);
    decodeImage(BASE + f).then((img) => { this.arr[m] = this.tex.resample(img, this.bbox); }).catch(console.warn).finally(() => this.busy.delete(m));
  }
  _get(m) {
    for (let d = 0; d < 7; d++) for (const k of [m + d, m - d]) { const v = this.arr[((k % 12) + 12) % 12]; if (v) return v; }
    return null;
  }
  loadAll() { for (let m = 0; m < 12; m++) this._want(m); }
  pair(p) {
    const x = p - 0.5, i0 = Math.floor(x), t = x - i0;
    const a = ((i0 % 12) + 12) % 12, b = (a + 1) % 12;
    this._want(a); this._want(b);
    const A = this._get(a), B = this._get(b);
    return A ? { a: A, b: B || A, t } : null;
  }
  get loaded() { return this.arr.filter(Boolean).length; }
}

/** Sub-daily GOES frames -> blend by time in ms. */
export class FrameSet {
  constructor(tex, entry, feather = 0) {
    this.tex = tex; this.entry = entry; this.bbox = entry.bbox; this.feather = feather;
    this.times = entry.frames.map((f) => Date.parse(f.t));
    this.arr = new Array(this.times.length).fill(null);
    this.dead = false;
    this._run();
  }
  async _run() {
    for (let k = 0; k < this.times.length && !this.dead; k++) {
      try {
        const img = await decodeImage(BASE + this.entry.frames[k].file, false);
        this.arr[k] = this.tex.resample(img, this.bbox, this.feather);
      } catch (e) { console.warn(e); }
    }
  }
  stop() { this.dead = true; }
  at(ms) {
    const T = this.times;
    let hi = T.findIndex((t) => t >= ms);
    if (hi < 0) hi = T.length - 1;
    const lo = Math.max(0, hi - 1);
    const near = (k, dir) => { for (let q = k; q >= 0 && q < T.length; q += dir) if (this.arr[q]) return q; return -1; };
    let a = near(lo, -1), b = near(hi, 1);
    if (a < 0 && b < 0) return null;
    if (a < 0) a = b; if (b < 0) b = a;
    const span = T[b] - T[a];
    return { a: this.arr[a], b: this.arr[b], t: span > 0 ? Math.min(1, Math.max(0, (ms - T[a]) / span)) : 0 };
  }
  get loaded() { return this.arr.filter(Boolean).length; }
}
