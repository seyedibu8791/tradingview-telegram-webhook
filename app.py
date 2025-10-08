from flask import Flask, request, jsonify
import requests, os

app = Flask(__name__)

# =========================
# CONFIG
# =========================
BOT_TOKEN = "8214186320:AAGpMuO7aMRjuozhMYHa3rxW9vW7NtG7g5w"
CHAT_ID   = "-1003103152784"
LEVERAGE  = 10  # leverage multiplier for PnL

# Store entry details
symbol_data = {}

# =========================
# FORMAT & SEND MESSAGE
# =========================
def send_telegram_message(text):
    """Send formatted message to Telegram"""
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    )

def format_timeframe(tf_raw):
    """Convert raw timeframe text to readable format"""
    if tf_raw.isdigit():
        return f"{tf_raw} Mins"
    tf_raw = tf_raw.upper().strip()
    if tf_raw.endswith("H"):
        return f"{tf_raw[:-1]} Hour"
    elif tf_raw.endswith("D"):
        return f"{tf_raw[:-1]} Day"
    return tf_raw if tf_raw else "Unknown"

def send_cornix_message(symbol, action, price, stop_loss=None, entry_price=None, timeframe="Unknown"):
    """Reconstruct Cornix-compatible formatted message"""
    ticker = f"#{symbol}"
    price = round(price, 6)
    if stop_loss:
        stop_loss = round(stop_loss, 6)

    if action in ["BUY", "SELL"]:
        # Entry message
        msg = (
            f"*Exchange:* Binance Futures\n"
            f"*Action:* {action}\n"
            f"*Symbol:* {ticker}\n"
            f"*Type:* MARKET\n"
            f"*Entry Price:* {price}\n"
            f"*Stop Loss:* {stop_loss}\n"
            f"*Leverage:* Isolated ({LEVERAGE}X)\n"
            f"*Timeframe:* {timeframe}"
        )
        send_telegram_message(msg)

    elif action == "CLOSE":
        # Close message
        send_telegram_message(f"Close {ticker}")

        # Exit + PnL message
        if entry_price:
            pnl_percent = round((price - entry_price) / entry_price * 100 * LEVERAGE, 2)
            pnl_text = f"{abs(pnl_percent)}% Profit" if pnl_percent > 0 else f"{abs(pnl_percent)}% Loss"
            pnl_report = (
                f"*{ticker} Report*\n"
                f"Exit Price: {round(price,6)}\n"
                f"PnL: {pnl_text}"
            )
            send_telegram_message(pnl_report)

# =========================
# WEBHOOK ENDPOINT
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    raw_msg = request.data.decode("utf-8").strip()
    if not raw_msg:
        return jsonify({"status": "no message"}), 200

    # Expecting: "TICKER|COMMENT|PRICE|TIMEFRAME"
    parts = raw_msg.split("|")
    if len(parts) < 3:
        return jsonify({"status": "invalid format"}), 200

    symbol = parts[0]
    comment = parts[1]
    price = float(parts[2])
    timeframe_raw = parts[3] if len(parts) > 3 else "Unknown"
    timeframe = format_timeframe(timeframe_raw)

    # Map comments to actions
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

    # Process actions
    if action in ["BUY", "SELL"]:
        stop_loss = price * 0.98 if action == "BUY" else price * 1.02
        symbol_data[symbol] = {"entry": price, "stop_loss": stop_loss}
        send_cornix_message(symbol, action, price, stop_loss=stop_loss, timeframe=timeframe)

    elif action == "CLOSE":
        entry_price = symbol_data.get(symbol, {}).get("entry")
        if symbol in symbol_data:
            del symbol_data[symbol]
        send_cornix_message(symbol, "CLOSE", price, entry_price=entry_price, timeframe=timeframe)

    return jsonify({"status": "ok"}), 200

# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
