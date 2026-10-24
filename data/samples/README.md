# Offline sample data

This directory contains a **small, versioned sample of genuine observations** used
by the application's offline demo mode. It is not a live feed.

| File | Rows | Content | Source | License |
|------|------|---------|--------|---------|
| `kp_2003.csv` | 2,920 | Three-hour Kp for 2003 | GFZ Helmholtz Centre for Geosciences | CC BY 4.0 |
| `kp_2024.csv` | 2,928 | Three-hour Kp for 2024 | GFZ Helmholtz Centre for Geosciences | CC BY 4.0 |
| `omni_2024_05.csv` | ~744 | Hourly solar wind for May 2024 | NASA OMNI2 | NASA usage guidance |

`kp_2003.csv` includes the late-October 2003 "Halloween" storms, and
`kp_2024.csv` includes the May 2024 superstorm. The fused sample gives the
heatmap and event explorer more than one year to compare without shipping a
large historical archive.

`samples.json` records retrieval time, source URLs, row counts, units, and the
required citations. Regenerate everything with:

```bash
.venv/bin/python scripts/fetch_data.py
```

Column times are UTC. Missing observations remain missing; they are never
replaced with zero. The bundled sample is deliberately excluded from any claim
of being current or live.
