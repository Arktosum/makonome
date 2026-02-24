# voice/mouth.py

def speak(text: str):
    import pyttsx3

    # clean markdown since we're speaking
    text = text.replace("*", "").replace("#", "").replace("`", "")

    # reinitialize fresh every time — fixes Windows audio issues
    engine = pyttsx3.init()

    # find a female voice
    voices = engine.getProperty('voices')
    for voice in voices:
        if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break

    engine.setProperty('rate', 175)
    engine.setProperty('volume', 0.9)

    engine.say(text)
    engine.runAndWait()
    engine.stop()
