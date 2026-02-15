import os
import queue
import json
import sys
import time
import webbrowser
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import pyttsx3
from dotenv import load_dotenv
import threading

# Load environment variables
load_dotenv()

# Paths to model, apps, and relax website
MODEL_PATH = os.getenv("MODEL_PATH")  # Path to English Vosk model
STEAM_PATH = os.getenv("STEAM_PATH")
DISCORD_PATH = os.getenv("DISCORD_PATH")
EDGE_PATH = os.getenv("EDGE_PATH")
RELAX_SITE = os.getenv("RELAX_SITE")

# Mapping of recognized words to application paths
APPS = {
    "steam": STEAM_PATH,
    "discord": DISCORD_PATH,
    "edge": EDGE_PATH
}

# Words used to address the assistant
appeal_words = ["andromeda"]

# Audio input queue
q = queue.Queue()

# Initialize TTS engine
engine = pyttsx3.init()
voices = engine.getProperty('voices')

# Choose an English voice (Zira)
for v in voices:
    if "Zira" in v.name or "English" in v.name:
        engine.setProperty('voice', v.id)
        break

engine.setProperty("rate", 190)
engine.setProperty("volume", 0.7)

# Queue for TTS messages
tts_queue = queue.Queue()

def tts_worker():
    """Thread to sequentially speak messages from the TTS queue"""
    while True:
        text = tts_queue.get()
        if text is None:
            break
        engine.say(text)
        engine.runAndWait()
        tts_queue.task_done()

# Start TTS worker thread
threading.Thread(target=tts_worker, daemon=True).start()

def speak(text):
    """Add text to the TTS queue"""
    tts_queue.put(text)

def launch_edge(url="https://www.bing.com"):
    """Open Microsoft Edge at the specified URL"""
    if os.path.exists(EDGE_PATH):
        webbrowser.register('edge', None, webbrowser.BackgroundBrowser(EDGE_PATH))
        webbrowser.get('edge').open(url)
    else:
        webbrowser.open(url)

def launch_programs():
    """Launch Steam, Discord, and Edge"""
    os.startfile(STEAM_PATH)
    os.system(DISCORD_PATH)
    launch_edge()

def launch_some_program(recognized_text):
    """Launch a specific application based on recognized text"""
    for key, path in APPS.items():
        if key in recognized_text:
            if path == EDGE_PATH:
                launch_edge()
            elif path == DISCORD_PATH:
                os.system(DISCORD_PATH)
            else:
                os.startfile(path)
            speak(f"{key} launched.")
            print(f"{key} launched.")
            return True
    return False

def callback(indata, frames, time_info, status):
    """Audio callback for the input stream"""
    if status:
        print(status)
    q.put(bytes(indata))

def listen_forever():
    """Continuously listen for voice commands"""
    if not MODEL_PATH or not os.path.exists(MODEL_PATH):
        print("Error: English model not found.")
        return

    model = Model(MODEL_PATH)
    recognizer = KaldiRecognizer(model, 16000)

    with sd.RawInputStream(
        samplerate=16000,
        blocksize=8000,
        dtype='int16',
        channels=1,
        callback=callback
    ):
        print("Andromeda is active and listening for commands...")
        speak("Hello boss, I am ready.")
        while True:
            data = q.get()
            # Ignore silent or almost silent data
            if not any(data) or max(data) < 100:
                continue

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()
                if not text:
                    continue

                print("You said:", text)

                # Wake-up command
                if any(word + " wake up" in text for word in appeal_words):
                    speak("Welcome back, commander.")
                    launch_programs()
                    print("Wake-up commands executed.")

                # Relax mode command
                elif any(word + " relax" in text for word in appeal_words):
                    speak("Relax mode activated.")
                    launch_edge(RELAX_SITE)
                    print("Relax mode active.")

                # Exit command
                elif any(word + " exit" in text for word in appeal_words):
                    speak("Goodbye, commander.")
                    print("Andromeda shutting down.")
                    engine.stop()
                    sys.exit(0)

                # Launch specific program
                elif any(word + " launch" in text for word in appeal_words):
                    prog_command = text.replace("andromeda launch", "").strip()
                    if not launch_some_program(prog_command):
                        speak("Cannot find an application with that name.")
                        print(f"No app found for command: {prog_command}")

def main():
    """Main entry point"""
    try:
        listen_forever()
    except KeyboardInterrupt:
        print("Andromeda shutting down by interrupt.")
        engine.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
