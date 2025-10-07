from flask import Flask, request
import requests
import json
import html

app = Flask(__name__)

BOT_TOKEN = "8214186320:AAGpMuO7aMRjuozhMYHa3rxW9vW7NtG7g5w"
CHAT_ID   = "-1003103152784"  # Your channel ID

def send_telegram_message(msg: str):
    """
    Send message to Telegram channel with safe Markdown escaping.
    """
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "MarkdownV2"
    }
    response = requests.post(url, json=payload)
    print("Telegram response:", response.status_code, response.text)
    return response

def escape_md(text: str) -> str:
    """
    Escape special MarkdownV2 characters
    """
    if not text:
        return ""
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # --- STEP 1: Get message from raw body or form ---
        raw_msg = request.data.decode('utf-8').strip()
        if not raw_msg:
            raw_msg = request.form.get('message', '').strip()

        if not raw_msg:
            print("No message received")
            return "No message received", 200

        # --- STEP 2: Try parsing JSON ---
        try:
            data = json.loads(raw_msg)
        except json.JSONDecodeError:
            print("Not JSON, sending raw message")
            send_telegram_message(escape_md(raw_msg))
            return "OK (sent raw message)", 200

        # --- STEP 3: Extract fields ---
        action     = escape_md(str(data.get("action","")))
        symbol     = escape_md(str(data.get("symbol","")))
        order_type = escape_md(str(data.get("type","")))
        entry      = escape_md(str(data.get("entry_price","")))
        stop_loss  = escape_md(str(data.get("stop_loss_price","")))
        exit_price = escape_md(str(data.get("exit_price","")))
        pnl        = escape_md(str(data.get("pnl","")))
        leverage   = escape_md(str(data.get("margin_leverage","")))
        amount     = escape_md(str(data.get("trade_amount","")))
        reason     = escape_md(str(data.get("reason","")))

        emoji = "📈" if action.upper()=="BUY" else "📉" if action.upper()=="SELL" else "⚡"

        # --- STEP 4: Build Telegram message ---
        msg_lines = [f"{emoji} *TradingView Alert*"]
        if action:     msg_lines.append(f"*Action:* {action}")
        if symbol:     msg_lines.append(f"*Symbol:* `{symbol}`")
        if order_type: msg_lines.append(f"*Type:* `{order_type}`")
        if entry:      msg_lines.append(f"*Entry Price:* `{entry}`")
        if stop_loss:  msg_lines.append(f"*Stop Loss:* `{stop_loss}`")
        if exit_price: msg_lines.append(f"*Exit Price:* `{exit_price}`")
        if pnl:        msg_lines.append(f"*PnL:* {'🟢' if '+' in pnl else '🔴'} `{pnl}`")
        if leverage:   msg_lines.append(f"*Leverage:* `{leverage}`")
        if amount:     msg_lines.append(f"*Amount:* `{amount}`")
        if reason:     msg_lines.append(f"*Reason:* {reason}")

        msg = "\n".join(msg_lines)

        # --- STEP 5: Send to Telegram ---
        send_telegram_message(msg)
        return "OK", 200

    except Exception as e:
        print(f"Webhook error: {e}")
        return "Error", 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
