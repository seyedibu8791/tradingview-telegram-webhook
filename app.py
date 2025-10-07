from flask import Flask, request
import requests
import json
import os

app = Flask(__name__)

# =============================
# Telegram Bot Settings
# =============================
BOT_TOKEN = "8214186320:AAGpMuO7aMRjuozhMYHa3rxW9vW7NtG7g5w"
CHAT_ID   = "-1003103152784"  # Your channel ID

def send_telegram_message(msg: str):
    """
    Send a message to Telegram channel as plain text (no Markdown).
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": None  # Do not use Markdown
    }
    response = requests.post(url, json=payload)
    print("Telegram response:", response.status_code, response.text)
    return response

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Handle TradingView alerts webhook.
    """
    try:
        # Get raw message
        raw_msg = request.data.decode("utf-8").strip()
        if not raw_msg:
            raw_msg = request.form.get("message", "").strip()

        if not raw_msg:
            print("No message received")
            return "No message received", 200

        # Try to parse JSON
        try:
            data = json.loads(raw_msg)
            # Format JSON nicely for Telegram
            formatted_msg = json.dumps(data, indent=2)
        except json.JSONDecodeError:
            # If not JSON, just send raw text
            formatted_msg = raw_msg

        # Send to Telegram
        send_telegram_message(formatted_msg)
        return "OK", 200

    except Exception as e:
        print(f"Webhook error: {e}")
        return "Error", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
