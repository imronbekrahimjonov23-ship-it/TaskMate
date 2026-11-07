import os
import threading
import requests
from flask import Flask, request

app = Flask(__name__)
TOKEN = os.environ.get("BOT_TOKEN", "")
API = f"https://api.telegram.org/bot{TOKEN}"
tasks = {}
lock = threading.Lock()

def send(chat_id, text):
    requests.post(
        API + "/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=15
    )

def handle(user_id, text):
    text = text.strip()
    if text == "/start" or text == "/help":
        return (
            "✅ TaskMate botiga xush kelibsiz!\n\n"
            "Vazifa qo‘shish: /add Kitob o‘qish\n"
            "Ro‘yxat: /list\n"
            "Bajarildi: /done 1\n"
            "Tahrirlash: /edit 1 Yangi nom\n"
            "O‘chirish: /delete 1"
        )

    with lock:
        user_tasks = tasks.setdefault(user_id, {})
        if text.startswith("/add "):
            name = text[5:].strip()
            if not name:
                return "Vazifa nomini yozing."
            task_id = max(user_tasks.keys(), default=0) + 1
            user_tasks[task_id] = {"name": name, "done": False}
            return f"✅ Vazifa qo‘shildi! ID: {task_id}\n{name}"

        if text == "/list":
            if not user_tasks:
                return "Hozircha vazifalar yo‘q."
            lines = ["📋 Vazifalaringiz:"]
            for task_id, task in user_tasks.items():
                mark = "✅" if task["done"] else "⬜"
                lines.append(f'{task_id}. {mark} {task["name"]}')
            return "\n".join(lines)

        parts = text.split(maxsplit=2)
        if len(parts) >= 2 and parts[0] in ("/done", "/delete", "/edit"):
            if not parts[1].isdigit():
                return "Vazifa ID raqamini kiriting."
            task_id = int(parts[1])
            if task_id not in user_tasks:
                return "Bunday vazifa topilmadi."

            if parts[0] == "/done":
                user_tasks[task_id]["done"] = True
                return "✅ Vazifa bajarildi!"
            if parts[0] == "/delete":
                del user_tasks[task_id]
                return "🗑 Vazifa o‘chirildi!"
            if len(parts) < 3 or not parts[2].strip():
                return "Yangi vazifa nomini yozing."
            user_tasks[task_id]["name"] = parts[2].strip()
            return "✏️ Vazifa yangilandi!"

    return "Buyruq tushunilmadi. /help deb yozing."

@app.get("/")
def home():
    return "TaskMate is running!", 200

@app.post("/webhook")
def webhook():
    update = request.get_json(silent=True) or {}
    msg = update.get("message", {})
    chat = msg.get("chat", {})
    user = msg.get("from", {})
    text = msg.get("text", "")

    if chat.get("type") == "private" and isinstance(text, str):
        send(chat["id"], handle(user["id"], text))
    return "OK", 200

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN sozlanmagan")
    url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if url:
        response = requests.post(
            API + "/setWebhook",
            json={"url": url.rstrip("/") + "/webhook"},
            timeout=15
        )
        response.raise_for_status()
        if not response.json().get("ok"):
            raise RuntimeError("Webhook sozlanmadi")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))

