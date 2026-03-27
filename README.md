# 🐷 Piggy - Voice Research Agent

> Ask by voice. Piggy researches it. Reports back by voice.

**Not a chatbot. Not a toy. A real research tool that speaks.**

## 🎯 The Problem We Solve

Every day, professionals need to research topics:
- "研究竞品分析"
- "最新AI行业动态"
- "帮我了解某项技术"

**Current options all suck:**
- Google → 信息太多太杂,要花几小时
- ChatGPT → 只知道训练数据,没有最新信息
- Perplexity → 好,但只能文字,不能语音
- Siri/Alexa → 玩具,只能答简单问题

**Piggy solves this:**
你说一个话题,Piggy 真正去研究它,用语音报告结果。

## 💡 What Piggy Does

```
你 (语音): "研究 Tesla 的主要竞争对手"

Piggy 做的:
1. 🎤 语音 → 文字
2. 🔍 多源搜索 (HackerNews + Reddit + News + 知乎 + 微博 + 百度新闻)
3. 📖 深度分析搜索摘要 (LLM)
4. 🧠 可信度评估 + 综合报告
5. 🎤 语音报告结果

整个过程 1-2 分钟,你在做别的事
```

## 📊 Features

- 🎤 **Voice First** — 说话就能用，不用打字
- 🔍 **Real Research** — 真正去网上搜索，不是瞎编
- 🇨🇳 **CN + EN Sources** — 知乎、微博、百度新闻 + HackerNews + Reddit + News
- 🧠 **Smart Synthesis** — LLM 综合分析，发现关联和趋势
- ✅ **Credibility Scoring** — 信息可信度分级，避免被垃圾信息误导
- 🎤 **Voice Report** — 走路、开车、健身都能听
- 💾 **Memory** — 记住你的偏好和之前的 research
- 📈 **Real-time Progress** — 研究过程实时推送状态，不让你干等

## 💰 Use Cases

| 场景 | 没有 Piggy | 有 Piggy |
|------|-----------|---------|
| 开车上班 | 无法研究 | 听研究报告 |
| 健身时 | 无法阅读 | 听行业分析 |
| 睡前想了解 | 要花1小时 | 5分钟听完 |
| 快速了解竞品 | Google太慢 | 直接语音回答 |

## 🏗️ Architecture

```
Voice Input (STT)
    ↓
Research Planner (LLM)
    ↓
┌────┴────┐
↓         ↓
Search   Read
(10+ sources)  (Pages)
    ↓
Synthesize (LLM)
    ↓
Voice Report (TTS)
```

## 🔧 Tech Stack

- **LLM**: MiniMax M2.7
- **TTS**: MiniMax speech-2.8-hd (Warm Girl voice)
- **STT**: Google Speech API (free tier)
- **Search**: HackerNews + Reddit + Google News + 知乎 + 微博 + 百度新闻
- **Memory**: Per-user context + history
- **HTTP**: httpx (fully async)

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/Leonxu6/piggy-voice-agent.git
cd piggy-voice-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
# Edit .env with your tokens

# 4. Run
python main.py
```

## ⚙️ Configuration

Get your tokens:
- **Telegram Bot**: https://t.me/BotFather
- **MiniMax API**: https://platform.minimax.io

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
MINIMAX_API_KEY=your_minimax_api_key_here
```

## 📄 License

MIT

---

*Built with ❤️ by Piggy AI*
