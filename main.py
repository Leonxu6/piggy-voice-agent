"""
Piggy Voice Research Agent - Main Entry Point
Voice in, research, voice out.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Setup
from dotenv import load_dotenv
load_dotenv()

# Check env
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ Missing TELEGRAM_BOT_TOKEN")
    print("   Get from: https://t.me/BotFather")
    sys.exit(1)

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
if not MINIMAX_API_KEY:
    print("❌ Missing MINIMAX_API_KEY")
    print("   Get from: https://platform.minimax.io")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('piggy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Telegram
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    VoiceHandler, filters, ContextTypes, Defaults
)

# Piggy modules
from voice_handler import VoiceHandler
from llm_client import LLMClient
from search_engine import SearchEngine
from memory import Memory
from research_agent import ResearchAgent

# Initialize
logger.info("🐷 Initializing Piggy...")
llm = LLMClient()
search = SearchEngine()
memory = Memory()
researcher = ResearchAgent(llm, search, memory)
voice = VoiceHandler(llm)

logger.info("✅ All modules initialized")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    await update.message.reply_text(
        "🐷 你好！我是 Piggy，你的语音研究助手。\n\n"
        "我可以帮你研究任何话题——行业动态、竞品分析、技术趋势...\n\n"
        "只需要说：\n"
        "• \"研究 Tesla 竞品\"\n"
        "• \"帮我了解 AI 最新进展\"\n"
        "• \"研究某个投资机会\"\n\n"
        "我说完就开始研究，1-2分钟后用语音报告结果。"
    )


async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle research requests"""
    user_id = str(update.message.from_user.id)
    text = update.message.text
    
    # Extract topic (remove /research or 研究)
    topic = text.replace('/research', '').replace('研究', '').strip()
    
    if not topic:
        await update.message.reply_text(
            "请告诉我你想研究什么话题。\n"
            "例如: /research Tesla 竞品分析"
        )
        return
    
    # Acknowledge
    await update.message.reply_text(f"🎤 收到，开始研究: {topic}")
    
    # Do research
    try:
        result = await researcher.research(topic, user_id)
        
        # Format for voice
        voice_report = researcher.format_for_voice(result)
        
        # Send text summary
        summary = f"📊 研究完成: {topic}\n\n{result.summary}"
        if result.key_findings:
            summary += "\n\n关键发现:"
            for f in result.key_findings:
                summary += f"\n• {f}"
        
        await update.message.reply_text(summary)
        
        # Send voice report
        await voice.send_voice(voice_report, update)
        
    except Exception as e:
        logger.error(f"Research error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 研究失败: {str(e)[:100]}")


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice input"""
    user_id = str(update.message.from_user.id)
    
    try:
        # Transcribe voice
        await update.message.reply_text("🎤 收到语音，正在转录...")
        
        topic = await voice.transcribe(update.message.voice)
        
        if not topic or topic == "[语音消息]":
            await update.message.reply_text("抱歉，我没听清楚，请再说一遍？")
            return
        
        await update.message.reply_text(f"🎤 听到了: {topic}")
        
        # Do research
        result = await researcher.research(topic, user_id)
        
        # Format for voice
        voice_report = researcher.format_for_voice(result)
        
        # Send text summary
        summary = f"📊 研究完成: {topic}\n\n{result.summary}"
        await update.message.reply_text(summary)
        
        # Send voice report
        await voice.send_voice(voice_report, update)
        
    except Exception as e:
        logger.error(f"Voice handle error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 处理失败: {str(e)[:100]}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input"""
    user_id = str(update.message.from_user.id)
    text = update.message.text
    
    # Check if it's a research request
    if any(kw in text.lower() for kw in ['研究', 'research', '了解', '分析']):
        await research_command(update, context)
        return
    
    # General chat - just respond
    await update.message.reply_text(
        "🐷 我是研究助手，不是聊天机器人。\n\n"
        "请说「研究 [话题]」来开始研究。\n"
        "例如: 研究 Tesla 竞品分析"
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Telegram error: {context.error}")


def main():
    """Start Piggy"""
    logger.info("=" * 50)
    logger.info("🐷 Piggy Voice Research Agent Starting...")
    logger.info("=" * 50)
    
    # Build app
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .defaults(Defaults(blocking_update_level=1))
        .build()
    )
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("research", research_command))
    app.add_handler(CommandHandler("研究", research_command))
    app.add_handler(VoiceHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)
    
    logger.info("✅ Piggy ready!")
    print("=" * 50)
    print("🐷 Piggy Voice Research Agent is running!")
    print("Send a voice or text message to start researching.")
    print("=" * 50)
    
    # Run
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
