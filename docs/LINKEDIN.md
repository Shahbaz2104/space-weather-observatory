# LinkedIn kit: Space Weather Observatory

A ready-to-publish set of copy, images, and checks for the project. The images use genuine
screenshots captured from the running app in offline sample mode, not mockups. The deployed
app is live at its root URL and opens on the Overview page.

## Assets

| File | Size | Use |
| --- | --- | --- |
| `assets/linkedin/space-weather-linkedin-carousel.pdf` | 6 pages, 1080 × 1350 | Preferred: upload as a LinkedIn document post |
| `assets/linkedin/linkedin-carousel-01-cover.png` | 1080 × 1350 | Carousel slide 1 / fallback image post |
| `assets/linkedin/linkedin-carousel-02-problem.png` | 1080 × 1350 | Carousel slide 2 |
| `assets/linkedin/linkedin-carousel-03-views.png` | 1080 × 1350 | Carousel slide 3 |
| `assets/linkedin/linkedin-carousel-04-integrity.png` | 1080 × 1350 | Carousel slide 4 |
| `assets/linkedin/linkedin-carousel-05-statistics.png` | 1080 × 1350 | Carousel slide 5 |
| `assets/linkedin/linkedin-carousel-06-closing.png` | 1080 × 1350 | Carousel slide 6 |
| `assets/linkedin/linkedin-hero-1200x627.png` | 1200 × 627 | Single-image post or link preview |
| `assets/linkedin/linkedin-banner-1584x396.png` | 1584 × 396 | Profile or company-page banner |

Regenerate everything with:

```bash
python3 scripts/build_linkedin_assets.py
```

The script uses Pillow, the screenshots in `assets/screenshots/`, and Inter when available.
It writes the PNGs and the six-page PDF to `assets/linkedin/`.

## Before publishing

The live app is configured with `app.py` as its **main file** and opens the styled dashboard
at the root URL. The `/overview` path is not a route on this deployment; use the root URL.
The dashboard pages are reachable at `/storm_explorer`, `/heatmap`, `/solar_wind`,
`/correlation`, `/animation`, and `/methodology`.

Do this before posting the live link:

1. Open the root URL in a private/incognito window and confirm it loads without a login.
2. Push the repository changes and wait for the `quality` and `container` jobs to pass.
3. Re-check the live app against the screenshots. If it looks unstyled or the screenshots do
   not match it, omit the live link and re-render slide 6 without the `LIVE DEMO` block.

The live demo URL is:

`https://space-weather-observatory-4xedxr5f2n5vpym7t5ix7p.streamlit.app`

## Main post

Use the PDF as a document post, or the six PNGs in order. Put the repo and live link in the
first comment rather than the post body.

```text
Space weather charts can lie without a single bad data point.

A missing observation can be drawn as quiet. An interpolated curve can look like a measurement. A Kp value can be mistaken for a storm.

I built the Space Weather Observatory to make those distinctions visible.

It is a seven-page Streamlit app for geomagnetic storms, solar wind, and the Kp index:

→ Overview: current Kp, G-scale context, storm runs, and source health.
→ Storm Explorer: threshold-based event forensics with missing-slot accounting.
→ Activity Heatmap: year/month and hour-of-day structure, with absent cells left absent.
→ Solar Wind: modeled NOAA propagation or OMNI2 observations, clearly labelled, beside the geomagnetic response.
→ Correlation Lab: association with effective sample size and autocorrelation-aware intervals.
→ Animation Studio: deterministic observed-Kp playback with provenance.
→ Methodology: every convention and caveat in one place.

The data comes from NOAA SWPC, the GFZ Helmholtz Centre for Geosciences, and NASA OMNIWeb. Values keep their source, timestamp, units, and status — observed, preliminary, definitive, or modeled.

On the bundled May 2024 sample:
• peak Kp 9.00 (G5)
• six detected threshold runs
• solar-wind speed vs Kp: r = 0.627, but effective n = 21.2 on 243 paired bins

That last number is the point. 243 autocorrelated three-hour bins are not 243 independent observations, so the naive confidence interval is too narrow.

The engineering rules are simple to state and hard to keep:
• missing stays missing — no interpolation, forward-fill, or zero-fill
• display sampling keeps endpoints and missing-gap boundaries
• metrics, events, tables, and exports use every row
• provenance is available as JSON for exports
• no forecast is dressed up as an observation

The project has 58 tests, Ruff and mypy checks, and a GitHub Actions workflow. It runs in offline sample mode with genuine observations, so the interface can be inspected without a live feed.

Live demo and repository are in the first comment.

If you work with operational space-weather data: which caveat would you put first?

#SpaceWeather #DataVisualization #Python #Streamlit #OpenSource
```

## Short version

```text
A missing observation is not a quiet day.

The Space Weather Observatory is a seven-page Streamlit app for geomagnetic storms, solar wind, and the Kp index — built on NOAA, GFZ, and NASA data, with no interpolation, no zero-fill, and JSON provenance for exports.

On the bundled May 2024 sample: peak Kp 9.00 (G5). Solar-wind speed vs Kp: r = 0.627, effective n = 21.2 on 243 paired bins. 243 autocorrelated bins are not 243 independent observations.

58 tests. Ruff and mypy. Live demo and repo in the first comment.

#SpaceWeather #DataVisualization #Python #Streamlit #OpenSource
```

## First comment

Post this immediately after publishing so the post body stays link-free.

```text
Live demo: https://space-weather-observatory-4xedxr5f2n5vpym7t5ix7p.streamlit.app
Repository: https://github.com/Shahbaz2104/space-weather-observatory
Methodology: https://github.com/Shahbaz2104/space-weather-observatory/blob/main/docs/METHODOLOGY.md

Data: NOAA SWPC (Kp and propagated solar wind), GFZ Helmholtz Centre for Geosciences (Kp/ap, CC BY 4.0), NASA OMNIWeb (OMNI2). The May 2024 figures come from the bundled sample; the app labels live mode and offline mode separately.
```

## Carousel copy

| Slide | On-image copy | Source visual |
| --- | --- | --- |
| 1 | **When the Sun disrupts Earth.** An evidence-first observatory for geomagnetic storms: real observations, explicit uncertainty, and no zero-fill. | Overview, May 2024 offline sample |
| 2 | **Three ways a chart can lie.** A gap drawn as quiet. An interpolated curve drawn as measurement. A Kp value confused with a storm. | Typographic |
| 3 | **Seven linked views. One time convention.** Overview, Storm Explorer, Activity Heatmap, Solar Wind, Correlation Lab, Animation Studio, Methodology. | Activity Heatmap |
| 4 | **Missing stays missing.** No interpolation. No zero-fill. No silent gap closure. Display sampling keeps endpoints and missing-run boundaries. | Storm Explorer, plus JSON provenance |
| 5 | **A correlation is not a mechanism.** Pearson r 0.627 · effective n 21.2 · 243 paired bins. The lab reports the sample size, not just the coefficient. | Correlation Lab |
| 6 | **Seven pages. Real observations.** Live demo and repository. 58 tests · Ruff · mypy. | Solar Wind |

Every screenshot slide carries a visible `Offline sample · not live` caption. Do not remove
that caption: the figures are from the bundled May 2024 record, not current conditions.

## Alt text

Use these when LinkedIn offers an alt-text field.

- **Hero:** Dark navy card titled “When the Sun disrupts Earth.” with a screenshot of the observatory overview showing the May 2024 Kp peak of 9.00, a G5 badge, and source labels for NOAA, GFZ, and NASA.
- **Banner:** Wide banner with the project title, repository URL, and a Kp timeline from the May 2024 offline sample.
- **Slide 1:** Carousel cover titled “When the Sun disrupts Earth.” with the observatory overview, NOAA/GFZ/NASA labels, and “58 tests.”
- **Slide 2:** Slide listing three misleading chart defaults: a gap drawn as quiet, an interpolated curve drawn as measurement, and a Kp value confused with a storm.
- **Slide 3:** Slide with seven page labels and a screenshot of the geomagnetic activity heatmap.
- **Slide 4:** Slide titled “Missing stays missing.” with a Storm Explorer screenshot and a note that JSON provenance is available for exports.
- **Slide 5:** Slide with Pearson r 0.627, effective n 21.2, 243 paired bins, and a screenshot of the Correlation Lab.
- **Slide 6:** Closing slide with the live demo URL, repository URL, 58 tests, and a solar-wind chart from the offline sample.
- **PDF:** Six-slide carousel about the Space Weather Observatory, covering the problem, seven linked views, missing-data policy, correlation statistics, and links to the live demo and repository.

## Posting checklist

- [x] Set the Streamlit Cloud **Main file path** to `app.py` and reboot.
- [x] Confirm the root URL loads without a login.
- [x] Run `pytest -q`, `ruff check .`, and `mypy src`; the current suite is 58 tests.
- [x] Push and confirm the GitHub Actions `quality` and `container` jobs pass. (Passed on commit `595a1f1`.)
- [x] Run `python3 scripts/build_linkedin_assets.py` after any copy or screenshot change.
- [ ] Upload `space-weather-linkedin-carousel.pdf` as a document post. Suggested title: “When the Sun disrupts Earth — Space Weather Observatory.”
- [ ] Add the first comment with the live demo and repository.
- [ ] Add alt text to every image, or use the document description.
- [ ] Check the post on mobile: the carousel is 4:5, the hero is 1.91:1.
- [ ] Do not claim a live forecast, current conditions, or official storm warnings.

## Accuracy notes

- Kp 9.00, G5, and the six detected runs refer to the bundled **May 2024 sample**, not current
  space weather.
- The correlation values (r = 0.627, effective n = 21.2, 243 paired bins) are also from that
  sample and are reported with an autocorrelation-aware effective sample size.
- “No interpolation / no zero-fill” describes the app’s data handling. Modeled NOAA
  propagation is labelled as modeled, not presented as a direct measurement.
- The live app has a live mode and a labelled offline sample; it is not an operational
  forecast or warning service.
- CI run `40329635430` (commit `595a1f1`) passed both Python quality jobs and the `container`
  build/offline-run/health-check job. Re-check after future pushes; local Docker is unavailable.
- NOAA, GFZ, and NASA are data providers, not project partners. Do not imply their endorsement.
