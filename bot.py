import asyncio
import http.server
import json
import os
import socketserver
import threading
import numpy as np
import pandas as pd
import requests
import websockets
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# --- Render के लिए फ़्री वेब सर्वर (ताकि कोई पोर्ट एरर न आए) ---
PORT = int(os.environ.get("PORT", 8080))


class DummyHandler(http.server.SimpleHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "text/plain")
    self.end_headers()
    self.wfile.write(b"Bot is Running 24/7!")

  def log_message(self, format, *args):
    return


def start_dummy_server():
  with socketserver.TCPServer(("", PORT), DummyHandler) as httpd:
    httpd.serve_forever()


threading.Thread(target=start_dummy_server, daemon=True).start()

# --- 1. सेटिंग्स ---
WS_URL = "wss://ws.olymptrade.com/otp?cid_ver=1&cid_app=web%40OlympTrade%402026.3.2396554%402396554&cid_device=%40%40phone&cid_os=android%4010"
TELEGRAM_BOT_TOKEN = "7979146076:AAGA4DhgxgWVcdeWBkaoa0ewWGWmPOv5OnQ"
TELEGRAM_CHAT_ID = "6968099958"

# आपकी पसंद के सारे पेयर्स और इंडेक्स
ASSETS_MAP = {
    "🌏 Asia Composite": "ASIA_X",
    "💧 Compound Index": "COMPOUND_X",
    "🪙 Crypto Composite": "CRYPTO_IDX",
    "⚽ Football 2026": "FOOTBALL_2026_X",
    "₿ Bitcoin OTC": "BTC_OTC",
    "💎 Ethereum OTC": "ETH_OTC",
    "🔶 BNB OTC": "BNB_OTC",
    "🐕 Dogecoin OTC": "DOGE_OTC",
    "⚡ Litecoin OTC": "LTC_OTC",
    "🌊 Ripple OTC": "XRP_OTC",
    "🐸 PEPE OTC": "PEPE_OTC",
    "🐶 SHIB OTC": "SHIB_OTC",
    "💶 EUR/USD OTC": "EURUSD_OTC",
    "🇦🇺 AUD/CAD OTC": "AUDCAD_OTC",
    "🇨🇭 AUD/CHF OTC": "AUDCHF_OTC",
    "🇪🇺 EUR/AUD OTC": "EURAUD_OTC",
}

current_target_pair = "ASIA_X"
current_target_name = "🌏 Asia Composite"
candles = pd.DataFrame(columns=["time", "open", "high", "low", "close"])
last_alert_signal = None


# --- 2. Telegram मेनू और बटन ---
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  buttons = []
  row = []
  for name, code in ASSETS_MAP.items():
    row.append(InlineKeyboardButton(name, callback_data=code))
    if len(row) == 2:
      buttons.append(row)
      row = []
  if row:
    buttons.append(row)

  reply_markup = InlineKeyboardMarkup(buttons)
  msg_text = (
      f"🎯 **लाइव स्कैनर कंट्रोल पैनल**\n\n"
      f"📍 **वर्तमान एक्टिव पेयर:** `{current_target_name}`\n"
      f"👇 **जिस पेयर का सिग्नल चाहिए उस बटन पर टैप करें:**"
  )
  await update.message.reply_text(
      msg_text, reply_markup=reply_markup, parse_mode="Markdown"
  )


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
  global current_target_pair, current_target_name, candles, last_alert_signal
  query = update.callback_query
  await query.answer()

  selected_code = query.data
  selected_name = [
      k for k, v in ASSETS_MAP.items() if v == selected_code
  ] or [selected_code]

  current_target_pair = selected_code
  current_target_name = selected_name[0]
  candles = pd.DataFrame(columns=["time", "open", "high", "low", "close"])
  last_alert_signal = None

  await query.edit_message_text(
      text=(
          f"✅ **सफलतापूर्वक सेट हुआ!**\n\n"
          f"📡 बोट अब सिर्फ **{current_target_name}** (`{current_target_pair}`) को 24/7 स्कैन कर रहा है।\n"
          f"जैसे ही स्ट्रेटेजी कन्फर्म होगी, तुरंत अलर्ट आएगा।"
      ),
      parse_mode="Markdown",
  )


# --- 3. इंडिकेटर्स और सिग्नल एनालिसिस ---
def analyze_market(df, pair_name):
  global last_alert_signal
  if len(df) < 35:
    return

  close = df["close"].astype(float)
  high = df["high"].astype(float)
  low = df["low"].astype(float)

  ema9 = close.ewm(span=9, adjust=False).mean().iloc[-1]
  ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
  sma10 = close.rolling(window=10).mean().iloc[-1]
  sma30 = close.rolling(window=30).mean().iloc[-1]
  roc5 = ((close.iloc[-1] - close.iloc[-6]) / close.iloc[-6]) * 100

  dc_high = high.rolling(window=20).max().iloc[-1]
  dc_low = low.rolling(window=20).min().iloc[-1]
  dc_mid = (dc_high + dc_low) / 2

  current_price = close.iloc[-1]

  up_signal = (
      (current_price > dc_mid)
      and (current_price > ema9)
      and (ema9 > ema20)
      and (roc5 > 0)
      and (current_price > sma10)
      and (sma10 > sma30)
  )

  down_signal = (
      (current_price < dc_mid)
      and (current_price < ema9)
      and (ema9 < ema20)
      and (roc5 < 0)
      and (current_price < sma10)
      and (sma10 < sma30)
  )

  if up_signal and last_alert_signal != "UP":
    last_alert_signal = "UP"
    send_telegram_alert(current_target_name, "STRONG UP (CALL 🟢)", current_price)
  elif down_signal and last_alert_signal != "DOWN":
    last_alert_signal = "DOWN"
    send_telegram_alert(
        current_target_name, "STRONG DOWN (PUT 🔴)", current_price
    )


def send_telegram_alert(pair_name, signal_type, price):
  emoji = "🟢" if "UP" in signal_type else "🔴"
  message = (
      f"{emoji} **AI SCANNER SIGNAL ALERT** {emoji}\n\n"
      f"📊 **Asset:** {pair_name}\n"
      f"🎯 **Direction:** {signal_type}\n"
      f"💵 **Price:** `{price}`\n"
      f"⏱ **Expiry:** 1 Minute\n\n"
      f"✅ **All 4 Strategies Confirmed**"
  )
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  try:
    requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        },
        timeout=5,
    )
  except Exception as e:
    print(f"Telegram Error: {e}")


# --- 4. WebSocket लाइव स्कैनर ---
async def websocket_scanner():
  global candles, current_target_pair
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like"
          " Gecko) Chrome/139.0.0.0 Mobile Safari/537.36"
      ),
      "Origin": "https://olymptrade.com",
  }

  while True:
    try:
      async with websockets.connect(
          WS_URL,
          extra_headers=headers,
          ping_interval=20,
          ping_timeout=20,
      ) as ws:
        print("✅ OlympTrade Live Stream Connected!")
        while True:
          msg = await ws.recv()
          try:
            data = json.loads(msg)
          except Exception:
            continue

          if isinstance(data, dict) and "d" in data:
            for item in data["d"]:
              if isinstance(item, dict) and "p" in item and "q" in item:
                pair = item.get("p", "").upper()

                if (
                    current_target_pair in pair
                    or pair in current_target_pair
                    or pair == current_target_pair
                ):
                  price = float(item["q"])
                  t_stamp = item.get("t", 0)
                  new_row = {
                      "time": t_stamp,
                      "open": price,
                      "high": price,
                      "low": price,
                      "close": price,
                  }

                  candles = pd.concat(
                      [candles, pd.DataFrame([new_row])], ignore_index=True
                  )
                  if len(candles) > 150:
                    candles = candles.iloc[-150:].reset_index(drop=True)

                  analyze_market(candles, current_target_pair)

    except Exception as e:
      print(f"WS Disconnected: {e}. Reconnecting in 5s...")
      await asyncio.sleep(5)


# --- 5. मुख्य रनर ---
async def main():
  app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
  app.add_handler(CommandHandler("start", show_menu))
  app.add_handler(CommandHandler("menu", show_menu))
  app.add_handler(CallbackQueryHandler(button_click))

  await app.initialize()
  await app.start()
  await app.updater.start_polling(drop_pending_updates=True)

  await websocket_scanner()


if __name__ == "__main__":
  asyncio.run(main())
    
    
