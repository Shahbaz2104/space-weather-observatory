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
A space weather chart can look calm when the data is simply missing.

A gap gets drawn as a flat line. A smooth curve looks like a real measurement. One high number gets read as a storm.

I built the Space Weather Observatory, a free seven-page web app, to make those differences visible.

Space weather is how the Sun's activity affects Earth's magnetic field. Strong storms can disrupt satellites, GPS, power grids, and radio. The app uses real data from NOAA, GFZ, and NASA to make those events easier to inspect.

What you can do:
→ See the latest Kp value. Kp is a 0–9 scale of how disturbed Earth's magnetic field is.
→ Explore past storms and the missing data around them.
→ View a heatmap of activity over many years.
→ Compare the solar wind (the stream of particles from the Sun) with Earth's response.
→ See why two things moving together does not mean one caused the other.
→ Watch the May 2024 storm unfold.
→ Check where every number came from.

From the built-in May 2024 sample:
• The strongest reading was Kp 9.00, a G5 — the top storm category.
• The app found six periods above the storm threshold.
• Solar wind speed and Kp tended to rise together. The correlation was 0.63, where 1 means they move together perfectly. But a storm lasts for hours, so consecutive readings are not independent. The 243 three-hour readings are worth only about 21 separate pieces of evidence. The pattern is there, but less certain than the raw count suggests.

The rules I tried to keep:
• Missing data stays missing. No filling gaps or drawing them as zero.
• Computer-model results are labelled as estimates, not as direct measurements.
• Every chart and download can show where its numbers came from and when.
• No forecast is presented as an observation.
• This is not an official forecast or warning service.

The project has 58 automated tests and code checks, so those rules are less likely to break without anyone noticing.

Live demo and code are in the first comment.

Which of these rules would you want every dashboard to follow?

#SpaceWeather #DataVisualization #Python #Streamlit #OpenSource
```

## Short version

```text
A missing reading is not a quiet day.

The Space Weather Observatory is a free seven-page web app about space weather: geomagnetic storms, solar wind, and the Kp index (a 0–9 scale of how disturbed Earth's magnetic field is). It uses real NOAA, GFZ, and NASA data.

It does not fill in gaps. It labels model output as model output. Every chart and download can show where its numbers came from.

From the May 2024 sample: the strongest Kp was 9.00 (G5, the top storm category). Solar wind speed and Kp tended to rise together (correlation 0.63), but a storm lasts for hours, so consecutive readings are not independent. The 243 three-hour readings are worth only about 21 separate pieces of evidence. The pattern is there, but less certain than it looks.

58 automated tests. Live demo and code are in the first comment.

#SpaceWeather #DataVisualization #Python #Streamlit #OpenSource
```

## First comment

Post this immediately after publishing so the post body stays link-free.

```text
Live demo: https://space-weather-observatory-4xedxr5f2n5vpym7t5ix7p.streamlit.app
Repository: https://github.com/Shahbaz2104/space-weather-observatory
Methodology: https://github.com/Shahbaz2104/space-weather-observatory/blob/main/docs/METHODOLOGY.md

Data: NOAA SWPC (current Kp and modeled solar wind), GFZ Helmholtz Centre for Geosciences (long-term Kp archive, CC BY 4.0), and NASA OMNIWeb (historical solar wind). The May 2024 numbers are from the app's built-in sample, not current conditions. The app labels live and sample data separately.
```

## Carousel copy

| Slide | On-image copy | Source visual |
| --- | --- | --- |
| 1 | **When the Sun disrupts Earth.** A clear, honest look at geomagnetic storms: real data, visible sources, and no made-up values. | Overview, May 2024 sample |
| 2 | **Three ways a chart can lie.** A gap drawn as calm. A smooth line drawn as real data. One high number mistaken for a storm. | Typographic |
| 3 | **Seven linked views. One shared timeline.** Overview, Storm Explorer, Activity Heatmap, Solar Wind, Correlation Lab, Animation Studio, Methodology. | Activity Heatmap |
| 4 | **Missing stays missing.** No filled gaps. No fake zeros. No hidden gaps. Charts keep the edges of every gap. | Storm Explorer, plus a source record |
| 5 | **Moving together is not proof.** Correlation 0.627 · 21.2 separate pieces of evidence · 243 readings. The lab shows how much evidence is behind the number. | Correlation Lab |
| 6 | **Seven pages. Real data.** Live demo and repository. 58 tests · automated checks · open source. | Solar Wind |

Every screenshot slide is captioned as sample data, not live. Do not remove that caption: the
figures are from the built-in May 2024 record, not current conditions.

## Alt text

Use these when LinkedIn offers an alt-text field.

- **Hero:** Dark navy card titled “When the Sun disrupts Earth.” with a screenshot of the observatory overview showing the May 2024 Kp peak of 9.00, a G5 badge, and source labels for NOAA, GFZ, and NASA.
- **Banner:** Wide banner with the project title, repository URL, and a Kp timeline from the May 2024 sample data.
- **Slide 1:** Carousel cover titled “When the Sun disrupts Earth.” with the observatory overview, NOAA/GFZ/NASA labels, and “58 tests.”
- **Slide 2:** Slide listing three misleading chart defaults: a gap drawn as calm, a smooth line drawn as real data, and one high number mistaken for a storm.
- **Slide 3:** Slide titled “Seven linked views. One shared timeline.” with seven page labels and a screenshot of the activity heatmap.
- **Slide 4:** Slide titled “Missing stays missing.” with a Storm Explorer screenshot and a note that every download can include a source record.
- **Slide 5:** Slide titled “Moving together is not proof.” with correlation 0.627, 21.2 separate pieces of evidence, 243 readings, and a screenshot of the Correlation Lab.
- **Slide 6:** Closing slide with the live demo URL, repository URL, 58 tests, automated checks, open source, and a solar-wind chart from the sample data.
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
