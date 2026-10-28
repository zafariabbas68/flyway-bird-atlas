// "The green wave": an animated, month-by-month vegetation map of the Americas.
// Click (or press the button) to pause. Modelled seasonal greenness, not satellite measurements.
import { SatelliteTexture } from './satellite.js';
import { MonthSet } from './imagery.js';

const NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

export class GreenWave {
  constructor(canvas, monthEl, hintBtn, layers, imagery) {
    this.ndviEntry = imagery && imagery.available && imagery.ndvi ? imagery.ndvi : null;
    this.canvas = canvas; this.monthEl = monthEl; this.hint = hintBtn; this.layers = layers;
    this.month = 6.0;
    this.paused = false;
    this.visible = false;
    this.acc = 0;
    this.hint.addEventListener('click', () => this.toggle());
    canvas.addEventListener('click', () => this.toggle());
    this.resize();
  }
  toggle() {
    this.paused = !this.paused;
    this.hint.textContent = this.paused ? 'Click map to play' : 'Click map to pause';
  }
  resize() {
    const r = this.canvas.getBoundingClientRect();
    if (r.width < 10 || r.height < 10) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    this.w = r.width; this.h = r.height;
    this.canvas.width = Math.round(r.width * dpr); this.canvas.height = Math.round(r.height * dpr);
    this.ctx = this.canvas.getContext('2d');
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const proj = d3.geoAzimuthalEquidistant().rotate([84, -8]).precision(0.3);
    proj.fitExtent([[this.w * 0.04, this.h * 0.03], [this.w * 0.96, this.h * 0.97]], {
      type: 'MultiPoint', coordinates: [[-166, 67], [-60, 72], [-34, -6], [-71, -56], [-97, 74]],
    });
    const tw = Math.min(720, Math.ceil(this.w * 0.8));
    const th = Math.ceil(this.h * (tw / this.w));
    this.tex = new SatelliteTexture(proj, tw, th, tw / this.w, this.layers);
    this.set = this.ndviEntry ? new MonthSet(this.tex, this.ndviEntry) : null;
    if (this.set) this.set.loadAll();
    this._paint();
  }
  get real() { return !!this.set; }
  _paint() {
    if (!this.tex) return;
    const pr = this.set ? this.set.pair(this.month) : null;
    if (pr) this.tex.paintReal(pr, null, 1);
    else this.tex.paint(this.month, { mode: 'ndvi', dim: 1 });
    this.ctx.imageSmoothingQuality = 'high';
    this.ctx.drawImage(this.tex.canvas, 0, 0, this.w, this.h);
    const name = NAMES[Math.floor(this.month) % 12];
    if (this.monthEl.textContent !== name) this.monthEl.textContent = name;
  }
  tick(dt) {
    if (!this.visible || this.paused) return;
    this.month = (this.month + dt * 0.8) % 12;
    this.acc += dt;
    if (this.acc > 0.05) { this.acc = 0; this._paint(); }
  }
}
