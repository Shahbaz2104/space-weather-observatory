# Methodology and limitations

This project aims to be **scientifically legible**, not merely visually convincing. Every transformation that could change an interpretation is either exposed in the interface or recorded in provenance metadata.

## Time and cadence

- All timestamps are UTC.
- Kp is a three-hour planetary index. A timestamp such as `2024-05-10T03:00:00Z` labels the interval **beginning** at 03:00 UTC.
- Solar-wind measurements are aggregated onto the same left-labelled three-hour bins as Kp.
- Windows are inclusive of both endpoint dates in the interface. CSV/Parquet exports preserve the exact displayed rows.

## Missing data

- Missing Kp values remain missing and are flagged.
- Solar-wind fill values are masked as missing.
- Aggregated bins report `n_samples` and `coverage_fraction`.
- No interpolation, forward-fill, zero-fill, or synthetic gap closure is used.
- A bin can be absent from a chart without being treated as zero.

This matters because “quiet” and “unknown” are different physical statements.

## Storm detection

A storm event is a contiguous run of samples with **Kp ≥ threshold**. The default threshold is 5.0 (G1).

- A run may bridge one missing three-hour slot. Two missing slots break the run.
- `duration_hours` is the sampled span from the first qualifying sample to the end of the last qualifying three-hour interval. It is **not** a physical storm onset/end duration.
- `sample_count` is the number of qualifying observations; `missing_samples` counts interior gaps.
- `peak_kp` and `mean_kp` describe the sampled Kp values only.
- G-scale labels are activity classifications based on peak Kp. They are not official warnings.

A single Kp = 7 row therefore produces a three-hour event, not a claim that the storm physically lasted exactly three hours.

## Solar-wind aggregation

For each three-hour bin, the observatory computes the arithmetic mean of available samples for speed, density, Bz (GSM), and |B|. It also records:

- the number of contributing samples;
- the expected samples based on the inferred cadence;
- the coverage fraction, clipped to 1.0.

Partial bins may therefore contribute a mean computed from fewer samples. The correlation lab does not silently impute missing values; it drops bins where the selected variable is missing.

## Correlation and uncertainty

For paired observations `x` and `y`, the lab reports:

- Pearson's linear correlation;
- Spearman's rank correlation;
- the number of paired bins;
- an autocorrelation-adjusted effective sample size;
- a naive Fisher 95% interval using `n`;
- a Fisher 95% interval using the effective `n`.

The effective sample size is a diagnostic based on lag-1 autocorrelation, not a full time-series model. When the estimated effective `n` is three or fewer, the effective interval is undefined and reported as missing. This is intentional: a three-point “confidence interval” would be false precision.

P-values are descriptive and are not corrected for multiple comparisons, autocorrelation, or the number of variables the user may try.

## Lag analysis

Positive lag means the solar-wind variable **leads** Kp by that many hours. The lab evaluates a symmetric grid around zero and requires a regular three-hour grid. It does not claim physical causality.

## Heatmap and anomalies

- The heatmap aggregates by UTC hour of day and by calendar day/year.
- Historical comparisons depend on the completeness of the selected window.
- Anomalies are descriptive deviations from a chosen baseline, not physical mechanisms.
- Composite or “superposed epoch” views, where present, state their alignment convention.

## Modeled products

NOAA's seven-day propagated solar wind is a **model product**. It is useful context but is not equivalent to OMNI2 measurements or to a direct spacecraft observation at Earth. The interface labels it explicitly.

## Operational limitations

- NOAA Kp is preliminary and can be revised.
- GFZ definitive data may lag recent activity.
- Live endpoints can fail, rate-limit, or change schema.
- DONKI is optional and can be unavailable with an anonymous API key.
- Animation rendering is intentionally capped; offline full-year animations can be slow.
- The project does not issue alerts, predictions, or safety recommendations.

## Reproducibility

`build_provenance()` records:

- software version and creation time;
- source URLs and retrieval timestamps;
- UTC time window;
- units;
- transformations, including the no-interpolation policy;
- storm threshold and animation configuration;
- sample/live mode and warnings.

The exported JSON is the authoritative description of how a result was produced.
