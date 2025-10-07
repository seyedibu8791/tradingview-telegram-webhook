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
# FUNCTION TO FORMAT MESSAGES
# =========================
def send_cornix_message(symbol, action, price, stop_loss=None, entry_price=None):
    """
    Reconstruct Cornix-compatible message for entry/exit
    """
    ticker = f"#{symbol}"  # Cornix symbol format

    # Round prices
    price = round(price, 6)
    if stop_loss:
        stop_loss = round(stop_loss, 6)

    messages = []

    if action in ["BUY", "SELL"]:
        # Entry message
        entry_msg = {
            "Exchange": "Binance Futures",
            "Action": action,
            "Symbol": ticker,
            "Type": "MARKET",
            "EntryPrice": price,
            "StopLossPrice": stop_loss,
            "Leverage": "Isolated (10X)",
            "TradeAmount": "2%"
        }
        messages.append(entry_msg)

    elif action == "CLOSE":
        # Close command for Cornix
        close_msg = {
            "Action": "CLOSE",
            "Symbol": ticker
        }
        messages.append(close_msg)

        # Combined ExitPrice + PnL
        combined_msg = {
            "ExitPrice": price
        }

        if entry_price:
            pnl_percent = round((price - entry_price)/entry_price * 100, 2)
            pnl_text = f"{abs(pnl_percent)}% Profit" if pnl_percent >= 0 else f"{abs(pnl_percent)}% Loss"
            combined_msg["PnL"] = pnl_text

        messages.append(combined_msg)

    return messages

# =========================
# FLASK WEBHOOK
# =========================
@app.route("/webhook", methods=["POST"])
def webhook():
    # Read TradingView message
    raw_msg = request.data.decode("utf-8").strip()
    if not raw_msg:
        return jsonify({"status":"no message"}), 200

    # Expected format from TradingView: "TICKER|COMMENT|PRICE"
    try:
        symbol, comment, price_str = raw_msg.split("|")
        price = float(price_str)
    except Exception as e:
        return jsonify({"status":"invalid format", "error": str(e)}), 200

    # Map strategy comment to action
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
        return jsonify({"status":"unknown comment"}), 200

    # Determine stop-loss and track entry for PnL
    if action in ["BUY", "SELL"]:
        stop_loss = price * 0.98 if action=="BUY" else price * 1.02
        symbol_data[symbol] = {"entry": price, "stop_loss": stop_loss}
        messages = send_cornix_message(symbol, action, price, stop_loss=stop_loss)

    elif action == "CLOSE":
        entry_price = symbol_data.get(symbol, {}).get("entry")
        if symbol in symbol_data:
            del symbol_data[symbol]
        messages = send_cornix_message(symbol, "CLOSE", price, entry_price=entry_price)

    # Send each message separately to Telegram
    for msg in messages:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": str(msg)}
        )

    return jsonify({"status":"ok"}), 200

# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
