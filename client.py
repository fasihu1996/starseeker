import os
import requests

WHISPER_PORT = 8000
OLLAMA_PORT = 18080

class Client:
    """
    Handles communication with Whisper for transcription and Ollama for parsing. Requires the setup
    of SSH tunnels as described in the README. Contains the Ollama system prompt.
    """

    def __init__(self,
                 url_whisper: str = f"http://localhost:{WHISPER_PORT}/v1/audio/transcriptions",
                 url_ollama: str = f"http://localhost:{OLLAMA_PORT}/api/chat"):
        self.url_whisper = url_whisper
        self.url_ollama = url_ollama

    def transcribe(self, wav_path: str) -> str:
        """Use Whisper to transcribe input audio into text string."""
        if not os.path.exists(wav_path):
            raise FileNotFoundError(wav_path)

        print("Transcribing via Whisper server...")
        with open(wav_path, "rb") as f:
            files = {"file": (os.path.basename(wav_path), f, "audio/wav")}
            data = {"model": "whisper-1"}
            resp = requests.post(self.url_whisper, files=files, data=data, timeout=120)

        resp.raise_for_status()
        whisper_json = resp.json()
        text = whisper_json.get("text", "").strip()
        if not text:
            raise RuntimeError("Whisper did not return text")
        print(f"Transcribed text: {text}")
        return text

    def query_object(self, text: str) -> tuple[str, str]:
        """
        Ask Ollama to interpret the TTS 'text' and convert it into 'Object,Type'.
        Returns (object, type).
        """
        system_prompt = (
            "You will be given an input and translate it into english if necessary. "
            "You will return a response in the format 'Object,Type'. The Input will include a astronomical object that someone wants to see. "
            "Return the english common name of the object for the first parameter 'Object'. For the parameter 'Type' the options are: 'Star', 'Planet' or 'Satellite'. "
            "Choose the correct type for the object you determined. Make sure that your response is in english and never a full sentence. "
            "If the object is a star other than our sun, always return the Hipparcos Identifier for the object and never the name of the star. Make sure you look this up in a current database such as Vizier and it is correct."
            "For example, if the input is 'Zeige mir den Stern Sirius', your response should be '32349,Star'. "
            "If the input is 'Ich möchte den Polarstern sehen', your response should be '11767,Star'."
			"If the object is a planet, return the response as 'Name,Planet'. For example, if the input was 'Bitte zeige mir den Uranus', your response should be 'Uranus,Planet'."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Your message is: {text}"},
        ]

        print("Querying Ollama...")
        resp = requests.post(
            self.url_ollama,
            json={"model": "llama3.2", "messages": messages, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        oj = resp.json()
        output = oj.get("message", {}).get("content", "").strip()
        print(f"Output Ollama: {output}")

        parsed = None
        for line in output.splitlines():
            if "," in line:
                parsed = line
                break
        if parsed is None:
            raise ValueError("Could not parse Ollama output. Expected 'Object,Type'.")

        skyo = parsed.replace("\n", "").split(",")
        # error handling in case Ollama returns an incomplete response
        if len(skyo) < 2:
            raise ValueError("Incomplete Ollama output.")

        # split response into the two important parts and return those
        skyobj = skyo[0].strip()
        skytyp = skyo[1].strip()
        print(f"Skyobj: {skyobj}, Skytyp: {skytyp}")
        return skyobj, skytyp
