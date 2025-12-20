from skyfield.api import Star, load
from skyfield.data import hipparcos

eph = load("de421.bsp")
ts = load.timescale()

with load.open(hipparcos.URL) as f:
    df = hipparcos.load_dataframe(f)

