from datetime import datetime

import ephem
import whisper

'''
mars = ephem.Mars()
date = datetime.date(datetime.now())
mars.compute(date)
print(mars.ra, mars.dec)
print(ephem.constellation(mars))


thb = ephem.Observer()
thb.lat = '52.410989373201794'
thb.lon = '12.538315792540791'
thb.date = date
mars.compute(thb)

print(mars.az, mars.alt)
'''
def seek(skyobject):
    sky_cls = getattr(ephem, skyobject, None)
    if not sky_cls:
        raise ValueError(f"Unknown sky object: {skyobject}")
    skyo = sky_cls()
    date = ephem.now()
    skyo.compute(date)
    print(skyo.ra, skyo.dec)

model = whisper.load_model("tiny")
result = model.transcribe("audio.mp3")
seek("Mars")