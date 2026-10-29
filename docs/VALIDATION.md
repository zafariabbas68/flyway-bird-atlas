# Validation: split-half stability of the observed maps

Generated 2026-10-29. Cells of 5.0 degrees. Half A uses records from 2010 to 2016, half B from 2017 to 2024.

| Species | Cells in both | Map correlation (mean of 52 weeks) | Weakest week | Seasonal-change correlation | Centroid latitude difference (deg) | Spring timing difference (weeks) | Autumn timing difference (weeks) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Wood Thrush | 5667 | 0.99 | 0.96 | 0.98 | 0.4 | 0.2 | 0.0 |
| Western Tanager | 7199 | 0.99 | 0.97 | 0.98 | 0.5 | 0.1 | 0.2 |
| White-throated Sparrow | 7940 | 0.98 | 0.96 | 0.95 | 0.5 | 0.2 | 0.2 |
| Broad-winged Hawk | 9165 | 0.96 | 0.87 | 0.94 | 0.8 | 0.1 | 0.3 |
| Eastern Kingbird | 11754 | 0.97 | 0.93 | 0.98 | 0.6 | 0.2 | 0.0 |
| Blackpoll Warbler | 12613 | 0.95 | 0.88 | 0.95 | 0.5 | 0.0 | 0.2 |
| Rufous Hummingbird | 6864 | 0.97 | 0.92 | 0.98 | 0.5 | 0.7 | 0.1 |

**How to read this.** Map correlation compares the two halves cell by cell and week by week, but is helped by the fixed range outline. Seasonal-change correlation removes each cell's own yearly mean, so it only credits agreement about how birds move. Timing difference is the gap between the halves in the week the population's average latitude crosses its mid-level, going north (spring) and south (autumn); n/a means the species moves too little to time. Values near 1 (and small gaps) mean the pattern does not depend on which years were used, so the method is reproducible. This tests stability, not accuracy: both halves share the same biases (where and when people watch birds). Accuracy needs an independent reference, listed in `docs/REFERENCES.md`.
