
# 🤖 Tech Pulse Daily — Telegram AI Agent

An AI agent that runs an entire Telegram channel on its own — posts a
fresh news digest on a schedule, replies to messages and commands in
natural Hinglish, and remembers what it's already posted so it can
answer questions like *"what did you post yesterday?"*

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-F55036?style=flat-square)
![Supabase](https://img.shields.io/badge/Supabase-3FCF8E?style=flat-square&logo=supabase&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white)

🔗 **Live:** [@techpulse_daily_bot](https://t.me/techpulse_daily_bot) on Telegram — running 24/7 on Railway

## ✨ What it does

The agent handles a Telegram channel the way a real (very dedicated)
admin would — posting on time, replying to people, and remembering
what it's already told them.

- 📰 **Scheduled posting** — fetches real tech/AI news, writes a
  Hinglish digest with a photo, and posts it to the channel at a fixed
  time every day
- 💬 **Conversational replies** — replies to DMs and channel messages
  in natural, friendly Hinglish
- 📢 **Command-driven posting** — tell it "channel par post karo about
  X" and it researches the topic, writes a polished post, finds a
  relevant photo and source link, and publishes it
- 🧠 **Memory** — every post is logged to Supabase, so it can answer
  "what did you post yesterday?" or "how many updates so far?"
- ☁️ **Runs independently** — deployed on Railway, no computer needs
  to stay on

## 🛠️ Tech stack

- **Python** — core agent logic
- **Groq API** — fast, free LLM for writing posts and replies
- **SerpAPI** — fetches real news and search results
- **Unsplash API** — relevant photos for each post
- **Supabase** — stores post history (the agent's memory)
- **Telegram Bot API** — the actual channel/chat interface
- **Flask** — minimal web server so it runs as a Railway web service
- Deployed on **Railway**

## 📁 Project structure

```
.
├── agent_combined.py   # scheduler + chat loop + Supabase memory, all in one
└── requirements.txt    # dependencies
```

## 🚀 Run it locally

**Prerequisites:** Python 3.10+

```bash
git clone https://github.com/sapnaramna68-ship-it/tech-pulse-daily-agent.git
cd tech-pulse-daily-agent
pip install -r requirements.txt
```

Create a `.env` file with:

```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=@yourchannel
GROQ_API_KEY=your_groq_key
SERPAPI_KEY=your_serpapi_key
UNSPLASH_ACCESS_KEY=your_unsplash_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

Then run it:

```bash
python agent_combined.py
```

## 📄 License

MIT © Sapna
