# Real data: what it is, where it comes from, how to get it

Out of the box Flyway runs fully offline with a **modelled** look (procedural imagery, simulated birds).
Run the fetch script on your own computer to replace each part with real data. Each part is independent
and every panel on the page carries a badge saying whether it is real or modelled.

| Part of the page | Real source | Command | Licence / credit |
|---|---|---|---|
| Coastlines | Natural Earth 1:50m | `python scripts/fetch_real_data.py coast` | public domain |
| Satellite background (chapters, opening) | NASA GIBS: Blue Marble Next Generation, monthly | `... imagery` | NASA GIBS acknowledgement (shown in the footer) |
| Opening scene | NASA GIBS: GOES-East GeoColor, 2-hourly frames over 4 days | `... goes` | as above |
| Green wave | NASA GIBS: MODIS Terra NDVI, monthly | `... imagery` | as above |
| Bird maps | GBIF occurrence API (includes the eBird Observation Dataset) | `... observations` | CC BY 4.0, cite GBIF |
| Hawk track | Movebank CSV you export (`flyway/data/tracks/hawk.csv`) | `... goes --track flyway/data/tracks/hawk.csv` | credit the data owner |

Run `python scripts/fetch_real_data.py check` first: it tests that your network can reach each service.

## How the bird maps are made from GBIF
GBIF gives record counts, not abundance. For each 3 degree cell and month the page uses
`share = species records / all bird records`, which removes most of the "more observers here" bias.
Months are interpolated to 52 weeks with a periodic cosine curve, resampled to the map grid, and scaled so
brightness is comparable across the year. This is an *observation-frequency* signal. It is not the
modelled relative abundance of eBird Status and Trends, which needs the Cornell data licence.
For publication, make a GBIF download to get a citable DOI.

## Honesty notes
* The download steps were written against the documented service formats and tested here only with mocks
  (`tests/test_pipeline.py`): the build environment had no internet. If a live run fails, paste the message.
* NDVI is shown in NASA's own colours; the legend is hidden when real NDVI is active.
* Without a real GPS file the hawk route stays labelled "simulated".
* To go back to modelled data: delete `flyway/cache/real`, `static/img/real`, or set `FLYWAY_DATA=simulated`.
