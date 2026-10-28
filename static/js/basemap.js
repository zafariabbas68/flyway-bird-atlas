// Dark cartographic basemap painted with Canvas 2D through a d3 projection.
const TWO_PI = 2 * Math.PI;

/** Fix ring winding so d3 fills the small side of every polygon. */
export function normalizeGeo(geo) {
  const feats = geo.features.map((f) => {
    if (!f.geometry || (f.geometry.type !== 'Polygon' && f.geometry.type !== 'MultiPolygon')) return f;
    if (d3.geoArea(f) > TWO_PI) {
      const flip = (rings) => rings.map((r) => r.slice().reverse());
      const g = f.geometry.type === 'Polygon'
        ? { type: 'Polygon', coordinates: flip(f.geometry.coordinates) }
        : { type: 'MultiPolygon', coordinates: f.geometry.coordinates.map(flip) };
      return { ...f, geometry: g };
    }
    return f;
  });
  const by = (k) => feats.filter((f) => f.properties && f.properties.kind === k);
  return { land: by('land'), lakes: by('lake'), borders: by('border'), countries: by('country') };
}

const GRATICULE = d3.geoGraticule().step([15, 15]);

export function drawBase(canvas, projection, layers, w, h, dpr, overlayOnly = false) {
  const ctx = canvas.getContext('2d');
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  if (overlayOnly) {
    // satellite imagery is underneath: draw only faint outlines and borders
    ctx.clearRect(0, 0, w, h);
    const p = d3.geoPath(projection, ctx);
    ctx.beginPath(); layers.land.forEach((f) => p(f));
    ctx.strokeStyle = 'rgba(210,230,255,0.22)'; ctx.lineWidth = 0.7; ctx.stroke();
    ctx.beginPath(); layers.borders.forEach((f) => p(f));
    ctx.strokeStyle = 'rgba(235,242,255,0.28)'; ctx.lineWidth = 0.7; ctx.setLineDash([3, 3]); ctx.stroke(); ctx.setLineDash([]);
    if (layers.countries.length) { ctx.beginPath(); layers.countries.forEach((f) => p(f)); ctx.strokeStyle = 'rgba(235,242,255,0.16)'; ctx.lineWidth = 0.6; ctx.stroke(); }
    return;
  }

  // Ocean
  const g = ctx.createRadialGradient(w * 0.6, h * 0.45, 0, w * 0.6, h * 0.45, Math.max(w, h) * 0.8);
  g.addColorStop(0, '#08111f');
  g.addColorStop(1, '#03060b');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);

  const path = d3.geoPath(projection, ctx);

  // Graticule
  ctx.beginPath(); path(GRATICULE());
  ctx.strokeStyle = 'rgba(120,150,200,0.07)'; ctx.lineWidth = 0.6; ctx.stroke();

  // Land glow, fill, edge
  ctx.save();
  ctx.shadowColor = 'rgba(70,130,255,0.35)'; ctx.shadowBlur = 14;
  ctx.beginPath(); layers.land.forEach((f) => path(f));
  ctx.fillStyle = '#0d1729'; ctx.fill();
  ctx.restore();

  ctx.beginPath(); layers.land.forEach((f) => path(f));
  ctx.fillStyle = '#0d1729'; ctx.fill();
  ctx.strokeStyle = 'rgba(140,185,255,0.42)'; ctx.lineWidth = 0.8; ctx.stroke();

  // Lakes
  ctx.beginPath(); layers.lakes.forEach((f) => path(f));
  ctx.fillStyle = '#060b14'; ctx.fill();
  ctx.strokeStyle = 'rgba(140,185,255,0.25)'; ctx.lineWidth = 0.6; ctx.stroke();

  // Borders
  ctx.beginPath();
  layers.borders.forEach((f) => path(f));
  ctx.strokeStyle = 'rgba(170,195,235,0.22)'; ctx.lineWidth = 0.7; ctx.setLineDash([3, 3]); ctx.stroke();
  ctx.setLineDash([]);
  if (layers.countries.length) {
    ctx.beginPath(); layers.countries.forEach((f) => path(f));
    ctx.strokeStyle = 'rgba(170,195,235,0.16)'; ctx.lineWidth = 0.6; ctx.stroke();
  }
}
