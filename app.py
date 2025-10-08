from flask import Flask, request, jsonify
import requests, os

app = Flask(__name__)

# =========================
# CONFIG
# =========================
BOT_TOKEN = "8214186320:AAGpMuO7aMRjuozhMYHa3rxW9vW7NtG7g5w"
CHAT_ID   = "-1003103152784"

symbol_data = {}

# =========================
# FUNCTION TO FORMAT MESSAGES
# =========================
def send_cornix_message(symbol, action, price, stop_loss=None, entry_price=None, timeframe=None):
    ticker = f"#{symbol}"
    price = round(price, 6)
    if stop_loss:
        stop_loss = round(stop_loss, 6)

    messages = []

    if action in ["BUY", "SELL"]:
        entry_msg = (
            f"📊 Exchange: Binance Futures\n"
            f"Action: {action}\n"
            f"Symbol: {ticker}\n"
            f"Type: MARKET\n"
            f"Entry Price: {price}\n"
            f"Stop Loss: {stop_loss}\n"
            f"Leverage: Isolated (10X)\n"
            f"Timeframe: {timeframe}"
        )
        messages.append(entry_msg)

    elif action == "CLOSE":
        # Message 1: Close Command
        messages.append(f"Close {ticker}")

        # Message 2: Exit Report
        if entry_price:
            pnl_percent = round((price - entry_price) / entry_price * 100, 2)
            pnl_percent *= 10  # leverage effect (10X)
            pnl_text = f"{abs(pnl_percent)}% Profit" if pnl_percent >= 0 else f"{abs(pnl_percent)}% Loss"
            exit_msg = (
                f"{ticker} Report\n"
                f"Exit Price: {price}\n"
                f"Pnl: {pnl_text}"
            )
            messages.append(exit_msg)
        else:
            messages.append(f"{ticker} Report\nExit Price: {price}")

    return messages


# =========================
# FLASK WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    raw_msg = request.data.decode("utf-8").strip()
    if not raw_msg:
        return jsonify({"status": "no message"}), 200

    # Expected format: "TICKER|COMMENT|PRICE|TIMEFRAME"
    try:
        parts = raw_msg.split("|")
        symbol, comment, price_str = parts[:3]
        timeframe = parts[3] if len(parts) > 3 else "Unknown"
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
        messages = send_cornix_message(symbol, action, price, stop_loss=stop_loss, timeframe=timeframe)

    elif action == "CLOSE":
        entry_price = symbol_data.get(symbol, {}).get("entry")
        if symbol in symbol_data:
            del symbol_data[symbol]
        messages = send_cornix_message(symbol, "CLOSE", price, entry_price=entry_price)

    for msg in messages:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg}
        )

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
