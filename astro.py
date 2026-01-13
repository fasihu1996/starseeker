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

    starchart = {
        "acamar": 13847,
        "achernar": 7588,
        "acrux": 60718,
        "adhara": 33579,
        "agena": 68702,
        "albireo": 95947,
        "alcor": 65477,
        "alcyone": 17702,
        "aldebaran": 21421,
        "alderamin": 105199,
        "algenib": 1067,
        "algieba": 50583,
        "algol": 14576,
        "alhena": 31681,
        "alioth": 62956,
        "alkaid": 67301,
        "almaak": 9640,
        "alnair": 109268,
        "alnath": 25428,
        "alnilam": 26311,
        "alnitak": 26727,
        "alphard": 46390,
        "alphekka": 76267,
        "alpheratz": 677,
        "alshain": 98036,
        "altair": 97649,
        "ankaa": 2081,
        "antares": 80763,
        "arcturus": 69673,
        "arneb": 25985,
        "babcock's star": 112247,
        "barnard's star": 87937,
        "bellatrix": 25336,
        "betelgeuse": 27989,
        "campbell's star": 96295,
        "canopus": 30438,
        "capella": 24608,
        "caph": 746,
        "castor": 36850,
        "cor caroli": 63125,
        "cyg x-1": 98298,
        "deneb": 102098,
        "denebola": 57632,
        "diphda": 3419,
        "dubhe": 54061,
        "enif": 107315,
        "etamin": 87833,
        "fomalhaut": 113368,
        "groombridge 1830": 57939,
        "hadar": 68702,
        "hamal": 9884,
        "izar": 72105,
        "kapteyn's star": 24186,
        "kaus australis": 90185,
        "kocab": 72607,
        "kruger 60": 110893,
        "luyten's star": 36208,
        "markab": 113963,
        "megrez": 59774,
        "menkar": 14135,
        "merak": 53910,
        "mintaka": 25930,
        "mira": 10826,
        "mirach": 5447,
        "mirphak": 15863,
        "mizar": 65378,
        "nihal": 25606,
        "nunki": 92855,
        "phad": 58001,
        "pleione": 17851,
        "polaris": 11767,
        "pollux": 37826,
        "procyon": 37279,
        "proxima": 70890,
        "rasalgethi": 84345,
        "rasalhague": 86032,
        "red rectangle": 30089,
        "regulus": 49669,
        "rigel": 24436,
        "rigil kent": 71683,
        "sadalmelik": 109074,
        "saiph": 27366,
        "scheat": 113881,
        "shaula": 85927,
        "shedir": 3179,
        "sheliak": 92420,
        "sirius": 32349,
        "spica": 65474,
        "tarazed": 97278,
        "thuban": 68756,
        "unukalhai": 77070,
        "van maanen 2": 3829,
        "vega": 91262,
        "vindemiatrix": 63608,
        "zaurak": 18543,
    }

    # Special cases for Sun since not listed by Hipparcos ID
    if objtype == "star" and skyobject.lower() != "sun":
        hip_id = 0
        if skyobject.lower() in starchart:
            hip_id = starchart[skyobject.lower()]
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

    con_az = azimuth_deg
    con_alt = altitude_deg

    # if in green area
    if 270 < azimuth_deg or azimuth_deg < 90:
        inter = 450 - azimuth_deg
        con_az = inter % 360

    # if in red area
    if 91 < azimuth_deg < 269:
        con_az = azimuth_deg + 180
        inter = 450 - con_az
        con_az = inter % 360

    # adjust altitude because of shift into green area
        altitude_deg = 180 - altitude_deg

    return azimuth_deg, altitude_deg, con_az, con_alt

def transmit(raw_url: str, altitude: float, azimuth: float):
    """Function to transmit the calculated values as altitude and azimuth
    to provided Arduino webserver URL."""
    transmit_url = raw_url + f"/alt={altitude}&az={azimuth}"
    res = requests.get(transmit_url)
    return res.status_code

