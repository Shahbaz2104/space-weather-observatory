# Architecture

```text
NOAA SWPC ─┐
GFZ Kp ────┼─> data_sources ─> validation ─> processing ─> analysis ─> visualization
NASA OMNI2 ┘        │              │             │            │            │
                    └─ HTTP cache ─┘             └─ events ───┘            │
                                                                           v
Streamlit pages <─ ui.py <─ services.py <─ bundles/provenance ── export/reports.py
```

## Layers

### `data_sources/`

Provider-specific adapters and parsers. They return canonical frames with a fixed column set and attach a `SourceInfo` to `DataFrame.attrs`.

- `noaa.py` — recent Kp, propagated solar wind, latest snapshots.
- `historical.py` — GFZ fixed-width Kp text and OMNI2 yearly flat files.
- `base.py` — canonical columns, empty frames, source metadata helpers.

### `ingestion/`

- `fetch.py` — retrying HTTP client, timeouts, and response caching.
- `cache.py` — file cache with TTL and explicit stale metadata.
- `validate.py` — table normalization, timestamp coercion, Kp masking, fill-value masking.
- `samples.py` — versioned offline sample loader with provenance.

### `processing/`

- `cleaning.py` — normalization, UTC filtering, completeness, source merging.
- `resampling.py` — three-hour solar-wind aggregation and Kp alignment.
- `events.py` — transparent storm-run detection and G-scale classification.

### `analysis/`

- `statistics.py` — summary statistics and distributions.
- `correlations.py` — Pearson/Spearman, effective sample size, Fisher intervals, lag search.
- `anomalies.py` — descriptive anomaly calculations.

### `visualization/`

- `theme.py` — shared palette, Plotly template, Matplotlib configuration.
- Figure modules for timelines, heatmaps, distributions, and solar-wind context.
- `animations.py` — deterministic frame rendering, GIF/MP4 encoding, static overview.

### `services.py`

The orchestration facade. It resolves windows, chooses authoritative sources, handles fallbacks, attaches provenance, and returns `DataBundle` objects. Streamlit pages never call provider adapters directly.

### `ui.py`

Shared presentation behavior:

- design tokens and CSS;
- sidebar mode, threshold, and date controls;
- status badges (live/sample/modeled/preliminary/cache/stale);
- cached service calls;
- metric cards, empty states, downloads, and Plotly display;
- timestamp and provenance helpers.

### `pages/`

Thin page modules that compose the service/UI layers. Each page owns only its narrative, controls, and figures.

### `export/reports.py`

Builds provenance, serializes JSON/CSV/Parquet, and writes export bundles.

## Data flow

1. A page asks `services` for a window.
2. `services` resolves the date range and selects a source strategy.
3. The adapter fetches through the cached HTTP client and parses into canonical columns.
4. Cleaning normalizes timestamps and missing values.
5. Processing aligns solar wind to Kp or detects events.
6. Analysis computes statistics with explicit caveats.
7. `ui` renders badges, figures, tables, and downloads.
8. `export` records the exact provenance of any exported artifact.

## Design principles

- **No hidden substitution.** Sample, live, cached, stale, modeled, and preliminary states are visible.
- **UTC everywhere.** Display and export share one time basis.
- **Missing is not zero.** Gaps remain gaps and are quantified where possible.
- **UI is a thin layer.** Scientific decisions live in testable modules.
- **Every export is explainable.** Provenance is generated alongside data.
- **Graceful failure.** Auto mode falls back with disclosure; live-only mode fails visibly.
