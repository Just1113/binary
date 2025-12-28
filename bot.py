import os
import time
import asyncio
import threading
import yfinance as yf
import pandas_ta as ta
from telegram import Bot
from flask import Flask

# ======================
TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PORT = int(os.environ.get("PORT", 8000))  # Render port

bot = Bot(token=TOKEN)

# ======================
PAIRS = {
    "AUD/USD": "AUDUSD=X",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "JPY=X",
    "USD/CAD": "CAD=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "AUD/JPY": "AUDJPY=X",
    "EUR/GBP": "EURGBP=X"
}

last_signal_time = {}
TIMEFRAME = "1m"
SCAN_INTERVAL = 60
PAIR_COOLDOWN = 300
HEARTBEAT_INTERVAL = 3*60*60
last_heartbeat = 0

# ======================
async def send_telegram(msg):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=msg)
        print(f"Sent Telegram message: {msg}")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

# ======================
def get_data(symbol):
    df = yf.download(
        tickers=symbol,
        period="1d",
        interval=TIMEFRAME,
        progress=False
    )
    return df.dropna()

def analyze(df):
    df["EMA50"] = ta.ema(df["Close"], 50)
    df["EMA200"] = ta.ema(df["Close"], 200)
    df["RSI"] = ta.rsi(df["Close"], 14)
    df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], 14)
    df["ADX"] = ta.adx(df["High"], df["Low"], df["Close"], 14)["ADX_14"]

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["ATR"] < 0.0004 or last["ADX"] < 20:
        return None

    price_dist = abs(last["Close"] - last["EMA50"])

    if last["EMA50"] > last["EMA200"] and 55 <= last["RSI"] <= 68 and last["RSI"] > prev["RSI"] and last["Close"] > last["Open"] and price_dist < last["ATR"]*1.2:
        return "HIGHER ↗️"

    if last["EMA50"] < last["EMA200"] and 32 <= last["RSI"] <= 45 and last["RSI"] < prev["RSI"] and last["Close"] < last["Open"] and price_dist < last["ATR"]*1.2:
        return "LOWER ↘️"

    return None

async def send_signal(pair, signal):
    message = f"""
🖇 Signal information:
{pair} (OTC) — 1 minute

💷 Bot signal:
{signal}
"""
    await send_telegram(message)

# ======================
async def bot_loop():
    global last_heartbeat
    while True:
        now = time.time()

        # heartbeat
        if now - last_heartbeat > HEARTBEAT_INTERVAL:
            await send_telegram(f"💓 Bot is alive! Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            last_heartbeat = now

        # scan pairs
        for pair_name, symbol in PAIRS.items():
            last_time = last_signal_time.get(pair_name, 0)
            if now - last_time < PAIR_COOLDOWN:
                continue

            df = get_data(symbol)
            signal = analyze(df)
            if signal:
                await send_signal(pair_name, signal)
                last_signal_time[pair_name] = now

        await asyncio.sleep(SCAN_INTERVAL)

# ======================
# FLASK SERVER
app = Flask(__name__)

@app.route("/")
def home():
    return "🟢 Telegram bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# ======================
if __name__ == "__main__":
    # startup message
    asyncio.run(send_telegram(f"🚀 Multi-pair Telegram bot started!\nTime: {time.strftime('%Y-%m-%d %H:%M:%S')}"))

    # run bot loop in thread
    threading.Thread(target=lambda: asyncio.run(bot_loop()), daemon=True).start()

    # run flask server (blocks main thread)
    run_flask()
