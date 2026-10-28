// Page controller: boots data, builds chapters, wires scroll, runs one rAF loop.
import { getBasemap, getMeta, getTrack } from './api.js';
import { normalizeGeo } from './basemap.js';
import { Chapter } from './chapter.js';
import { Hero } from './hero.js';
import { GreenWave } from './greenwave.js';
import { VEG_CSS } from './satellite.js';
import { buildAnalysis } from './analysis.js';
import { el } from './util.js';
import { getImagery } from './imagery.js';

const OVERVIEW_STEPS = [
  { week: null, title: 'Seven journeys, one year',
    body: 'Every glow is a species. Scroll slowly and the map will stop on the moments that matter. Use the chips above to hide or show any of them, or drag the timeline to scrub through the year yourself.', labels: [] },
  { week: 1, title: 'January: everyone is south',
    body: 'In midwinter nearly every bird here sits in the tropics or the southern United States. North America is quiet.',
    labels: [
      { text: 'Central American forests', lon: -86, lat: 13, dx: -150, dy: 90 },
      { text: 'Amazon basin', lon: -66, lat: -4, dx: 120, dy: 50 },
    ] },
  { week: 16, title: 'April: the great northward flow',
    body: 'Spring departures overlap. In a few weeks tens of millions of birds funnel through Central America, across the Gulf and up the continent.',
    labels: [
      { text: 'Gulf of Mexico', lon: -90, lat: 25, dx: -140, dy: 80 },
      { text: 'Land bridge', lon: -83, lat: 9.5, dx: -150, dy: 70 },
    ] },
  { week: 26, title: 'July: spread thin across the north',
    body: 'On the breeding grounds the same birds occupy several times the area. The glow fades because each square kilometre holds fewer of them.',
    labels: [
      { text: 'Boreal forest', lon: -100, lat: 56, dx: -130, dy: -50 },
      { text: 'Pacific Northwest', lon: -122, lat: 46, dx: -150, dy: 30 },
    ] },
  { week: 37, title: 'September: the largest movement',
    body: 'Autumn brings young birds as well as adults, so more individuals travel than in spring. Different species take the coast, the mountains and the open ocean.',
    labels: [
      { text: 'Open Atlantic', lon: -62, lat: 30, dx: 90, dy: -50 },
      { text: 'Rocky Mountain route', lon: -108, lat: 38, dx: -120, dy: 30 },
    ] },
];

const OVERVIEW_VIEW = { center: [-92, 18], span: 80 };

async function boot() {
  const [meta, baseRaw, track, imagery] = await Promise.all([getMeta(), getBasemap(), getTrack(), getImagery()]);
  const geo = normalizeGeo(baseRaw);
  const shared = { grid: meta.grid, geo, imagery };

  const kinds = Object.values(meta.data.species);
  const nObs = kinds.filter((k) => k === 'observed').length;
  const foot = [meta.basemap_source === 'natural-earth' ? 'Coastlines: Natural Earth.' : 'Coastlines: simplified built-in outlines.'];
  if (imagery.available) foot.push(imagery.bluemarble?.attribution || imagery.goes?.attribution || 'Imagery: NASA GIBS.');
  if (nObs) foot.push(`Bird records: GBIF.org (includes eBird), ${nObs} of ${kinds.length} species.`);
  else foot.push('Bird data: modelled, not eBird.');
  document.getElementById('foot-source').textContent = foot.join(' ');
  if (nObs) {
    const c = meta.data.provenance._citation || '';
    const m = document.getElementById('method-obs');
    m.hidden = false;
    m.innerHTML = `<strong>Observed for ${nObs} of ${kinds.length} species.</strong> Brightness is the share of all bird records in each 3-degree cell and month that belong to the species, which corrects for where observers happen to be. ${c}`;
  }
  const hasTrack = track.source === 'movebank';
  const badge = (id, text, real) => { const n = document.getElementById(id); if (n) { n.textContent = text; n.classList.toggle('real', !!real); } };
  const sat = imagery.available && (imagery.goes || imagery.bluemarble);
  badge('hero-badge', `${sat ? 'Real satellite imagery (NASA GIBS)' : 'Illustrative satellite look'} · ${hasTrack ? 'Real GPS track (Movebank)' : 'Simulated route'}`, sat && hasTrack);
  if (!hasTrack) document.querySelector('#hero .caption .pre').textContent = 'An illustrative fall route of a';
  else document.querySelector('#hero .caption .pre').textContent = 'The fall migration of a tagged';
  badge('gw-badge', imagery.available && imagery.ndvi ? 'Real vegetation index (NASA MODIS NDVI)' : 'Modelled seasonal greenness', imagery.available && imagery.ndvi);
  if (imagery.available && imagery.ndvi) {
    document.getElementById('gw-note').textContent = 'Each frame is NASA satellite-measured vegetation greenness for that month. Watch the green climb the continent from March to July and drain away by November.';
    document.querySelector('.gw-legend').hidden = true;
  }

  // ---- hero: satellite-style scene with the hawk
  const globe = new Hero(document.getElementById('sat'), geo, track, {
    time: document.getElementById('tr-time'), km: document.getElementById('tr-km'), state: document.getElementById('tr-state'),
  }, imagery);

  // ---- green wave
  document.getElementById('gw-ramp').style.background = VEG_CSS;
  const gw = new GreenWave(document.getElementById('gw-canvas'), document.getElementById('gw-month'), document.getElementById('gw-hint'), geo, imagery);
  new IntersectionObserver(([e]) => { gw.visible = e.isIntersecting; }, { threshold: 0.05 }).observe(document.getElementById('greenwave'));

  // ---- chapters
  const chaptersHost = document.getElementById('chapters');
  const chapters = [];
  const overviewEl = document.getElementById('overview');
  chapters.push(new Chapter(overviewEl, {
    domId: 'overview', isOverview: true, title: 'The whole hemisphere', group: 'Seven migrants at once',
    color: '#e9edf5', view: OVERVIEW_VIEW, steps: OVERVIEW_STEPS, layerSpecies: meta.species,
    ariaLabel: 'Animated map of seven bird species moving across the Americas over one year', startWeek: 0,
  }, shared));

  meta.species.forEach((sp) => {
    sp.kind = meta.data.species[sp.id];
    sp.prov = meta.data.provenance[sp.id];
    const sec = el('section', { 'aria-label': sp.common });
    chaptersHost.append(sec);
    chapters.push(new Chapter(sec, {
      domId: sp.id, title: sp.common, latin: sp.latin, group: sp.group, color: sp.color, view: sp.view,
      steps: sp.steps, layerSpecies: [sp], startWeek: 0,
      ariaLabel: `Animated map of the ${sp.common} across one year: ${sp.tagline}`,
    }, shared));
  });

  // ---- rail navigation
  const rail = document.getElementById('rail');
  const railLinks = chapters.map((c) => {
    const a = el('a', { href: `#${c.cfg.domId}`, style: `--c:${c.cfg.isOverview ? '#e9edf5' : c.cfg.color}`, 'aria-label': c.cfg.title }, [el('span', { text: c.cfg.title })]);
    rail.append(a);
    return a;
  });

  // ---- lazy init + visibility
  const loadIO = new IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) e.target._chapter.init().catch(console.error); });
  }, { rootMargin: '120% 0px 120% 0px' });
  // A chapter is ~6 screens tall, so ask for any overlap (threshold 0), then
  // pick the "current" chapter for the rail from the scroll position instead.
  const seeIO = new IntersectionObserver((entries) => {
    entries.forEach((e) => { e.target._chapter.visible = e.isIntersecting; });
  }, { threshold: 0 });
  let railTick = false;
  const updateRail = () => {
    railTick = false;
    const mid = window.innerHeight * 0.5;
    let cur = -1;
    chapters.forEach((c, i) => { const r = c.root.getBoundingClientRect(); if (r.top <= mid && r.bottom > mid) cur = i; });
    railLinks.forEach((a, i) => a.classList.toggle('on', i === cur));
  };
  window.addEventListener('scroll', () => { if (!railTick) { railTick = true; requestAnimationFrame(updateRail); } }, { passive: true });
  updateRail();
  chapters.forEach((c) => { c.root._chapter = c; loadIO.observe(c.root); seeIO.observe(c.root); });

  // ---- scroll steps
  const stepIO = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      const c = e.target.closest('.chapter')._chapter;
      c.setStep(parseInt(e.target.dataset.i, 10));
    });
  }, { rootMargin: '-48% 0px -48% 0px' });
  document.querySelectorAll('.step').forEach((s) => stepIO.observe(s));

  // ---- header + hero visibility
  const mast = document.getElementById('masthead');
  const hero = document.getElementById('hero');
  new IntersectionObserver(([e]) => { globe.visible = e.isIntersecting; mast.classList.toggle('solid', !e.isIntersecting); }, { threshold: 0.12 }).observe(hero);
  let rt;
  window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => { globe.resize(); gw.resize(); }, 160); });

  // ---- single animation loop
  let last = performance.now();
  const loop = (now) => {
    const dt = Math.min(0.1, (now - last) / 1000); last = now;
    globe.tick(dt);
    gw.tick(dt);
    for (const c of chapters) if (c.visible) c.tick(dt);
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);

  buildAnalysis(meta).catch(console.error);
  window.__flyway = { chapters, globe, gw, meta };
}

boot().catch((err) => {
  console.error(err);
  document.getElementById('hero-title').textContent = 'The map could not load';
  document.querySelector('.lede').textContent = 'Start the Flask server with run.py and open the page from http://127.0.0.1:5000 so the data requests can reach it.';
});
