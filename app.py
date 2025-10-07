from flask import Flask, request
import requests
import json

app = Flask(__name__)

# Telegram config
BOT_TOKEN = "8214186320:AAGpMuO7aMRjuozhMYHa3rxW9vW7NtG7g5w"
CHAT_ID   = "-1003103152784"

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # --- STEP 1: Get raw message from TradingView alert ---
        raw_msg = request.form.get('message') or request.data.decode('utf-8')
        if not raw_msg:
            return "No message received", 400

        # --- STEP 2: Parse JSON string from Pine Script ---
        try:
            data = json.loads(raw_msg)
        except json.JSONDecodeError:
            # If not valid JSON, send raw message
            send_telegram_message(raw_msg)
            return "OK (sent raw message)", 200

        # --- STEP 3: Extract fields ---
        action     = data.get("action", "")
        symbol     = data.get("symbol", "")
        order_type = data.get("type", "")
        leverage   = data.get("margin_leverage", "")
        amount     = data.get("trade_amount", "")
        entry      = data.get("entry_price", None)
        stop_loss  = data.get("stop_loss_price", None)
        exit_price = data.get("exit_price", None)
        pnl        = data.get("pnl", "")
        reason     = data.get("reason", "")

        # --- STEP 4: Add emojis for quick recognition ---
        emoji_action = "📈" if action.upper() == "BUY" else "📉" if action.upper() == "SELL" else "⚡"

        # --- STEP 5: Build pretty Telegram message ---
        msg = f"*{emoji_action} TradingView Alert*\n"
        msg += f"*Action      :* {action}\n"
        msg += f"*Symbol      :* `{symbol}`\n"
        msg += f"*Type        :* `{order_type}`\n"
        if entry: msg += f"*Entry Price :* `{entry}`\n"
        if stop_loss: msg += f"*Stop Loss   :* `{stop_loss}`\n"
        if exit_price: msg += f"*Exit Price  :* `{exit_price}`\n"
        if pnl:
            # Color-code PnL using + / - signs
            msg += f"*PnL         :* {'🟢' if '+' in str(pnl) else '🔴'} `{pnl}`\n"
        if leverage: msg += f"*Leverage    :* `{leverage}`\n"
        if amount: msg += f"*Amount      :* `{amount}`\n"
        if reason: msg += f"*Reason      :* `{reason}`"

        send_telegram_message(msg)
        return "OK", 200

    except Exception as e:
        print(f"Error: {e}")
        return "Error", 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
