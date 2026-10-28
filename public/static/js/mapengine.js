// MapEngine: one sticky map. Paints a basemap once per resize and animated
// abundance layers every frame by inverting the projection for each pixel.
import { drawBase } from './basemap.js';
import { SatelliteTexture } from './satellite.js';
import { MonthSet } from './imagery.js';
import { clamp, hexToRgb, smoothstep, mod } from './util.js';

/** 256-step colour ramp for one species, packed as little-endian RGBA uint32. */
export function buildRamp(hex, gain = 1) {
  const [r, g, b] = hexToRgb(hex);
  const lut = new Uint32Array(256);
  const css = [];
  for (let i = 0; i < 256; i++) {
    const t = i / 255;
    const m1 = smoothstep(0.08, 0.5, t);
    const m2 = smoothstep(0.62, 1.0, t) * 0.9 * gain;
    let rr = r * (0.3 + 0.7 * m1), gg = g * (0.3 + 0.7 * m1), bb = b * (0.3 + 0.7 * m1);
    rr += (255 - rr) * m2 * (0.55 + 0.45 * (r / 255));
    gg += (255 - gg) * m2 * (0.55 + 0.45 * (g / 255));
    bb += (255 - bb) * m2 * (0.55 + 0.45 * (b / 255));
    const a = smoothstep(0.012, 0.22, t) * (0.55 + 0.45 * smoothstep(0.2, 0.7, t)) * gain;
    const A = Math.round(a * 255);
    lut[i] = (A << 24) | (Math.round(bb) << 16) | (Math.round(gg) << 8) | Math.round(rr);
    if (i % 32 === 0 || i === 255) css.push(`rgba(${Math.round(rr)},${Math.round(gg)},${Math.round(bb)},${a.toFixed(2)}) ${(t * 100).toFixed(0)}%`);
  }
  return { lut, css: `linear-gradient(90deg, ${css.join(',')})` };
}

export class MapEngine {
  /**
   * @param host    element that will contain the canvases
   * @param opts    { view:{center,span}, grid, geo, layers:[{id,color,frames}], offset:{x,y} }
   */
  constructor(host, opts) {
    this.host = host;
    this.grid = opts.grid;
    this.geo = opts.geo;
    this.view = opts.view;
    this.offset = opts.offset || { x: 0.62, y: 0.5 };
    this.mobileOffset = opts.mobileOffset || { x: 0.5, y: 0.4 };
    this.layers = opts.layers.map((l) => {
      const { lut } = buildRamp(l.color, opts.gain ?? 1);
      const cells = this.grid.width * this.grid.height;
      return { id: l.id, color: l.color, frames: l.frames, lut, cur: new Float32Array(cells), visible: true, off: document.createElement('canvas') };
    });
    this.base = document.createElement('canvas');
    this.heat = document.createElement('canvas');
    this.heat.className = 'heat';
    this.base.setAttribute('aria-hidden', 'true');
    this.heat.setAttribute('aria-hidden', 'true');
    host.append(this.base, this.heat);
    this.projection = null;
    this.t = 0;
    this.w = 0; this.h = 0;
    this.lookup = null;
    this.useSat = !!opts.sat;
    this.bmEntry = opts.imagery && opts.imagery.available && opts.imagery.bluemarble ? opts.imagery.bluemarble : null;
    this.satDim = opts.satDim ?? 0.55;
    this.sat = null;
    this.lastSatMonth = -99;
    this.onResize = null;
  }

  resize() {
    const r = this.host.getBoundingClientRect();
    if (r.width < 10 || r.height < 10) return false;
    const w = r.width, h = r.height;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const mobile = w < 820;
    const off = mobile ? this.mobileOffset : this.offset;
    const spanRad = (this.view.span * Math.PI) / 180;
    const radius = (Math.min(w, h) / 2) * (mobile ? 1.18 : 1.0);
    const proj = d3.geoAzimuthalEquidistant()
      .rotate([-this.view.center[0], -this.view.center[1]])
      .scale(radius / spanRad)
      .translate([w * off.x, h * off.y])
      .precision(0.3);
    this.projection = proj;
    this.w = w; this.h = h;
    this.host.style.setProperty('--mx', `${off.x * 100}%`);
    this.host.style.setProperty('--my', `${off.y * 100}%`);
    drawBase(this.base, proj, this.geo, w, h, dpr, this.useSat);
    this._buildLookup();
    this.render();
    if (this.onResize) this.onResize(this);
    return true;
  }

  /** Per internal pixel: grid cell + fractions for bilinear sampling. */
  _buildLookup() {
    const { width: GW, height: GH, lon_min, lat_max, res } = this.grid;
    const s = Math.min(0.5, 700 / this.w);
    const iw = Math.max(2, Math.ceil(this.w * s));
    const ih = Math.max(2, Math.ceil(this.h * s));
    const n = iw * ih;
    const idx = new Int32Array(n).fill(-1);
    const fx = new Float32Array(n);
    const fy = new Float32Array(n);
    const inv = this.projection.invert;
    const p = [0, 0];
    for (let y = 0; y < ih; y++) {
      for (let x = 0; x < iw; x++) {
        p[0] = (x + 0.5) / s; p[1] = (y + 0.5) / s;
        const ll = inv(p);
        if (!ll || !isFinite(ll[0]) || !isFinite(ll[1])) continue;
        const gx = (ll[0] - lon_min) / res - 0.5;
        const gy = (lat_max - ll[1]) / res - 0.5;
        if (gx < 0 || gy < 0 || gx >= GW - 1 || gy >= GH - 1) continue;
        const i0 = Math.floor(gx), j0 = Math.floor(gy);
        const k = y * iw + x;
        idx[k] = j0 * GW + i0; fx[k] = gx - i0; fy[k] = gy - j0;
      }
    }
    this.lookup = { iw, ih, idx, fx, fy };
    if (this.useSat) {
      if (this.sat) this.sat.canvas.remove();
      this.sat = new SatelliteTexture(this.projection, iw, ih, s, this.geo);
      this.sat.canvas.className = 'satimg';
      this.sat.canvas.setAttribute('aria-hidden', 'true');
      this.host.insertBefore(this.sat.canvas, this.base);
      this.bm = this.bmEntry ? new MonthSet(this.sat, this.bmEntry) : null;
      if (this.bm) this.bm.loadAll();
      this.lastSatMonth = -99;
    }
    this.heat.width = iw; this.heat.height = ih;
    for (const l of this.layers) {
      l.off.width = iw; l.off.height = ih;
      l.img = new ImageData(iw, ih);
      l.px = new Uint32Array(l.img.data.buffer);
    }
  }

  project(lonlat) { return this.projection ? this.projection(lonlat) : [0, 0]; }

  setLayerVisible(id, visible) {
    const l = this.layers.find((x) => x.id === id);
    if (l) { l.visible = visible; this.render(); }
  }

  setTime(t) { this.t = mod(t, this.grid.weeks); this.render(); }

  _paintSat() {
    if (!this.sat) return;
    const month = (this.t / this.grid.weeks) * 12;
    const loaded = this.bm ? this.bm.loaded : 0;
    if (Math.abs(month - this.lastSatMonth) < 0.045 && loaded === this.lastLoaded) return;
    this.lastSatMonth = month; this.lastLoaded = loaded;
    const pr = this.bm ? this.bm.pair(month) : null;
    if (pr) { this.sat.paintReal(pr, null, this.satDim * 1.35); return; }
    this.sat.paint(month, { mode: 'sat', dim: this.satDim, relief: 1 });
  }

  render() {
    if (!this.lookup) return;
    this._paintSat();
    const { iw, ih, idx, fx, fy } = this.lookup;
    const { width: GW, height: GH, weeks } = this.grid;
    const cells = GW * GH;
    const w0 = Math.floor(this.t) % weeks;
    const w1 = (w0 + 1) % weeks;
    const a = this.t - Math.floor(this.t);
    const hctx = this.heat.getContext('2d');
    hctx.globalCompositeOperation = 'source-over';
    hctx.clearRect(0, 0, iw, ih);

    for (const l of this.layers) {
      if (!l.visible) continue;
      const f0 = l.frames.subarray(w0 * cells, (w0 + 1) * cells);
      const f1 = l.frames.subarray(w1 * cells, (w1 + 1) * cells);
      const cur = l.cur;
      for (let i = 0; i < cells; i++) cur[i] = f0[i] + (f1[i] - f0[i]) * a;
      const px = l.px, lut = l.lut;
      for (let k = 0; k < px.length; k++) {
        const i = idx[k];
        if (i < 0) { px[k] = 0; continue; }
        const u = fx[k], v = fy[k];
        const top = cur[i] + (cur[i + 1] - cur[i]) * u;
        const bot = cur[i + GW] + (cur[i + GW + 1] - cur[i + GW]) * u;
        const val = top + (bot - top) * v;
        px[k] = lut[val < 0 ? 0 : val > 255 ? 255 : val | 0];
      }
      l.off.getContext('2d').putImageData(l.img, 0, 0);
      hctx.globalCompositeOperation = 'lighter';
      hctx.drawImage(l.off, 0, 0);
    }
  }
}
