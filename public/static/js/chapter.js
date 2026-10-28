// A Chapter = sticky map + scroll steps + HUD. Used for each species and for the overview.
import { getAnalysis, getFrames } from './api.js';
import { MapEngine, buildRamp } from './mapengine.js';
import { Timeline } from './timeline.js';
import { clamp, easeInOut, el, fmtLat, mod, prefersReducedMotion, weekInfo } from './util.js';

const SVG_NS = 'http://www.w3.org/2000/svg';
const LOOP_SPEED = 1.7; // weeks per second while playing

export class Chapter {
  /**
   * cfg: { id, title, latin, group, color, view, steps, species:[meta...] (layers), isOverview }
   */
  constructor(root, cfg, shared) {
    this.root = root;
    this.cfg = cfg;
    this.shared = shared; // {grid, geo}
    this.visible = false;
    this.ready = false;
    this.t = cfg.startWeek ?? 0;
    this.playing = !prefersReducedMotion();
    this.tween = null;
    this.stepIndex = -1;
    this.pendingStep = 0;
    this.lastRendered = -1;
    this._build();
  }

  // ------------------------------------------------------------------ DOM
  _build() {
    const { cfg, root } = this;
    root.style.setProperty('--accent', cfg.color);
    root.id = cfg.domId;
    root.classList.add('chapter');

    this.mapwrap = el('div', { class: 'mapwrap', role: 'img', 'aria-label': cfg.ariaLabel });
    this.leaders = document.createElementNS(SVG_NS, 'svg');
    this.leaders.setAttribute('class', 'leaders');
    this.leaders.setAttribute('aria-hidden', 'true');
    this.labelLayer = el('div', { class: 'labels', 'aria-hidden': 'true' });
    this.hudHost = el('div');
    const title = el('header', { class: 'chapter-title' }, [
      el('p', { class: 'group', text: cfg.group }),
      el('h2', { text: cfg.title }),
      cfg.latin ? el('p', { class: 'latin', text: cfg.latin }) : null,
    ]);
    this.chips = cfg.isOverview ? el('div', { class: 'chips', role: 'group', 'aria-label': 'Show or hide species' }) : null;
    this.loading = el('p', { class: 'small', style: 'position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);z-index:4', text: 'Loading the weekly maps...' });
    this.stage = el('div', { class: 'stage' }, [this.mapwrap, this.leaders, this.labelLayer, title, this.chips, this.hudHost, this.loading]);

    this.stepsWrap = el('div', { class: 'steps' });
    this.stepEls = cfg.steps.map((s, i) => {
      const when = s.week == null ? 'Playing the full year' : `Showing ${weekInfo(s.week + 0.5).label}`;
      const art = el('article', { class: 'step', 'data-i': String(i) }, [
        el('div', { class: 'card' }, [
          el('h3', { text: s.title }),
          el('p', { text: s.body }),
          el('span', { class: 'when', text: when }),
        ]),
      ]);
      this.stepsWrap.append(art);
      return art;
    });
    this.root.replaceChildren(this.stage, this.stepsWrap);
  }

  // ----------------------------------------------------------------- init
  async init() {
    if (this.ready || this.initializing) return;
    this.initializing = true;
    const { cfg } = this;
    const speciesIds = cfg.layerSpecies.map((s) => s.id);
    const [frames, analyses] = await Promise.all([
      Promise.all(speciesIds.map((id) => getFrames(id))),
      Promise.all(speciesIds.map((id) => getAnalysis(id))),
    ]);
    const layers = cfg.layerSpecies.map((s, i) => ({ id: s.id, color: s.color, frames: frames[i] }));
    this.engine = new MapEngine(this.mapwrap, {
      view: cfg.view, grid: this.shared.grid, geo: this.shared.geo, layers,
      offset: cfg.isOverview ? { x: 0.6, y: 0.52 } : { x: 0.64, y: 0.52 },
      gain: cfg.isOverview ? 0.5 : 1,
      imagery: this.shared.imagery, sat: true, satDim: cfg.isOverview ? 0.5 : 0.58,
    });
    this.analyses = analyses;
    const allObs = analyses.every((a) => a.kind === 'observed'), anyObs = analyses.some((a) => a.kind === 'observed');
    const bd = this.root.querySelector('.chapter-title') || null;
    if (bd) bd.append(el('p', { class: `badge chapter-badge${allObs ? ' real' : ''}`,
      text: allObs ? 'Observed: GBIF / eBird records' : anyObs ? 'Mixed: observed and modelled' : 'Modelled, not measured' }));

    // Sparkline = share of birds in transit (average across layers for the overview)
    const spark = new Array(52).fill(0).map((_, w) => analyses.reduce((s, a) => s + a.moving_share[w], 0) / analyses.length);
    const ramp = cfg.isOverview ? 'linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,0.9))' : buildRamp(cfg.color).css;
    this.timeline = new Timeline({
      accent: cfg.color, rampCss: ramp, spark, sparkMax: 1,
      legendTitle: allObs ? 'Share of bird records' : cfg.isOverview ? 'Brighter means more birds' : 'Relative abundance',
      extra: (wk) => {
        if (cfg.isOverview) return [`${Math.round(spark[wk] * 100)}% of birds on the move`];
        const a = analyses[0];
        return [`${Math.round(a.moving_share[wk] * 100)}% ${a.kind === 'observed' ? 'weekly change' : 'on the move'}, centre ${fmtLat(a.centroid_lat[wk])}`];
      },
      onScrub: (t) => this._userScrub(t),
      onToggle: () => this._userToggle(),
    });
    this.hudHost.replaceWith(this.timeline.root);
    this.timeline.setPlaying(this.playing);

    if (this.chips) this._buildChips();
    this._buildLabels();
    this.engine.onResize = () => this._positionLabels();
    this.ro = new ResizeObserver(() => { clearTimeout(this._rt); this._rt = setTimeout(() => this.engine.resize(), 80); });
    this.ro.observe(this.mapwrap);
    this.engine.resize();
    this.loading.remove();
    this.ready = true;
    this.setStep(this.pendingStep);
    this._apply(true);
  }

  _buildChips() {
    this.cfg.layerSpecies.forEach((s) => {
      const b = el('button', { class: 'chip', type: 'button', 'aria-pressed': 'true', style: `--c:${s.color}`, text: s.common });
      b.addEventListener('click', () => {
        const on = b.getAttribute('aria-pressed') !== 'true';
        b.setAttribute('aria-pressed', String(on));
        this.engine.setLayerVisible(s.id, on);
      });
      this.chips.append(b);
    });
  }

  // --------------------------------------------------------------- labels
  _buildLabels() {
    this.labelItems = [];
    this.cfg.steps.forEach((s, si) => {
      (s.labels || []).forEach((l) => {
        const g = document.createElementNS(SVG_NS, 'g');
        const line = document.createElementNS(SVG_NS, 'line');
        const dot = document.createElementNS(SVG_NS, 'circle');
        dot.setAttribute('r', '3');
        g.append(line, dot);
        this.leaders.append(g);
        const div = el('div', { class: 'maplabel', text: l.text });
        this.labelLayer.append(div);
        this.labelItems.push({ step: si, l, g, line, dot, div });
      });
    });
  }

  _positionLabels() {
    if (!this.labelItems) return;
    const W = this.engine.w;
    const mobile = W < 820;
    const k = clamp(W / 1200, 0.55, 1);
    const minY = mobile ? 150 : 90;
    for (const it of this.labelItems) {
      const [ax, ay] = this.engine.project([it.l.lon, it.l.lat]);
      const left = it.l.dx < 0;
      let ex = ax + it.l.dx * k;
      const ey = Math.max(minY, ay + it.l.dy * k);
      // keep the text box fully on screen
      const lw = it.div.offsetWidth || 120;
      if (left) { const edge = ex - 7 - lw; if (edge < 10) ex += 10 - edge; }
      else { const edge = ex + 7 + lw; if (edge > W - 10) ex -= edge - (W - 10); }
      const len = Math.hypot(ex - ax, ey - ay);
      it.line.setAttribute('x1', ax); it.line.setAttribute('y1', ay);
      it.line.setAttribute('x2', ex); it.line.setAttribute('y2', ey);
      it.dot.setAttribute('cx', ax); it.dot.setAttribute('cy', ay);
      it.g.style.setProperty('--len', len.toFixed(1));
      it.line.style.setProperty('--len', len.toFixed(1));
      it.div.style.left = `${ex + (left ? -7 : 7)}px`;
      it.div.style.top = `${ey}px`;
      it.div.style.transform = `translate(${left ? '-100%' : '0'}, -50%)`;
      it.div.style.textAlign = left ? 'right' : 'left';
    }
  }

  _showLabels(step) {
    if (!this.labelItems) return;
    for (const it of this.labelItems) {
      const on = it.step === step;
      it.g.classList.toggle('on', on);
      it.div.classList.toggle('on', on);
    }
  }

  // ---------------------------------------------------------------- steps
  setStep(i) {
    this.pendingStep = i;
    this.stepEls.forEach((e, k) => e.classList.toggle('active', k === i));
    if (!this.ready || i === this.stepIndex) return;
    this.stepIndex = i;
    const step = this.cfg.steps[i];
    this._showLabels(-1);
    if (step.week == null) {
      this.tween = null;
      this.playing = !prefersReducedMotion();
    } else {
      this.playing = false;
      this._startTween(step.week + 0.5, i);
    }
    this.timeline.setPlaying(this.playing);
  }

  _startTween(to, stepIdx) {
    const delta = mod(to - this.t, 52);
    if (delta < 0.15 || prefersReducedMotion()) {
      this.t = to; this.tween = null; this._apply(true); this._showLabels(stepIdx); return;
    }
    this.tween = { from: this.t, delta, dur: clamp(0.8 + delta * 0.07, 1.0, 3.4), el: 0, step: stepIdx };
  }

  _userScrub(t) {
    this.playing = false; this.tween = null; this.t = t;
    this.timeline.setPlaying(false);
    this._showLabels(-1);
    this._apply(true);
  }

  _userToggle() {
    this.tween = null;
    this.playing = !this.playing;
    if (this.playing) this._showLabels(-1);
    this.timeline.setPlaying(this.playing);
  }

  // ----------------------------------------------------------------- loop
  tick(dt) {
    if (!this.ready) return;
    if (this.tween) {
      const tw = this.tween;
      tw.el += dt;
      const p = clamp(tw.el / tw.dur, 0, 1);
      this.t = mod(tw.from + tw.delta * easeInOut(p), 52);
      if (p >= 1) { this.tween = null; this._showLabels(tw.step); }
    } else if (this.playing) {
      this.t = mod(this.t + dt * LOOP_SPEED, 52);
    }
    this._apply(false);
  }

  _apply(force) {
    if (!this.engine) return;
    const q = Math.round(this.t * 40);
    if (!force && q === this.lastRendered) return;
    this.lastRendered = q;
    this.engine.setTime(this.t);
    this.timeline.setTime(this.t);
  }
}
