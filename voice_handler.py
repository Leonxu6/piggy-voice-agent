"""
Voice Handler - STT and TTS for Piggy
"""

import os
import asyncio
import logging
import io
import speech_recognition as sr

import requests

logger = logging.getLogger(__name__)

# Config
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
TTS_URL = "https://api.minimaxi.com/v1/t2a_v2"
TTS_MODEL = "speech-2.8-hd"
TTS_VOICE = "Chinese (Mandarin)_Soft_Girl"


class VoiceHandler:
    """Handles STT and TTS"""
    
    def __init__(self, llm_client):
        self.llm = llm_client
        self.recognizer = sr.Recognizer()
    
    async def transcribe(self, voice) -> str:
        """
        Transcribe voice message to text.
        """
        try:
            # Download voice
            voice_bytes = await voice.get_file().download_as_bytearray()
            logger.info(f"Downloaded voice: {len(voice_bytes)} bytes")
            
            # Save temp file
            temp_path = f"/tmp/voice_{voice.file_unique_id}.wav"
            with open(temp_path, "wb") as f:
                f.write(voice_bytes)
            
            # Transcribe
            loop = asyncio.get_event_loop()
            
            def do_recognize():
                with sr.AudioFile(temp_path) as source:
                    audio_data = self.recognizer.record(source)
                    # Try Google Speech (free tier, supports Chinese)
                    text = self.recognizer.recognize_google(audio_data, language="zh-CN")
                    return text
            
            text = await loop.run_in_executor(None, do_recognize)
            logger.info(f"Transcribed: {text}")
            return text
            
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return "[听不清，请再说一遍]"
        except Exception as e:
            logger.error(f"STT error: {e}")
            return "[语音识别失败]"
    
    async def send_voice(self, text: str, update, emotion: str = "happy"):
        """
        Convert text to speech and send via Telegram.
        """
        try:
            # Generate TTS
            headers = {
                "Authorization": f"Bearer {MINIMAX_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": TTS_MODEL,
                "text": text[:500],  # Limit length
                "stream": False,
                "output_format": "hex",
                "voice_setting": {
                    "voice_id": TTS_VOICE,
                    "speed": 1,
                    "vol": 1,
                    "pitch": 0,
                    "emotion": emotion
                },
                "audio_setting": {
                    "sample_rate": 32000,
                    "bitrate": 128000,
                    "format": "mp3",
                    "channel": 1
                }
            }
            
            loop = asyncio.get_event_loop()
            
            def do_tts():
                resp = requests.post(TTS_URL, headers=headers, json=payload, timeout=30)
                data = resp.json()
                
                if data.get("base_resp", {}).get("status_code") != 0:
                    raise Exception(f"TTS error: {data}")
                
                audio_hex = data["data"]["audio"]
                return bytes.fromhex(audio_hex)
            
            audio_data = await loop.run_in_executor(None, do_tts)
            
            # Save temp file
            temp_path = "/tmp/piggy_voice.mp3"
            with open(temp_path, "wb") as f:
                f.write(audio_data)
            
            # Send voice
            with open(temp_path, "rb") as f:
                await update.message.reply_voice(voice=f)
            
            logger.info(f"Sent voice: {text[:30]}...")
            
        except Exception as e:
            logger.error(f"TTS send error: {e}")
            # Fallback to text
            await update.message.reply_text(f"🎤 {text[:500]}")
