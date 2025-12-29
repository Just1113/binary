import os
import asyncio
import threading
from datetime import datetime

import yfinance as yf
import pandas as pd
import pandas_ta as ta

from flask import Flask
from telegram import Bot

# ================== CONFIG ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

PAIRS = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X",
    "USDCAD=X", "NZDUSD=X", "USDCHF=X",
    "EURJPY=X", "GBPJPY=X", "EURGBP=X"
]

bot = Bot(BOT_TOKEN)

# ================== FLASK ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "Binary + Forex bot running ✅"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ================== BINARY ANALYSIS (M1) ==================
def analyze_binary(df):
    if df is None or len(df) < 60:
        return None

    df["EMA50"] = ta.ema(df["Close"], 50)
    df["EMA200"] = ta.ema(df["Close"], 200)
    df["RSI"] = ta.rsi(df["Close"], 14)

    adx = ta.adx(df["High"], df["Low"], df["Close"], 14)
    if adx is None:
        return None

    df["ADX"] = adx["ADX_14"]

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["ADX"] < 15:
        return None

    if (
        last["EMA50"] > last["EMA200"]
        and last["RSI"] > prev["RSI"]
        and 52 <= last["RSI"] <= 72
        and last["Close"] > last["Open"]
    ):
        return "HIGHER ⬆️"

    if (
        last["EMA50"] < last["EMA200"]
        and last["RSI"] < prev["RSI"]
        and 28 <= last["RSI"] <= 48
        and last["Close"] < last["Open"]
    ):
        return "LOWER ⬇️"

    return None

# ================== FOREX TREND (M15) ==================
def forex_trend(symbol):
    df = yf.download(symbol, interval="15m", period="5d", progress=False)
    if len(df) < 100:
        return None

    df["EMA50"] = ta.ema(df["Close"], 50)
    df["EMA200"] = ta.ema(df["Close"], 200)

    adx = ta.adx(df["High"], df["Low"], df["Close"], 14)
    if adx is None or adx["ADX_14"].iloc[-1] < 20:
        return None

    last = df.iloc[-1]

    if last["EMA50"] > last["EMA200"]:
        return "BUY"
    if last["EMA50"] < last["EMA200"]:
        return "SELL"

    return None

# ================== FOREX ENTRY (M5) ==================
def forex_entry(symbol, trend):
    df = yf.download(symbol, interval="5m", period="2d", progress=False)
    if len(df) < 50:
        return None

    df["RSI"] = ta.rsi(df["Close"], 14)
    df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], 14)

    last = df.iloc[-1]
    price = last["Close"]
    atr = last["ATR"]

    if trend == "BUY" and 40 <= last["RSI"] <= 55 and last["Close"] > last["Open"]:
        return price, price - atr * 1.5, price + atr * 3

    if trend == "SELL" and 45 <= last["RSI"] <= 60 and last["Close"] < last["Open"]:
        return price, price + atr * 1.5, price - atr * 3

    return None

# ================== TELEGRAM ==================
async def send(msg):
    await bot.send_message(chat_id=CHAT_ID, text=msg)

# ================== MAIN LOOP ==================
async def bot_loop():
    await send(f"🚀 Binary + Forex Bot Started\n{datetime.now()}")

    while True:
        for pair in PAIRS:
            try:
                # ----- BINARY -----
                df1m = yf.download(pair, interval="1m", period="1d", progress=False)
                binary_signal = analyze_binary(df1m)

                if binary_signal:
                    await send(
                        f"📈 BINARY SIGNAL\n"
                        f"Pair: {pair.replace('=X','')}\n"
                        f"Direction: {binary_signal}\n"
                        f"TF: 1 Minute\n"
                        f"Time: {datetime.now().strftime('%H:%M:%S')}"
                    )

                # ----- FOREX -----
                trend = forex_trend(pair)
                if not trend:
                    continue

                entry = forex_entry(pair, trend)
                if not entry:
                    continue

                price, sl, tp = entry

                await send(
                    f"📊 FOREX SIGNAL\n"
                    f"Pair: {pair.replace('=X','')}\n"
                    f"Type: {trend}\n"
                    f"Entry: {price:.5f}\n"
                    f"SL: {sl:.5f}\n"
                    f"TP: {tp:.5f}\n"
                    f"RR: 1:2\n"
                    f"Time: {datetime.now().strftime('%H:%M')}"
                )

            except Exception as e:
                print(pair, e)

        await asyncio.sleep(60)

# ================== START ==================
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(bot_loop())
