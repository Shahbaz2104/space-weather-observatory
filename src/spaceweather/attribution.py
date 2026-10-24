"""Static attribution for every data provider used by the project."""

from __future__ import annotations

from spaceweather.models import Attribution

NOAA_SWPC = Attribution(
    key="noaa_swpc",
    name="NOAA Space Weather Prediction Center",
    url="https://www.swpc.noaa.gov/",
    license="U.S. Government work; public domain",
    citation=(
        "NOAA Space Weather Prediction Center, planetary K-index and solar-wind "
        "products. https://www.swpc.noaa.gov/"
    ),
)

GFZ_KP = Attribution(
    key="gfz_kp",
    name="GFZ Helmholtz Centre for Geosciences (Kp index)",
    url="https://kp.gfz.de/",
    license="CC BY 4.0",
    citation=(
        "Matzka, J., Stolle, C., Yamazaki, Y., Bronkalla, O., & Morschhauser, A. "
        "(2021). The geomagnetic Kp index and derived indices of geomagnetic "
        "activity. Space Weather, 19, e2020SW002641. "
        "https://doi.org/10.1029/2020SW002641"
    ),
)

NASA_OMNI = Attribution(
    key="nasa_omni",
    name="NASA OMNIWeb / Space Physics Data Facility",
    url="https://omniweb.gsfc.nasa.gov/",
    license="NASA data usage guidance; attribution requested",
    citation=(
        "NASA Space Physics Data Facility, OMNI2 hourly interplanetary magnetic "
        "field and solar-wind data. https://omniweb.gsfc.nasa.gov/"
    ),
)

NASA_DONKI = Attribution(
    key="nasa_donki",
    name="NASA DONKI",
    url="https://api.nasa.gov/DONKI/",
    license="NASA API terms of use; API key required for production use",
    citation="NASA Space Weather Database Of Notifications, Knowledge, Information (DONKI).",
)

ATTRIBUTIONS = [NOAA_SWPC, GFZ_KP, NASA_OMNI, NASA_DONKI]
