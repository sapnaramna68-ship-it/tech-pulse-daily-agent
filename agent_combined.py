"""
Tech Pulse Daily - Combined Agent (Scheduler + Chat, ek saath)
------------------------------------------------------------------
Ye single script channel ko poori tarah handle karta hai:

1. SCHEDULED POSTS: Fixed time (jo tumne set kiya hai) par channel mein
   automatically news digest (photo + text) post karta hai
2. CONVERSATIONAL AGENT: Isi waqt, jo bhi tumhe (ya channel mein kisi ko)
   message aaye, uska bhi turant reply deta hai - insaan jaisa

Dono cheezein EK HI terminal mein, EK HI samay par chalti hain
(Python "threading" ke through) - isliye ab tumhe alag-alag scripts
chalane ki zaroorat nahi.

Run karne se pehle:
- .env file mein saari keys honi chahiye (already hain)
- pip install -r requirements.txt

Time badalne ke liye neeche "POST_TIME" variable edit karo.
"""

import os
import time
import json
import threading
import schedule
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ==================== YAHAN TIME SET KARO ====================
POST_TIME = "09:00"   # 24-hour format, jaise "18:30" = shaam 6:30
# ===============================================================

SYSTEM_PERSONALITY = """
Tumhara naam "Pulse" hai. Tum "Tech Pulse Daily" channel ke friendly
assistant ho. Hinglish (Hindi-English mix) mein, warm aur natural
tarike se baat karo - robotic mat lagna. Chhote, seedhe replies do
(2-4 lines).

Zaroori: Agar koi tumhara naam poochhe, hamesha "Pulse" hi batana -
kabhi koi aur naam mat lena.
"""


# ==================== SCHEDULED DIGEST POSTING ====================
def fetch_news():
    url = "https://serpapi.com/search.json"
    params = {"q": "latest tech AI news today", "tbm": "nws", "api_key": SERPAPI_KEY, "num": 6}
    res = requests.get(url, params=params)
    data = res.json()
    articles = []
    for item in data.get("news_results", [])[:5]:
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        source = item.get("source", "")
        if title:
            articles.append(f"- {title} ({source}): {snippet}")
    return "\n".join(articles) if articles else "No fresh news found today."


MEMORY_FILE = "user_memory.json"


def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}


def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def remember_name_if_mentioned(chat_id, text):
    """Simple pattern match - agar user apna naam bataye, save kar lo.
    Sawaal wale words (kya, kaun, etc.) ko naam samajhne se bachate hain."""
    import re

    # Ye words kabhi bhi naam nahi ho sakte - inhe ignore karo
    blacklist = {
        "kya", "kaun", "kaisa", "kaisi", "kahan", "kab", "batao",
        "hai", "ho", "kar", "toh", "bhi", "mera", "mere", "tera",
    }

    patterns = [
        r"mera naam\s+([A-Za-z]+)\s+h",
        r"mere naam\s+([A-Za-z]+)\s+h",
        r"main\s+([A-Za-z]+)\s+(?:hoon|bol raha)",
        r"my name is\s+([A-Za-z]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            candidate = match.group(1)
            # Agar sentence mein "kya" hai (sawaal), ya candidate blacklist mein hai, skip karo
            if "kya" in text.lower() or candidate.lower() in blacklist:
                continue
            memory = load_memory()
            key = str(chat_id)
            if key not in memory:
                memory[key] = {}
            memory[key]["name"] = candidate.capitalize()
            save_memory(memory)
            return candidate.capitalize()
    return None


def get_user_context(chat_id):
    """User ke baare mein yaad rakhi hui info, system prompt mein daalne ke liye."""
    memory = load_memory()
    user_data = memory.get(str(chat_id), {})
    if user_data.get("name"):
        return f"\n\nZaroori: Is user ka naam '{user_data['name']}' hai - use isi naam se bulao, poochna mat."
    return ""


def groq_chat(messages, max_tokens=500, model="openai/gpt-oss-120b"):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
    res = requests.post(url, headers=headers, json=payload)
    data = res.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError):
        print("Groq error:", data)
        return None


def generate_digest(raw_news: str):
    today = datetime.now().strftime("%d %B %Y")
    prompt = f"""
Aaj ki date hai {today}. Neeche diye gaye raw news ko use karke ek clean
Telegram post banao, Hinglish mein, is format mein:

RAW NEWS:
{raw_news}

🔥 <b>TECH DIGEST | {today}</b>

1️⃣ <b>[Headline]</b>
[2 line summary]

2️⃣ <b>[Headline]</b>
[2 line summary]

3️⃣ <b>[Headline]</b>
[2 line summary]

📌 <b>AI Update of the Day:</b>
[Summary]

#TechNews #AI #DailyDigest

Sirf final message do, extra explanation mat likhna.
"""
    return groq_chat([{"role": "user", "content": prompt}], max_tokens=800)


def fetch_source_link(topic: str):
    """
    SerpAPI se topic ke baare mein search karke ek relevant source link
    return karta hai (jo Chrome mein khulega jab user tap karega).
    """
    try:
        url = "https://serpapi.com/search.json"
        params = {"q": topic, "api_key": SERPAPI_KEY, "num": 3}
        res = requests.get(url, params=params)
        data = res.json()
        results = data.get("organic_results", [])
        if results:
            return results[0].get("link")
    except Exception as e:
        print("fetch_source_link error:", e)
    return None


def fetch_image_url(query="technology AI"):
    url = "https://api.unsplash.com/photos/random"
    params = {"query": query, "client_id": UNSPLASH_ACCESS_KEY, "orientation": "landscape"}
    res = requests.get(url, params=params)
    if res.status_code == 200:
        return res.json().get("urls", {}).get("regular")
    return None


def send_photo(image_url, caption=None):
    url = f"{TELEGRAM_API}/sendPhoto"
    payload = {"chat_id": TELEGRAM_CHANNEL_ID, "photo": image_url}
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = "HTML"
    requests.post(url, json=payload)


def send_channel_message(text):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHANNEL_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    requests.post(url, json=payload)


def run_daily_post():
    print(f"[{datetime.now()}] Scheduled post: fetching news...")
    raw_news = fetch_news()
    digest = generate_digest(raw_news)
    if not digest:
        print("Digest generation failed.")
        return
    image_url = fetch_image_url()
    if image_url and len(digest) <= 1024:
        send_photo(image_url, caption=digest)
    elif image_url:
        send_photo(image_url)
        send_channel_message(digest)
    else:
        send_channel_message(digest)
    save_update_to_supabase(digest)
    print(f"[{datetime.now()}] Scheduled post done!")


def scheduler_loop():
    schedule.every().day.at(POST_TIME).do(run_daily_post)
    print(f"Scheduler active: roz {POST_TIME} par digest post hoga.")
    while True:
        schedule.run_pending()
        time.sleep(30)


# ==================== CONVERSATIONAL AGENT ====================
# ==================== SUPABASE MEMORY ====================
def save_update_to_supabase(content: str):
    """Har channel post ko Supabase mein save karta hai, taaki baad mein
    'parso/pichle hafte kya post kiya tha' jaise sawaal ka jawab de sakein."""
    try:
        url = f"{SUPABASE_URL}/rest/v1/channel_updates"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"content": content}
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code not in (200, 201):
            print("Supabase save error:", res.status_code, res.text)
    except Exception as e:
        print("Supabase save exception:", e)


def get_recent_updates(limit=15):
    """Supabase se recent posts nikalta hai (naye se purane order mein)."""
    try:
        url = f"{SUPABASE_URL}/rest/v1/channel_updates"
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        params = {"select": "content,posted_at", "order": "posted_at.desc", "limit": limit}
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            return res.json()
        print("Supabase fetch error:", res.status_code, res.text)
        return []
    except Exception as e:
        print("Supabase fetch exception:", e)
        return []


def answer_from_history(user_question: str):
    """User ke sawaal (jaise 'parso kya post kiya tha') ka jawab, Supabase
    mein saved history ke aadhar par Groq se generate karta hai."""
    updates = get_recent_updates()
    if not updates:
        return "Abhi tak mere paas koi purani post ka record nahi hai."

    history_text = "\n".join(
        f"- [{u['posted_at']}] {u['content'][:200]}" for u in updates
    )

    prompt = f"""
User ne poochha: "{user_question}"

Neeche channel ki recent posts ki history hai (date/time ke saath):
{history_text}

Is history ke aadhar par user ke sawaal ka Hinglish mein, natural,
chhota jawab do (2-4 lines). Agar exact date ka data na mile, jo
closest/relevant mile wo batao.
"""
    return groq_chat([{"role": "user", "content": prompt}], max_tokens=400) or \
        "Sorry, history check karne mein dikkat aa gayi."


def get_updates(offset=None):
    url = f"{TELEGRAM_API}/getUpdates"
    params = {"timeout": 20, "offset": offset}
    res = requests.get(url, params=params, timeout=30)
    return res.json().get("result", [])


def send_reply(chat_id, text, reply_to_message_id=None):
    url = f"{TELEGRAM_API}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    requests.post(url, json=payload)


def classify_intent(user_message: str):
    """
    Groq se poochte hain ki message ka intent kya hai - normal chat ya
    channel par post karne ka command.
    """
    prompt = f"""
User ka message: "{user_message}"

Iska intent classify karo aur SIRF JSON return karo (koi extra text nahi):

{{"action": "post_channel" | "history" | "chat", "content": "..."}}

Rules:
- "post_channel": agar user seedha keh raha hai channel par kuch post/daalo/bhejo
  (jaise "channel par post karo ki...", "yeh message channel mein daalo",
  "channel ko ye message bhejo")
  -> content = jo exact text post karna hai (sirf wo hissa, "channel par post karo" jaisa
     instruction hata kar)
- "history": agar user pooch raha hai ki pehle/parso/pichle hafte/kal kya post
  kiya tha, ya channel ki purani updates ke baare mein poochh raha hai
  -> content = user ka poora sawaal, jaisa hai waisa hi
- "chat": baaki sab normal conversation

Sirf JSON do, kuch aur mat likhna.
"""
    result = groq_chat([{"role": "user", "content": prompt}], max_tokens=200)
    if not result:
        return {"action": "chat", "content": user_message}
    try:
        cleaned = result.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"action": "chat", "content": user_message}


def chat_loop():
    print("Chat agent active: messages ka reply dega, aur commands bhi follow karega.")
    offset = None
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message") or update.get("channel_post")
                if not message:
                    continue
                text = message.get("text")
                if not text or text.startswith("/"):
                    continue
                chat_id = message["chat"]["id"]
                message_id = message["message_id"]

                print(f"New message: {text}")

                remember_name_if_mentioned(chat_id, text)
                user_context = get_user_context(chat_id)

                intent = classify_intent(text)
                action = intent.get("action", "chat")
                content = intent.get("content", text)

                if action == "post_channel":
                    # Topic ke baare mein ek source link dhoondo (SerpAPI se)
                    source_link = fetch_source_link(content)

                    polished = groq_chat(
                        [
                            {
                                "role": "system",
                                "content": (
                                    "Tum Tech Pulse Daily channel ke liye content likhte ho. "
                                    "User jo topic/idea de, usse samajh kar ek achha likha hua, "
                                    "engaging Telegram post banao (Hinglish mein, 2-5 lines, "
                                    "emoji ka thoda use karo). Sirf final post do, koi extra "
                                    "explanation ya preamble mat likhna - seedha post likhna hai."
                                ),
                            },
                            {"role": "user", "content": content},
                        ],
                        max_tokens=400,
                    ) or content

                    if source_link:
                        polished = f"{polished}\n\n🔗 Read more: {source_link}"

                    image_url = fetch_image_url(content)

                    if image_url and len(polished) <= 1024:
                        send_photo(image_url, caption=polished)
                    elif image_url:
                        send_photo(image_url)
                        send_channel_message(polished)
                    else:
                        send_channel_message(polished)

                    reply = f"Ho gaya! Maine channel par photo + link ke saath post kar diya:\n\n{polished}"
                    save_update_to_supabase(polished)
                elif action == "history":
                    reply = answer_from_history(text)
                else:
                    reply = groq_chat(
                        [
                            {"role": "system", "content": SYSTEM_PERSONALITY + user_context},
                            {"role": "user", "content": text},
                        ]
                    ) or "Sorry, thodi dikkat aa gayi!"

                send_reply(chat_id, reply, reply_to_message_id=message_id)
                print(f"Replied: {reply}")
        except Exception as e:
            print("Chat loop error:", e)
            time.sleep(5)


# ==================== RENDER KE LIYE CHHOTA WEB SERVER ====================
# Render free tier sirf "Web Service" ko free mein chalane deta hai (jo
# ek port par sunta hai). Isliye hum ek chhota Flask server bana rahe hain
# jo bas "Bot is running!" dikhata hai - asli kaam (scheduler + chat) 
# background threads mein chalta hai.
from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "Tech Pulse Daily agent is running! 🚀"


# ==================== MAIN: SAB EK SAATH CHALAO ====================
if __name__ == "__main__":
    print("=== Tech Pulse Daily - Combined Agent Starting ===")

    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()

    chat_thread = threading.Thread(target=chat_loop, daemon=True)
    chat_thread.start()

    # Render environment variable PORT provide karta hai - use hi use karo
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
