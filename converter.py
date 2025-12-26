from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from astropy import units as u
import datetime

from skyfield.api import load, Star
from skyfield.data import hipparcos

# Load ephemeris and timescale once at module level
eph = load('de421.bsp')  # planets, sun, moon
ts = load.timescale()

# Load Hipparcos star catalog for named stars
with load.open(hipparcos.URL) as f:
    df = hipparcos.load_dataframe(f)

uni = EarthLocation(lat=52.41095680655865*u.deg, lon=12.53826803317537*u.deg, height=40*u.m)

def seek(skyobject, objtype):
    objtype = objtype.lower()
    earth = eph['earth']
    t = ts.now()

    if objtype == "star":
        # Try common star names via Hipparcos
        star_names = {
            'polaris': 11767,
            'sirius': 32349,
            'vega': 91262,
            'betelgeuse': 27989,
            'rigel': 24436,
            'arcturus': 69673,
            'aldebaran': 21421,
            'antares': 80763,
            'spica': 65474,
            'capella': 24608,
        }
        hip_id = star_names.get(skyobject.lower())
        if hip_id is None:
            raise ValueError(f"Unknown star: {skyobject}")
        star_data = df.loc[hip_id]
        skyo = Star.from_dataframe(star_data)
        astrometric = earth.at(t).observe(skyo)
        apparent = astrometric.apparent()

    elif objtype == "planet":
        # Map common names to ephemeris keys
        planet_map = {
            'mercury': 'mercury',
            'venus': 'venus',
            'mars': 'mars',
            'jupiter': 'jupiter barycenter',
            'saturn': 'saturn barycenter',
            'uranus': 'uranus barycenter',
            'neptune': 'neptune barycenter',
            'pluto': 'pluto barycenter',
            'sun': 'sun',
        }
        key = planet_map.get(skyobject.lower())
        if key is None:
            raise ValueError(f"Unknown planet: {skyobject}")
        skyo = eph[key]
        astrometric = earth.at(t).observe(skyo)
        apparent = astrometric.apparent()

    elif objtype == "moon":
        skyo = eph['moon']
        astrometric = earth.at(t).observe(skyo)
        apparent = astrometric.apparent()

    elif objtype == "satellite":
        # Load TLE data for satellites
        stations_url = 'https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle'
        satellites = load.tle_file(stations_url, reload=True)
        by_name = {sat.name.lower(): sat for sat in satellites}
        skyo = by_name.get(skyobject.lower())
        if skyo is None:
            raise ValueError(f"Unknown satellite: {skyobject}")
        astrometric = (skyo - earth).at(t)
        apparent = astrometric.apparent()

    else:
        raise ValueError(f"Unknown object type: {objtype}")

    ra, dec, distance = apparent.radec()
    print(f"RA: {ra}, Dec: {dec}")
    return ra, dec


def convert(right_ascension, declination, loc = uni):
    target = SkyCoord(ra=right_ascension.hours*u.hour, dec=declination.degrees*u.deg, frame='icrs')
    curr_utc = datetime.datetime.now().astimezone().astimezone(datetime.timezone.utc)
    obstime = Time(curr_utc, scale='utc')

    altaz_frame = AltAz(obstime=obstime, location=loc)
    altaz = target.transform_to(altaz_frame)

    altitude_deg, azimuth_deg = altaz.alt.degree, altaz.az.degree
    return azimuth_deg, altitude_deg



ra_str, dec_str = seek("Venus", "Planet")
az_str, alt_str = convert(ra_str, dec_str, EarthLocation(lat=53.4793*u.deg, lon=9.7023*u.deg, height=50*u.m))
print(az_str, alt_str)
