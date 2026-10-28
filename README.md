# Flyway: an animated bird migration atlas

A scroll-driven, dark-map storytelling page about seven migratory birds crossing the
Americas, one week at a time. Python (Flask + NumPy) builds the data, the browser
(Canvas + D3) does the cartography and animation.


> **Important: the data is modelled, not measured.** Ranges, routes, dates and the
> hawk track are illustrative, written from general knowledge of each species. They are
> **not** eBird Status and Trends data and **not** real GPS tags. The page says so too.

## Run it in PyCharm

1. **File > Open** and choose the `flyway-bird-migration` folder.
2. **Settings > Project > Python Interpreter > Add Interpreter > Add Local Interpreter >
   Virtualenv** (a new `.venv` is fine). Python 3.10 or newer.
3. Open the terminal in PyCharm and run `pip install -r requirements.txt`.
4. Right-click `run.py` > **Run 'run'** (or pick the **Flyway** run configuration in the
   top-right dropdown).
5. Open <http://127.0.0.1:5000>.

The first start builds seven yearly grids in about two seconds and caches them in
`flyway/cache/`. D3 is bundled in `static/vendor/`, so the only thing that needs internet
is the Google Fonts stylesheet (the page falls back to system fonts without it).

From any terminal: `python run.py`. Tests: `pytest`.

## What you will see

| Section | What it does |
| --- | --- |
| Satellite-style opening | A full-bleed view of the Americas with drifting clouds, soft cloud shadows and a day/night edge. A green line traces a simulated Broad-winged Hawk from Pennsylvania to Peru, with a live date, local time and distance. |
| Green wave | A month-by-month animated vegetation map (least to most vegetation). Click the map to pause. |
| Overview map | All seven species glow together. Scroll to jump to January, April, July and September. Toggle species with the chips. Drag the timeline to scrub. |
| Seven chapters | One sticky map per species. Scroll cards move the map to a week; leader lines and labels fade in for each step. The sparkline shows how much of the population is in transit. |
| Compare | Route length ledger, latitude-by-week panels with hover read-out, and an in-transit chart for all species. |

## Project layout

```
run.py                     start the server
flyway/
  species_data.py          the 7 species: ranges, routes, timing, story steps (edit here)
  simulate.py              agent-based model -> 52 weekly grids + analysis metrics
  geo.py                   haversine / polyline helpers
  tracks.py                simulated hawk track for the globe
  basemap_builtin.py       built-in simplified coastlines
  basemap.py               loads Natural Earth if present
  routes.py                page + JSON/binary API
templates/index.html       page shell
static/css/main.css        design system
static/js/                 main, chapter, mapengine, timeline, hero, greenwave, satellite, analysis, basemap, api, util
static/vendor/d3.min.js    D3 7.9.0 (ISC licence)
scripts/                   rebuild_cache.py, fetch_natural_earth.py
tests/                     model and API tests
docs/ANALYSIS.md           analysis of the reference piece and how this project maps to it
```

## API

`/api/meta`, `/api/species`, `/api/species/<id>`, `/api/species/<id>/frames.bin`
(52 x 136 x 173 uint8), `/api/species/<id>/analysis`, `/api/compare`, `/api/basemap`,
`/api/track/hawk`, `/healthz`.

## About the satellite look

There are no photographs in this project and no network calls for imagery. `static/js/satellite.js`
**synthesises** the picture in the browser: fractal coastlines, vegetation that follows the
seasons, hand-placed wet and dry regions, mountain ranges with hill-shading, snow and ice, a
shallow-sea tint and tileable moving clouds. It looks like Earth-observation imagery but it is
procedural, so treat it as illustration.

To use real imagery instead (for example NASA Blue Marble monthly composites, public domain),
download the images yourself and draw them in `Hero.draw()` and `MapEngine` in place of
`SatelliteTexture`. The projection maths is already there.

## Customising

* **Add or change a species** in `flyway/species_data.py`; the grids rebuild automatically
  when the definition changes (a fingerprint is stored with each cache file).
* **Sharper coastlines:** `python scripts/fetch_natural_earth.py` (needs internet),
  restart. This script was not run in the build environment, which had no internet.
* **Use real abundance data:** replace `simulate_species` so it returns a
  `(52, HEIGHT, WIDTH)` uint8 array resampled from your own rasters (for example eBird
  Status and Trends weekly abundance, subject to its licence and attribution terms).
  Nothing else in the project changes.
* **Speed** of the loop: `LOOP_SPEED` in `static/js/chapter.js`.
* **Colours / look:** CSS variables at the top of `static/css/main.css`; each species'
  colour is in `species_data.py`.

## Credits and originality

The format was inspired by the animated abundance maps from the Cornell Lab of Ornithology
and the 2018 National Geographic feature "Billions of Birds Migrate". No text, images,
data or code from those works are used. All copy, code and data here are original.


## Real data (optional)
The project runs offline with modelled data. To use real NASA satellite imagery and real GBIF/eBird bird
records, run on your own computer (needs internet):

    python scripts/fetch_real_data.py check
    python scripts/fetch_real_data.py all --quick      # quick = coarser bird grid, a few minutes
    python run.py

See `docs/DATA_SOURCES.md`. Tests: `pytest` (17 tests, all offline).
