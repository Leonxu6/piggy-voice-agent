"""
Voice Handler - TTS and voice message processing
"""

import os
import asyncio
import logging
from telegram import Update

logger = logging.getLogger(__name__)

# MiniMax TTS Configuration
TTS_API_KEY = os.getenv("MINIMAX_TTS_API_KEY", os.getenv("MINIMAX_API_KEY"))
TTS_API_URL = "https://api.minimaxi.com/v1/t2a_v2"
VOICE_ID = "Chinese (Mandarin)_Soft_Girl"
MODEL = "speech-2.8-hd"


async def process_voice_message(update: Update, llm, executor, memory, user_id):
    """
    Process incoming voice message:
    1. Download voice file
    2. Transcribe to text (using LLM)
    3. Get LLM response
    4. Execute tasks if needed
    5. Generate TTS response
    """
    # Download the voice file
    voice_file = await update.message.voice.get_file()
    
    # For now, we'll use the LLM to summarize/respond
    # In production, you'd use Whisper or MiniMax STT
    
    # Simulate transcription (in real impl, use STT API)
    transcription = "[语音消息]"  # Placeholder
    
    # Get response
    response = await llm.chat(f"用户发送了语音消息: {transcription}")
    
    return {
        'voice_response': response,
        'text_summary': f"🎤 语音已处理: {response[:100]}...",
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
