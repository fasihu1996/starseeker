from datetime import datetime, timezone

from skyfield.api import load, Star
from skyfield.data import hipparcos

from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from astropy import units as u

import requests

# Load ephemeris and timescale. Downloaded if not found in project dir.
eph = load("de421.bsp")
ts = load.timescale()

# Load Hipparcos star catalog. Downloaded if not found in project dir.
with load.open(hipparcos.URL) as f:
    df = hipparcos.load_dataframe(f)


def seek(skyobject: str, objtype: str):
    """
    Resolve 'skyobject' of type 'objtype' into apparent RA/Dec as seen from Earth now.
    Returns (ra, dec) as Skyfield Angle objects for further conversion.
    """

    # convert objtype for comparisons
    objtype = objtype.lower()

    # create earth object for apparent tracking
    earth = eph["earth"]
    t = ts.now()

    # Special cases for Sun since not listed by Hipparcos ID
    if objtype == "star" and skyobject.lower() != "sun":
        hip_id = int(skyobject)
        star_data = df.loc[hip_id]
        skyo = Star.from_dataframe(star_data)
        apparent = earth.at(t).observe(skyo).apparent()

    # Mapping common names to skyfield astronomic designations
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

    # Only Earth's moon can be found with this
    elif objtype == "moon":
        skyo = eph["moon"]
        apparent = earth.at(t).observe(skyo).apparent()

    # TODO: Possibly remove this since we have not used it so far
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

    # Calculate apparent positions (as visible in the sky) instead of astronomic positions
    ra, dec, distance = apparent.radec()
    print(f"RA: {ra}, Dec: {dec}")
    return ra, dec


def convert(right_ascension, declination,
            lat_deg: float = 52.41094790018972,
            lon_deg: float = 12.538302555315548,
            height_m: float = 36.0):
    """
    Convert RA/Dec (Skyfield Angle objects) to Azimuth and Altitude
    for given EarthLocation and current UTC time, using Astropy.
    Default coordinates use the location of the department of computer science
    and media at the University of Applied Sciences Brandenburg.
    """
    # Target as provided
    target = SkyCoord(
        ra=right_ascension.hours * u.hour,
        dec=declination.degrees * u.deg,
        frame="icrs",
    )
    # Three-dimensional observation location
    location = EarthLocation(
        lat=lat_deg * u.deg,
        lon=lon_deg * u.deg,
        height=height_m * u.m,
    )
    # Create timezone aware datetime object for conversion to UTC
    curr_utc = datetime.now().astimezone().astimezone(timezone.utc)
    obstime = Time(curr_utc, scale="utc")

    altaz_frame = AltAz(obstime=obstime, location=location)
    altaz = target.transform_to(altaz_frame)

    azimuth_deg = altaz.az.degree
    altitude_deg = altaz.alt.degree

    # if in green area
    if 280 < azimuth_deg or azimuth_deg < 80:
        if 280 < azimuth_deg < 360:
            azimuth_deg -= 270
        if 0 < azimuth_deg < 80:
            azimuth_deg += 90

    # if in red area
    if 81 < azimuth_deg < 279:
        if 81 < azimuth_deg < 180:
            azimuth_deg += 180
        if 181 < azimuth_deg < 279:
            azimuth_deg -= 180

    # adjust altitude because of shift into green area
        altitude_deg = 180 - altitude_deg

    return azimuth_deg, altitude_deg

def transmit(raw_url: str, altitude: float, azimuth: float):
    """Function to transmit the calculated values as altitude and azimuth
    to provided Arduino webserver URL."""
    transmit_url = raw_url + f"/alt={altitude}&az={azimuth}"
    res = requests.get(transmit_url)
    return res.status_code

