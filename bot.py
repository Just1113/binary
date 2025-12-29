import os
import asyncio
import threading
import time
from datetime import datetime

import yfinance as yf
import pandas as pd
import pandas_ta as ta

from flask import Flask
from telegram import Bot

# ===================== CONFIG =====================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "PUT_YOUR_BOT_TOKEN_HERE"
CHAT_ID = os.getenv("CHAT_ID") or "PUT_YOUR_CHAT_ID_HERE"

SYMBOLS = [
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "AUDUSD=X",
    "USDCAD=X",
    "NZDUSD=X",
    "USDCHF=X",
    "EURJPY=X",
    "GBPJPY=X",
    "EURGBP=X",
]

TIMEFRAME = "1m"
LOOKBACK = "1d"
SCAN_INTERVAL = 60  # seconds

bot = Bot(token=BOT_TOKEN)

# ===================== FLASK (PORT FIX) =====================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running ✅"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ===================== ANALYSIS =====================
def analyze(df):
    if df is None or len(df) < 60:
        return None

    df["EMA50"] = ta.ema(df["Close"], 50)
    df["EMA200"] = ta.ema(df["Close"], 200)
    df["RSI"] = ta.rsi(df["Close"], 14)
    df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], 14)

    adx = ta.adx(df["High"], df["Low"], df["Close"], 14)
    if adx is None:
        return None

    df["ADX"] = adx["ADX_14"]

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["ADX"] < 20 or last["ATR"] is None:
        return None

    # HIGHER condition
    if (
        last["EMA50"] > last["EMA200"]
        and last["RSI"] > prev["RSI"]
        and 55 <= last["RSI"] <= 70
        and last["Close"] > last["Open"]
    ):
        return "HIGHER ⬆️"

    # LOWER condition
    if (
        last["EMA50"] < last["EMA200"]
        and last["RSI"] < prev["RSI"]
        and 30 <= last["RSI"] <= 45
        and last["Close"] < last["Open"]
    ):
        return "LOWER ⬇️"

    return None

# ===================== TELEGRAM =====================
async def send_message(text):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text)
        print("Sent Telegram message:", text)
    except Exception as e:
        print("Telegram error:", e)

# ===================== BOT LOOP =====================
async def bot_loop():
    await send_message(
        f"🚀 Multi-pair Telegram bot started!\nTime: {datetime.now()}"
    )

    while True:
        for symbol in SYMBOLS:
            try:
                df = yf.download(
                    symbol,
                    interval=TIMEFRAME,
                    period=LOOKBACK,
                    progress=False,
                )

                signal = analyze(df)

                if signal:
                    msg = (
                        f"📊 Signal Alert\n"
                        f"Pair: {symbol.replace('=X','')}\n"
                        f"Direction: {signal}\n"
                        f"Time: {datetime.now().strftime('%H:%M:%S')}"
                    )
                    await send_message(msg)

            except Exception as e:
                print(f"Error on {symbol}:", e)

        await asyncio.sleep(SCAN_INTERVAL)

# ===================== START EVERYTHING =====================
if __name__ == "__main__":
    # Flask thread (Render port)
    threading.Thread(target=run_flask, daemon=True).start()

    # Async bot loop
    asyncio.run(bot_loop())
