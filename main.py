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


async def _do_research(
    update: Update,
    topic: str,
    user_id: str,
    reply_to_message_id: int = None,
):
    """
    Shared research pipeline with real-time status updates.
    Sends progress messages to Telegram as research runs.
    """
    try:
        # Build a callback that sends Telegram status messages
        async def status_callback(msg: str):
            try:
                await update.message.reply_text(msg)
            except Exception:
                pass  # Message may be too old to reply to

        # Track last status time to avoid flooding
        last_status = {"time": 0}

        async def throttled_status(msg: str):
            now = asyncio.get_event_loop().time()
            if now - last_status["time"] > 3:  # At least 3s between messages
                last_status["time"] = now
                try:
                    await update.message.reply_text(msg)
                except Exception:
                    pass

        # Run research with progress reporting
        result = await researcher.research(topic, user_id, status_callback=throttled_status)

        # Format voice report
        voice_report = researcher.format_for_voice(result)

        # Send text summary
        summary_lines = [f"📊 **{topic}** 研究报告\n"]
        summary_lines.append(result.summary[:500])

        if result.key_findings:
            summary_lines.append("\n🔍 **关键发现：**")
            for f in result.key_findings[:5]:
                summary_lines.append(f"• {f[:200]}")

        if result.recommendations:
            summary_lines.append("\n💡 **建议：**")
            for r in result.recommendations[:3]:
                summary_lines.append(f"• {r[:200]}")

        if result.sources:
            summary_lines.append("\n📚 **主要来源：**")
            for src in result.sources[:5]:
                # Shorten display
                display = src if len(src) <= 50 else src[:47] + "..."
                summary_lines.append(f"• {display}")

        summary_text = '\n'.join(summary_lines)
        await update.message.reply_text(summary_text[:4000], parse_mode='Markdown')

        # Send voice report
        await update.message.reply_text("🎤 正在生成语音报告...")
        await voice.send_voice(voice_report, update)

    except Exception as e:
        logger.error(f"Research error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 研究失败: {str(e)[:100]}")


async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle research requests via text command"""
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

    await update.message.reply_text(f"🎤 收到，开始深度研究: **{topic}**", parse_mode='Markdown')
    await _do_research(update, topic, user_id)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice input"""
    user_id = str(update.message.from_user.id)

    try:
        # Transcribe voice
        await update.message.reply_text("🎤 收到语音，正在转录...")

        topic = await voice.transcribe(update.message.voice)

        if not topic or topic == "[语音消息]" or "[听不清" in topic:
            await update.message.reply_text(
                "抱歉，我没听清楚，请再说一遍？\n"
                "或者直接打字：研究 [话题]"
            )
            return

        await update.message.reply_text(f"🎤 听到了: **{topic}**\n正在开始研究...", parse_mode='Markdown')
        await _do_research(update, topic, user_id)

    except Exception as e:
        logger.error(f"Voice handle error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ 处理失败: {str(e)[:100]}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text input"""
    user_id = str(update.message.from_user.id)
    text = update.message.text.strip()

    # Check if it's a research request
    research_kw = ['研究', 'research', '了解', '分析', '查一下', '帮我查', '搜索']
    if any(kw in text.lower() for kw in research_kw):
        # Extract topic - strip command prefixes
        topic = text
        for prefix in ['研究', '/research', '了解', '分析', '帮我', '查一下', '搜索']:
            topic = topic.replace(prefix, '').strip()
        if topic:
            await update.message.reply_text(f"🎤 开始研究: **{topic}**", parse_mode='Markdown')
            await _do_research(update, topic, user_id)
        else:
            await update.message.reply_text("请说要研究什么话题～\n例如：研究 Tesla 竞品")
        return

    # Special commands
    if text.lower() in ['/help', 'help', '帮助']:
        await start(update, context)
        return

    if text.lower() in ['/history', '历史', '研究历史']:
        await _show_history(update, user_id)
        return

    # Default - friendly redirect
    await update.message.reply_text(
        "🐷 我是研究助手，不是聊天机器人哦~\n\n"
        "试试这样说：\n"
        "• 研究 Tesla 最近的负面新闻\n"
        "• 帮我了解 AI Agent 最新进展\n"
        "• 分析苹果公司的竞争格局\n\n"
        "或者直接发语音告诉我你想研究什么！"
    )


async def _show_history(update: Update, user_id: str):
    """Show user's research history"""
    try:
        import json
        research_file = memory.storage_dir / f"{user_id}_research.json"
        if not research_file.exists():
            await update.message.reply_text("还没有研究记录～说个话题开始吧！")
            return

        with open(research_file, 'r', encoding='utf-8') as f:
            history = json.load(f)

        if not history:
            await update.message.reply_text("还没有研究记录～说个话题开始吧！")
            return

        lines = ["📜 **研究历史**（最近5条）：\n"]
        for item in history[-5:]:
            topic = item.get('topic', '')
            ts = item.get('timestamp', '')[:10]
            summary = item.get('summary', '')[:80]
            lines.append(f"• **{topic}** ({ts})\n  {summary}...")

        await update.message.reply_text('\n'.join(lines)[:4000], parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"读取历史失败: {str(e)[:100]}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Telegram error: {context.error}")
    if update and update.message:
        await update.message.reply_text("出错了，请重试～")


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
    app.add_handler(CommandHandler("help", handle_text))
    app.add_handler(CommandHandler("history", _show_history))
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
