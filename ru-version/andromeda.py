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

load_dotenv()

MODEL_PATH = os.getenv("MODEL_PATH")
STEAM_PATH = os.getenv("STEAM_PATH")
DISCORD_PATH = os.getenv("DISCORD_PATH")
EDGE_PATH = os.getenv("EDGE_PATH")
RELAX_SITE = os.getenv("RELAX_SITE")

APPS = {
    "с тем": STEAM_PATH,
    "с тим": STEAM_PATH,
    "чтим": STEAM_PATH,
    "тим": STEAM_PATH,
    "тем": STEAM_PATH,
    "систем": STEAM_PATH,
    "дискомфорт": DISCORD_PATH,
    "эскорт": DISCORD_PATH,
    "ди скоро": DISCORD_PATH,
    "диск орт": DISCORD_PATH,
    "эдж": EDGE_PATH,
    "этаж": EDGE_PATH,
}

appeal_words = ["андромеда", "андромеду", "андромеды"]

q = queue.Queue()

engine = pyttsx3.init()
voices = engine.getProperty('voices')


engine.setProperty('voice', voices[0].id)  # здесь меняем голос
engine.setProperty("rate", 190)  
engine.setProperty("volume", 0.7)  


tts_queue = queue.Queue()

def tts_worker():
    """Поток, который озвучивает все сообщения из очереди последовательно"""
    while True:
        text = tts_queue.get()
        if text is None:
            break
        engine.say(text)
        engine.runAndWait()
        tts_queue.task_done()

threading.Thread(target=tts_worker, daemon=True).start()

def speak(text):
    """Кладёт текст в очередь TTS"""
    tts_queue.put(text)

def launch_edge(url="https://www.bing.com"):
    """Открывает Microsoft Edge на указанной странице"""
    if os.path.exists(EDGE_PATH):
        webbrowser.register('edge', None, webbrowser.BackgroundBrowser(EDGE_PATH))
        webbrowser.get('edge').open(url)
    else:
        print("Edge не найден, открываю в браузере по умолчанию")
        webbrowser.open(url)

def launch_programs():
    os.startfile(STEAM_PATH)
    os.system(DISCORD_PATH)
    launch_edge()

def launch_some_program(recognized_text):
    for key, path in APPS.items():
        if key in recognized_text:
            if path == EDGE_PATH:
                launch_edge()
            elif path == DISCORD_PATH:
                os.system(DISCORD_PATH)
            else:
                os.startfile(path)
            speak(f"{key} запущен.")
            print(f"{key} запущен.")
            return True
    return False

def callback(indata, frames, time_info, status):
    if status:
        print(status)
    q.put(bytes(indata))

def listen_forever():
    """Бесконечное прослушивание всех голосовых команд"""
    if not MODEL_PATH or not os.path.exists(MODEL_PATH):
        print("Ошибка: модель не найдена.")
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
        print("Андромеда активна и слушает команды...")
        speak("Привет босс.")
        while True:
            data = q.get()

            # Игнорируем полностью пустые или почти пустые данные
            if not any(data):  # если все нули
                continue
            if max(data) < 100:  # порог для слабого шума, можно подстроить
                continue

            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").lower()
                if not text:  # игнорируем пустой результат
                    continue    

                print("Вы сказали:", text)

                if any(word + " пробуждение" in text for word in appeal_words):
                    speak("С возвращением, командир.")
                    launch_programs()
                    print("Команды пробуждения выполнены.")

                elif any(word + " релакс" in text for word in appeal_words):
                    speak("Сегодня как обычно?")
                    launch_edge(RELAX_SITE)
                    print("Режим релакс активирован.")

                elif any(word + " пока" in text for word in appeal_words):
                    speak("До свидания, командир.")
                    print("Андромеда завершает работу.")
                    engine.stop()
                    sys.exit(0)

                elif any(word + " запусти" in text for word in appeal_words):
                    prog_command = text.replace("андромеда запусти", "").strip()
                    if not launch_some_program(prog_command):
                        speak("Не могу найти программу с таким названием.")
                        print(f"Не найдено приложение для команды: {prog_command}")

def main():
    try:
        listen_forever()
    except KeyboardInterrupt:
        print("Андромеда завершает работу по прерыванию.")
        engine.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
