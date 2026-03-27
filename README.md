# 🐷 Piggy - Voice AI Agent

> Speak to control everything. Your 24/7 AI agent on Telegram.

## 🎯 What is Piggy?

Piggy is a **voice-first AI agent** that listens to you, understands your needs, and actually **gets things done**. Not just chat — real execution.

You speak to it on Telegram. It speaks back with voice.

## ✨ Features

- 🎤 **Voice-first** — Talk to Piggy, it talks back
- 🤖 **Actually does things** — Not just chat, but executes tasks
- 🔍 **Web research** — Multi-source search (HN, Reddit, News)
- 💻 **Coding assistant** — Writes, reviews, and fixes code
- 📊 **Deep research** — Comprehensive reports on any topic
- 🧠 **Self-improving** — Gets smarter over time
- 💾 **Persistent memory** — Remembers everything
- 🔄 **Subagent parallelism** — Handles multiple tasks at once

## 💰 Pricing

| Plan | Price | Features |
|------|-------|----------|
| Free | $0 | 10 requests/day |
| Pro | $19/mo | Unlimited requests |
| Team | $49/mo | 5 agents, team features |

**Competitors:** Relsa $39/mo, Angie $29/mo

## 🚀 Quick Start

### 1. Get Required APIs

- **MiniMax API** (LLM + TTS): https://platform.minimax.io
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

```
You: "搜索最新的 AI 新闻"
Piggy: 🎤 [语音回复] "找到了5条关于AI语音代理的最新资讯..."

You: "研究一下 Tesla 的竞争对手"
Piggy: 🎤 [语音回复] "根据研究，特斯拉的主要竞争对手包括..."

You: "帮我写个 Python 脚本处理文件"
Piggy: 🎤 [语音回复] "写好了，脚本已创建..."
```

## 🏗️ Architecture

```
Telegram Voice/Text
        ↓
MiniMax LLM (M2.7) - Understand & Plan
        ↓
┌───────┴───────┐
↓               ↓
Task Executor  Memory
(Search/Code)  (Context)
        ↓
MiniMax TTS (speech-2.8-hd)
        ↓
Voice Response on Telegram
```

## 📊 Tech Stack

- **LLM**: MiniMax M2.7
- **TTS**: MiniMax speech-2.8-hd (Chinese Soft Girl voice)
- **Platform**: Telegram Bot API
- **Search**: HackerNews + Reddit + Google News
- **Memory**: Persistent JSON storage

## 📄 License

MIT License

---

*🐷 Built with ❤️ by Piggy AI Agent*
