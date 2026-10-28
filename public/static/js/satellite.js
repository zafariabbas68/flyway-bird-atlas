// Procedural "satellite" imagery.
//
// There is no photo data in this project. Instead the browser synthesises an
// Earth-observation style picture from the coastlines:
//   * fractal coastlines (blurred land mask + noise)
//   * vegetation that greens up and browns off with the seasons, wetter and
//     drier regions hand-placed, mountains with hill-shading, snow and ice
//   * continental shelf tint in the ocean
//   * tileable drifting clouds with soft shadows
// Everything is generated once per view, then re-coloured cheaply per frame.
import { clamp, smoothstep } from './util.js';

const TAU = Math.PI * 2;

// ------------------------------------------------------------------ noise
function hash2(x, y, s) {
  let h = Math.imul(x, 374761393) ^ Math.imul(y, 668265263) ^ Math.imul(s, 1013904223);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}
function vnoise(x, y, s) {
  const xi = Math.floor(x), yi = Math.floor(y);
  const xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash2(xi, yi, s), b = hash2(xi + 1, yi, s), c = hash2(xi, yi + 1, s), d = hash2(xi + 1, yi + 1, s);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
export function fbm(x, y, oct, s) {
  let a = 0.5, f = 1, sum = 0, norm = 0;
  for (let i = 0; i < oct; i++) { sum += a * vnoise(x * f, y * f, s + i * 17); norm += a; a *= 0.5; f *= 2.03; }
  return sum / norm;
}
// tileable variants (lattice wraps every P cells)
const wrap = (v, P) => ((v % P) + P) % P;
function tnoise(x, y, s, P) {
  const xi = Math.floor(x), yi = Math.floor(y);
  const xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const x0 = wrap(xi, P), x1 = wrap(xi + 1, P), y0 = wrap(yi, P), y1 = wrap(yi + 1, P);
  const a = hash2(x0, y0, s), b = hash2(x1, y0, s), c = hash2(x0, y1, s), d = hash2(x1, y1, s);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
function tfbm(x, y, oct, s, P) {
  let a = 0.5, f = 1, sum = 0, norm = 0;
  for (let i = 0; i < oct; i++) { sum += a * tnoise(x * f, y * f, s + i * 13, P * f); norm += a; a *= 0.5; f *= 2; }
  return sum / norm;
}

// ----------------------------------------------------------------- clouds
/** Two seamless tiles: bright clouds and their soft dark shadows. */
export function makeCloudTiles(size = 384) {
  const mk = () => { const c = document.createElement('canvas'); c.width = c.height = size; return c; };
  const cloud = mk(), shadow = mk();
  const cc = cloud.getContext('2d'), sc = shadow.getContext('2d');
  const ci = cc.createImageData(size, size), si = sc.createImageData(size, size);
  const P = 4;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const u = (x / size) * P, v = (y / size) * P;
      const wx = tfbm(u + 3.1, v + 7.7, 2, 5, P), wy = tfbm(u + 9.2, v + 1.3, 2, 6, P);
      const n = tfbm(u + (wx - 0.5) * 0.7, v + (wy - 0.5) * 0.7, 5, 11, P);
      const a = smoothstep(0.54, 0.8, n);
      const i = (y * size + x) * 4;
      const shade = 255 - (1 - a) * 28;
      ci.data[i] = shade; ci.data[i + 1] = shade; ci.data[i + 2] = 255 - (1 - a) * 14; ci.data[i + 3] = a * 235;
      si.data[i] = 4; si.data[i + 1] = 9; si.data[i + 2] = 22; si.data[i + 3] = a * 90;
    }
  }
  cc.putImageData(ci, 0, 0); sc.putImageData(si, 0, 0);
  return { cloud, shadow, size };
}

/** Draw a tile as an endlessly repeating, drifting layer. */
export function drawCloudLayer(ctx, tile, w, h, scale, ox, oy, alpha) {
  const pat = ctx.createPattern(tile, 'repeat');
  const period = tile.width * scale;
  const px = ((ox % period) + period) % period - period;
  const py = ((oy % period) + period) % period - period;
  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.translate(px, py);
  ctx.scale(scale, scale);
  ctx.fillStyle = pat;
  ctx.fillRect(0, 0, (w - px) / scale + 2, (h - py) / scale + 2);
  ctx.restore();
}

// --------------------------------------------------------------- geography
// [lon, lat, sigma_lon, sigma_lat, weight]: positive = wetter / greener
const WET = [
  [-62, -4, 12, 8, 0.65], [-86, 12, 8, 5, 0.5], [-85, 33, 9, 5, 0.42], [-80, 44, 10, 5, 0.38],
  [-123, 46, 3, 5, 0.55], [-100, 56, 26, 6, 0.28], [-45, -18, 6, 8, 0.4], [-95, 18, 5, 3, 0.4],
  [-62, -34, 7, 5, 0.18], [-100, 40, 7, 6, 0.1], [-76, 2, 3, 5, 0.4], [-72, 6, 6, 3, 0.25],
  [-75, 18, 6, 3, 0.2],
  [-113, 36, 8, 5, -0.5], [-106, 28, 6, 4, -0.45], [-69, -45, 6, 8, -0.4], [-70, -22, 2.5, 6, -0.75],
  [-40, -8, 4, 3, -0.35], [-118, 34, 4, 3, -0.3], [-111, 29, 4, 3, -0.4],
];
// polylines of mountain ranges (lon, lat), width in degrees, height 0..1
const RANGES = [
  { sigma: 1.7, amp: 0.85, pts: [[-150, 63], [-139, 60], [-130, 57], [-123, 52], [-118, 49]] },
  { sigma: 1.8, amp: 0.95, pts: [[-125, 62], [-119, 58], [-114, 51], [-110, 46], [-107, 41], [-106, 36], [-106, 32]] },
  { sigma: 1.1, amp: 0.8, pts: [[-122, 48], [-121.5, 44], [-121, 40], [-119, 37], [-117.5, 34]] },
  { sigma: 1.4, amp: 0.8, pts: [[-108, 31], [-106, 28], [-105, 25], [-104, 21.5], [-100, 19]] },
  { sigma: 1.1, amp: 0.7, pts: [[-101, 27], [-99.5, 24], [-98.5, 20]] },
  { sigma: 1.2, amp: 0.7, pts: [[-92, 16], [-90, 15], [-86, 13], [-84.5, 10], [-82.5, 9]] },
  { sigma: 1.2, amp: 0.4, pts: [[-85, 34.5], [-81, 37.5], [-77.5, 41], [-73, 44], [-70, 46]] },
  { sigma: 1.5, amp: 1.0, pts: [[-77.5, 8], [-76, 3], [-77.5, -2], [-78.5, -6], [-75.5, -11], [-71, -15], [-69, -19], [-69.5, -25], [-70, -31], [-71, -37], [-72, -43], [-73, -50]] },
  { sigma: 1.3, amp: 0.5, pts: [[-73, 11], [-72.5, 8], [-71, 6]] },
];

function segDist2(px, py, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay;
  const t = clamp(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy || 1), 0, 1);
  const ex = ax + t * dx - px, ey = ay + t * dy - py;
  return ex * ex + ey * ey;
}

function boxBlur(src, w, h, r) {
  const tmp = new Float32Array(src.length), out = new Float32Array(src.length), k = 2 * r + 1;
  for (let y = 0; y < h; y++) {
    const row = y * w; let acc = 0;
    for (let x = -r; x <= r; x++) acc += src[row + clamp(x, 0, w - 1)];
    for (let x = 0; x < w; x++) {
      tmp[row + x] = acc / k;
      acc += src[row + Math.min(x + r + 1, w - 1)] - src[row + Math.max(x - r, 0)];
    }
  }
  for (let x = 0; x < w; x++) {
    let acc = 0;
    for (let y = -r; y <= r; y++) acc += tmp[clamp(y, 0, h - 1) * w + x];
    for (let y = 0; y < h; y++) {
      out[y * w + x] = acc / k;
      acc += tmp[Math.min(y + r + 1, h - 1) * w + x] - tmp[Math.max(y - r, 0) * w + x];
    }
  }
  return out;
}

function lut(stops, n = 256) {
  const out = new Uint8Array(n * 3);
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    let k = 0;
    while (k < stops.length - 2 && t > stops[k + 1][0]) k++;
    const [t0, c0] = stops[k], [t1, c1] = stops[k + 1];
    const f = clamp((t - t0) / (t1 - t0), 0, 1);
    for (let c = 0; c < 3; c++) out[i * 3 + c] = c0[c] + (c1[c] - c0[c]) * f;
  }
  return out;
}
const VEG = lut([
  [0, [196, 168, 116]], [0.22, [178, 168, 98]], [0.45, [128, 152, 62]],
  [0.7, [58, 112, 42]], [1, [14, 58, 26]],
]);

// ----------------------------------------------------------------- texture
export class SatelliteTexture {
  /**
   * @param projection d3 projection mapping lon/lat to CSS pixels
   * @param w,h        texture size in texture pixels
   * @param scale      texture pixels per CSS pixel
   * @param layers     { land:[Feature], lakes:[Feature] } from normalizeGeo()
   */
  constructor(projection, w, h, scale, layers) {
    this.w = w; this.h = h;
    const N = w * h;
    this.canvas = document.createElement('canvas');
    this.canvas.width = w; this.canvas.height = h;
    this.ctx = this.canvas.getContext('2d');
    this.img = this.ctx.createImageData(w, h);
    this.px = new Uint32Array(this.img.data.buffer);

    // pixels per degree at the centre of the view, used to keep noise sizes constant on screen
    const c = projection.invert([w / scale / 2, h / scale / 2]) || [-90, 20];
    const a = projection(c), b = projection([c[0] + 1, c[1]]);
    const ppd = Math.max(1, Math.hypot(b[0] - a[0], b[1] - a[1]) * scale);
    this.ppd = ppd;

    const americas = (f) => { const c = d3.geoCentroid(f)[0]; return c < -12 && c > -175; };
    layers = { ...layers, land: layers.land.filter(americas) };

    // 1. land mask by rasterising the coastlines
    const mc = document.createElement('canvas'); mc.width = w; mc.height = h;
    const m2 = mc.getContext('2d');
    m2.scale(scale, scale);
    const path = d3.geoPath(projection, m2);
    m2.fillStyle = '#000'; m2.fillRect(0, 0, w / scale, h / scale);
    m2.fillStyle = '#fff'; m2.beginPath(); layers.land.forEach((f) => path(f)); m2.fill();
    m2.fillStyle = '#000'; m2.beginPath(); layers.lakes.forEach((f) => path(f)); m2.fill();
    const md = m2.getImageData(0, 0, w, h).data;
    const m = new Float32Array(N);
    for (let i = 0; i < N; i++) m[i] = md[i * 4] / 255;
    const r1 = clamp(Math.round(ppd * 0.28), 1, 5);
    const mb = boxBlur(boxBlur(m, w, h, r1), w, h, r1);
    const shelfRaw = boxBlur(boxBlur(m, w, h, Math.max(2, Math.round(ppd * 0.7))), w, h, Math.max(2, Math.round(ppd * 0.7)));

    // 2. per-pixel geography
    const fCoast = clamp(ppd / 16, 0.12, 1.5), fDetail = clamp(ppd / 5, 0.5, 5);
    this.land = new Uint8Array(N); this.space = new Uint8Array(N); this.ice = new Uint8Array(N);
    this.cov = new Float32Array(N); this.shelf = new Float32Array(N); this.E = new Float32Array(N); this.vb = new Float32Array(N);
    this.amp = new Float32Array(N); this.hemi = new Int8Array(N); this.snowB = new Float32Array(N);
    this.nz = new Float32Array(N); this.shade = new Float32Array(N);
    this.lon = new Float32Array(N); this.lat = new Float32Array(N);
    this._maps = new Map();

    const pt = [0, 0], inv = projection.invert;
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const i = y * w + x;
        pt[0] = (x + 0.5) / scale; pt[1] = (y + 0.5) / scale;
        const ll = inv(pt);
        if (!ll || !isFinite(ll[0]) || !isFinite(ll[1])) { this.space[i] = 1; continue; }
        const lon = ll[0], lat = ll[1];
        this.lon[i] = lon; this.lat[i] = lat;
        const cn = fbm(lon * fCoast, lat * fCoast, 4, 3);
        const landness = 0.42 * m[i] + 0.58 * mb[i] + (cn - 0.5) * 0.75;
        this.shelf[i] = clamp(shelfRaw[i] * 2.2, 0, 1);
        this.hemi[i] = lat >= 0 ? 1 : -1;
        if (landness <= 0.44) continue;
        this.land[i] = 1;
        this.cov[i] = smoothstep(0.455, 0.545, landness);

        const n1 = fbm(lon * 0.22, lat * 0.22, 4, 21);
        const n2 = fbm(lon * fDetail * 0.5, lat * fDetail * 0.5, 4, 5);
        this.nz[i] = n2;

        let veg = 0.34 + (n1 - 0.5) * 0.5;
        for (let k = 0; k < WET.length; k++) {
          const [wx, wy, sx, sy, wt] = WET[k];
          const dx = (lon - wx) / sx, dy = (lat - wy) / sy;
          veg += wt * Math.exp(-0.5 * (dx * dx + dy * dy));
        }
        const al = Math.abs(lat);
        veg -= smoothstep(56, 74, al) * 0.5;
        this.vb[i] = clamp(veg, 0.02, 1);
        this.amp[i] = 0.5 * smoothstep(9, 38, al);

        // mountains
        let e = 0;
        for (let k = 0; k < RANGES.length; k++) {
          const R = RANGES[k], p = R.pts, s2 = 2 * R.sigma * R.sigma;
          let d2 = 1e9;
          for (let j = 0; j < p.length - 1; j++) {
            const d = segDist2(lon, lat, p[j][0], p[j][1], p[j + 1][0], p[j + 1][1]);
            if (d < d2) d2 = d;
          }
          const v = R.amp * Math.exp(-d2 / s2);
          if (v > e) e = v;
        }
        const ridge = 1 - Math.abs(2 * n2 - 1);
        this.E[i] = clamp(e * (0.45 + 0.8 * ridge) + (n2 - 0.5) * 0.1, 0, 1.1);

        const ice = lon > -75 && lon < -8 && lat > 59.5;
        this.ice[i] = ice ? 1 : 0;
        this.snowB[i] = clamp(smoothstep(44, 70, al) * 0.95 + smoothstep(0.55, 1, this.E[i]) * 0.65, 0, 1);
      }
    }
    // hill-shade from the elevation field, lit from the north-west
    const d = Math.max(1, Math.round(ppd * 0.35));
    for (let y = d; y < h - d; y++) {
      for (let x = d; x < w - d; x++) {
        const i = y * w + x;
        if (!this.land[i]) continue;
        const gx = this.E[i - d] - this.E[i + d];
        const gy = this.E[i - d * w] - this.E[i + d * w];
        this.shade[i] = clamp((gx + gy) * 1.25, -0.4, 0.4);
      }
    }
  }

  /**
   * Re-colour for a point in the year.
   * @param month 0..12 (fractional); 0 = 1 Jan
   * @param o     { mode:'sat'|'ndvi', dim, relief, snow }
   */
  paint(month, o = {}) {
    const mode = o.mode || 'sat', dim = o.dim ?? 1, relief = o.relief ?? 1, snowK = o.snow ?? 1;
    const sN = Math.cos((TAU * (month - 6.5)) / 12);
    const sS = Math.cos((TAU * (month - 0.5)) / 12);
    const { px, land, space, shelf, E, vb, amp, hemi, snowB, nz, shade, ice } = this;
    const N = this.w * this.h;
    const sat = mode === 'sat';
    const cov = this.cov;
    for (let i = 0; i < N; i++) {
      if (space[i]) { px[i] = 0xff000000; continue; }
      // ocean colour (always needed: it is the background of every land pixel's coverage)
      const t = shelf[i];
      let or, og, ob;
      if (sat) { or = 5 + 11 * t * t; og = 11 + 36 * t * t; ob = 27 + 52 * t * t; }
      else { or = 9; og = 13; ob = 38; }
      or *= dim; og *= dim; ob *= dim;
      let r = or, g = og, b = ob;
      if (land[i]) {
        const season = hemi[i] > 0 ? sN : sS;
        let veg = vb[i] + amp[i] * season;
        veg = veg < 0 ? 0 : veg > 1 ? 1 : veg;
        const li = ((veg * 255) | 0) * 3;
        let lr = VEG[li], lg = VEG[li + 1], lb = VEG[li + 2];
        const tex = (nz[i] - 0.5) * (sat ? 34 : 10);
        lr += tex * 0.8; lg += tex; lb += tex * 0.6;
        if (sat) {
          const rock = smoothstep(0.35, 1.0, E[i]) * 0.32 * relief;
          lr += (150 - lr) * rock; lg += (124 - lg) * rock; lb += (98 - lb) * rock;
          const winter = (1 - season) * 0.5;
          let sn = snowB[i] * (0.1 + 0.9 * winter) * snowK;
          if (ice[i]) sn = 1;
          sn = sn > 1 ? 1 : sn;
          lr += (228 - lr) * sn * 0.9; lg += (234 - lg) * sn * 0.9; lb += (244 - lb) * sn * 0.9;
          const L = 1 + shade[i] * relief * 0.9;
          lr *= L; lg *= L; lb *= L;
        } else if (ice[i]) { lr = 40; lg = 54; lb = 108; }
        lr *= dim; lg *= dim; lb *= dim;
        const c = cov[i];
        r = or + (lr - or) * c; g = og + (lg - og) * c; b = ob + (lb - ob) * c;
      }
      px[i] = 0xff000000 | ((b < 0 ? 0 : b > 255 ? 255 : b | 0) << 16) | ((g < 0 ? 0 : g > 255 ? 255 : g | 0) << 8) | (r < 0 ? 0 : r > 255 ? 255 : r | 0);
    }
    this.ctx.putImageData(this.img, 0, 0);
  }

  /** Resample a decoded EPSG:4326 image ({w,h,data}) covering bbox [lon0,lat0,lon1,lat1] onto this texture. Returns RGBA bytes. */
  resample(src, bbox, feather = 0) {
    const N = this.w * this.h, key = `${bbox.join(',')}|${src.w}x${src.h}|${feather}`;
    let m = this._maps.get(key);
    if (!m) {
      const [lon0, lat0, lon1, lat1] = bbox;
      m = { x0: new Int32Array(N), y0: new Int32Array(N), fx: new Float32Array(N), fy: new Float32Array(N), ok: new Uint8Array(N), f: new Float32Array(N).fill(1) };
      for (let i = 0; i < N; i++) {
        if (this.space[i]) continue;
        const lon = this.lon[i], lat = this.lat[i];
        if (lon < lon0 || lon > lon1 || lat < lat0 || lat > lat1) continue;
        const u = ((lon - lon0) / (lon1 - lon0)) * src.w - 0.5, v = ((lat1 - lat) / (lat1 - lat0)) * src.h - 0.5;
        const x0 = Math.floor(u), y0 = Math.floor(v);
        m.x0[i] = x0; m.y0[i] = y0; m.fx[i] = u - x0; m.fy[i] = v - y0; m.ok[i] = 1;
        if (feather > 0) {
          const e = Math.min(lon - lon0, lon1 - lon, lat - lat0, lat1 - lat) / feather;
          m.f[i] = e >= 1 ? 1 : e * e * (3 - 2 * e);
        }
      }
      this._maps.set(key, m);
    }
    const out = new Uint8ClampedArray(N * 4), d = src.data, W = src.w, H = src.h;
    const clx = (x) => (x < 0 ? 0 : x >= W ? W - 1 : x), cly = (y) => (y < 0 ? 0 : y >= H ? H - 1 : y);
    for (let i = 0; i < N; i++) {
      if (!m.ok[i]) continue;
      const xa = clx(m.x0[i]), xb = clx(m.x0[i] + 1), ya = cly(m.y0[i]), yb = cly(m.y0[i] + 1);
      const fx = m.fx[i], fy = m.fy[i];
      const w00 = (1 - fx) * (1 - fy), w10 = fx * (1 - fy), w01 = (1 - fx) * fy, w11 = fx * fy;
      const p00 = (ya * W + xa) * 4, p10 = (ya * W + xb) * 4, p01 = (yb * W + xa) * 4, p11 = (yb * W + xb) * 4;
      const a00 = d[p00 + 3] * w00, a10 = d[p10 + 3] * w10, a01 = d[p01 + 3] * w01, a11 = d[p11 + 3] * w11;
      const at = a00 + a10 + a01 + a11, o = i * 4;
      if (at < 1) continue;
      out[o] = (d[p00] * a00 + d[p10] * a10 + d[p01] * a01 + d[p11] * a11) / at;
      out[o + 1] = (d[p00 + 1] * a00 + d[p10 + 1] * a10 + d[p01 + 1] * a01 + d[p11 + 1] * a11) / at;
      out[o + 2] = (d[p00 + 2] * a00 + d[p10 + 2] * a10 + d[p01 + 2] * a01 + d[p11 + 2] * a11) / at;
      out[o + 3] = at * m.f[i];
    }
    return out;
  }

  /**
   * Paint from real imagery. base/over = { a, b, t } (RGBA arrays from resample(); b may equal a; t blends a to b).
   * `over` (optional) is composited on top using its own alpha. Ocean shows through any transparent pixel.
   */
  paintReal(base, over, dim = 1) {
    const N = this.w * this.h, px = this.px, space = this.space;
    const A = base.a, B = base.b || base.a, t = base.t || 0;
    const OA = over && over.a, OB = over && (over.b || over.a), ot = over ? over.t || 0 : 0;
    for (let i = 0; i < N; i++) {
      if (space[i]) { px[i] = 0xff000000; continue; }
      const j = i * 4;
      const al = (A[j + 3] + (B[j + 3] - A[j + 3]) * t) / 255;
      let r = 9 + (A[j] + (B[j] - A[j]) * t - 9) * al;
      let g = 13 + (A[j + 1] + (B[j + 1] - A[j + 1]) * t - 13) * al;
      let b = 38 + (A[j + 2] + (B[j + 2] - A[j + 2]) * t - 38) * al;
      if (OA) {
        const oal = (OA[j + 3] + (OB[j + 3] - OA[j + 3]) * ot) / 255;
        if (oal > 0.004) {
          r += (OA[j] + (OB[j] - OA[j]) * ot - r) * oal;
          g += (OA[j + 1] + (OB[j + 1] - OA[j + 1]) * ot - g) * oal;
          b += (OA[j + 2] + (OB[j + 2] - OA[j + 2]) * ot - b) * oal;
        }
      }
      r *= dim; g *= dim; b *= dim;
      px[i] = 0xff000000 | ((b > 255 ? 255 : b | 0) << 16) | ((g > 255 ? 255 : g | 0) << 8) | (r > 255 ? 255 : r | 0);
    }
    this.ctx.putImageData(this.img, 0, 0);
  }
}

export const VEG_CSS = `linear-gradient(90deg, rgb(${[0, 56, 112, 168, 224, 255].map((k) => `${VEG[k * 3]},${VEG[k * 3 + 1]},${VEG[k * 3 + 2]}`).join('), rgb(')}))`;
