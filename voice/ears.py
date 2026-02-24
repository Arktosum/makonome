# voice/ears.py
import whisper
import sounddevice as sd
import numpy as np
import tempfile
import soundfile as sf

# Load whisper model once when the module is imported
# "small" is the sweet spot for speed vs accuracy on your hardware
print("Loading Whisper... ", end="", flush=True)
whisper_model = whisper.load_model("small", device="cpu")
print("ready!")

SAMPLE_RATE = 16000  # Whisper expects 16kHz audio
SILENCE_THRESHOLD = 0.01  # volume below this is considered silence
SILENCE_DURATION = 2.0  # seconds of silence before we stop recording
MAX_DURATION = 30  # maximum recording length in seconds

def record_until_silence() -> np.ndarray:
    """
    Records audio from mic until the user stops talking.
    Returns the recorded audio as a numpy array.
    """
    print("🎤 Listening...", flush=True)
    
    recorded_chunks = []
    silent_chunks = 0
    chunk_duration = 0.1  # process audio in 100ms chunks
    chunk_samples = int(SAMPLE_RATE * chunk_duration)
    silence_chunks_needed = int(SILENCE_DURATION / chunk_duration)
    max_chunks = int(MAX_DURATION / chunk_duration)

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32') as stream:
        # wait for user to start talking first
        print("(waiting for you to speak...)", flush=True)
        while True:
            chunk, _ = stream.read(chunk_samples)
            volume = np.abs(chunk).mean()
            if volume > SILENCE_THRESHOLD:
                recorded_chunks.append(chunk.copy())
                break

        # now record until silence
        print("(recording... stop talking to finish)", flush=True)
        while len(recorded_chunks) < max_chunks:
            chunk, _ = stream.read(chunk_samples)
            recorded_chunks.append(chunk.copy())
            volume = np.abs(chunk).mean()

            if volume < SILENCE_THRESHOLD:
                silent_chunks += 1
                if silent_chunks >= silence_chunks_needed:
                    break
            else:
                silent_chunks = 0  # reset silence counter if they speak again

    audio = np.concatenate(recorded_chunks, axis=0).flatten()
    return audio

def listen() -> str:
    """
    Full pipeline: record audio → transcribe with Whisper → return text.
    This is the only function brain.py needs to call.
    """
    audio = record_until_silence()
    
    print("🧠 Transcribing...", flush=True)
    
    # Whisper expects float32 numpy array at 16kHz
    result = whisper_model.transcribe(audio, fp16=False, language="en")
    text = result["text"].strip()
    
    print(f"You said: {text}", flush=True)
    return text