# Case study, demo script, and application drafts

This file is the portfolio layer of the project: why it exists, what was actually built,
how it was verified, and drafts that can be reused in applications.

Every capability described here exists in the repository, and every number is traceable to
the **Evidence log** at the end. Nothing is estimated or aspirational. Where a figure has
not been measured, the text says so instead of filling it in.

---

## 1. The problem

Geomagnetic storms are one of the few space-physics phenomena with direct consequences on
the ground: satellite drag, HF radio propagation, GPS positioning, power-grid currents.
The headline number, the planetary Kp index, is widely published and widely misread.

Three misreadings are common and all of them are representational:

1. **Missing data drawn as quiet data.** A gap in a three-hour series is "unknown", not "Kp 0".
2. **Interpolated curves presented as measurements.** A smooth line implies observations that
   do not exist.
3. **A Kp value confused with a storm.** Kp 5 is an activity classification; a "storm" in this
   project is a defined run of qualifying samples, and the two are reported separately.

Space Weather Observatory started from that problem: build the observatory interface that
shows what was measured, when, by which provider, and with which caveats — and make the
visual design good enough that the caveats are not ignored.

## 2. Why this dataset is interesting

Four genuinely different data products have to coexist:

| Product | Cadence | Status | What makes it awkward |
| --- | --- | --- | --- |
| NOAA SWPC recent planetary K index | 3 h | Preliminary, observed | Short window; values may be revised |
| GFZ Kp archive since 1932 | 3 h | Definitive (recent may be preliminary) | ~277k rows; licensing requires citation |
| NOAA seven-day propagated solar wind | 1 min | **Modeled** | Not an in-situ measurement at Earth |
| NASA OMNI2 hourly solar wind and IMF | 1 h | Observed | Fill values, different cadence from Kp |

So the interesting engineering problems are not "draw a line chart". They are alignment
across cadences, provenance, staleness, and keeping three data statuses from collapsing into
one confident-looking number.

The bundled offline sample is a genuine slice of that record: GFZ Kp for 2003 and 2024, and
OMNI2 hourly measurements for May 2024 — the window that contains the G5 storm of
10–11 May 2024, where the sample peaks at Kp 9.00.

## 3. Engineering challenges and decisions

**Provider adapters instead of one fetch function.** Each source validates its own schema and
returns a typed `DataBundle` with units, status, retrieval time, and URL. A provider changing
its JSON shape breaks one adapter, not the application.

**One time convention.** Kp timestamps label the *start* of a three-hour interval. Solar-wind
samples are aggregated onto the same left-labelled bins, and each bin carries `n_samples` and
`coverage_fraction` so a mean of two samples is not mistaken for a mean of 180.

**Missing stays missing.** No interpolation, forward-fill, or zero-fill anywhere in the
processing layer. The heatmap renders an absent cell differently from a zero cell; the event
detector reports interior gaps rather than closing them.

**Render-time sampling that cannot hide a gap.** Charts above a configurable point cap use a
uniform stride for rendering only, but always retain the first and last rows and the
boundaries of missing-data runs. Metrics, event detection, tables, and exports keep every row,
and the reduction is captioned under the chart. A long series can therefore be responsive
without quietly turning a gap into a continuous line or changing the statistics.

**Failures are visible.** HTTP calls have timeouts, bounded retries with backoff, and a disk
cache with an explicit TTL. When a source is unreachable the interface says so; a stale cache
is labelled "source unavailable", never presented as a fresh observation. The bundled sample
identifies itself as a sample on every page that uses it.

**A sidebar state bug found by testing the real UI.** Capturing the screenshots exposed that
selecting "Offline sample" and then navigating to another page silently reset the data mode to
live. For an app whose entire argument is "never confuse sample data with live data", that is a
correctness bug, so the sidebar controls were moved off Streamlit widget keys onto explicit
session state and the mode now survives page changes.

**Deterministic animation.** Frames are sampled from real observations, frame count is capped
(600 by default), rendering has no random seed dependency, and any stride or cap is written into
the provenance record. MP4 export needs `ffmpeg`; GIF works without it and the UI degrades
rather than crashing when the encoder is missing.

**Provenance on exports.** CSV, Parquet, figures, and animations can be downloaded with a JSON
provenance record: source URLs, retrieval timestamps, UTC window, units, transformations,
threshold, software version, and warnings.

## 4. Design decisions

- **Streamlit** for the application shell: the fastest honest way to ship seven linked
  analytical pages without inventing a frontend build.
- **Plotly** for interactive time series (zoom, hover, linked ranges) and **Matplotlib** for
  publication figures and animation export, where frame-level control matters.
- **A single design system** in `visualization/theme.py` and `ui.py`: deep navy canvas, cyan
  for observations, violet for peaks and secondary series, coral for storm-level values,
  tabular monospace numerals in metric cards.
- **Colour is never the only channel.** Storm conditions get a badge, a label, and a threshold
  line, not just a red pixel.
- **Every page opens with the same status line**: source, data status, timezone, last update.
  The reader learns where the numbers came from before reading the numbers.

## 5. Analytical methods

- **Summary metrics** — latest valid Kp, peak Kp with G-scale band, count and share of samples
  at or above the threshold, completeness against expected three-hour slots.
- **Event detection** — contiguous runs of `Kp >= threshold`, bridging a single missing slot.
  Reported duration is the sampled span, labelled as such; a single qualifying sample is a
  three-hour run, not proof of a three-hour storm.
- **Heatmap** — mean Kp by year and month, and by date and hour, with absent cells kept absent.
- **Correlation lab** — Pearson and Spearman coefficients, paired-bin count, an
  autocorrelation-adjusted effective sample size, Fisher intervals on both the naive and
  effective `n`, and a signed lag scan where positive lag means the solar-wind variable leads Kp.
- **Language discipline** — associations are reported as associations. P-values are descriptive
  and not corrected for multiple comparisons; that limitation is stated in the interface.

## 6. Validation approach

The test suite targets the places where a visualization can quietly become wrong:

- source parsing, including header rows, fill values, and malformed payloads;
- UTC conversion, deduplication, and sorting;
- threshold logic and event boundaries, including the one-gap rule and empty input;
- resampling, left-labelled bin alignment, and the "empty wind is not zero" case;
- correlation edge cases: perfect correlation, too few pairs, missing pairs, lag direction;
- provenance round-trip and CSV time formatting;
- the bundled sample, asserted to be genuine observations with no zero-fill.

On top of the unit and integration suite, the running application was exercised page by page
through Streamlit's own `AppTest` harness in offline mode, and the animation export was executed
end to end with `ffmpeg`.

## 7. Limitations

- It is **not** a forecast service, an alerting system, or a safety tool.
- NOAA Kp is preliminary and may be revised after publication.
- The NOAA propagated solar wind is a model product, not an in-situ measurement at Earth.
- NASA DONKI is optional, disabled by default, and not exercised without an API key.
- The effective sample size is a lag-1 diagnostic, not a full time-series model.
- The heatmap describes selected windows; the offline sample covers 2003 and 2024 only.
- Charts above `SWO_DISPLAY_MAX_POINTS` subsample for rendering; very short structure between
  displayed points may be absent from the chart even though it remains in the data and exports.
- The Docker image was **not** built locally. GitHub Actions builds it, runs it offline, and
  polls the health endpoint successfully. A public Streamlit deployment serves `app.py` at its
  root URL; `/overview` is not a route on this deployment.
- The screenshots in `assets/screenshots/` come from the offline sample, not a live feed.

## 8. Five most useful next improvements

1. Refresh the live demo screenshots from the public deployment.
2. Add a superposed-epoch view aligned on storm onset to compare the 2003 and 2024 events.
3. Overlay NASA DONKI event notices with a documented anonymous-key fallback.
4. Add a block-bootstrap or HAC uncertainty estimate alongside the current effective-`n` interval.
5. Explore an isolated 3D module (field lines, day/night terminator) that ships as an optional
   extra rather than a dependency of the core dashboard.

---

## Interview demo script (~6 minutes)

1. **Open the Overview in offline sample mode** (~40 s). Point at the status line before the
   numbers: source, "Offline sample · not live", UTC, last update. Then the metric cards:
   peak Kp 9.00 with G5, 25 storm-level samples, 100% completeness for the window.
   *Say: the page is designed so you cannot read a value without seeing its provenance.*
2. **Read one storm out of the timeline** (~40 s). The shaded intervals are detected runs;
   the dashed line is the threshold, and changing the slider re-derives the events.
3. **Storm Explorer** (~60 s). Select the 2 May 2024 run: peak Kp 6.67, G2, 9 h sampled span,
   0 missing slots. Explain the difference between "sampled duration" and physical storm duration,
   and that a single row would be reported as a three-hour run.
4. **Activity Heatmap** (~30 s). Switch tabs; note that an absent cell means no observation, never
   zero. Explain the aggregation rule.
5. **Solar Wind** (~50 s). Show the May 2024 speed jump and the strongly southward Bz; note that
   in live mode this page uses NOAA's *propagated* product, which is modelled, and the UI says so.
6. **Correlation Lab** (~60 s). Pearson 0.627 for speed vs Kp on 243 paired bins, but effective
   `n` is 21.2, so the naive interval is too narrow. *Say: the interesting part of this page is
   the sample size, not the headline coefficient.*
7. **Animation Studio** (~30 s). Mention deterministic frames, the 600-frame cap, and the
   verified MP4 export; the animation replays observations, it does not simulate physics.
8. **Close on integrity** (~30 s). Open Methodology; mention no zero-fill, preliminary-data
   warnings, provenance JSON on exports, and the test suite that covers each convention.

If asked "what would you do next": add a superposed-epoch comparison of the two sampled
storms.

---

## LinkedIn project description (draft)

> **Space Weather Observatory — an evidence-first dashboard for geomagnetic storms**
>
> Live demo: <https://space-weather-observatory-4xedxr5f2n5vpym7t5ix7p.streamlit.app/>
>
> I built a Streamlit application that turns NOAA, GFZ, and NASA space-weather data into a
> scientific observatory interface: a live overview of planetary Kp, threshold-driven storm
> detection, a ninety-year activity heatmap, aligned solar-wind and IMF views, and a correlation
> lab that reports effective sample size instead of a bare coefficient.
>
> The engineering problem was not charting — it was keeping four data products with different
> cadences and different trust levels honest. Missing observations stay missing, modelled
> products are labelled as modelled, preliminary values are marked preliminary, and every export
> carries provenance metadata. The test suite covers the conventions that are easy to break
> silently: timestamp handling, fill-value masking, event boundaries, resampling, and correlation
> edge cases.
>
> Stack: Python, pandas, NumPy, SciPy, Plotly, Matplotlib, Streamlit, pytest, Ruff, mypy,
> GitHub Actions. Server cold start is under two seconds locally (1.5 s and 1.8 s on two
> runs, offline mode); the first page build adds about a second.
>
> Educational project, not an operational forecast service.

---

## CV bullets (draft)

- Built a seven-page Streamlit observatory for geomagnetic activity over NOAA SWPC, GFZ, and
  NASA OMNI2 data, with provider adapters, schema validation, bounded retries, TTL caching, and
  explicit stale-source states instead of silent fallbacks.
- Implemented the analytical layer — completeness metrics, threshold-based event detection,
  three-hour resampling with coverage fractions, and autocorrelation-adjusted correlation
  intervals — and covered each convention with unit and integration tests (58 tests, Ruff and
  mypy clean), including an offline `AppTest` smoke test of all seven pages.
- Delivered reproducibility tooling: CSV, Parquet, figure, GIF/MP4 exports with JSON provenance
  recording sources, retrieval times, units, transformations, and warnings; verified MP4
  rendering end to end through ffmpeg.

---

## Evidence log

Captured on 24–26 October 2026 in this repository's virtual environment (Python 3.12, Linux).

| Check | Command | Result |
| --- | --- | --- |
| Test suite | `pytest -q` | 58 passed in 15.79 s |
| Lint | `ruff check .` | All checks passed |
| Types | `mypy src` | Success: no issues found in 36 source files |
| Page smoke test | `pytest tests/integration/test_pages_smoke.py` (`AppTest` over `app.py` + 7 pages, offline mode) | 8 scripts, no exceptions |
| Clean-install deployability | Fresh venv, `pip install -r requirements.txt` only, then the same page smoke test | Package imported without an extra `pip install -e .`; 8 scripts, no exceptions |
| Server cold start | `streamlit run app.py`, timed to `/_stcore/health` = 200, offline, two runs | 1.5 s and 1.8 s |
| First page build | `AppTest` on `app.py` / `pages/overview.py`, offline | 1.5 s entry point; ~0.3 s per page script |
| App serves | `streamlit run app.py --server.port 8501` | HTTP 200, live mode reached NOAA SWPC |
| Public deployment | Streamlit Cloud browser smoke check | Root URL loaded live mode (latest Kp 2.00) with no login on 26 Oct 2026; `/overview` returns Page not found on this deployment |
| CI suite and container | GitHub Actions run `40329635430` (commit `595a1f1`) | Python 3.11 and 3.12 quality jobs passed; `container` job built the image, ran it offline, and polled the health endpoint |
| Animation export | `python main.py --offline --format mp4` | 391 frames at 6 fps, 65.2 s video, 1.0 MB, ffmpeg 6.1.1, ~3 min 39 s wall time (single run, not a benchmark) |
| Screenshots | `agent-browser` captures of the running app | `assets/screenshots/*.png`, offline sample, 1600 × 1000 viewport |

Not verified in this environment, and therefore not claimed anywhere: a local Docker build,
NASA DONKI behaviour with an API key, and live-mode behaviour during a real geomagnetic
storm. The CI container build and health check are verified in GitHub Actions. The public
root URL was smoke-checked in a browser with no login; the dashboard loaded in live mode.
