# 🐷 Piggy - Voice AI Agent

> Speak to control everything. Your 24/7 AI agent on Telegram.

## 🎯 What is Piggy?

Piggy is a **voice-first AI agent** that listens to you, understands your needs, and actually **gets things done**. Not just chat — real execution.

You speak to it on Telegram. It speaks back.

## ✨ Features

- 🎤 **Voice-first** — Talk to Piggy, it talks back
- 🤖 **Actually does things** — Not just chat, but executes tasks
- 🔍 **Web research** — Searches and synthesizes information
- 💻 **Coding assistant** — Writes, reviews, and fixes code
- 🧠 **Self-improving** — Gets smarter over time
- 💾 **Persistent memory** — Remembers everything
- 🔄 **Subagent parallelism** — Handles multiple tasks at once

## 🚀 Quick Start

### 1. Get Required APIs

- **MiniMax API** (for LLM + TTS): https://platform.minimax.io
- **Telegram Bot Token**: https://t.me/BotFather

### 2. Install

```bash
git clone https://github.com/Leonxu6/piggy-voice-agent.git
cd piggy-voice-agent
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Run

```bash
python main.py
```

## 📱 Usage

Send Piggy a voice message or text on Telegram:

- "Search for the latest AI news"
- "Write a Python script to rename files"
- "What's my schedule tomorrow?"
- "Research competitor products for [topic]"

Piggy will research, execute, and report back with a voice response.

## 🏗️ Architecture

```
Telegram Voice Message
        ↓
Speech-to-Text (MiniMax STT)
        ↓
MiniMax LLM (M2.7) - Analyze & Plan
        ↓
┌───────┴───────┐
↓               ↓
Subagent 1    Subagent 2    Subagent 3
(Web Search)  (Coding)     (Research)
        ↓
        ↓
TTS Generation (MiniMax TTS)
        ↓
Voice Response on Telegram
```

## 💡 Use Cases

- **Researchers** — Get comprehensive reports on any topic
- **Developers** — Coding help without switching context
- **Entrepreneurs** — Market research and competitive analysis
- **Students** — Learn anything with voice conversations
- **Busy professionals** — Delegate tasks by voice

## 🧠 Tech Stack

- **LLM**: MiniMax M2.7 (via OpenClaw)
- **TTS**: MiniMax speech-2.8-hd
- **Platform**: Telegram Bot API
- **Execution**: Subagent parallelism
- **Memory**: Persistent context

## 📄 License

MIT License

---

*🐷 Built with ❤️ by Piggy AI Agent*
