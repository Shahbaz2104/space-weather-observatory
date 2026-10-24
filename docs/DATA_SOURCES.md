# Data sources and fallbacks

The observatory uses four data families. Every displayed result is accompanied by source metadata, and an optional provenance JSON records the exact source URLs and retrieval times.

## NOAA SWPC — recent observed Kp

- **Endpoint:** `https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json`
- **Cadence:** three hours (61 records for roughly seven days at the time of development)
- **Timestamp meaning:** start of the three-hour Kp interval
- **Status:** preliminary, observed
- **License:** U.S. Government work; public domain
- **Role:** live headline Kp, recent events, quickstart default
- **Fallback:** versioned GFZ sample when Auto mode is active

The JSON parser accepts both header-plus-row and list-of-object layouts. Invalid timestamps are dropped; Kp outside 0–9 is masked as missing rather than clamped.

## GFZ Helmholtz Centre — Kp and ap since 1932

- **Endpoint:** `https://kp.gfz.de/fileadmin/files_for_gfz_cms/Kp_ap_since_1932.txt`
- **Cadence:** three hours
- **Status:** definitive
- **License:** CC BY 4.0
- **Citation:** Matzka, J., Stolle, C., Yamazaki, Y., Bronkalla, O., & Morschhauser, A. (2021). The geomagnetic Kp index and derived indices of geomagnetic activity. *Space Weather*, 19, e2020SW002641. <https://doi.org/10.1029/2020SW002641>
- **Role:** historical windows, offline sample, long-term heatmap
- **Fallback:** live NOAA Kp when recent GFZ data are unavailable

The parser validates whitespace field counts so a truncated file cannot be silently padded into all-missing records. Missing Kp values (`-1`) are retained and flagged.

## NOAA SWPC — propagated solar wind

- **Endpoint:** `https://services.swpc.noaa.gov/products/geospace/propagated-solar-wind.json`
- **Cadence:** one minute, roughly seven days
- **Status:** **estimated / modeled**, not a direct in-situ measurement
- **License:** U.S. Government work; public domain
- **Role:** live solar-wind context and correlation input
- **Fallback:** NASA OMNI2 for historical windows; versioned OMNI sample when offline

The product is explicitly labeled `Modeled / propagated · not direct observation` in the interface. Fill values (`9999`, `999`, etc.) are masked as missing. No interpolation is performed.

## NASA OMNIWeb — OMNI2 hourly data

- **Endpoint template:** `https://spdf.gsfc.nasa.gov/pub/data/omni/low_res_omni/omni2_{year}.dat`
- **Cadence:** one hour
- **Status:** observed
- **License:** NASA data guidance; attribution requested
- **Role:** historical solar wind, IMF, and offline May 2024 sample
- **Fallback:** NOAA propagated solar wind for recent windows

OMNI2 files are validated for the expected 55 whitespace-separated fields before parsing. The loader masks OMNI fill values and marks rows where every selected field is missing. It does not zero-fill or interpolate gaps.

## NASA DONKI — optional

- **Base:** `https://api.nasa.gov/DONKI`
- **Status:** optional, disabled by default
- **License:** NASA API terms; a production key is recommended
- The project does not depend on DONKI for any dashboard page. Anonymous access can be rate-limited or unavailable.

## Validity and staleness

- HTTP responses are cached under `data/cache/` with per-product TTLs.
- A cache hit is disclosed with a `Cache used` badge.
- A stale cache is disclosed with a `Stale cache · source unavailable` badge.
- Live-only mode never substitutes sample data; it fails visibly.
- Offline mode never contacts the network.

## Source health

The UI distinguishes:

- **Live source** — a network-backed product was used.
- **Offline sample · not live** — the versioned genuine-data sample was used.
- **Modeled / propagated · not direct observation** — an estimated product.
- **Preliminary · may be revised** — recent Kp or similarly provisional data.
- **Cache used** / **Stale cache** — freshness caveats.
- **Timezone · UTC** — all timestamps and windows are UTC.
