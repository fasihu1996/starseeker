import os
import queue
import threading
from datetime import datetime

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write

class AudioRecorder:
    """
    Simple audio recorder using sounddevice.
    Produces a WAV file path when recording stops.
    Audio file is stored in the tmp folder
    """

    def __init__(self, audio_dir: str, fs: int = 44100, channels: int = 1):
        self.audio_dir = audio_dir
        os.makedirs(self.audio_dir, exist_ok=True)

        self.fs = fs
        self.channels = channels

        self._recording = False
        self._q: queue.Queue[np.ndarray] = queue.Queue()
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._consumer_thread: threading.Thread | None = None
        self.output_file: str | None = None

    # internal
    def _audio_callback(self, indata, frames, time, status):
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

    # public API
    def start(self):
        if self._recording:
            return
        self._frames = []
        self._q = queue.Queue()
        self._recording = True

        self._stream = sd.InputStream(
            samplerate=self.fs,
            channels=self.channels,
            callback=self._audio_callback,
        )
        self._stream.start()

        self._consumer_thread = threading.Thread(target=self._consume, daemon=True)
        self._consumer_thread.start()
        print("Now recording... (press Stop when finished)")

    def stop(self) -> str | None:
        if not self._recording:
            return None

        self._recording = False
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None

        if self._consumer_thread is not None:
            self._consumer_thread.join(timeout=1.0)
            self._consumer_thread = None

        if not self._frames:
            print("No audio captured.")
            return None

        audio = np.concatenate(self._frames, axis=0)
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        audio_clipped = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio_clipped * 32767).astype(np.int16)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_file = os.path.join(self.audio_dir, f"recording_{ts}.wav")
        wav_write(self.output_file, self.fs, audio_int16)
        print(f"Recording finished. Saved to {self.output_file}")
        return self.output_file
