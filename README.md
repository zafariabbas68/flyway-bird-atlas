
# Flyway: an animated bird migration atlas

**Live site: https://flyway-bird-atlas.vercel.app**

A scroll-driven storytelling page about seven migratory birds crossing the Americas, one week
at a time. Python (Flask + NumPy) serves the data; the browser (Canvas + D3) does the
cartography and animation. The format was inspired by National Geographic's "Billions of
Birds Migrate" interactive.

## What is real and what is not

| Part of the page | Source | Status |
| --- | --- | --- |
| Opening satellite scene | NASA GIBS, GOES-East GeoColor, 49 frames every 2 hours from 8 to 12 Oct 2026 | Real |
| Green wave | NASA GIBS, MODIS Terra NDVI, 12 monthly images | Real |
| Chapter map background | NASA GIBS, Blue Marble (one still image, not seasonal) | Real |
| Coastlines and borders | Natural Earth 1:50m | Real |
| Bird maps (7 species) | GBIF occurrence records (includes eBird), about 18.7 million, 2010 to 2024 | Real, but see below |
| Hawk route in the opening scene | Simulated | **Not real** |

**Bird map brightness is observation frequency, not abundance.** For each 5 degree cell and
month it is the species' share of all bird records, interpolated to 52 weeks. It corrects for
where observers are, but it is not eBird Status and Trends abundance. The hawk is a simulated
route, not a tagged bird; add a Movebank CSV to change that (see `docs/DATA_SOURCES.md`).

Every panel carries a badge saying "Real" or "Modelled". Without the downloaded data the
project runs offline on a fully modelled dataset (`FLYWAY_DATA=simulated` forces this).

## Run it locally (PyCharm or any terminal)

1. Open the project folder, create a virtual environment (Python 3.10 or newer).
2. `pip install -r requirements-dev.txt`
3. `python run.py`, then open <http://127.0.0.1:5000>.
4. Tests: `pytest` (18 tests, all offline).

## Download real data (needs internet, run once)

    python scripts/fetch_real_data.py check
    python scripts/fetch_real_data.py coast
    python scripts/fetch_real_data.py imagery
    python scripts/fetch_real_data.py goes
    python scripts/fetch_real_data.py observations --quick    # drop --quick for 3 degree cells (20 to 60 min)

If GBIF answers "429 Too Many Requests", wait a few minutes and add `--workers 2`.
Restart the server and hard-refresh afterwards. Details and licences: `docs/DATA_SOURCES.md`.

## Deploy on Vercel

The site is deployed from this repository. `app.py` exposes the Flask `app`. Vercel cannot write
files at run time, so the cache is built ahead of time and committed:

    python scripts/rebuild_cache.py
    rm -rf public && mkdir public && cp -R static public/static
    git add . && git commit -m "Update" && git push

Vercel redeploys on every push to `main`.

## Project layout

```
app.py                     Vercel entry point
run.py                     local development server
flyway/
  species_data.py          the 7 species: ranges, routes, timing, story steps
  simulate.py              agent-based model -> 52 weekly grids (offline fallback)
  observed.py              GBIF counts -> weekly observation-frequency maps
  store.py                 chooses real or modelled data per species
  routes.py                page + JSON/binary API
  tracks.py                simulated hawk track, Movebank CSV loader
  basemap.py, basemap_builtin.py, geo.py
  sources/                 http, gibs (NASA), gbif, pipeline (download steps)
templates/index.html       page shell
static/css, static/js      design, hero, greenwave, chapters, map engine, imagery, analysis
static/img/real/           downloaded NASA imagery
flyway/cache/real/         downloaded bird data, converted
scripts/                   fetch_real_data.py, rebuild_cache.py
tests/                     model, API and offline pipeline tests
docs/                      ANALYSIS.md, DATA_SOURCES.md
```

## API

`/api/meta`, `/api/species`, `/api/species/<id>`, `/api/species/<id>/frames.bin`
(52 x 136 x 173 uint8), `/api/species/<id>/analysis`, `/api/compare`, `/api/basemap`,
`/api/imagery`, `/api/track/hawk`, `/healthz`.

## Credits

There are no photographs in this project and no network calls for imagery. `static/js/satellite.js`
**synthesises** the picture in the browser: fractal coastlines, vegetation that follows the
seasons, hand-placed wet and dry regions, mountain ranges with hill-shading, snow and ice, a
shallow-sea tint and tileable moving clouds. It looks like Earth-observation imagery but it is
procedural, so treat it as illustration.

To use real imagery instead (for example NASA Blue Marble monthly composites, public domain),
download the images yourself and draw them in `Hero.draw()` and `MapEngine` in place of
`SatelliteTexture`. The projection maths is already there.

## Validation
`python scripts/validate_observations.py --quick` builds each species' map from two independent
sets of years (2010-2016 and 2017-2024). Seasonal-change correlation between the halves is 0.94 to
0.98 for all seven species (see `docs/VALIDATION.md`). This shows the maps are reproducible, not
that they are accurate: accuracy still needs an independent reference such as eBird Status and
Trends (`docs/REFERENCES.md`).
