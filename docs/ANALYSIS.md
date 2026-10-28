# Analysis of the reference piece, and how Flyway maps to it

Source of this analysis: the page's own metadata, a public write-up by its map developer
(Source, OpenNews, 2018), and the Cartographic Perspectives article on the same project.
The live page renders client-side, so it could not be read directly; details below come
from those write-ups, not from inspecting the page's code.

## What the reference does

**Concept.** Not a conversion of the print poster but a screen-native piece about *fewer*
species, chosen so each shows a different migration strategy: night flier, mountain route,
short-distance migrant, soaring bird, long-distance flycatcher, and so on.

**Narrative structure.**
1. Opening: a satellite-style Earth animation with one GPS-tracked hawk drawn on top,
   synced in time, to start with drama and show that birds move through a living planet.
2. Context graphics explaining what drives migration.
3. One section per species with autoplay looping map video (the pulse of migration) and a
   scroll stepper (stepping through weeks, with text and map labels for each step) for
   readers who want to go deeper. Audio of birdsong and photography accompany each.

**Data.** Weekly abundance models (52 files per species) from eBird, rescaled with one
min/max for the whole year so frames are comparable.

**Cartography.**
* A dark basemap with neon-coloured data, like a night-lights image.
* Species-specific crop and projection (azimuthal equidistant), vignette to fade edges.
* Animated map = pre-rendered video (so heavy raster work is not done in the browser).
* Labels as live HTML text and leader lines as SVG, aligned over the video, shown and
  hidden step by step. This keeps text legible and the lines responsive to screen size.
* The hawk's route is drawn live in SVG from GPS data and synced with the video.

## What Flyway does with each idea

| Reference idea | Flyway implementation |
| --- | --- |
| Few species, varied strategies | 7 species with distinct "strategy" tags (night flier, mountain route, short hop, thermal rider, day flocks, over-ocean, loop). |
| Weekly abundance, 52 frames, one shared scale | `simulate.py` builds 52 grids per species, scaled once across the year. |
| Pre-rendered video | Replaced with **live rendering**: the browser inverts the projection per pixel, blends two neighbouring weeks, and paints through a colour ramp. Smooth scrubbing at any speed, no video files. |
| Dark neon look | Night ocean, slate land, one glowing hue per species, additive blending in the overview. |
| Autoplay loop + scroll stepper | Chapters autoplay the full year; scroll steps tween the map to a chosen week and show labels. A play/pause button and a draggable timeline give manual control. |
| HTML labels + SVG leaders over the map | Same layering, re-projected on every resize, clamped to the screen on phones. |
| GPS hawk over satellite imagery | Full-bleed procedural satellite view with drifting clouds, a moving day/night edge, a green route line, a centred caption (species, date, local time) and a scroll chevron. The track is *simulated* and only advances in daylight. |
| Animated vegetation map with month label | `greenwave.js`: modelled seasonal greenness, legend (least to most vegetation), month name, click to pause. |
| Light relief basemap under each species | Satellite-style terrain under every map, dimmed so the glow stays readable. |
| Audio and photos | Left out on purpose (would need licensed media). |

## Additions that go beyond the reference

* An **overview map** that overlays all seven species with toggles.
* A **compare section** that reads numbers back out of the model: route length, trip
  duration and pace, a latitude-by-week panel per species (a Hovmoller-style plot), and a
  share-in-transit chart that exposes how synchronised each species is.
* A **cache and API layer** (Flask) so data can be swapped without touching the front end.

## Model details

Per species, 6,000 simulated birds:
1. Winter and breeding sites are sampled from Gaussian mixtures.
2. Each bird gets its own spring and fall departure week and trip duration (normal
   distributions), so a population forms a wave rather than a single front.
3. Spring route: winter site, jittered shared waypoints, breeding site. Fall route reuses
   them in reverse unless a separate fall route exists (blackpoll warbler, rufous
   hummingbird loop migrations).
4. Stopovers are a time-warp: progress along the route pauses at random hops.
5. Weekly positions are binned to a 0.75 degree grid and blurred (sigma 1.4 cells).
6. Frames are scaled once per species (99.7th percentile, square-root stretch) to uint8.

Derived metrics: median great-circle and route distance, trip days, pace, first/peak/last
week of spring and fall, share in transit, centroid latitude, latitude-by-week histogram,
and the ratio between the widest and narrowest range area.

## Limitations (please read)

* Everything is **illustrative**. The ranges are rough, the routes are stylised, and the
  dates are plausible rather than measured. Do not use this to make ecological claims.
* Abundance here means "share of simulated birds per cell", not birds per km as in eBird.
* The built-in coastlines are coarse (about 500 vertices). Use
  `scripts/fetch_natural_earth.py` for better ones.
* Hawk speeds and rest days are invented to look like a soaring bird's track.
* The satellite look and the vegetation map are **procedural**, not photographs or NDVI measurements.

## Where to take it next

* Replace `simulate_species` with a loader for real weekly rasters (eBird S&T, with
  attribution) and keep the rest.
* Add real tracking data (for example from Movebank, with the owners' permission) in
  place of `tracks.py`.
* Add birdsong clips and photographs you have the rights to use.
* Add a Spanish translation; the copy lives in `species_data.py` and `main.js`.
