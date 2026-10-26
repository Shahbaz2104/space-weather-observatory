# Deployment

Three supported ways to run the observatory: a local virtual environment, the Docker
image, and a hosted Streamlit runtime. Each one ends in the same place — a server on
`http://localhost:8501` (or the platform's assigned port) serving `app.py`.

**Status of each path in this repository's development environment:**

| Path | Verified here |
| --- | --- |
| Local virtual environment | Yes (`streamlit run app.py`, HTTP 200) |
| `pip install -r requirements.txt` in a clean venv, then all eight page scripts | Yes (clean-venv probe, `AppTest`, offline mode, no exceptions) |
| `docker build` / `docker run` / `docker compose up` | **Locally no** (Docker is not installed here); **yes in CI** (`container` job builds, runs offline, and polls `/_stcore/health`) |
| Public hosting URL | **Partially** — the Streamlit Cloud app loads at `/overview`; the root URL is blank because the app's main file is currently `main.py` |

The public app is live at
<https://space-weather-observatory-nsnhccmkm2xumzqopwzi7q.streamlit.app/overview>.
Its Streamlit Cloud settings currently point at `main.py`, so the bare root URL serves an
empty `main` page and falls back to the default multipage navigation. Set **Main file path**
to `app.py` and reboot before sharing the root URL. Until then, use the `/overview` link.

The GitHub Actions `container` job builds the Docker image, runs the container offline,
and confirms the health endpoint before stopping it. This verifies the packaging path;
local Docker remains unavailable in this development environment.

## 1. Local

Requires **Python 3.11+** (3.12 is used in development).

```bash
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements-dev.txt # runtime deps + pytest/ruff/mypy; installs the project itself
streamlit run app.py
```

`requirements.txt` ends with an editable install of this repository (`-e .`) because the
package uses a `src/` layout: `app.py` and every page import `spaceweather` directly. If
you skip that line, the app starts and then fails with `ModuleNotFoundError: spaceweather`.

Check that it is serving:

```bash
curl -fsS http://localhost:8501/_stcore/health   # -> ok
```

### Configuration

Copy `.env.example` to `.env` and adjust. Every setting uses the `SWO_` prefix and is
read by `spaceweather.config.Settings`; see the table in the [README](../README.md#configuration).
`.env` is git-ignored. No key is required for any page.

Useful overrides while developing:

```bash
SWO_OFFLINE_MODE=true  streamlit run app.py   # never touches the network
SWO_KP_STORM_THRESHOLD=6  streamlit run app.py # stricter event definition
```

Animation Studio reads its initial playback rate, figure size, and resolution from
`SWO_DEFAULT_ANIMATION_*`, and enforces `SWO_MAX_ANIMATION_FRAMES` on every export.
Charts cap rendered points at `SWO_DISPLAY_MAX_POINTS` (default 5,000) while metrics,
events, tables, and downloads keep every row.

### Writable paths

The app writes to `data/cache/` (HTTP response cache), `data/processed/` (rebuilt
datasets), and `output/` (figures, animations). All three are git-ignored and are
recreated on demand. The bundled `data/samples/` directory is read-only input.

## 2. Docker

The image is `python:3.12-slim`, installs `ffmpeg` (MP4 export) and `curl` (health check),
runs as the non-root user `app` (uid 10001), and exposes port 8501.

```bash
docker build -t space-weather-observatory .
docker run --rm -p 8501:8501 \
  -v "$PWD/data/cache:/app/data/cache" \
  -v "$PWD/output:/app/output" \
  space-weather-observatory
```

Or with Compose, which declares the same volumes as named volumes and forwards every
`SWO_*` setting from `.env`:

```bash
cp .env.example .env      # optional
docker compose up --build
docker compose down
```

The image health check is:

```bash
docker inspect --format '{{.State.Health.Status}}' space-weather-observatory
# or
curl -fsS http://localhost:8501/_stcore/health
```

Notes:

- Mount `data/cache` and `output` if you want the source cache and exported animations to
  survive `docker run --rm`. Named volumes in `compose.yaml` do this automatically.
- The offline sample is baked into the image; live mode still needs outbound network access.
- `ffmpeg` ships in the image, so MP4 export works there even when it is missing locally.
- The build was **not** executed in the environment that produced this repository. Treat
  the Dockerfile and `compose.yaml` as reviewed-but-unbuilt until you run them.

## 3. Hosted (Streamlit Community Cloud)

1. Push the repository to GitHub (public, or private with Cloud access granted).
2. In Streamlit Community Cloud, create an app pointing at:
   - **Repository:** your fork or copy of this project
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **Python version:** 3.12
3. No extra build command is needed. Cloud runs `pip install -r requirements.txt`, whose
   final `-e .` line installs the local package from `pyproject.toml`.
4. Add settings as **secrets** if you want non-default behaviour, for example:

   ```toml
   SWO_OFFLINE_MODE = "false"
   SWO_KP_STORM_THRESHOLD = "5.0"
   ```

   Streamlit exposes secrets to the app process as environment variables, which is what
   `Settings` reads. Never commit a `.env`, a secrets file, or an API key.

Constraints that matter on this platform:

- **Ephemeral filesystem.** `data/cache` and `output/` disappear on restart or redeploy, so
  caching is effectively per-session and exported animation files are not durable.
  Download an export in the same session you generate it.
- **Animation export.** GIF rendering is pure Python/Matplotlib and works, but is CPU- and
  memory-heavy; the app caps frames (`SWO_MAX_ANIMATION_FRAMES`, default 600). MP4 needs
  `ffmpeg`, which is not guaranteed on Cloud — the page falls back to GIF instead of
  crashing.
- **Cold start.** The first request after a restart re-downloads sources unless the cache
  is warm.
- **Free tier sleeps** after inactivity, so the first visit may take a while.

### Container hosts

Any host that runs a container works unchanged: expose port **8501**, set the health check
path to `/_stcore/health`, give it at least ~1 GB of memory (animation export is the peak),
and forward `SWO_*` variables. That path also gives you `ffmpeg` and a persistent volume,
which the free Streamlit tier does not.

### Network egress

Live mode needs outbound HTTPS to:

| Host | Used for |
| --- | --- |
| `services.swpc.noaa.gov` | Recent observed Kp, propagated solar wind, snapshots |
| `kp.gfz.de` | Definitive Kp archive since 1932 |
| `spdf.gsfc.nasa.gov` | OMNI2 hourly solar wind and IMF |
| `api.nasa.gov` | Optional DONKI integration, disabled by default |

If egress is blocked, run with `SWO_OFFLINE_MODE=true`: the app then uses the versioned
genuine-data sample and labels every screen accordingly. It never presents sample data as
live.

## 4. Post-deployment verification

Run these in order after any deployment:

```bash
curl -fsS https://<host>/_stcore/health                  # 200 + "ok"
```

Then in the browser:

1. The sidebar badge reads **Live source** (not the offline-sample badge) if egress works.
2. Overview shows a latest Kp value with a timestamp within roughly the last three hours and
   a **Preliminary · may be revised** badge.
3. Storm Explorer finds at least one run when the window contains a Kp ≥ 5 period.
4. Correlation Lab reports `n` and `n_effective` rather than a bare coefficient.
5. Animation Studio exports a short GIF in offline mode, and the export includes a
   provenance JSON.

If step 1 fails with a network error and step 2 shows the sample badge, the app is working
as designed — the source is unreachable, not the application.

## 5. Reproducing the build locally

```bash
make install    # venv + dev dependencies
make check      # ruff + mypy + pytest
make run        # streamlit
make quickstart # static PNG + GIF via main.py
make animate    # MP4 export (requires ffmpeg)
```

`make install` uses `requirements-dev.txt`, which includes `requirements.txt` and therefore
the editable install of this package.
