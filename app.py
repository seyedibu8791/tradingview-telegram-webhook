from flask import Flask, request, jsonify
import requests, os, threading, time

app = Flask(__name__)

# =========================
# CONFIG FROM ENVIRONMENT
# =========================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID   = os.environ.get("CHAT_ID")
LEVERAGE  = int(os.environ.get("LEVERAGE", 20))  # default 20x
SELF_URL  = os.environ.get("SELF_URL")  # optional: URL for self-ping
PORT      = int(os.environ.get("PORT", 5000))

# Store entry details
symbol_data = {}

# =========================
# UTILITIES
# =========================
def send_telegram_message(text):
    """Send formatted message to Telegram"""
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    )

def format_timeframe(tf_raw):
    """Convert TradingView interval to readable text"""
    if tf_raw.isdigit():
        return f"{tf_raw} Mins"
    tf_raw = tf_raw.upper().strip()
    if tf_raw.endswith("H"):
        return f"{tf_raw[:-1]} Hour"
    elif tf_raw.endswith("D"):
        return f"{tf_raw[:-1]} Day"
    return tf_raw if tf_raw else "Unknown"

# =========================
# MESSAGE BUILDER
# =========================
def send_cornix_message(symbol, action, price, stop_loss=None, timeframe="Unknown"):
    ticker = f"#{symbol}"
    price = round(price, 6)
    if stop_loss:
        stop_loss = round(stop_loss, 6)

    # ENTRY MESSAGE
    if action in ["BUY 💹", "SELL 🛑"]:
        msg = (
            f"*Action:* {action}\n"
            f"*Symbol:* {ticker}\n"
            f"--- ⌁ ---\n"
            f"*Exchange:* Binance Futures\n"
            f"*Timeframe:* {timeframe}\n"
            f"*Leverage:* Isolated ({LEVERAGE}X)\n"
            f"--- ⌁ ---\n"
            f"*☑️ Entry Price:* {price}\n"
            f"*☑️ Stop Loss:* {stop_loss}\n"
            f"--- ⌁ ---\n"
            f"⚠️ Wait for Close Signal!\n"
        )
        send_telegram_message(msg)

    # EXIT MESSAGE
    elif action == "CLOSE":
        send_telegram_message(f"/Close {ticker}")

# =========================
# WEBHOOK
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

    symbol = parts[0].replace("/", "")  # remove "/" to normalize
    comment = parts[1]
    price = float(parts[2])
    timeframe_raw = parts[3] if len(parts) > 3 else "Unknown"
    timeframe = format_timeframe(timeframe_raw)

    # BLOCK *ALL* 1-MIN TIMEFRAME SIGNALS
    if timeframe.strip().lower() in ["1 min", "1 mins", "1 minute", "1 minutes"]:
        print(f"[BLOCKED] {symbol} | {comment} | {price} | {timeframe}")
        return jsonify({"status": "blocked"}), 200

    # Map comments to actions
    action_map = {
        "BUY_ENTRY": "BUY 💹",
        "SELL_ENTRY": "SELL 🛑",
        "EXIT_LONG": "CLOSE",
        "EXIT_SHORT": "CLOSE",
        "CROSS_EXIT_LONG": "CLOSE",
        "CROSS_EXIT_SHORT": "CLOSE",
        "MANUALLY_CANCELLED": "CLOSE"
    }
    action = action_map.get(comment.upper())
    if not action:
        return jsonify({"status": "unknown comment"}), 200

    # Process Entry
    if action in ["BUY 💹", "SELL 🛑"]:
        stop_loss = price * 0.97 if action == "BUY 💹" else price * 1.03
        symbol_data[symbol] = {"entry": price, "action": action, "stop_loss": stop_loss}
        send_cornix_message(symbol, action, price, stop_loss=stop_loss, timeframe=timeframe)

    # Process Exit
    elif action == "CLOSE":
        if symbol in symbol_data:
            del symbol_data[symbol]
        send_cornix_message(symbol, "CLOSE", price, timeframe=timeframe)

    print(f"[FORWARDED] {symbol} | {comment} | {price} | {timeframe}")
    return jsonify({"status": "ok"}), 200

# =========================
# KEEP-ALIVE THREAD
# =========================
def keep_alive():
    while True:
        if SELF_URL:
            try:
                requests.get(f"{SELF_URL}/ping")
                print(f"[KEEP-ALIVE] Pinged {SELF_URL}")
            except Exception as e:
                print(f"[KEEP-ALIVE ERROR] {e}")
        time.sleep(180)  # every 3 minutes

threading.Thread(target=keep_alive, daemon=True).start()

# =========================
# PING ENDPOINT
# =========================
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "alive"}), 200

# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    print(f"Starting Flask TradingView → Telegram Bot on port {PORT}")
    app.run(host="0.0.0.0", port=PORT)
