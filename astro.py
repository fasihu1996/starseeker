from datetime import datetime, timezone

from skyfield.api import load, Star
from skyfield.data import hipparcos

from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from astropy import units as u

import requests

# Load ephemeris and timescale once
eph = load("de421.bsp")
ts = load.timescale()

# Load Hipparcos star catalog once
with load.open(hipparcos.URL) as f:
    df = hipparcos.load_dataframe(f)


def seek(skyobject: str, objtype: str):
    """
    Resolve 'skyobject' of type 'objtype' into apparent RA/Dec as seen from Earth now.
    Returns (ra, dec) as Skyfield Angle objects.
    """
    objtype = objtype.lower()
    earth = eph["earth"]
    t = ts.now()

    if objtype == "star" and skyobject.lower() != "sun":
        hip_id = int(skyobject)
        star_data = df.loc[hip_id]
        skyo = Star.from_dataframe(star_data)
        apparent = earth.at(t).observe(skyo).apparent()

    elif objtype == "planet" or skyobject.lower() == "sun":
        planet_map = {
            "mercury": "mercury",
            "venus": "venus",
            "mars": "mars",
            "jupiter": "jupiter barycenter",
            "saturn": "saturn barycenter",
            "uranus": "uranus barycenter",
            "neptune": "neptune barycenter",
            "pluto": "pluto barycenter",
            "sun": "sun",
        }
        key = planet_map.get(skyobject.lower())
        if key is None:
            raise ValueError(f"Unknown planet: {skyobject}")
        skyo = eph[key]
        apparent = earth.at(t).observe(skyo).apparent()

    elif objtype == "moon":
        skyo = eph["moon"]
        apparent = earth.at(t).observe(skyo).apparent()

    elif objtype == "satellite":
        stations_url = (
            "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
        )
        satellites = load.tle_file(stations_url, reload=True)
        by_name = {sat.name.lower(): sat for sat in satellites}
        skyo = by_name.get(skyobject.lower())
        if skyo is None:
            raise ValueError(f"Unknown satellite: {skyobject}")
        apparent = (skyo - earth).at(t).apparent()

    else:
        raise ValueError(f"Unknown object type: {objtype}")

    ra, dec, distance = apparent.radec()
    print(f"RA: {ra}, Dec: {dec}")
    return ra, dec


def convert(right_ascension, declination,
            lat_deg: float = 52.0,
            lon_deg: float = 13.0,
            height_m: float = 50.0):
    """
    Convert RA/Dec (Skyfield Angle objects) to (azimuth_deg, altitude_deg)
    for given EarthLocation and current UTC time, using Astropy.
    """
    target = SkyCoord(
        ra=right_ascension.hours * u.hour,
        dec=declination.degrees * u.deg,
        frame="icrs",
    )
    location = EarthLocation(
        lat=lat_deg * u.deg,
        lon=lon_deg * u.deg,
        height=height_m * u.m,
    )
    curr_utc = datetime.now().astimezone().astimezone(timezone.utc)
    obstime = Time(curr_utc, scale="utc")

    altaz_frame = AltAz(obstime=obstime, location=location)
    altaz = target.transform_to(altaz_frame)

    azimuth_deg = altaz.az.degree
    altitude_deg = altaz.alt.degree

    if 90 < azimuth_deg < 270:
        azimuth_deg = azimuth_deg - 180
        altitude_deg = 180 - altitude_deg

    if 270 < azimuth_deg <= 360:
        azimuth_deg = azimuth_deg - 360

    return azimuth_deg, altitude_deg

def transmit(raw_url: str, altitude: float, azimuth: float):
    transmit_url = raw_url + f"/alt={altitude}&az={azimuth}"
    res = requests.get(transmit_url)
    return res.status_code

