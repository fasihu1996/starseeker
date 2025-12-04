import os
import queue
import threading
from datetime import datetime

import ephem
import numpy as np
import requests
import sounddevice as sd
from scipy.io.wavfile import write as wav_write

# GUI
import tkinter as tk
from tkinter import ttk, messagebox

# Endpoints via SSH tunnels
URL_WHISPER = "http://localhost:8000/v1/audio/transcriptions"
URL_OLLAMA = "http://localhost:18080/api/chat"

AUDIO_DIR = os.path.join(os.path.dirname(__file__), "tmp")
os.makedirs(AUDIO_DIR, exist_ok=True)


def seek(skyobject, objtype):
    objtype = objtype.lower()
    if skyobject == "Sun":
        skyo = ephem.Sun()
    else:
        match objtype:
            case "star":
                skyo =ephem.star(skyobject)
            case "moon":
                skyo = ephem.Moon(skyobject)
            case "satellite":
                skyo = ephem.EarthSatellite(skyobject)
            case "planetmoon":
                skyo = ephem.PlanetMoon(skyobject)
            case _:
                sky_cls = getattr(ephem, skyobject, None)
                if sky_cls is None:
                    raise ValueError(f"Unknown sky object: {skyobject}")
                skyo = sky_cls()


    date = ephem.now()
    skyo.compute(date)
    print(skyo.ra, skyo.dec)


class Logger:
    def __init__(self, text_widget: tk.Text):
        self.text_widget = text_widget
        self._lock = threading.Lock()

    def write(self, msg: str):
        if not msg:
            return
        with self._lock:
            self.text_widget.after(0, self._append, msg)

    def flush(self):
        pass

    def _append(self, msg: str):
        self.text_widget.insert(tk.END, msg)
        self.text_widget.see(tk.END)


class RecorderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("StarSeeker Recorder")

        self.fs = 44100
        self.channels = 1
        self._recording = False
        self._q: queue.Queue[np.ndarray] = queue.Queue()
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._consumer_thread: threading.Thread | None = None
        self.output_file: str | None = None

        # UI
        self.frame = ttk.Frame(root, padding=10)
        self.frame.grid(row=0, column=0, sticky="nsew")
        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)

        btns = ttk.Frame(self.frame)
        btns.grid(row=0, column=0, sticky="w")
        self.btn_start = ttk.Button(btns, text="Start Recording", command=self.start_recording)
        self.btn_stop = ttk.Button(btns, text="Stop", command=self.stop_recording, state=tk.DISABLED)
        self.btn_process = ttk.Button(btns, text="Transcribe & Analyze", command=self.process_audio, state=tk.DISABLED)
        self.btn_start.grid(row=0, column=0, padx=5)
        self.btn_stop.grid(row=0, column=1, padx=5)
        self.btn_process.grid(row=0, column=2, padx=5)

        self.file_label_var = tk.StringVar(value="No recording yet")
        ttk.Label(self.frame, textvariable=self.file_label_var).grid(row=1, column=0, sticky="w", pady=(8, 4))

        self.log = tk.Text(self.frame, height=20, width=100)
        self.log.grid(row=2, column=0, sticky="nsew")
        self.frame.rowconfigure(2, weight=1)
        self.frame.columnconfigure(0, weight=1)
        self.logger = Logger(self.log)

        # Redirect prints to the window logger as well
        import sys
        self._orig_stdout = sys.stdout
        sys.stdout = self  # redirect to this app (implements write/flush)

    # stdout redirection
    def write(self, msg: str):
        self.logger.write(msg)
        # also to console
        # Keep original stdout for debugging
        try:
            self._orig_stdout.write(msg)
        except Exception:
            pass

    def flush(self):
        try:
            self._orig_stdout.flush()
        except Exception:
            pass

    def _audio_callback(self, indata, frames, time, status):  # sounddevice callback
        if status:
            print(f"Audio status: {status}")
        if self._recording:
            self._q.put(indata.copy())

    def _consume(self):
        while self._recording:
            try:
                chunk = self._q.get(timeout=0.2)
                self._frames.append(chunk)
            except queue.Empty:
                continue

    def start_recording(self):
        if self._recording:
            return
        self._frames = []
        self._q = queue.Queue()
        self._recording = True
        self._stream = sd.InputStream(samplerate=self.fs, channels=self.channels, callback=self._audio_callback)
        self._stream.start()
        self._consumer_thread = threading.Thread(target=self._consume, daemon=True)
        self._consumer_thread.start()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_process.config(state=tk.DISABLED)
        print("Now recording... (press Stop when finished)")

    def stop_recording(self):
        if not self._recording:
            return
        self._recording = False
        if self._stream is not None:
            try:
                self._stream.stop(); self._stream.close()
            finally:
                self._stream = None
        if self._consumer_thread is not None:
            self._consumer_thread.join(timeout=1.0)
            self._consumer_thread = None

        if not self._frames:
            print("No tmp captured.")
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            return

        audio = np.concatenate(self._frames, axis=0)
        # Normalize to int16 for WAV writing
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        audio_clipped = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio_clipped * 32767).astype(np.int16)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = os.path.join(AUDIO_DIR, f"recording_{ts}.wav")
        wav_write(self.output_file, self.fs, audio_int16)
        self.file_label_var.set(f"Saved: {self.output_file}")
        print(f"Recording finished. Saved to {self.output_file}")

        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_process.config(state=tk.NORMAL)

    def process_audio(self):
        if not self.output_file or not os.path.exists(self.output_file):
            messagebox.showwarning("No tmp", "Please record tmp first.")
            return
        self.btn_process.config(state=tk.DISABLED)
        threading.Thread(target=self._process_worker, daemon=True).start()

    def _process_worker(self):
        try:
            # Whisper transcription
            print("Transcribing via Whisper server...")
            with open(self.output_file, "rb") as f:
                files = {"file": (os.path.basename(self.output_file), f, "tmp/wav")}
                data = {"model": "whisper-1"}
                resp = requests.post(URL_WHISPER, files=files, data=data, timeout=120)
            resp.raise_for_status()
            whisper_json = resp.json()
            # print(whisper_json)
            text = whisper_json.get("text", "").strip()
            if not text:
                raise RuntimeError("Whisper did not return text")
            print(f"Transcribed text: {text}")

            # Ollama analysis
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You will be given an input and translate it into english if necessary. "
                        "You will return a response in the format 'Object,Type'. The Input will include a astronomical object that someone wants to see. "
                        "Return the english common name of the object for the first parameter 'Object'. For the parameter 'Type' the options are: 'Star', 'Planet', 'Moon' or 'Satellite'. "
                        "Choose the correct type for the object you determined. Make sure that your response is in english and never a full sentence. "
                        "For example, if the input is 'Zeige mir den Stern Sirius', your response should be 'Sirius,Star'. "
                        "If the input is 'Ich möchte den Polarstern sehen', your response should be 'Polaris,Star'."
                        "If the input is 'Bitte zeige mir die Sonne', your response should be 'Sun,Star'."
                    ),
                },
                {"role": "user", "content": f"Your message is: {text}"},
            ]

            print("Querying Ollama...")
            ollama_response = requests.post(
                URL_OLLAMA,
                json={
                    "model": "llama3.2",
                    "messages": messages,
                    "stream": False,
                },
                timeout=120,
            )
            ollama_response.raise_for_status()
            oj = ollama_response.json()
            # print(oj)
            output = oj.get("message", {}).get("content", "").strip()
            print(f"Output Ollama: {output}")

            # Parse 'Object,Type'
            parsed = None
            for line in output.splitlines():
                if "," in line:
                    parsed = line
                    break
            if parsed is None:
                raise ValueError("Could not parse Ollama output. Expected 'Object,Type'.")
            skyo = parsed.replace("\n", "").split(",")
            if len(skyo) < 2:
                raise ValueError("Incomplete Ollama output.")
            skyobj = skyo[0].strip()
            skytyp = skyo[1].strip()
            print(f"Skyobj: {skyobj}, Skytyp: {skytyp}")

            # Compute coordinates
            seek(skyobj, skytyp)
            print("Done.")

            # delete all .wav files in tmp
            filelist = [f for f in os.listdir(AUDIO_DIR) if f.endswith(".wav")]
            for f in filelist:
                os.remove(os.path.join(AUDIO_DIR, f))


        except Exception as e:
            print(f"Error: {e}")
            messagebox.showerror("Processing failed", str(e))
        finally:
            self.btn_process.config(state=tk.NORMAL)






if __name__ == "__main__":
    root = tk.Tk()
    app = RecorderApp(root)
    root.mainloop()
