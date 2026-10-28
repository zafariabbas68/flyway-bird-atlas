// HUD: colour legend, in-transit sparkline, month scrubber, date readout, play button.
import { MONTHS, el, monthProgress, weekInfo } from './util.js';

export class Timeline {
  /**
   * @param opts {accent, rampCss, legendTitle, spark:number[], sparkMax, extra:(t)=>string[],
   *              onScrub(t), onToggle()}
   */
  constructor(opts) {
    this.opts = opts;
    this.t = 0;
    this.spark = el('canvas', { class: 'spark', 'aria-hidden': 'true' });
    this.range = el('input', {
      type: 'range', min: '0', max: '51.99', step: '0.01', value: '0',
      'aria-label': 'Week of the year',
    });
    this.range.addEventListener('input', () => opts.onScrub(parseFloat(this.range.value)));
    this.dateText = el('span', { text: 'Jan 1' });
    const NS = 'http://www.w3.org/2000/svg';
    this.ring = document.createElementNS(NS, 'svg');
    this.ring.setAttribute('viewBox', '0 0 28 28'); this.ring.setAttribute('class', 'ring'); this.ring.setAttribute('aria-hidden', 'true');
    const bg = document.createElementNS(NS, 'circle'); const fg = document.createElementNS(NS, 'circle');
    [bg, fg].forEach((c) => { c.setAttribute('cx', '14'); c.setAttribute('cy', '14'); c.setAttribute('r', '11'); c.setAttribute('fill', 'none'); c.setAttribute('stroke-width', '3'); });
    bg.setAttribute('stroke', 'rgba(233,237,245,0.2)');
    fg.setAttribute('stroke', 'currentColor'); fg.setAttribute('stroke-dasharray', '69.115'); fg.setAttribute('stroke-linecap', 'round');
    fg.setAttribute('transform', 'rotate(-90 14 14)');
    this.ringFg = fg; this.ring.append(bg, fg);
    this.date = el('div', { class: 'date' }, [this.ring, this.dateText]);
    this.sub1 = el('div', { class: 'sub' });
    this.sub2 = el('div', { class: 'sub' });
    this.btn = el('button', { class: 'playbtn', type: 'button', text: 'Pause' });
    this.btn.addEventListener('click', () => opts.onToggle());

    const months = el('div', { class: 'months', 'aria-hidden': 'true' }, MONTHS.map((m) => el('span', { text: m[0] })));
    const legend = el('div', { class: 'legend' }, [
      el('b', { text: opts.legendTitle || 'Relative abundance' }),
      el('div', { class: 'ramp', style: `background:${opts.rampCss}` }),
      el('div', { class: 'ends' }, [el('span', { text: 'Fewer birds' }), el('span', { text: 'More birds' })]),
    ]);
    const timeline = el('div', { class: 'timeline' }, [this.spark, el('div', { class: 'scrub' }, [this.range]), months]);
    const readout = el('div', { class: 'readout', 'aria-live': 'off' }, [this.date, this.sub1, this.sub2, this.btn]);
    this.root = el('div', { class: 'hud' }, [legend, timeline, readout]);
    this._ro = new ResizeObserver(() => this._sizeSpark());
    this._ro.observe(this.spark);
  }

  _sizeSpark() {
    const r = this.spark.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.spark.width = Math.max(10, Math.round(r.width * dpr));
    this.spark.height = Math.max(10, Math.round(r.height * dpr));
    this._drawSpark();
  }

  _drawSpark() {
    const c = this.spark, ctx = c.getContext('2d');
    const w = c.width, h = c.height, s = this.opts.spark || [];
    ctx.clearRect(0, 0, w, h);
    if (!s.length) return;
    const max = this.opts.sparkMax || Math.max(...s, 0.01);
    const xs = (i) => ((i + 0.5) / s.length) * w;
    ctx.beginPath(); ctx.moveTo(0, h);
    s.forEach((v, i) => ctx.lineTo(xs(i), h - (v / max) * (h - 3)));
    ctx.lineTo(w, h); ctx.closePath();
    ctx.fillStyle = this.opts.accent + '30'; ctx.fill();
    ctx.beginPath();
    s.forEach((v, i) => { const x = xs(i), y = h - (v / max) * (h - 3); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.strokeStyle = this.opts.accent; ctx.lineWidth = 1.4 * (w / this.spark.clientWidth || 1); ctx.stroke();
    const cx = (this.t / 52) * w;
    ctx.fillStyle = '#e9edf5'; ctx.fillRect(cx - 0.5, 0, Math.max(1, w / 400), h);
  }

  setTime(t) {
    this.t = t;
    const wk = Math.floor(t) % 52;
    const d = weekInfo(t);
    this.dateText.textContent = d.label;
    this.ringFg.setAttribute('stroke-dashoffset', String(69.115 * (1 - monthProgress(t))));
    this.sub1.textContent = `Week ${wk + 1} of 52`;
    const extra = this.opts.extra ? this.opts.extra(wk) : [];
    this.sub2.textContent = extra[0] || '';
    if (document.activeElement !== this.range) this.range.value = String(t);
    this._drawSpark();
  }

  setPlaying(p) { this.btn.textContent = p ? 'Pause' : 'Play the year'; }
}
