
from datetime import datetime

import ephem
import torch
import whisper
import torch
import subprocess
import ollama

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
def seek(skyobject, objtype):
    if objtype == "Star":
        skyo = ephem.star(skyobject)
    else:
        sky_cls = getattr(ephem, skyobject, None)
        if sky_cls is None:
            raise ValueError(f"Unknown sky object: {skyobject}")
        skyo = sky_cls()
    # sky_cls = getattr(ephem, skyobject, None)
    # skyo = ephem.star(skyobject)
    # if not sky_cls:
        # raise ValueError(f"Unknown sky object: {skyobject}")
    # skyo = sky_cls()
    date = ephem.now()
    skyo.compute(date)
    print(skyo.ra, skyo.dec)

# seek("Mars")


def transcribe_audio(audio_file):
    model = whisper.load_model("base")
    audio = whisper.load_audio(audio_file, sr=16000)
    audio_tensor = torch.from_numpy(audio).to(torch.float32)
    result = model.transcribe(audio_tensor, fp16=False)['text']
    print(result)
    return result

text = transcribe_audio("audio.mp3")
# subprocess.run(["ollama", "run", "llama3.2", "'Antworte mit Hallo, falls du dies lesen kannst'"])

messages = [
    {
        "role": "system",
	"content": "You are an astronomy assistant. You will be given an input and its your job to analyze, what sky object the user wants to see and what type of object, i.e. star, planet or moon it is. Return your response in the format of 'Object,Type'. Make sure you reply in English"
},
    {
	"role": "user",
	"content": f"Your message is: Show me the Moon"
}
]

response = ollama.chat(model="llama3.2", messages=messages)
output = response["message"]["content"]
print(output)
# output = subprocess.run(["ollama", "run", "llama3.2", f"'Du bist ein Sternsucher und bekommst gleich einen Satz gegeben, der vom Nutzer gesprochen wurde. Du sollt aus diesem Satz das erste Himmelobjekt bestimmen, das der nutzer sehen möchte. Gebe nur den Namen des Objektes zurück und keine weiteren Zeichen, damit es als parameter verwendet werden kann. Dein Satz lautet: {text}'"], capture_output=True, text=True)
# print(output.stdout)

skyo = f"{output}"
skyo = skyo.replace("\n", "")
skyo = skyo.split(",")
skyobj = skyo[0]
skytyp = skyo[1]
print(f"Skyobj: {skyobj}, Skytyp: {skytyp}")
seek(skyobj, skytyp)
