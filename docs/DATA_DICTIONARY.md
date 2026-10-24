# Data dictionary

Every artifact in this project is derived from one of the canonical frames below. The
column sets are defined once in `src/spaceweather/data_sources/base.py`
(`KP_COLUMNS`, `SOLAR_WIND_COLUMNS`) and are reused by every adapter, so a provider
change cannot silently alter what the pages receive.

Conventions that apply everywhere:

- **Timestamps** are UTC. In memory they are timezone-aware `datetime64[ns, UTC]`; in
  CSV and JSON exports they are ISO-8601 strings ending in `Z`.
- **A Kp timestamp marks the start of a three-hour interval**, not its midpoint or end.
- **Missing is missing.** Missing values are `NaN` (floats), `pd.NA` (nullable integers),
  or `true` in `is_missing`. They are never replaced with `0`, and nothing is
  interpolated or forward-filled.

## 1. Canonical Kp frame

Produced by `parse_recent_kp` (NOAA SWPC) and `parse_gfz_kp` (GFZ), then normalized by
`cleaning.normalize_kp_frame`.

| Column | Type | Unit | Meaning | Missing representation |
| --- | --- | --- | --- | --- |
| `time_utc` | datetime64[ns, UTC] | — | Start of the three-hour Kp interval | Rows with unparseable timestamps are dropped, with a validation issue |
| `kp` | float64 | unitless, 0–9 | Planetary Kp index | `NaN`; values outside 0–9 are masked, never clamped |
| `a_running` | Int64 | nT | Running `ap` amplitude reported with some Kp products | `pd.NA` when the provider does not supply it (GFZ does not) |
| `station_count` | Int64 | count | Number of observatories contributing | `pd.NA` when not supplied |
| `source` | string | — | `GFZ` or `NOAA SWPC` | `"unknown"` if absent |
| `status` | string | — | `definitive`, `preliminary`, or `unknown` (see §7) | `"unknown"` if absent |
| `is_missing` | bool | — | True when the row is flagged missing or `kp` is `NaN` | — |

`ap` (nT) is produced by the GFZ parser and is preserved *only if present* in the frame
that reaches `resampling.align_solar_wind_with_kp`. The canonical Kp columns do not
guarantee it; the bundled Kp samples do not contain it.

Sorting and de-duplication: rows are sorted by `time_utc` and duplicate timestamps keep
the **last** occurrence, so a newer source wins over an older one when frames are merged.

## 2. Canonical solar-wind frame

Produced by `parse_propagated_solar_wind` (NOAA SWPC, one-minute, **modeled**) and
`parse_omni2` (NASA OMNI2, hourly, observed).

| Column | Type | Unit | Meaning | Missing representation |
| --- | --- | --- | --- | --- |
| `time_utc` | datetime64[ns, UTC] | — | Observation time (hourly OMNI2 or one-minute propagated) | Invalid timestamps dropped |
| `speed_kms` | float64 | km/s | Proton bulk flow speed | `NaN` |
| `density_cm3` | float64 | protons/cm³ | Proton density | `NaN` |
| `temperature_k` | float64 | K | Proton temperature | `NaN` if the provider omits the field |
| `bz_gsm_nt` | float64 | nT (GSM) | North–south IMF component; negative values favour coupling | `NaN` |
| `bt_nt` | float64 | nT | IMF field magnitude | `NaN` |
| `source` | string | — | `NOAA SWPC` or `NASA OMNI2` | — |
| `status` | string | — | `estimated` (NOAA propagated) or `observed` (OMNI2) | — |
| `is_missing` | bool | — | True only when **all four** value columns are `NaN` for that row | — |

OMNI2 fill values are masked before this frame is built: `999` for `density`, `bz`,
`bt`; `9999` for `speed`; `9 999 999` for `temperature`. Region-2 propagated values use
the same thresholds. Rows where every selected field is missing are retained and flagged
rather than deleted, so coverage stays visible.

## 3. Three-hour solar-wind aggregate

`resampling.aggregate_solar_wind(frame, freq="3h")` aligns hourly or one-minute input to
the Kp cadence.

| Column | Unit | Meaning |
| --- | --- | --- |
| `time_utc` | — | **Left edge** of the three-hour bin (`label="left"`, `closed="left"`) |
| `speed_kms`, `density_cm3`, `bz_gsm_nt`, `bt_nt` | as above | Arithmetic **mean of the present** values in the bin |
| `n_samples` | count | Number of source rows that contributed |
| `coverage_fraction` | 0–1 | `n_samples / expected`, clipped at 1.0, where `expected` is the bin length divided by the median inferred cadence |

Bins with no observations are **absent** from the output, not zero. If the cadence cannot
be inferred (fewer than two timestamps), `coverage_fraction` is reported as `1.0` because
expectation is undefined rather than because coverage is complete — read it together with
`n_samples`.

## 4. Kp-aligned solar-wind frame

`resampling.align_solar_wind_with_kp` inner-joins the aggregate above with Kp on the
three-hour grid (`validate="one_to_one"`).

Columns are those of §3 plus:

| Column | Meaning |
| --- | --- |
| `kp` | Kp for the same left-labelled bin |
| `kp_status` | Renamed `status` from the Kp frame (`definitive` / `preliminary`) |
| `kp_source` | Renamed `source` from the Kp frame |
| `solar_wind_source` | `source` of the first non-null solar-wind row |
| `ap` | Present only if the Kp frame carried it (§1) |

An inner join is deliberate: a bin without both signals is excluded, and the resulting
`n` is always reported next to every statistic computed from this frame.

## 5. Storm event table

`events.events_to_frame(events)` — one row per contiguous run of qualifying observations.

| Column | Unit | Meaning |
| --- | --- | --- |
| `start_utc` | — | Timestamp of the first qualifying observation |
| `end_utc` | — | `start` of the **last** qualifying observation **plus three hours** |
| `duration_hours` | h | `end_utc - start_utc`; the sampled span, not the physical storm duration |
| `peak_kp` | Kp | Highest Kp inside the run |
| `mean_kp` | Kp | Mean of the qualifying Kp values |
| `sample_count` | count | Number of qualifying observations in the run |
| `expected_samples` | count | `round(duration_hours / 3)`, at least 1 |
| `missing_samples` | count | `expected_samples - sample_count`, floored at 0 |
| `threshold` | Kp | Threshold used for detection (default 5.0) |
| `status` | string | `definitive` if every row is definitive, `preliminary` if any is |
| `source` | string | Comma-joined distinct sources inside the run |
| `g_scale` | G1–G5 or null | `peak_kp` mapped by the NOAA G-scale bands (5 → G1 … 9 → G5) |

A gap of at most **two cadence steps** (six hours) does not break a run; the missing slots
are counted in `missing_samples`. A longer gap starts a new event. One qualifying
observation is reported as a three-hour run, not as a "storm" in the physical sense.

## 6. Correlation outputs

`analysis.correlations.correlate(x, y)` returns a dict (and the pages also export a
one-row table):

| Key | Meaning |
| --- | --- |
| `n` | Paired, non-missing observations used |
| `n_effective` | Approximate independent sample size from lag-1 autocorrelation, clamped to `[3, n]` |
| `pearson_r`, `pearson_p` | Pearson coefficient and two-sided p-value |
| `pearson_ci95_naive_low` / `_high` | Fisher z interval using `n` |
| `pearson_ci95_effective_low` / `_high` | Fisher z interval using `round(n_effective)` — the honest one for autocorrelated series |
| `spearman_rho`, `spearman_p` | Rank correlation and p-value |

`lagged_cross_correlation` returns `lag_hours`, `r`, `p_value`, `n`, with positive lags
meaning `x` leads `y`. Lags are multiples of the resampling step; the number of pairs
shrinks by one per step, which is why `n` is reported per row.

## 7. Status vocabulary

`models.DataStatus`:

| Value | Meaning |
| --- | --- |
| `observed` | A measurement, as published |
| `preliminary` | Published but subject to revision (recent NOAA Kp) |
| `definitive` | Final quality-controlled value (GFZ Kp) |
| `estimated` | A model or propagation product (NOAA propagated solar wind) |
| `forecast` | Reserved for future forecast products; not currently produced |
| `unknown` | Provenance not established |

The UI renders these as badges next to the number they describe, and provenance JSON
stores them verbatim.

## 8. Provenance JSON

`export.reports.build_provenance` → `models.Provenance`, written next to CSV/Parquet and
animation exports.

| Field | Content |
| --- | --- |
| `project` | Fixed project name |
| `software_version` | Installed distribution version, or source version when running from a checkout |
| `created_at` | Export time, UTC |
| `source_urls` | Sorted, distinct URLs actually requested |
| `retrieved_at` | Retrieval timestamps of each contributing source |
| `time_window_utc` | Min/max `time_utc` of the exported frame |
| `units` | Unit string per column (`DEFAULT_UNITS` extended by `DataFrame.attrs["units"]`) |
| `transformations` | Explicit list; always includes the window filter and the no-imputation statement |
| `missing_data_policy` | Fixed statement: missing observations stay missing |
| `animation` | Frame rate, stride, size, dpi, frame cap, seed, threshold (animation exports only) |
| `notes` | Data mode, sample flag, warnings, threshold, and per-source `SourceInfo` |

## 9. Bundled sample files

`data/samples/` holds genuine observations, never synthetic ones:

| File | Rows | Content | Source | License |
| --- | --- | --- | --- | --- |
| `kp_2003.csv` | 2,920 | Three-hour Kp for 2003 (includes the October 2003 storms) | GFZ | CC BY 4.0 |
| `kp_2024.csv` | 2,928 | Three-hour Kp for 2024 (includes the May 2024 superstorm) | GFZ | CC BY 4.0 |
| `omni_2024_05.csv` | ~744 | Hourly solar wind and IMF for May 2024 | NASA OMNI2 | NASA data guidance |
| `samples.json` | — | Retrieval times, URLs, row counts, units, citations | — | — |

The CSVs use the canonical column sets from §1 and §2, with timestamps serialized as
`YYYY-MM-DDTHH:MM:SSZ`. Synthetic fixtures exist only inside `tests/` and never reach
these files or any published figure.

## 10. Processed dataset

`scripts/build_dataset.py` (via `datasets.build_samples`) writes
`data/processed/kp_combined.parquet`: GFZ and NOAA Kp concatenated, sorted by `time_utc`,
de-duplicated keeping the last row per timestamp, with the canonical columns only. It is
git-ignored and regenerated on demand.
