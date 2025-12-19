from skyfield.api import Star, load
from skyfield.data import hipparcos
import datetime
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
from astropy import units as u


with load.open(hipparcos.URL) as f:
    df = hipparcos.load_dataframe(f)

barnards_star = Star.from_dataframe(df.loc[87937])

planets = load('de421.bsp')
earth = planets['earth']

ts = load.timescale()
t = ts.now()
astrometric = earth.at(t).observe(barnards_star)
ra, dec, distance = astrometric.radec()
print(ra)
print(dec)

# Create sky coordinate in ICRS (typical RA/Dec frame)
target = SkyCoord(ra=ra.hours*u.hour, dec=dec.degrees*u.deg, frame='icrs')

# Observer location
location = EarthLocation(lat=52.0*u.deg, lon=13.0*u.deg, height=50*u.m)

curr_time = datetime.datetime.now().astimezone()
curr_utc = curr_time.astimezone(datetime.timezone.utc)
# Observation time (UTC)
obstime = Time(curr_utc, scale='utc')

# AltAz frame for that time and place
altaz_frame = AltAz(obstime=obstime, location=location)

# Transform RA/Dec → Alt/Az
altaz = target.transform_to(altaz_frame)

altitude_deg = altaz.alt.degree
azimuth_deg  = altaz.az.degree

print(f"Azimuth: {azimuth_deg}  Altitude: {altitude_deg}")
