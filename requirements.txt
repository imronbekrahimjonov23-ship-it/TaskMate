import os
import requests
from flask import Flask, request

app = Flask(__name__)
TOKEN = os.environ.get("BOT_TOKEN", "")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

@app.get("/")
def home():
    return "TaskMate is running!", 200

@app.post("/webhook")
def webhook():
    message = request.get_json(silent=True) or {}
    msg = message.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    text = msg.get("text", "")

    if chat_id:
        if text == "/start":
            reply = "Salom! TaskMate botiga xush kelibsiz! ✅"
        else:
            reply = "Xabaringiz qabul qilindi! ✅"
        requests.post(
            BASE_URL + "/sendMessage",
            json={"chat_id": chat_id, "text": reply},
            timeout=15,
        )
    return "OK", 200

if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN sozlanmagan")
    url = os.environ.get("RENDER_EXTERNAL_URL", "")
    if url:
        response = requests.post(
            BASE_URL + "/setWebhook",
            json={"url": url.rstrip("/") + "/webhook"},
            timeout=15,
        )
        response.raise_for_status()
        if not response.json().get("ok"):
            raise RuntimeError("Webhook sozlanmadi")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
