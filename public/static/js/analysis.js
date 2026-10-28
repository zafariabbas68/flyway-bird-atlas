// Comparison panels: ledger bars, latitude-by-week heat panels, in-transit lines.
import { getAnalysis, getCompare } from './api.js';
import { MONTHS, el, fmtInt, hexToRgb, weekInfo } from './util.js';

export async function buildAnalysis(meta) {
  const [rows, analyses] = await Promise.all([getCompare(), Promise.all(meta.species.map((s) => getAnalysis(s.id)))]);
  buildLedger(rows);
  buildHov(meta, analyses);
  buildTransit(meta, analyses);
}

function buildLedger(rows) {
  const host = document.getElementById('ledger');
  const sorted = [...rows].sort((a, b) => b.summary.spring_route_km - a.summary.spring_route_km);
  const max = Math.max(...sorted.map((r) => r.summary.spring_route_km));
  sorted.forEach((r) => {
    const w = (r.summary.spring_route_km / max) * 78;
    const s = r.summary;
    host.append(el('div', { class: 'lrow', style: `--c:${r.color}` }, [
      el('div', { class: 'nm' }, [document.createTextNode(r.common), el('small', { text: r.strategy })]),
      el('div', { class: 'bar', role: 'img', 'aria-label': `${r.common}: about ${fmtInt(s.spring_route_km)} kilometres` }, [
        el('i', { style: `width:${w}%` }),
        el('span', { style: `--w:${w}%`, text: `${fmtInt(s.spring_route_km)} km` }),
      ]),
      el('div', { class: 'meta', html: `${s.spring_days} days<br>${s.spring_speed_km_day} km a day` }),
    ]));
  });
}

function buildHov(meta, analyses) {
  const host = document.getElementById('hovmoller');
  meta.species.forEach((sp, k) => {
    const a = analyses[k];
    const hv = a.hovmoller;
    const bands = hv.values[0].length;
    const [r, g, b] = hexToRgb(sp.color);
    let max = 0;
    hv.values.forEach((row) => row.forEach((v) => { if (v > max) max = v; }));

    const W = 624, H = 320, padL = 70, padB = 34, padT = 8, padR = 8;
    const cw = W - padL - padR, ch = H - padB - padT;
    const cvs = el('canvas', { 'aria-label': `${sp.common}: latitude of the population by week`, role: 'img' });
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    cvs.width = W * dpr; cvs.height = H * dpr;
    cvs.style.aspectRatio = `${W} / ${H}`;
    const ctx = cvs.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.fillStyle = '#060a12'; ctx.fillRect(0, 0, W, H);

    const off = document.createElement('canvas');
    off.width = 52; off.height = bands;
    const octx = off.getContext('2d');
    const img = octx.createImageData(52, bands);
    for (let w = 0; w < 52; w++) for (let j = 0; j < bands; j++) {
      const v = Math.sqrt(hv.values[w][j] / max);
      const row = bands - 1 - j; // north at top
      const i = (row * 52 + w) * 4;
      const m = Math.min(1, v * 1.15);
      img.data[i] = r * (0.35 + 0.65 * m) + (255 - r) * Math.max(0, m - 0.7);
      img.data[i + 1] = g * (0.35 + 0.65 * m) + (255 - g) * Math.max(0, m - 0.7);
      img.data[i + 2] = b * (0.35 + 0.65 * m) + (255 - b) * Math.max(0, m - 0.7);
      img.data[i + 3] = Math.min(255, v * 330);
    }
    octx.putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = true; ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(off, padL, padT, cw, ch);

    // axes
    ctx.fillStyle = '#8d99b1'; ctx.font = '18px "IBM Plex Sans", system-ui, sans-serif'; ctx.textAlign = 'right'; ctx.textBaseline = 'middle';
    const yOf = (lat) => padT + ((hv.lat_max - lat) / (hv.lat_max - hv.lat_min)) * ch;
    [60, 40, 20, 0, -20].forEach((lat) => {
      const y = yOf(lat);
      ctx.strokeStyle = lat === 0 ? 'rgba(233,237,245,0.28)' : 'rgba(233,237,245,0.09)'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
      ctx.fillText(lat === 0 ? '0°' : `${Math.abs(lat)}°${lat > 0 ? 'N' : 'S'}`, padL - 6, y);
    });
    ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    MONTHS.forEach((m, i) => ctx.fillText(m[0], padL + ((i + 0.5) / 12) * cw, H - padB + 8));

    // centroid line
    ctx.beginPath();
    a.centroid_lat.forEach((lat, w) => { const x = padL + ((w + 0.5) / 52) * cw, y = yOf(lat); w ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.strokeStyle = 'rgba(255,255,255,0.9)'; ctx.lineWidth = 1.5; ctx.stroke();

    const tip = el('div', { class: 'tip' });
    const box = el('div', { class: 'hov', style: `--c:${sp.color}` }, [el('h4', { text: sp.common }), cvs, tip]);
    cvs.addEventListener('pointermove', (e) => {
      const rc = cvs.getBoundingClientRect();
      const x = ((e.clientX - rc.left) / rc.width) * W, y = ((e.clientY - rc.top) / rc.height) * H;
      const w = Math.floor(((x - padL) / cw) * 52), j = Math.floor(((H - padB - y) / ch) * bands);
      if (w < 0 || w > 51 || j < 0 || j >= bands) { tip.style.opacity = 0; return; }
      const lat0 = hv.lat_min + j * hv.band_deg;
      tip.textContent = `${weekInfo(w + 0.5).label}, ${lat0}° to ${lat0 + hv.band_deg}°: ${(hv.values[w][j] * 100).toFixed(1)}% of birds`;
      tip.style.opacity = 1;
      tip.style.left = `${Math.min(e.clientX - rc.left + 12, rc.width - tip.offsetWidth - 4)}px`;
      tip.style.top = `${e.clientY - rc.top + 26}px`;
    });
    cvs.addEventListener('pointerleave', () => { tip.style.opacity = 0; });
    host.append(box);
  });
}

function buildTransit(meta, analyses) {
  const host = document.getElementById('transit');
  const W = 1100, H = 340, m = { l: 48, r: 12, t: 14, b: 28 };
  const x = d3.scaleLinear([0, 51], [m.l, W - m.r]);
  const y = d3.scaleLinear([0, 1], [H - m.b, m.t]);

  const legend = el('div', { style: 'display:flex;flex-wrap:wrap;gap:6px 18px;margin-bottom:10px;font-size:0.85rem' },
    meta.species.map((s) => el('span', { style: 'display:inline-flex;align-items:center;gap:7px' }, [
      el('i', { style: `width:14px;height:3px;border-radius:2px;background:${s.color};box-shadow:0 0 8px ${s.color}` }), document.createTextNode(s.common),
    ])));
  host.append(legend);

  const svg = d3.select(host).append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('role', 'img')
    .attr('aria-label', 'Share of each species in transit, by week of the year');
  svg.append('g').selectAll('line').data(y.ticks(5)).join('line')
    .attr('x1', m.l).attr('x2', W - m.r).attr('y1', y).attr('y2', y).attr('stroke', 'rgba(233,237,245,0.09)');
  svg.append('g').selectAll('text').data(y.ticks(5)).join('text')
    .attr('x', m.l - 8).attr('y', y).attr('dy', '0.32em').attr('text-anchor', 'end').attr('fill', '#8d99b1').attr('font-size', 11)
    .text((d) => `${Math.round(d * 100)}%`);
  svg.append('g').selectAll('text').data(MONTHS).join('text')
    .attr('x', (d, i) => x((i + 0.5) * (51 / 12))).attr('y', H - 8).attr('text-anchor', 'middle').attr('fill', '#8d99b1').attr('font-size', 11).text((d) => d);

  const line = d3.line().x((d, i) => x(i)).y((d) => y(d)).curve(d3.curveMonotoneX);
  meta.species.forEach((sp, k) => {
    const v = analyses[k].moving_share;
    svg.append('path').attr('d', line(v)).attr('fill', 'none').attr('stroke', sp.color).attr('stroke-width', 2.2).attr('stroke-linejoin', 'round')
      .style('filter', `drop-shadow(0 0 4px ${sp.color}88)`);
  });

  const guide = svg.append('line').attr('y1', m.t).attr('y2', H - m.b).attr('stroke', 'rgba(255,255,255,0.45)').style('opacity', 0);
  const dots = meta.species.map((sp) => svg.append('circle').attr('r', 4).attr('fill', sp.color).attr('stroke', '#04070d').attr('stroke-width', 1.5).style('opacity', 0));
  const tip = el('div', { class: 'tip' });
  host.append(tip);
  const hit = svg.append('rect').attr('x', m.l).attr('y', m.t).attr('width', W - m.l - m.r).attr('height', H - m.t - m.b).attr('fill', 'transparent');
  hit.on('pointermove', (e) => {
    const [px] = d3.pointer(e, svg.node());
    const w = Math.round(Math.min(51, Math.max(0, x.invert(px))));
    guide.attr('x1', x(w)).attr('x2', x(w)).style('opacity', 1);
    dots.forEach((d, k) => d.attr('cx', x(w)).attr('cy', y(analyses[k].moving_share[w])).style('opacity', 1));
    const items = meta.species.map((sp, k) => ({ sp, v: analyses[k].moving_share[w] })).sort((a, b) => b.v - a.v);
    tip.innerHTML = `<b>${weekInfo(w + 0.5).label}</b><br>` + items.map((i) => `<span style="color:${i.sp.color}">●</span> ${i.sp.common} ${Math.round(i.v * 100)}%`).join('<br>');
    const rc = host.getBoundingClientRect(), sx = (x(w) / W) * rc.width;
    tip.style.opacity = 1;
    tip.style.left = `${sx > rc.width * 0.6 ? sx - tip.offsetWidth - 14 : sx + 14}px`;
    tip.style.top = `40px`;
  });
  hit.on('pointerleave', () => { guide.style('opacity', 0); dots.forEach((d) => d.style('opacity', 0)); tip.style.opacity = 0; });
}
