"""
Voice Handler - STT and TTS for Piggy
"""

import os
import asyncio
import logging
import io

import httpx
import speech_recognition as sr

logger = logging.getLogger(__name__)

# Config
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
TTS_URL = "https://api.minimaxi.com/v1/t2a_v2"
TTS_MODEL = "speech-2.8-hd"
TTS_VOICE = "Chinese (Mandarin)_Warm_Girl"  # Warm girl voice (better than Soft_Girl)
TTS_EMOTION = "happy"

# TTS character limit per request (MiniMax limit ~1024 chars, leave buffer)
TTS_CHUNK_SIZE = 480


def chunk_text(text: str, max_chars: int = TTS_CHUNK_SIZE) -> list:
    """
    Split text into chunks suitable for TTS.
    Try to split at sentence boundaries.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    # Split by common sentence-ending punctuation
    import re
    sentences = re.split(r'(?<=[。！？；\n])\s*', text)

    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) <= max_chars:
            current += sentence
        else:
            if current:
                chunks.append(current.strip())
            # If single sentence is too long, split by phrase
            if len(sentence) > max_chars:
                # Split by commas/clauses
                phrases = re.split(r'(?<=[，、])\s*', sentence)
                current = ""
                for phrase in phrases:
                    if len(current) + len(phrase) <= max_chars:
                        current += phrase
                    else:
                        if current:
                            chunks.append(current.strip())
                        current = phrase
                if current.strip():
                    continue  # don't double-add
            else:
                current = sentence

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if c]


class VoiceProcessor:
    """Handles STT and TTS using async httpx"""

    def __init__(self, llm_client):
        self.llm = llm_client
        self.recognizer = sr.Recognizer()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def transcribe(self, voice) -> str:
        """
        Transcribe voice message to text using Google Speech API.
        """
        try:
            # Download voice file from Telegram
            voice_file = await voice.get_file()
            voice_bytes = await voice_file.download_as_bytearray()
            logger.info(f"Downloaded voice: {len(voice_bytes)} bytes")

            # Save temp file
            temp_path = f"/tmp/voice_{voice.file_unique_id}.wav"
            with open(temp_path, "wb") as f:
                f.write(voice_bytes)

            # Run sync STT in executor
            loop = asyncio.get_event_loop()

            def do_recognize():
                with sr.AudioFile(temp_path) as source:
                    audio_data = self.recognizer.record(source)
                    # Google Speech free tier, supports zh-CN
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

    async def send_voice(self, text: str, update, emotion: str = TTS_EMOTION):
        """
        Convert text to speech and send via Telegram.
        Handles long text by chunking into multiple TTS requests.
        """
        if not text or len(text.strip()) < 2:
            logger.warning("Empty text for TTS, skipping")
            return

        try:
            client = await self._get_client()
            headers = {
                "Authorization": f"Bearer {MINIMAX_API_KEY}",
                "Content-Type": "application/json"
            }

            chunks = chunk_text(text.strip(), TTS_CHUNK_SIZE)
            logger.info(f"TTS: {len(text)} chars -> {len(chunks)} chunks")

            if len(chunks) == 1:
                # Single chunk - generate and send directly
                audio_data = await self._tts_request(client, headers, chunks[0], emotion)
                temp_path = "/tmp/piggy_voice.mp3"
                with open(temp_path, "wb") as f:
                    f.write(audio_data)
                with open(temp_path, "rb") as f:
                    await update.message.reply_voice(voice=f)
            else:
                # Multiple chunks - generate each and combine
                all_audio = b""
                for i, chunk in enumerate(chunks):
                    chunk_data = await self._tts_request(client, headers, chunk, emotion)
                    all_audio += chunk_data
                    # Small delay to avoid rate limiting
                    if i < len(chunks) - 1:
                        await asyncio.sleep(0.3)

                temp_path = "/tmp/piggy_voice_combined.mp3"
                with open(temp_path, "wb") as f:
                    f.write(all_audio)
                with open(temp_path, "rb") as f:
                    await update.message.reply_voice(voice=f)

            logger.info(f"Sent voice report: {text[:30]}...")

        except Exception as e:
            logger.error(f"TTS send error: {e}")
            # Fallback to text
            await update.message.reply_text(f"🎤 {text[:500]}")

    async def _tts_request(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        text: str,
        emotion: str,
    ) -> bytes:
        """Make a single TTS API request"""
        payload = {
            "model": TTS_MODEL,
            "text": text,
            "stream": False,
            "output_format": "mp3",
            "voice_setting": {
                "voice_id": TTS_VOICE,
                "speed": 1.0,
                "vol": 1.0,
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

        resp = await client.post(TTS_URL, headers=headers, json=payload)
        data = resp.json()

        if data.get("base_resp", {}).get("status_code", 0) != 0:
            raise Exception(f"TTS error: {data.get('base_resp', {}).get('status_msg', 'unknown')}")

        audio_hex = data["data"]["audio"]
        return bytes.fromhex(audio_hex)
