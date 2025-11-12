import requests
import ephem
# import ollama
from datetime import datetime

url_whisper = "http://localhost:8000/v1/audio/transcriptions"
files = {"file": open("./audio.mp3", "rb")}
data = {"model": "whisper-1"}

url_ollama = "http://localhost:18080/api/chat"

text = requests.post(url_whisper, files=files, data=data)
print(text.json())

def seek(skyobject, objtype):
    if objtype == "Star":
        skyo = ephem.star(skyobject)
    else:
        sky_cls = getattr(ephem, skyobject, None)
        if sky_cls is None:
            raise ValueError(f"Unknown sky object: {skyobject}")
        skyo = sky_cls()

    date = ephem.now()
    skyo.compute(date)
    print(skyo.ra, skyo.dec)

messages = [
    {
        "role": "system",
	"content": "You are an astronomy assistant. You will be given an input and its your job to analyze, what sky object the user wants to see and what type of object, i.e. star, planet or moon it is. Return your response in the format of 'Object,Type'. Make sure you reply in English"
    },
    {
	"role": "user",
	"content": f"Your message is: {text.json()['text']}"
    }
]

ollama_response = requests.post(
    url_ollama,
    json={
        "model": "llama3.2",
        "messages": messages,
        "stream": False
    }
)
print(ollama_response.json())

output = ollama_response.json()["message"]["content"]
print(f"Output Ollama: {output}")


skyo = f"{output}"
skyo = skyo.replace("\n", "").split(",")
skyobj = skyo[0]
skytyp = skyo[1]
print(f"Skyobj: {skyobj}, Skytyp: {skytyp}")
seek(skyobj, skytyp)
