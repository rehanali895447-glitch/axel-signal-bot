import asyncio
import json
import numpy as np
import pandas as pd
import requests
import websockets

# --- 1. WebSocket और Telegram सेटिंग्स ---
WS_URL = "wss://ws.olymptrade.com/otp?cid_ver=1&cid_app=web%40OlympTrade%402026.3.2396554%402396554&cid_device=%40%40phone&cid_os=android%4010"

# अपने Telegram बॉट का टोकन और चैट आईडी यहाँ डालें
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"

# डेटा स्टोर
candles = pd.DataFrame(columns=["time", "open", "high", "low", "close"])
last_alert_signal = None  # बार-बार एक ही अलर्ट न भेजने के लिए


# --- 2. Telegram पर अलर्ट भेजने का फंक्शन ---
def send_telegram_alert(pair_name, signal_type, price):
  global last_alert_signal
  if last_alert_signal == signal_type:
    return  # अगर लगातार वही सिग्नल है तो स्पैम न करे

  last_alert_signal = signal_type

  emoji = "🟢" if "UP" in signal_type else "🔴"
  message = (
      f"{emoji} **AI SCANNER SIGNAL ALERT** {emoji}\n\n"
      f"📊 **Asset:** {pair_name}\n"
      f"🎯 **Direction:** {signal_type}\n"
      f"💵 **Price:** {price}\n"
      f"⏱ **Expiry:** 1 Minute\n\n"
      f"✅ **Indicators Active:**\n"
      f"• EMA 9 / EMA 20\n"
      f"• SMA 10 / SMA 30\n"
      f"• Donchian Channel (20)\n"
      f"• Rate of Change (ROC 5)"
  )

  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}

  try:
    requests.post(url, json=payload, timeout=5)
  except Exception as e:
    print(f"Telegram Send Error: {e}")


# --- 3. इंडिकेटर्स कैलकुलेशन और सिग्नल लॉजिक ---
def analyze_market(df, pair_name="ASIA_X"):
  if len(df) < 35:
    return

  close = df["close"].astype(float)
  high = df["high"].astype(float)
  low = df["low"].astype(float)

  # Moving Averages
  ema9 = close.ewm(span=9, adjust=False).mean().iloc[-1]
  ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
  sma10 = close.rolling(window=10).mean().iloc[-1]
  sma30 = close.rolling(window=30).mean().iloc[-1]

  # Rate of Change (ROC 5)
  roc5 = ((close.iloc[-1] - close.iloc[-6]) / close.iloc[-6]) * 100

  # Donchian Channel (20)
  dc_high = high.rolling(window=20).max().iloc[-1]
  dc_low = low.rolling(window=20).min().iloc[-1]
  dc_mid = (dc_high + dc_low) / 2

  current_price = close.iloc[-1]

  # Strong UP (CALL) की शर्तें
  up_signal = (
      (current_price > dc_mid)
      and (current_price > ema9)
      and (ema9 > ema20)
      and (roc5 > 0)
      and (current_price > sma10)
      and (sma10 > sma30)
  )

  # Strong DOWN (PUT) की शर्तें
  down_signal = (
      (current_price < dc_mid)
      and (current_price < ema9)
      and (ema9 < ema20)
      and (roc5 < 0)
      and (current_price < sma10)
      and (sma10 < sma30)
  )

  if up_signal:
    print(f"🟢 [UP SIGNAL] {pair_name} @ {current_price}")
    send_telegram_alert(pair_name, "STRONG UP (CALL 🟢)", current_price)
  elif down_signal:
    print(f"🔴 [DOWN SIGNAL] {pair_name} @ {current_price}")
    send_telegram_alert(pair_name, "STRONG DOWN (PUT 🔴)", current_price)


# --- 4. WebSocket डेटा लिसनर (Auto-Reconnect के साथ) ---
async def connect_and_scan():
  global candles
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like"
          " Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
      ),
      "Origin": "https://olymptrade.com",
  }

  while True:
    try:
      print("Connecting to OlympTrade WebSocket...")
      async with websockets.connect(
          WS_URL,
          extra_headers=headers,
          ping_interval=20,
          ping_timeout=20,
      ) as ws:
        print("✅ Live Stream Connected! Scanning for Signals...")

        while True:
          msg = await ws.recv()
          try:
            data = json.loads(msg)
          except Exception:
            continue

          # लाइव टिक/कैंडल डेटा पार्सिंग
          if isinstance(data, dict) and "d" in data:
            for item in data["d"]:
              if isinstance(item, dict) and "p" in item and "q" in item:
                pair = item.get("p", "ASIA_X")
                price = float(item["q"])
                time_stamp = item.get("t", 0)

                new_row = {
                    "time": time_stamp,
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                }

                candles = pd.concat(
                    [candles, pd.DataFrame([new_row])], ignore_index=True
                )

                # मेमोरी मैनेजमेंट: सिर्फ आखिरी 150 कैंडल सुरक्षित रखें
                if len(candles) > 150:
                  candles = candles.iloc[-150:].reset_index(drop=True)

                analyze_market(candles, pair_name=pair)

    except Exception as e:
      print(f"Connection dropped: {e}. Reconnecting in 5 seconds...")
      await asyncio.sleep(5)


if __name__ == "__main__":
  asyncio.run(connect_and_scan())
    
