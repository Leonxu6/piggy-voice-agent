"""
Piggy Voice AI Agent - Main Entry Point v2
Improved version with better error handling and logging
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Check required env vars
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not set in .env")
    print("   Get one from https://t.me/BotFather")
    sys.exit(1)

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY")
if not MINIMAX_API_KEY:
    print("❌ MINIMAX_API_KEY not set in .env")
    print("   Get one from https://platform.minimax.io")
    sys.exit(1)

# Import after env check
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, VoiceHandler, filters, ContextTypes

# Import our modules
from voice_handler import process_voice_message, send_voice_message
from llm_client import LLMClient
from task_executor import TaskExecutor
from memory import Memory

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('piggy.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize modules
llm = LLMClient()
executor = TaskExecutor()
memory = Memory()

logger.info("🐷 Piggy Voice AI Agent Starting...")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"🐷 你好 {user_name}！我是 Piggy，你的语音 AI 助手。\n\n"
        f"发语音给我，或者直接打字，我会帮你完成任务！\n\n"
        f"示例：\n"
        f"• '搜索最新的 AI 新闻'\n"
        f"• '研究竞品分析'\n"
        f"• '帮我写个 Python 脚本'\n\n"
        f"我可以用语音回复你～"
    )
    logger.info(f"New user started: {user_name}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    await update.message.reply_text(
        "🐷 Piggy 使用指南：\n\n"
        "🎤 语音消息 — 我会听你的指令并用语音回复\n"
        "📝 文字消息 — 直接打字也可以\n\n"
        "我能帮你：\n"
        "• 🔍 网络搜索和研究\n"
        "• 💻 写代码、调试、review\n"
        "• 📊 市场分析和竞品研究\n"
        "• 🌐 网页内容抓取\n"
        "• 🧠 任何你需要的信息\n\n"
        "有需求尽管说！"
    )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice messages"""
    try:
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        
        logger.info(f"Voice from {user_name} (ID: {user_id})")
        
        # Send "thinking" message
        thinking_msg = await update.message.reply_text("🎤 收到，让我处理一下...")
        
        # Process voice → text → LLM → action → TTS response
        result = await process_voice_message(
            update=update,
            llm=llm,
            executor=executor,
            memory=memory,
            user_id=user_id
        )
        
        # Delete thinking message
        await thinking_msg.delete()
        
        # Send text response
        if result.get('text_summary'):
            await update.message.reply_text(result['text_summary'])
        
        # Send voice response back
        if result.get('voice_response'):
            await send_voice_message(update, result['voice_response'], emotion='happy')
        
        logger.info(f"Completed request from {user_name}")
        
    except Exception as e:
        logger.error(f"Handle voice error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 处理失败: {str(e)[:100]}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages"""
    try:
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        text = update.message.text
        
        logger.info(f"Text from {user_name}: {text[:50]}...")
        
        # Send "thinking" indicator
        thinking_msg = await update.message.reply_text("🤔 处理中...")
        
        # Process text → LLM → action → TTS response
        from main import process_text_message
        result = await process_text_message(
            update=update,
            text=text,
            llm=llm,
            executor=executor,
            memory=memory,
            user_id=user_id
        )
        
        # Delete thinking message
        await thinking_msg.delete()
        
        # Send text summary
        if result.get('text_summary'):
            await update.message.reply_text(result['text_summary'])
        
        # Send voice response
        if result.get('voice_response'):
            await send_voice_message(update, result['voice_response'], emotion='fluent')
        
        logger.info(f"Completed text request from {user_name}")
        
    except Exception as e:
        logger.error(f"Handle text error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 处理失败: {str(e)[:100]}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Telegram error: {context.error}")


def main():
    """Start the bot"""
    logger.info("🐷 Building Piggy application...")
    
    try:
        # Build application
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(VoiceHandler(filters.VOICE, handle_voice))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        # Error handler
        app.add_error_handler(error_handler)
        
        logger.info("✅ Piggy ready! Starting polling...")
        print("=" * 50)
        print("🐷 Piggy Voice AI Agent is running!")
        print("=" * 50)
        print("Send a message to your Telegram bot to start!")
        
        # Start polling
        app.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
