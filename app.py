from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = "8214186320:AAGpMuO7aMRjuozhMYHa3rxW9vW7NtG7g5w"
CHAT_ID   = "-1003103152784"

symbol_data = {}  # Store last entry info per symbol

def send_telegram_message(msg: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": None}
    try:
        r = requests.post(url, json=payload, timeout=5)
        print("Telegram response:", r.status_code, r.text)
    except Exception as e:
        print("Error sending Telegram message:", e)

@app.route("/webhook", methods=["POST"])
def webhook():
    raw_msg = request.data.decode("utf-8").strip()
    if not raw_msg:
        raw_msg = request.form.get("message","").strip()
    if not raw_msg:
        return "No message", 200

    # Split: symbol, action, price
    parts = raw_msg.split()
    if len(parts) != 3:
        return "Invalid message format", 200

    symbol, action, price_str = parts
    action = action.upper()
    try:
        price = float(price_str)
    except:
        price = 0.0

    # --- Construct message dynamically ---
    if action == "LONG":
        stop_loss   = price * 0.98  # example 2% SL
        leverage    = "10X"
        trade_size  = "2%"
        msg = f"📈 BUY Alert\nSymbol: {symbol}\nEntry Price: {price}\nStop Loss: {stop_loss}\nLeverage: {leverage}\nAmount: {trade_size}"
        symbol_data[symbol] = {"entry": price, "stop_loss": stop_loss, "action": "LONG"}

    elif action == "SHORT":
        stop_loss   = price * 1.02
        leverage    = "10X"
        trade_size  = "2%"
        msg = f"📉 SELL Alert\nSymbol: {symbol}\nEntry Price: {price}\nStop Loss: {stop_loss}\nLeverage: {leverage}\nAmount: {trade_size}"
        symbol_data[symbol] = {"entry": price, "stop_loss": stop_loss, "action": "SHORT"}

    elif action == "EXIT":
        data = symbol_data.get(symbol, {})
        pnl = f"{((price - data.get('entry',price))/data.get('entry',price)*100):.2f}%" if data else "N/A"
        msg = f"⚡ EXIT Alert\nSymbol: {symbol}\nExit Price: {price}\nPnL: {pnl}"
        if symbol in symbol_data:
            del symbol_data[symbol]

    else:
        msg = f"⚠️ Unknown action: {action}"

    send_telegram_message(msg)
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
