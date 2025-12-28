import yfinance as yf
import pandas_ta as ta
from telegram import Bot
import time

# ======================
# CONFIG
# ======================
TOKEN = "8085092545:AAHCY7MahLYj8zWLF0pj3Jyx9CL1BYVO8m0"
CHAT_ID = "8013408393"

TIMEFRAME = "1m"
SCAN_INTERVAL = 60        # scan every minute
PAIR_COOLDOWN = 300       # 5 mins per pair

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

bot = Bot(token=TOKEN)
last_signal_time = {}

# ======================
# FETCH DATA
# ======================
def get_data(symbol):
    df = yf.download(
        symbol,
        period="1d",
        interval=TIMEFRAME,
        progress=False
    )
    return df.dropna()

# ======================
# ANALYSIS
# ======================
def analyze(df):
    df["EMA50"] = ta.ema(df["Close"], 50)
    df["EMA200"] = ta.ema(df["Close"], 200)
    df["RSI"] = ta.rsi(df["Close"], 14)
    df["ATR"] = ta.atr(df["High"], df["Low"], df["Close"], 14)
    df["ADX"] = ta.adx(df["High"], df["Low"], df["Close"], 14)["ADX_14"]

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # Filters
    if last["ATR"] < 0.0004 or last["ADX"] < 20:
        return None

    price_dist = abs(last["Close"] - last["EMA50"])

    # HIGHER
    if (
        last["EMA50"] > last["EMA200"]
        and 55 <= last["RSI"] <= 68
        and last["RSI"] > prev["RSI"]
        and last["Close"] > last["Open"]
        and price_dist < last["ATR"] * 1.2
    ):
        return "HIGHER ↗️"

    # LOWER
    if (
        last["EMA50"] < last["EMA200"]
        and 32 <= last["RSI"] <= 45
        and last["RSI"] < prev["RSI"]
        and last["Close"] < last["Open"]
        and price_dist < last["ATR"] * 1.2
    ):
        return "LOWER ↘️"

    return None

# ======================
# SEND SIGNAL
# ======================
def send_signal(pair, signal):
    message = f"""
🖇 Signal information:
{pair} (OTC) — 1 minute

📰 Market Setting:
Trend-following
Volatility: Confirmed

🖥 Technical overview:
EMA 50 / EMA 200
RSI + ADX
ATR + Candle confirmation

💷 Probabilities:
High confluence (rule-based)

🧨 Bot signal:
{signal}
"""
    bot.send_message(chat_id=CHAT_ID, text=message)

# ======================
# MAIN LOOP
# ======================
while True:
    try:
        now = time.time()

        for pair_name, symbol in PAIRS.items():
            last_time = last_signal_time.get(pair_name, 0)

            # Cooldown check
            if now - last_time < PAIR_COOLDOWN:
                continue

            df = get_data(symbol)
            signal = analyze(df)

            if signal:
                send_signal(pair_name, signal)
                last_signal_time[pair_name] = now

        time.sleep(SCAN_INTERVAL)

    except Exception as e:
        print("Error:", e)
        time.sleep(60)
