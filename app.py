from flask import Flask, request, jsonify
import requests, os

app = Flask(__name__)

# =========================
# CONFIG
# =========================
BOT_TOKEN = "8214186320:AAGpMuO7aMRjuozhMYHa3rxW9vW7NtG7g5w"
CHAT_ID   = "-1003103152784"

# Keep track of entry prices for PnL calculation
symbol_data = {}

# =========================
# TELEGRAM MESSAGE FORMATTER
# =========================
def send_telegram_message(text):
    """Send nicely formatted message to Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

# =========================
# FUNCTION TO RECONSTRUCT MESSAGES
# =========================
def send_cornix_message(symbol, action, price, stop_loss=None, entry_price=None):
    """
    Reconstruct Cornix-compatible message for entry/exit.
    """
    ticker = f"#{symbol.upper()}"
    price = round(price, 6)
    if stop_loss:
        stop_loss = round(stop_loss, 6)

    if action in ["BUY", "SELL"]:
        # Entry message
        text = (
            f"**Exchange:** Binance Futures\n"
            f"**Action:** {action}\n"
            f"**Symbol:** {ticker}\n"
            f"**Type:** MARKET\n"
            f"**Entry Price:** {price}\n"
            f"**Stop Loss:** {stop_loss}\n"
            f"**Leverage:** Isolated (10X)\n"
            f"**Trade Amount:** 2%"
        )
        send_telegram_message(text)

    elif action == "CLOSE":
        # Exit message
        text = f"✅ Close {ticker}\n"
        if entry_price:
            pnl_percent = round((price - entry_price) / entry_price * 100, 2)
            pnl_symbol = "🟢" if pnl_percent > 0 else "🔻"
            pnl_type = "Profit" if pnl_percent > 0 else "Loss"
            text += f"**Exit Price:** {price}\n**PnL:** {pnl_symbol} {abs(pnl_percent)}% {pnl_type}"
        else:
            text += f"**Exit Price:** {price}"
        send_telegram_message(text)

# =========================
# FLASK WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    # Read TradingView message
    raw_msg = request.data.decode("utf-8").strip()
    if not raw_msg:
        return jsonify({"status": "no message"}), 200

    # Expected format: "TICKER|COMMENT|PRICE"
    try:
        symbol, comment, price_str = raw_msg.split("|")
        price = float(price_str)
    except Exception as e:
        return jsonify({"status": "invalid format", "error": str(e)}), 200

    # Map comment → action
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

    # Handle entries
    if action in ["BUY", "SELL"]:
        stop_loss = price * 0.98 if action == "BUY" else price * 1.02
        symbol_data[symbol] = {"entry": price, "stop_loss": stop_loss}
        send_cornix_message(symbol, action, price, stop_loss=stop_loss)

    # Handle exits
    elif action == "CLOSE":
        entry_price = symbol_data.get(symbol, {}).get("entry")
        if symbol in symbol_data:
            del symbol_data[symbol]
        send_cornix_message(symbol, "CLOSE", price, entry_price=entry_price)

    return jsonify({"status": "ok"}), 200


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
