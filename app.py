from flask import Flask, request, jsonify
import requests, os

app = Flask(__name__)

# =========================
# CONFIG
# =========================
BOT_TOKEN = "8214186320:AAGpMuO7aMRjuozhMYHa3rxW9vW7NtG7g5w"
CHAT_ID   = "-1003103152784"
LEVERAGE  = 10  # 10x leverage

# Keep track of entry prices for PnL calculation
symbol_data = {}

# =========================
# FUNCTION TO FORMAT MESSAGES
# =========================
def send_cornix_message(symbol, action, price, stop_loss=None, entry_price=None):
    ticker = f"#{symbol}"
    price = round(price, 6)
    if stop_loss:
        stop_loss = round(stop_loss, 6)

    messages = []

    if action in ["BUY", "SELL"]:
        # Entry message with bold labels
        text = (
            f"**Action:** {action}\n"
            f"**Symbol:** {ticker}\n"
            f"**Exchange:** Binance Futures\n"
            f"**Leverage:** Isolated (10X)\n"
            f"**Trade Amount:** 2%"
            f"**Type:** MARKET\n"
            f"**Entry Price:** {price}\n"
            f"**Stop Loss:** {stop_loss}\n"
        )
        messages.append(text)

    elif action == "CLOSE":
        # 1️⃣ Close command message
        close_text = f"Close {ticker}"
        messages.append(close_text)

        # 2️⃣ PnL report message
        if entry_price:
            pnl_percent = round((price - entry_price) / entry_price * 100, 2)
            pnl_percent *= LEVERAGE  # multiply by leverage

            if pnl_percent >= 0:
                pnl_text = f"💰 Profit: +{abs(pnl_percent)}%"
            else:
                pnl_text = f"🔻 Loss: -{abs(pnl_percent)}%"

            report = (
                f"{ticker} Report\n"
                f"Exit Price: {price}\n"
                f"{pnl_text}"
            )
            messages.append(report)
        else:
            messages.append(f"{ticker} Report\nExit Price: {price}\nPnL: N/A")

    return messages


# =========================
# FLASK WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    raw_msg = request.data.decode("utf-8").strip()
    if not raw_msg:
        return jsonify({"status": "no message"}), 200

    try:
        symbol, comment, price_str = raw_msg.split("|")
        price = float(price_str)
    except Exception as e:
        return jsonify({"status": "invalid format", "error": str(e)}), 200

    action_map = {
        "BUY_ENTRY": "BUY",
        "SELL_ENTRY": "SELL",
        "EXIT_LONG": "CLOSE",
        "EXIT_SHORT": "CLOSE",
        "CROSS_EXIT_LONG": "CLOSE",
        "CROSS_EXIT_SHORT": "CLOSE"
    }

    action = action_map.get(comment)
    if not action:
        return jsonify({"status": "unknown comment"}), 200

    if action in ["BUY", "SELL"]:
        stop_loss = price * 0.98 if action == "BUY" else price * 1.02
        symbol_data[symbol] = {"entry": price, "stop_loss": stop_loss}
        messages = send_cornix_message(symbol, action, price, stop_loss=stop_loss)

    elif action == "CLOSE":
        entry_price = symbol_data.get(symbol, {}).get("entry")
        if symbol in symbol_data:
            del symbol_data[symbol]
        messages = send_cornix_message(symbol, "CLOSE", price, entry_price=entry_price)

    # Send formatted messages to Telegram (enable markdown)
    for msg in messages:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
        )

    return jsonify({"status": "ok"}), 200


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
