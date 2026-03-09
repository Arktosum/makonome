# voice/mouth.py
import edge_tts
import asyncio
import tempfile
import os

async def _speak_async(text: str):
    text = text.replace("*", "").replace("#", "").replace("`", "")
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name
    
    try:
        communicate = edge_tts.Communicate(text, voice="en-US-JennyNeural")
        await communicate.save(tmp_path)
        
        # play with pygame
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(tmp_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
    finally:
        os.unlink(tmp_path)

def speak(text: str):
    asyncio.run(_speak_async(text))