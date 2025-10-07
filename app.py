from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

BOT_TOKEN = "8214186320:AAGpMuO7aMRjuozhMYHa3rxW9vW7NtG7g5w"
CHAT_ID   = "-1003103152784"

symbol_data = {}

def send_telegram_json(symbol, action, price, stop_loss=None, pnl=None):
    # Construct JSON payload for bots
    payload = {
        "action": action,         # BUY, SELL, CLOSE
        "symbol": symbol,
        "type": "MARKET",
        "entry_price": price,
        "stop_loss_price": stop_loss,
        "pnl": pnl,
        "leverage": "10X",
        "trade_amount": "2%"
    }
    # Send as text JSON to Telegram (or bot)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": str(payload)})

@app.route("/webhook", methods=["POST"])
def webhook():
    raw_msg = request.data.decode("utf-8").strip()
    if not raw_msg:
        return jsonify({"status":"no message"}), 200

    # Parse symbol, price, comment
    try:
        symbol, price_str, comment = raw_msg.split()
        price = float(price_str)
    except:
        return jsonify({"status":"invalid format"}), 200

    # Map comment to action
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

    if action in ["BUY","SELL"]:
        stop_loss = price * 0.98 if action=="BUY" else price * 1.02
        symbol_data[symbol] = {"entry": price, "stop_loss": stop_loss}
        send_telegram_json(symbol, action, price, stop_loss)
    elif action == "CLOSE":
        data = symbol_data.get(symbol, {})
        entry_price = data.get("entry", price)
        pnl = round((price - entry_price)/entry_price*100,2) if entry_price else None
        if symbol in symbol_data:
            del symbol_data[symbol]
        send_telegram_json(symbol, action, price, pnl=pnl)
    
    return jsonify({"status":"ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
