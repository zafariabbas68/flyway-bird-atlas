// Thin fetch layer with in-memory caching.
const jsonCache = new Map();
const frameCache = new Map();

export async function getJSON(url) {
  if (!jsonCache.has(url)) {
    jsonCache.set(url, fetch(url).then((r) => {
      if (!r.ok) throw new Error(`${url} -> ${r.status}`);
      return r.json();
    }));
  }
  return jsonCache.get(url);
}

export function getFrames(speciesId) {
  if (!frameCache.has(speciesId)) {
    frameCache.set(speciesId, fetch(`/api/species/${speciesId}/frames.bin`).then(async (r) => {
      if (!r.ok) throw new Error(`frames ${speciesId} -> ${r.status}`);
      return new Uint8Array(await r.arrayBuffer());
    }));
  }
  return frameCache.get(speciesId);
}

export const getMeta = () => getJSON('/api/meta');
export const getBasemap = () => getJSON('/api/basemap');
export const getAnalysis = (id) => getJSON(`/api/species/${id}/analysis`);
export const getCompare = () => getJSON('/api/compare');
export const getTrack = () => getJSON('/api/track/hawk');
