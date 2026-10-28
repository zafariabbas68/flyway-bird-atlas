// Opening scene: full-bleed satellite-style view with drifting clouds and a
// simulated Broad-winged Hawk drawn as a green line, with date and time.
import { clamp, fmtInt, lerp, prefersReducedMotion } from './util.js';
import { SatelliteTexture, drawCloudLayer, makeCloudTiles } from './satellite.js';
import { FrameSet, MonthSet } from './imagery.js';

const GREEN = '#46e27c';
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function subsolar(date) {
  const start = Date.UTC(date.getUTCFullYear(), 0, 0);
  const n = (date.getTime() - start) / 86400000;
  const decl = -23.44 * Math.cos(((2 * Math.PI) / 365) * (n + 10));
  const hours = date.getUTCHours() + date.getUTCMinutes() / 60;
  return [-15 * (hours - 12), decl];
}
const km = (a, b) => d3.geoDistance(a, b) * 6371.0088;

export class Hero {
  constructor(canvas, layers, track, out, imagery) {
    this.canvas = canvas;
    this.im = imagery && imagery.available ? imagery : null;
    this.goesEntry = this.im && this.im.goes && this.im.goes.frames && this.im.goes.frames.length > 3 ? this.im.goes : null;
    this.bmEntry = this.im && this.im.bluemarble && this.im.bluemarble.files ? this.im.bluemarble : null;
    this.realImagery = !!(this.goesEntry || this.bmEntry);
    this.u = 0;
    this.layers = layers;
    this.out = out;
    this.pts = track.points.map((p) => ({ ...p, time: new Date(p.t), ll: [p.lon, p.lat] }));
    this.t0 = this.t1 = 0;
    this.aligned = false;
    if (this.goesEntry) {
      this.t0 = Date.parse(this.goesEntry.frames[0].t);
      this.t1 = Date.parse(this.goesEntry.frames[this.goesEntry.frames.length - 1].t);
      if (track.source === 'movebank' && this.goesEntry.track_aligned) {
        const sub = this.pts.filter((p) => p.time >= this.t0 && p.time <= this.t1);
        if (sub.length > 3) { this.pts = sub; this.aligned = true; }
      }
    }
    this.cum = [0];
    for (let i = 1; i < this.pts.length; i++) this.cum.push(this.cum[i - 1] + km(this.pts[i - 1].ll, this.pts[i].ll));
    this.visible = true;
    this.hold = 0;
    this.reduced = prefersReducedMotion();
    this.f = this.reduced ? this.pts.length - 1 : 0;
    if (this.reduced) this.u = 1;
    this.clouds = makeCloudTiles(384);
    this.lastMonth = -99;
    this.clock = 0;
    this.resize();
  }

  resize() {
    const r = this.canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    this.w = r.width; this.h = r.height;
    this.canvas.width = Math.round(r.width * dpr);
    this.canvas.height = Math.round(r.height * dpr);
    this.ctx = this.canvas.getContext('2d');
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const coords = this.pts.map((p) => p.ll);
    const mobile = this.w < 820;
    if (this.goesEntry) {
      // Real satellite scene: plain lon/lat projection (what the GOES images are), scaled so the picture
      // covers the whole screen. Nothing sits underneath it, so there is no second layer to see.
      const [lon0, lat0, lon1, lat1] = this.goesEntry.bbox;
      const rc = d3.geoCentroid({ type: 'MultiPoint', coordinates: coords });
      let k = Math.max(this.w / (lon1 - lon0), this.h / (lat1 - lat0)); // pixels per degree, "cover"
      const ext = d3.geoBounds({ type: 'MultiPoint', coordinates: coords });
      const routeH = (ext[1][1] - ext[0][1]) * k;
      this.cover = routeH <= this.h * 0.92;       // otherwise zoom out a little and let the edges feather away
      if (!this.cover) k = (this.h * 0.8) / (ext[1][1] - ext[0][1]);
      const hw = this.w / k / 2, hh = this.h / k / 2;
      const clon = this.cover ? Math.min(Math.max(rc[0], lon0 + hw), lon1 - hw) : rc[0];
      const clat = this.cover ? Math.min(Math.max(rc[1] - (mobile ? 3 : 0), lat0 + hh), lat1 - hh) : rc[1];
      this.proj = d3.geoEquirectangular().scale((k * 180) / Math.PI).center([clon, clat]).translate([this.w / 2, this.h / 2]).precision(0.3);
    } else {
      const centre = d3.geoCentroid({ type: 'MultiPoint', coordinates: coords });
      const pad = mobile ? { t: 170, b: 230, l: 28, r: 28 } : { t: 110, b: 190, l: 90, r: 90 };
      this.proj = d3.geoAzimuthalEquidistant().rotate([-centre[0], -centre[1]]).precision(0.3);
      this.proj.fitExtent([[pad.l, pad.t], [this.w - pad.r, this.h - pad.b]], { type: 'MultiPoint', coordinates: coords });
    }

    const tw = this.goesEntry ? Math.min(1000, Math.ceil(this.w * 0.75)) : Math.min(900, Math.ceil(this.w * 0.62));
    const th = Math.ceil(this.h * (tw / this.w));
    this.tex = new SatelliteTexture(this.proj, tw, th, tw / this.w, this.layers);
    this.lastMonth = -99;
    this.lastKey = null;
    if (this.goes) this.goes.stop();
    // with real GOES frames there is no Blue Marble underlay: one picture, full screen
    this.bm = this.bmEntry && !this.goesEntry ? new MonthSet(this.tex, this.bmEntry) : null;
    this.goes = this.goesEntry ? new FrameSet(this.tex, this.goesEntry, this.cover ? 0 : 5) : null;
    this.draw();
  }

  get real() { return !!(this.bm || this.goes); }

  tick(dt) {
    if (!this.visible) return;
    this.clock += dt;
    if (this.real && this.goesEntry) {
      if (!this.reduced) {
        if (this.hold > 0) { this.hold -= dt; if (this.hold <= 0) this.u = 0; }
        else { this.u += dt / 26; if (this.u >= 1) { this.u = 1; this.hold = 3.5; } }
      }
      this._syncF();
    } else if (!this.reduced) {
      const n = this.pts.length;
      if (this.hold > 0) {
        this.hold -= dt;
        if (this.hold <= 0) this.f = 0;
      } else {
        this.f += dt * 9;
        if (this.f >= n - 1) { this.f = n - 1; this.hold = 3.5; }
      }
    }
    this.draw();
  }

  _syncF() {
    const n = this.pts.length, ms = this.t0 + this.u * (this.t1 - this.t0);
    this.clockMs = ms;
    if (!this.aligned) { this.f = this.u * (n - 1); return; }
    let i = 0;
    while (i < n - 1 && this.pts[i + 1].time.getTime() <= ms) i++;
    const a = this.pts[i].time.getTime(), b = this.pts[Math.min(i + 1, n - 1)].time.getTime();
    this.f = i + (b > a ? clamp((ms - a) / (b - a), 0, 1) : 0);
  }

  state() {
    const n = this.pts.length;
    const i = clamp(Math.floor(this.f), 0, n - 2);
    const a = this.f - i;
    const p0 = this.pts[i], p1 = this.pts[Math.min(i + 1, n - 1)];
    const ll = d3.geoInterpolate(p0.ll, p1.ll)(a);
    const time = this.real && this.goesEntry ? new Date(this.clockMs ?? this.t0) : new Date(lerp(p0.time.getTime(), p1.time.getTime(), a));
    return { i, ll, time, dist: lerp(this.cum[i], this.cum[Math.min(i + 1, n - 1)], a), moving: km(p0.ll, p1.ll) > 4 };
  }

  draw() {
    const ctx = this.ctx, { w, h } = this;
    const s = this.state();
    const month = s.time.getUTCMonth() + (s.time.getUTCDate() - 1) / 30;
    let realPainted = false;
    if (this.real) {
      const key = `${Math.round(s.time.getTime() / 1500000)}|${this.goes ? this.goes.loaded : 0}|${this.bm ? this.bm.loaded : 0}`;
      const base = this.bm ? this.bm.pair(month + 0.5 - 0.5) : null;
      const over = this.goes ? this.goes.at(s.time.getTime()) : null;
      if (base || over) {
        realPainted = true;
        if (key !== this.lastKey) { this.lastKey = key; this.tex.paintReal(base || over, base ? over : null, this.goesEntry ? 1.0 : 0.95); }
      }
    }
    if (!realPainted && Math.abs(month - this.lastMonth) > 0.02) {
      this.tex.paint(month, { mode: 'sat', dim: 0.92, relief: 1 });
      this.lastMonth = month;
    }
    ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(this.tex.canvas, 0, 0, w, h);
    const path = d3.geoPath(this.proj, ctx);

    // national borders, very faint
    if (!realPainted) {
      ctx.beginPath(); this.layers.borders.forEach((f) => path(f));
      ctx.strokeStyle = 'rgba(255,255,255,0.2)'; ctx.lineWidth = 0.8; ctx.stroke();
    }

    // clouds with shadows (procedural only; real imagery already has real clouds)
    const t = this.clock;
    if (!realPainted) {
    const { cloud, shadow } = this.clouds;
    drawCloudLayer(ctx, shadow, w, h, 2.1, t * 7 + 10, t * 3 + 8, 0.9);
    drawCloudLayer(ctx, cloud, w, h, 2.1, t * 7, t * 3, 0.78);
    drawCloudLayer(ctx, cloud, w, h, 1.2, -t * 4, t * 5, 0.38);

    // night side: stacked rings give a soft twilight edge
    const sun = subsolar(s.time);
    const anti = [sun[0] + 180, -sun[1]];
    for (const [rad, al] of [[90, 0.2], [86, 0.12], [82, 0.1], [78, 0.08], [72, 0.07]]) {
      ctx.beginPath(); path(d3.geoCircle().center(anti).radius(rad)());
      ctx.fillStyle = `rgba(2,5,14,${al})`; ctx.fill();
    }
    }

    // route so far
    const proj = this.proj;
    const pts = this.pts.slice(0, s.i + 1).map((p) => proj(p.ll));
    pts.push(proj(s.ll));
    if (pts.length > 1) {
      const line = d3.line().curve(d3.curveCatmullRom.alpha(0.5)).context(ctx);
      ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      ctx.save();
      ctx.shadowColor = 'rgba(70,226,124,0.7)'; ctx.shadowBlur = 14;
      ctx.beginPath(); line(pts); ctx.strokeStyle = GREEN; ctx.lineWidth = 4; ctx.stroke();
      ctx.restore();
    }
    const o = proj(this.pts[0].ll);
    ctx.beginPath(); ctx.arc(o[0], o[1], 4, 0, 7); ctx.fillStyle = '#fff'; ctx.fill();
    const p = proj(s.ll);
    const pulse = 9 + 4 * Math.sin(this.clock * 4);
    ctx.beginPath(); ctx.arc(p[0], p[1], pulse + 6, 0, 7); ctx.fillStyle = 'rgba(70,226,124,0.2)'; ctx.fill();
    ctx.beginPath(); ctx.arc(p[0], p[1], 6.5, 0, 7); ctx.fillStyle = GREEN; ctx.fill();
    ctx.lineWidth = 2; ctx.strokeStyle = '#fff'; ctx.stroke();

    // edge vignette
    const vg = ctx.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.35, w / 2, h / 2, Math.max(w, h) * 0.78);
    vg.addColorStop(0, 'rgba(2,5,12,0)'); vg.addColorStop(1, 'rgba(2,5,12,0.62)');
    ctx.fillStyle = vg; ctx.fillRect(0, 0, w, h);

    this._readout(s);
  }

  _readout(s) {
    const o = this.out;
    // show local solar time at the bird, like a clock on the ground below it
    const local = new Date(s.time.getTime() + (s.ll[0] / 15) * 3600000);
    let hr = local.getUTCHours();
    const ampm = hr >= 12 ? 'p.m.' : 'a.m.';
    hr = hr % 12 || 12;
    const mm = String(local.getUTCMinutes()).padStart(2, '0');
    if (o.time) o.time.textContent = `${MON[local.getUTCMonth()]} ${local.getUTCDate()}, ${local.getUTCFullYear()} ${hr}:${mm} ${ampm}`;
    if (o.km) o.km.textContent = `${fmtInt(s.dist)} km flown`;
    if (o.state) {
      const h24 = local.getUTCHours();
      const day = h24 >= 8 && h24 <= 17;
      o.state.textContent = s.moving ? 'riding thermals' : day ? 'resting' : 'roosting for the night';
    }
  }
}
