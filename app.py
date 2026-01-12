import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import sys

# Custom imports from other application parts
from astro import seek, convert, transmit
from recorder import AudioRecorder
from client import Client
from tts import say

# directory for saving the temporary recording files. directory is emptied when application is closed
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "tmp")

# transmission URL for the arduino webserver
TRANSMIT_URL = "http://192.168.0.153/"


class Logger:
    """Class for logging output of commands and function calls."""
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
    """Class for core functionaly and UI of the application."""
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("StarSeeker Recorder")

        # core components
        self.recorder = AudioRecorder(AUDIO_DIR)
        self.client = Client()

        self.output_file: str | None = None

        # UI layout
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
        ttk.Label(self.frame, textvariable=self.file_label_var).grid(
            row=1, column=0, sticky="w", pady=(8, 4)
        )

        self.log = tk.Text(self.frame, height=20, width=100)
        self.log.grid(row=2, column=0, sticky="nsew")
        self.frame.rowconfigure(2, weight=1)
        self.frame.columnconfigure(0, weight=1)
        self.logger = Logger(self.log)

        self._orig_stdout = sys.stdout
        sys.stdout = self

    def write(self, msg: str):
        """Function to write a message into the logging section."""
        self.logger.write(msg)
        try:
            self._orig_stdout.write(msg)
        except (OSError, AttributeError, ValueError):
            pass

    def flush(self):
        """Function to flush the logging section."""
        try:
            self._orig_stdout.flush()
        except (OSError, AttributeError, ValueError):
            pass

    # Button functionality

    def start_recording(self):
        self.recorder.start()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_process.config(state=tk.DISABLED)

    def stop_recording(self):
        output = self.recorder.stop()
        self.output_file = output
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        if output:
            self.file_label_var.set(f"Saved: {output}")
            self.btn_process.config(state=tk.NORMAL)
        else:
            self.file_label_var.set("No recording yet")
            self.btn_process.config(state=tk.DISABLED)

    def process_audio(self):
        if not self.output_file or not os.path.exists(self.output_file):
            messagebox.showwarning("No audio", "Please record audio first.")
            return
        self.btn_process.config(state=tk.DISABLED)
        threading.Thread(target=self._process_worker, daemon=True).start()

    def _process_worker(self):
        try:
            text = self.client.transcribe(self.output_file)
            skyobj, skytyp = self.client.query_object(text)

            ra, dec = seek(skyobj, skytyp)
            azimuth, altitude = convert(ra, dec)
            print(f"Altitude: {altitude}    Azimuth: {azimuth}")
            # print(f"Converted altitude: {con_alt}    Converted azimuth: {con_azi}")
            if altitude < 0:
                print("Object is below the horizon")
                say(f"The {skyobj} is currently below the horizon, try again some other time.")
            else:
                say(f"Now seeking {skyobj}")
                res_status = transmit(TRANSMIT_URL, altitude, azimuth)
                if res_status == 200:
                    print(f"Information transmitted to {TRANSMIT_URL}")
                else:
                    print("Transmission failed!")
            print("Done.")

            # clean up wav files
            for f in os.listdir(AUDIO_DIR):
                if f.endswith(".wav"):
                    os.remove(os.path.join(AUDIO_DIR, f))

        except Exception as e:
            print(f"Error: {e}")
            messagebox.showerror("Processing failed", str(e))
        finally:
            self.btn_process.config(state=tk.NORMAL)


def main():
    root = tk.Tk()
    app = RecorderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
