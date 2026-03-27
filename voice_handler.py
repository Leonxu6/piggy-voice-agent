"""
Voice Handler - TTS and voice message processing
"""

import os
import asyncio
import logging
import io
from telegram import Update

logger = logging.getLogger(__name__)

# MiniMax TTS Configuration
TTS_API_KEY = os.getenv("MINIMAX_TTS_API_KEY", os.getenv("MINIMAX_API_KEY"))
TTS_API_URL = "https://api.minimaxi.com/v1/t2a_v2"
VOICE_ID = "Chinese (Mandarin)_Soft_Girl"
MODEL = "speech-2.8-hd"


async def transcribe_voice(voice_file) -> str:
    """
    Transcribe voice message to text using Telegram's built-in recognition
    or fallback to placeholder.
    
    Telegram voice messages have duration limit of 5MB audio.
    """
    try:
        # Download voice file
        voice_bytes = await voice_file.download_as_bytearray()
        
        # Try using speech recognition via HTTP API
        # For now, we'll use a simple approach with the file
        
        # Note: MiniMax doesn't have free STT, using alternative
        # For production, consider: Whisper API, Google STT, or Vosk
        
        # Save to temp file for potential STT processing
        temp_path = f"/tmp/voice_{voice_file.file_unique_id}.mp3"
        with open(temp_path, "wb") as f:
            f.write(voice_bytes)
        
        logger.info(f"Downloaded voice file: {len(voice_bytes)} bytes")
        
        # Return placeholder - in production, integrate with STT API
        return "[语音消息]"  # Placeholder until STT is integrated
        
    except Exception as e:
        logger.error(f"Voice transcription error: {e}")
        return "[语音消息处理失败]"


async def process_voice_message(update: Update, llm, executor, memory, user_id):
    """
    Process incoming voice message:
    1. Download voice file
    2. Transcribe to text
    3. Get LLM response
    4. Execute tasks if needed
    5. Generate TTS response
    """
    # Get voice file
    voice_file = await update.message.voice.get_file()
    
    # Transcribe
    transcription = await transcribe_voice(voice_file)
    
    if transcription == "[语音消息]":
        # Use LLM to respond anyway (it can infer from context)
        response = await llm.chat(
            f"用户发送了一条语音消息。请以 Piggy 助手的身份，用简洁友好的方式回应用户。",
            user_id=user_id
        )
    else:
        # Process the transcription
        response = await llm.chat(
            f"用户语音内容：{transcription}",
            user_id=user_id
        )
    
    return {
        'voice_response': response,
        'text_summary': f"🎤 听到了: {transcription[:50]}...",
        'transcription': transcription
    }


async def send_voice_message(update: Update, text: str, emotion: str = "fluent"):
    """
    Send a voice message response using MiniMax TTS
    """
    import requests
    import json
    
    headers = {
        "Authorization": f"Bearer {TTS_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "text": text,
        "stream": False,
        "output_format": "hex",
        "voice_setting": {
            "voice_id": VOICE_ID,
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
    
    try:
        # Generate TTS
        resp = requests.post(TTS_API_URL, headers=headers, json=payload, timeout=30)
        data = resp.json()
        
        if data.get("base_resp", {}).get("status_code") != 0:
            logger.error(f"TTS API error: {data}")
            # Fallback to text
            await update.message.reply_text(text)
            return
        
        audio_hex = data["data"]["audio"]
        audio_data = bytes.fromhex(audio_hex)
        
        # Save temp file
        temp_path = "/tmp/piggy_voice.mp3"
        with open(temp_path, "wb") as f:
            f.write(audio_data)
        
        # Send voice message
        with open(temp_path, "rb") as f:
            await update.message.reply_voice(voice=f)
        
        logger.info(f"发送语音消息成功: {text[:30]}...")
        
    except Exception as e:
        logger.error(f"发送语音失败: {e}")
        # Fallback to text
        await update.message.reply_text(text)
