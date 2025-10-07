from flask import Flask, request
import requests
import json

app = Flask(__name__)

# Telegram Bot Config
BOT_TOKEN = "8214186320:AAGpMuO7aMRjuozhMYHa3rxW9vW7NtG7g5w"
CHAT_ID   = "-1003103152784"

def send_telegram_message(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # --- STEP 1: Detect payload type ---
        data = None

        # Case 1: JSON payload
        if request.is_json:
            data = request.get_json()

        # Case 2: Form-data from TradingView default POST
        elif request.form:
            # TradingView sends 'payload' field for JSON
            payload_str = request.form.get('payload')
            if payload_str:
                data = json.loads(payload_str)
            else:
                # fallback: take first key-value as JSON
                for key in request.form:
                    try:
                        data = json.loads(key)
                        break
                    except:
                        continue

        # Case 3: Raw body
        else:
            try:
                body = request.data.decode('utf-8')
                data = json.loads(body)
            except:
                pass

        if not data:
            return "Unsupported Media Type / Invalid payload", 415

        # --- STEP 2: Extract fields ---
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

        # --- STEP 3: Build Telegram message ---
        msg = f"*📊 TradingView Alert*\n"
        msg += f"Action      : *{action}*\n"
        msg += f"Symbol      : `{symbol}`\n"
        msg += f"Type        : `{order_type}`\n"
        if entry: msg += f"Entry Price : `{entry}`\n"
        if stop_loss: msg += f"Stop Loss   : `{stop_loss}`\n"
        if exit_price: msg += f"Exit Price  : `{exit_price}`\n"
        if pnl: msg += f"PnL         : `{pnl}`\n"
        if leverage: msg += f"Leverage    : `{leverage}`\n"
        if amount: msg += f"Amount      : `{amount}`\n"
        if reason: msg += f"Reason      : `{reason}`"

        send_telegram_message(msg)
        return "OK", 200

    except Exception as e:
        print(f"Error: {e}")
        return "Error", 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
