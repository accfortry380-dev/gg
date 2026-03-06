from fastapi import FastAPI, Request, BackgroundTasks
import requests
import os
import time
import re
import html
from urllib.parse import quote_plus

app = FastAPI()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
OWNER_USERNAME = os.environ.get("OWNER_USERNAME", "RASHIK_69").strip("@")
UPDATE_CHANNEL = os.environ.get("UPDATE_CHANNEL", "https://t.me/TrickHubBD_2nD")
AI_API = os.environ.get("AI_API", "https://ai-hyper.vercel.app/api")
WEATHER_API = os.environ.get("WEATHER_API", "https://wttr.in")
QUOTE_API = os.environ.get("QUOTE_API", "https://api.quotable.io/random")
JOKE_API = os.environ.get("JOKE_API", "https://official-joke-api.appspot.com/random_joke")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# =========================
# Helpers
# =========================

def tg_post(method: str, payload: dict):
    try:
        return requests.post(f"{TG_API}/{method}", json=payload, timeout=20).json()
    except Exception:
        return {"ok": False, "description": "Telegram request failed"}

def remove_references(text: str) -> str:
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\.\d+", "", text)
    return text.strip()

def markdown_to_html(text: str) -> str:
    code_blocks = []

    def extract(match):
        placeholder = f"__CODEBLOCK_{len(code_blocks)}__"
        code_blocks.append(match.group(1))
        return placeholder

    text = re.sub(r"```(?:\w+)?\s*([\s\S]*?)```", extract, text)
    text = re.sub(r"`([^`]*)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.*?)__", r"<b>\1</b>", text)
    text = re.sub(r"~~(.*?)~~", r"<s>\1</s>", text)
    text = re.sub(r"^###\s*(.*)$", r"<b>\1</b>", text, flags=re.MULTILINE)

    for i, code in enumerate(code_blocks):
        safe_code = html.escape(code)
        html_block = f"<pre><code>{safe_code}</code></pre>"
        text = text.replace(f"__CODEBLOCK_{i}__", html_block)

    return text

def clean_and_convert(text: str) -> str:
    text = remove_references(text)
    text = markdown_to_html(text)
    return text

def safe_html(text: str) -> str:
    return html.escape(str(text or ""))

def truncate_text(text: str, limit: int = 4090) -> str:
    if len(text) > limit:
        return text[:limit] + "\n\n<b>... [Message Truncated]</b>"
    return text

def send_message(chat_id, text, reply_markup=None, reply_to_message_id=None):
    payload = {
        "chat_id": chat_id,
        "parse_mode": "HTML",
        "text": truncate_text(text),
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    return tg_post("sendMessage", payload)

def edit_message(chat_id, message_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "parse_mode": "HTML",
        "text": truncate_text(text),
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return tg_post("editMessageText", payload)

def answer_callback(callback_query_id, text="Done"):
    return tg_post("answerCallbackQuery", {
        "callback_query_id": callback_query_id,
        "text": text,
        "show_alert": False
    })

def send_typing(chat_id):
    tg_post("sendChatAction", {"chat_id": chat_id, "action": "typing"})

def main_menu():
    return {
        "inline_keyboard": [
            [
                {"text": "🤖 AI", "callback_data": "menu_ai"},
                {"text": "🌦 Weather", "callback_data": "menu_weather"}
            ],
            [
                {"text": "😂 Joke", "callback_data": "menu_joke"},
                {"text": "💬 Quote", "callback_data": "menu_quote"}
            ],
            [
                {"text": "🔗 Shortlink", "callback_data": "menu_short"},
                {"text": "📡 IP Info", "callback_data": "menu_ip"}
            ],
            [
                {"text": "👨‍💻 Developer", "url": f"https://t.me/{OWNER_USERNAME}"},
                {"text": "📢 Updates", "url": UPDATE_CHANNEL}
            ]
        ]
    }

def back_menu():
    return {
        "inline_keyboard": [
            [{"text": "⬅️ Back To Menu", "callback_data": "menu_home"}]
        ]
    }

# =========================
# Features
# =========================

def ai_reply(query: str) -> str:
    start_time = time.time()
    ai_res = None

    while True:
        try:
            ai_res = requests.post(AI_API, json={"q": query}, timeout=20).json()
            if ai_res.get("ok"):
                raw_answer = ai_res.get("results", {}).get("answer", "")
                if raw_answer:
                    return clean_and_convert(raw_answer)
        except Exception:
            pass

        if time.time() - start_time > 30:
            break
        time.sleep(2)

    return "❌ <b>Error:</b> AI server is busy or unreachable. Please try again later."

def get_weather(city: str) -> str:
    try:
        url = f"{WEATHER_API}/{quote_plus(city)}?format=j1"
        res = requests.get(url, timeout=20).json()

        area = res["nearest_area"][0]["areaName"][0]["value"]
        country = res["nearest_area"][0]["country"][0]["value"]
        current = res["current_condition"][0]

        temp_c = current.get("temp_C", "N/A")
        feels = current.get("FeelsLikeC", "N/A")
        humidity = current.get("humidity", "N/A")
        wind = current.get("windspeedKmph", "N/A")
        desc = current["weatherDesc"][0]["value"]

        return f"""
<b>🌦 Weather Report</b>
━━━━━━━━━━━━━━━━━━━━━━
📍 <b>Location:</b> {safe_html(area)}, {safe_html(country)}
🌡 <b>Temperature:</b> <code>{safe_html(temp_c)}°C</code>
🤗 <b>Feels Like:</b> <code>{safe_html(feels)}°C</code>
💧 <b>Humidity:</b> <code>{safe_html(humidity)}%</code>
🌬 <b>Wind:</b> <code>{safe_html(wind)} km/h</code>
☁️ <b>Condition:</b> {safe_html(desc)}
"""
    except Exception:
        return "❌ <b>Error:</b> Weather info fetch failed.\n\nUsage: <code>/weather Dhaka</code>"

def get_quote() -> str:
    try:
        res = requests.get(QUOTE_API, timeout=20).json()
        content = res.get("content", "No quote found.")
        author = res.get("author", "Unknown")
        return f"""
<b>💬 Random Quote</b>
━━━━━━━━━━━━━━━━━━━━━━
<i>{safe_html(content)}</i>

— <b>{safe_html(author)}</b>
"""
    except Exception:
        return "❌ <b>Error:</b> Quote API is unavailable."

def get_joke() -> str:
    try:
        res = requests.get(JOKE_API, timeout=20).json()
        setup = res.get("setup", "No joke setup.")
        punchline = res.get("punchline", "No punchline.")
        return f"""
<b>😂 Random Joke</b>
━━━━━━━━━━━━━━━━━━━━━━
<b>{safe_html(setup)}</b>

{safe_html(punchline)}
"""
    except Exception:
        return "❌ <b>Error:</b> Joke API is unavailable."

def get_ip_info(ip_or_domain: str) -> str:
    try:
        res = requests.get(f"http://ip-api.com/json/{quote_plus(ip_or_domain)}", timeout=20).json()
        if res.get("status") != "success":
            return "❌ <b>Error:</b> Invalid IP or domain."

        return f"""
<b>📡 IP Information</b>
━━━━━━━━━━━━━━━━━━━━━━
🔎 <b>Query:</b> <code>{safe_html(res.get("query"))}</code>
🌍 <b>Country:</b> {safe_html(res.get("country"))}
🏙 <b>City:</b> {safe_html(res.get("city"))}
🗺 <b>Region:</b> {safe_html(res.get("regionName"))}
📮 <b>ZIP:</b> {safe_html(res.get("zip"))}
🛰 <b>ISP:</b> {safe_html(res.get("isp"))}
🕒 <b>Timezone:</b> {safe_html(res.get("timezone"))}
"""
    except Exception:
        return "❌ <b>Error:</b> IP info fetch failed."

def shorten_link(url: str) -> str:
    try:
        api = f"https://is.gd/create.php?format=simple&url={quote_plus(url)}"
        short = requests.get(api, timeout=20).text.strip()
        if short.startswith("Error"):
            return "❌ <b>Error:</b> Could not shorten this link."
        return f"""
<b>🔗 Short Link Created</b>
━━━━━━━━━━━━━━━━━━━━━━
🌐 <b>Original:</b>
<code>{safe_html(url)}</code>

⚡ <b>Short:</b>
<code>{safe_html(short)}</code>
"""
    except Exception:
        return "❌ <b>Error:</b> Shortlink service unavailable."

# =========================
# Router
# =========================

def handle_start(chat_id: int, user_info: dict):
    name = safe_html(user_info.get("first_name", "User"))
    welcome_msg = f"""
<b>👋 Welcome to API Hub Pro</b>
━━━━━━━━━━━━━━━━━━━━━━
🤖 <b>Multi-Tool Telegram Bot</b>
<i>Powered by FastAPI + Webhook</i>

👤 <b>User:</b> {name}
🆔 <b>ID:</b> <code>{chat_id}</code>

🚀 <b>Features:</b>
• AI Chat
• Weather Lookup
• Random Joke
• Random Quote
• IP Info
• Short Link Tool

👇 <b>Select a tool below:</b>
"""
    send_message(chat_id, welcome_msg, main_menu())

def handle_help(chat_id: int):
    help_msg = """
<b>🆘 API Hub Help Center</b>
━━━━━━━━━━━━━━━━━━━━━━
<b>📌 Commands:</b>
• /start - Show main menu
• /help - Bot instructions
• /about - Developer info
• /ai your question
• /weather city
• /joke
• /quote
• /ip 8.8.8.8
• /short https://example.com

<b>💡 Examples:</b>
• <code>/ai Write a Python calculator</code>
• <code>/weather Dhaka</code>
• <code>/ip google.com</code>
• <code>/short https://openai.com</code>
"""
    send_message(chat_id, help_msg, back_menu())

def handle_about(chat_id: int):
    about_msg = f"""
<b>ℹ️ About API Hub Pro</b>
━━━━━━━━━━━━━━━━━━━━━━
🛠 <b>Developer:</b> <a href="https://t.me/{OWNER_USERNAME}">@{OWNER_USERNAME}</a>
📡 <b>Channel:</b> <a href="{safe_html(UPDATE_CHANNEL)}">Updates Channel</a>
⚙️ <b>Version:</b> <code>1.0.0 Stable</code>

🧩 <b>Technology:</b>
• FastAPI (Python)
• Telegram Bot API
• Vercel Serverless
• External Utility APIs

<i>Made with ❤️</i>
"""
    send_message(chat_id, about_msg, back_menu())

def process_text(chat_id: int, text: str, message_id: int, user_info: dict):
    text = text.strip()

    if text == "/start":
        handle_start(chat_id, user_info)
        return

    if text == "/help":
        handle_help(chat_id)
        return

    if text == "/about":
        handle_about(chat_id)
        return

    if text.startswith("/weather "):
        city = text.replace("/weather ", "", 1).strip()
        if not city:
            send_message(chat_id, "⚠️ শহরের নাম দাও.\n\nExample: <code>/weather Dhaka</code>", reply_to_message_id=message_id)
            return
        send_typing(chat_id)
        send_message(chat_id, get_weather(city), back_menu(), reply_to_message_id=message_id)
        return

    if text == "/quote":
        send_typing(chat_id)
        send_message(chat_id, get_quote(), back_menu(), reply_to_message_id=message_id)
        return

    if text == "/joke":
        send_typing(chat_id)
        send_message(chat_id, get_joke(), back_menu(), reply_to_message_id=message_id)
        return

    if text.startswith("/ip "):
        target = text.replace("/ip ", "", 1).strip()
        if not target:
            send_message(chat_id, "⚠️ IP বা domain দাও.\n\nExample: <code>/ip 8.8.8.8</code>", reply_to_message_id=message_id)
            return
        send_typing(chat_id)
        send_message(chat_id, get_ip_info(target), back_menu(), reply_to_message_id=message_id)
        return

    if text.startswith("/short "):
        url = text.replace("/short ", "", 1).strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            send_message(chat_id, "⚠️ Full URL দাও.\n\nExample: <code>/short https://example.com</code>", reply_to_message_id=message_id)
            return
        send_typing(chat_id)
        send_message(chat_id, shorten_link(url), back_menu(), reply_to_message_id=message_id)
        return

    if text.startswith("/ai "):
        query = text.replace("/ai ", "", 1).strip()
        if not query:
            send_message(chat_id, "⚠️ প্রশ্ন দাও.\n\nExample: <code>/ai make a python calculator</code>", reply_to_message_id=message_id)
            return

        thinking = send_message(
            chat_id,
            "🔮 <i>Thinking...</i>",
            reply_to_message_id=message_id
        )

        if not thinking.get("ok"):
            return

        thinking_id = thinking["result"]["message_id"]
        send_typing(chat_id)
        result = ai_reply(query)
        edit_message(chat_id, thinking_id, result)
        return

    # default = AI chat
    thinking = send_message(
        chat_id,
        "🔮 <i>Thinking...</i>",
        reply_to_message_id=message_id
    )

    if not thinking.get("ok"):
        return

    thinking_id = thinking["result"]["message_id"]
    send_typing(chat_id)
    result = ai_reply(text)
    edit_message(chat_id, thinking_id, result)

def process_callback(callback: dict):
    cq_id = callback["id"]
    msg = callback.get("message", {})
    chat_id = msg["chat"]["id"]
    message_id = msg["message_id"]
    data = callback.get("data", "")

    answer_callback(cq_id, "Opened")

    if data == "menu_home":
        text = """
<b>🏠 API Hub Main Menu</b>
━━━━━━━━━━━━━━━━━━━━━━
Choose any tool below.
"""
        edit_message(chat_id, message_id, text, main_menu())
        return

    menus = {
        "menu_ai": """
<b>🤖 AI Chat Tool</b>
━━━━━━━━━━━━━━━━━━━━━━
Use:
<code>/ai your question</code>

Or just send any normal message directly.
""",
        "menu_weather": """
<b>🌦 Weather Tool</b>
━━━━━━━━━━━━━━━━━━━━━━
Use:
<code>/weather Dhaka</code>
""",
        "menu_joke": """
<b>😂 Joke Tool</b>
━━━━━━━━━━━━━━━━━━━━━━
Use:
<code>/joke</code>
""",
        "menu_quote": """
<b>💬 Quote Tool</b>
━━━━━━━━━━━━━━━━━━━━━━
Use:
<code>/quote</code>
""",
        "menu_short": """
<b>🔗 Short Link Tool</b>
━━━━━━━━━━━━━━━━━━━━━━
Use:
<code>/short https://example.com</code>
""",
        "menu_ip": """
<b>📡 IP Info Tool</b>
━━━━━━━━━━━━━━━━━━━━━━
Use:
<code>/ip 8.8.8.8</code>
or
<code>/ip google.com</code>
"""
    }

    content = menus.get(data, "<b>Unknown menu</b>")
    edit_message(chat_id, message_id, content, back_menu())

# =========================
# FastAPI Routes
# =========================

@app.get("/")
def home():
    return {"status": "Active", "bot": "API Hub Pro", "webhook": "/webhook"}

@app.get("/health")
def health():
    return {"ok": True, "message": "Bot is running"}

@app.post("/webhook")
async def telegram_webhook(req: Request, background_tasks: BackgroundTasks):
    data = await req.json()

    if "message" in data:
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "").strip()
        message_id = msg.get("message_id")
        user = msg.get("from", {})

        if text:
            background_tasks.add_task(process_text, chat_id, text, message_id, user)

    elif "callback_query" in data:
        callback = data["callback_query"]
        background_tasks.add_task(process_callback, callback)

    return {"ok": True}