import requests
import ephem
# import ollama
from datetime import datetime

url_whisper = "http://localhost:8000/v1/audio/transcriptions"
files = {"file": open("./audio/Mars_eng.m4a", "rb")}
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
	"content": "You will be given an input and translate it into english if necessary. You will return a response in the format 'Object,Type'. The Input will include a astronomical object that someone wants to see. Return the english common name of the object for the first parameter 'Object'. For the parameter 'Type' the options are: 'Star', 'Planet', 'Moon' or 'Satellite'. Choose the correct type for the object you determined. Make sure that your response is in english and never a full sentence. For example, if the input is 'Zeige mir den Stern Sirius', your response should be 'Sirius,Star'. If the input is 'Ich möchte den Polarstern sehen', your response should be 'Polaris,Star'."
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
skyobj = skyo[0].strip()
skytyp = skyo[1].strip()
print(f"Skyobj: {skyobj}, Skytyp: {skytyp}")
seek(skyobj, skytyp)
