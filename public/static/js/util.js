// Small shared helpers.
export const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
export const lerp = (a, b, t) => a + (b - a) * t;
export const smoothstep = (a, b, x) => {
  const t = clamp((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
};
export const easeInOut = (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);
export const mod = (n, m) => ((n % m) + m) % m;

export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];

/** Week index (float) to a calendar label. Week 0 starts on 1 January. */
export function weekInfo(t) {
  let day = Math.floor(mod(t, 52) * 7 + 0.0001);
  let m = 0;
  while (m < 11 && day >= DAYS[m]) { day -= DAYS[m]; m++; }
  return { month: m, day: day + 1, label: `${MONTHS[m]} ${day + 1}` };
}

export function hexToRgb(hex) {
  const n = parseInt(hex.replace('#', ''), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export const fmtInt = (n) => Math.round(n).toLocaleString('en-US');
export const fmtLat = (v) => `${Math.abs(v).toFixed(1)}° ${v >= 0 ? 'N' : 'S'}`;
export const fmtLon = (v) => `${Math.abs(v).toFixed(1)}° ${v >= 0 ? 'E' : 'W'}`;

export const prefersReducedMotion = () =>
  window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v;
    else if (k === 'text') node.textContent = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) if (c) node.append(c);
  return node;
}

/** Fraction (0..1) of the current calendar month elapsed at week-float t. */
export function monthProgress(t) {
  let day = mod(t, 52) * 7, m = 0;
  while (m < 11 && day >= DAYS[m]) { day -= DAYS[m]; m++; }
  return clamp(day / DAYS[m], 0, 1);
}
