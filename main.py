"""
Piggy Voice AI Agent - Main Entry Point
Speaks to you, listens to you, gets things done.
"""

import os
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, VoiceHandler, filters, ContextTypes

# Load environment
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Import our modules
from voice_handler import process_voice_message, send_voice_message
from llm_client import LLMClient
from task_executor import TaskExecutor
from memory import Memory

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize modules
llm = LLMClient()
executor = TaskExecutor()
memory = Memory()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await update.message.reply_text(
        "🐷 你好！我是 Piggy，你的语音 AI 助手。\n\n"
        "发语音给我，或者直接打字，我会帮你完成任务！\n\n"
        "示例：\n"
        "• '帮我搜索最新的 AI 新闻'\n"
        "• '写一个 Python 脚本'\n"
        "• '研究一下 [主题] 的竞争对手'\n\n"
        "我可以用语音回复你～"
    )


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
        "• 📅 日程管理和提醒\n"
        "• 🌐 网页内容抓取\n\n"
        "有需求尽管说！"
    )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming voice messages"""
    try:
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        
        logger.info(f"收到 {user_name} 的语音消息")
        
        # Process voice → text → LLM → action → TTS response
        result = await process_voice_message(
            update=update,
            llm=llm,
            executor=executor,
            memory=memory,
            user_id=user_id
        )
        
        # Send voice response back
        if result.get('voice_response'):
            await send_voice_message(update, result['voice_response'])
        
        # Also send text summary
        if result.get('text_summary'):
            await update.message.reply_text(result['text_summary'])
            
    except Exception as e:
        logger.error(f"处理语音消息失败: {e}")
        await update.message.reply_text(f"❌ 处理失败: {str(e)}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages"""
    try:
        user_id = update.message.from_user.id
        user_name = update.message.from_user.first_name
        text = update.message.text
        
        logger.info(f"收到 {user_name} 的文字消息: {text[:50]}...")
        
        # Process text → LLM → action → TTS response
        result = await process_text_message(
            update=update,
            text=text,
            llm=llm,
            executor=executor,
            memory=memory,
            user_id=user_id
        )
        
        # Send voice response back
        if result.get('voice_response'):
            await send_voice_message(update, result['voice_response'])
        
        # Also send text summary
        if result.get('text_summary'):
            await update.message.reply_text(result['text_summary'])
            
    except Exception as e:
        logger.error(f"处理文字消息失败: {e}")
        await update.message.reply_text(f"❌ 处理失败: {str(e)}")


async def process_text_message(update, text, llm, executor, memory, user_id):
    """Process a text message and generate response"""
    # Get conversation history from memory
    history = memory.get_conversation(user_id)
    
    # Add user message to history
    history.append({"role": "user", "content": text})
    
    # Get LLM response with task planning
    prompt = build_prompt(text, history)
    response = await llm.chat(prompt)
    
    # Execute tasks if needed
    tasks = extract_tasks(response)
    results = []
    for task in tasks:
        result = await executor.execute(task)
        results.append(result)
    
    # Build final response
    if results:
        final_response = synthesize_results(text, response, results)
    else:
        final_response = response
    
    # Save to memory
    history.append({"role": "assistant", "content": final_response})
    memory.save_conversation(user_id, history)
    
    return {
        'voice_response': final_response,
        'text_summary': None
    }


def build_prompt(user_input, history):
    """Build the prompt for the LLM"""
    history_text = "\n".join([f"{m['role']}: {m['content']}" for m in history[-10:]])
    
    return f"""你是一个智能助手 Piggy，用户通过 Telegram 与你对话。

对话历史：
{history_text}

用户：{user_input}

Piggy 的职责：
1. 理解用户需求
2. 制定执行计划（如果需要多步骤）
3. 用简洁、自然的语言回复
4. 如果需要执行任务，在回复末尾用 [TASK] 标签标注

[TASK] 标签格式：
- 搜索任务：[TASK] SEARCH: <搜索 query>
- 编码任务：[TASK] CODE: <任务描述>
- 研究任务：[TASK] RESEARCH: <研究主题>
- 通用任务：[TASK] EXECUTE: <任务描述>

请回复："""


def extract_tasks(response):
    """Extract tasks from LLM response"""
    import re
    tasks = []
    task_pattern = r'\[TASK\] (\w+): (.+)'
    matches = re.findall(task_pattern, response)
    for match in matches:
        task_type, task_desc = match
        tasks.append({'type': task_type, 'description': task_desc})
    return tasks


async def synthesize_results(original_request, llm_response, task_results):
    """Synthesize task results into final response"""
    results_text = "\n".join([str(r) for r in task_results])
    
    synthesis_prompt = f"""用户请求：{original_request}

LLM 原始回复：{llm_response}

执行结果：
{results_text}

请根据执行结果，给用户一个简洁的总结回复。用自然语言，不要重复上述信息。
"""
    
    final = await llm.chat(synthesis_prompt)
    return final


def main():
    """Start the bot"""
    logger.info("🐷 Piggy Voice Agent 启动中...")
    
    # Build application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(VoiceHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("🐷 Piggy 已就绪！")
    
    # Start polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
