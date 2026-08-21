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

# --- 1. Render Port Listener ---
PORT = int(os.environ.get("PORT", 8080))


class ServerHandler(http.server.SimpleHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.send_header("Content-type", "text/plain")
    self.end_headers()
    self.wfile.write(b"Bot Server Active")

  def log_message(self, format, *args):
    return


def run_http_server():
  try:
    with socketserver.TCPServer(("", PORT), ServerHandler) as httpd:
      httpd.serve_forever()
  except Exception:
    pass


threading.Thread(target=run_http_server, daemon=True).start()

# --- 2. Configurations & WebSocket URL ---
TELEGRAM_BOT_TOKEN = "7979146076:AAGA4DhgxgWVcdeWBkaoa0ewWGWmPOv5OnQ"
TELEGRAM_CHAT_ID = "6968099958"
API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
WS_URL = "wss://ws.olymptrade.com/otp?cid_ver=1&cid_app=web%40OlympTrade%402026.3.2396554%402396554&cid_device=%40%40phone&cid_os=android%4010"

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

current_pair = "ASIA_X"
current_name = "🌏 Asia Composite"
price_history = []
last_alert_type = None


def get_main_menu():
  buttons = []
  row = []
  for name, code in ASSETS_MAP.items():
    row.append({"text": name, "callback_data": code})
    if len(row) == 2:
      buttons.append(row)
      row = []
  if row:
    buttons.append(row)
  return {"inline_keyboard": buttons}


# --- 3. Fast Signal Engine ---
def check_signals(prices, pair_display_name):
  global last_alert_type
  if len(prices) < 5:
    return

  closes = np.array(prices, dtype=float)
  ema_fast = pd.Series(closes).ewm(span=3, adjust=False).mean().iloc[-1]
  ema_slow = pd.Series(closes).ewm(span=6, adjust=False).mean().iloc[-1]
  dc_high = pd.Series(closes).rolling(window=5, min_periods=1).max().iloc[-1]
  dc_low = pd.Series(closes).rolling(window=5, min_periods=1).min().iloc[-1]
  dc_mid = (dc_high + dc_low) / 2
  roc = ((closes[-1] - closes[-3]) / closes[-3]) * 100 if len(closes) >= 3 else 0
  curr = closes[-1]

  is_call = (
      (curr >= dc_mid)
      and (curr >= ema_fast)
      and (ema_fast >= ema_slow)
      and (roc >= 0)
  )
  is_put = (
      (curr <= dc_mid)
      and (curr <= ema_fast)
      and (ema_fast <= ema_slow)
      and (roc <= 0)
  )

  if is_call and last_alert_type != "CALL":
    last_alert_type = "CALL"
    msg = (
        f"🟢 **STRONG UP (CALL) ALERT** 🟢\n\n"
        f"📊 **Asset:** `{pair_display_name}`\n"
        f"🎯 **Direction:** CALL (1 Min Expiry)\n"
        f"💵 **Price:** `{curr}`\n\n"
        f"⚡ **Conditions Matched! Place Trade Now!**"
    )
    requests.post(
        f"{API_URL}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown",
        },
        timeout=5,
    )
  elif is_put and last_alert_type != "PUT":
    last_alert_type = "PUT"
    msg = (
        f"🔴 **STRONG DOWN (PUT) ALERT** 🔴\n\n"
        f"📊 **Asset:** `{pair_display_name}`\n"
        f"🎯 **Direction:** PUT (1 Min Expiry)\n"
        f"💵 **Price:** `{curr}`\n\n"
        f"⚡ **Conditions Matched! Place Trade Now!**"
    )
    requests.post(
        f"{API_URL}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown",
        },
        timeout=5,
    )


# --- 4. High-Speed Telegram Listener ---
def telegram_worker():
  global current_pair, current_name, price_history, last_alert_type
  offset = 0

  requests.get(f"{API_URL}/deleteWebhook?drop_pending_updates=true", timeout=5)

  while True:
    try:
      params = {"timeout": 10, "offset": offset}
      res = requests.get(f"{API_URL}/getUpdates", params=params, timeout=15)
      if res.status_code == 200:
        data = res.json()
        if data.get("ok"):
          for update in data.get("result", []):
            offset = update["update_id"] + 1

            if "message" in update and "text" in update["message"]:
              t = update["message"]["text"]
              cid = update["message"]["chat"]["id"]
              if t in ["/start", "/menu"]:
                menu_msg = (
                    "🎯 **OlympTrade Live AI Scanner**\n\n👇 **जिस पेयर को"
                    " स्कैन करना है उस पर क्लिक करें:**"
                )
                requests.post(
                    f"{API_URL}/sendMessage",
                    json={
                        "chat_id": cid,
                        "text": menu_msg,
                        "reply_markup": get_main_menu(),
                        "parse_mode": "Markdown",
                    },
                    timeout=5,
                )

            elif "callback_query" in update:
              cb = update["callback_query"]
              cid = cb["message"]["chat"]["id"]
              mid = cb["message"]["message_id"]
              cb_id = cb["id"]
              action = cb["data"]

              # Instant Telegram Acknowledge
              requests.post(
                  f"{API_URL}/answerCallbackQuery",
                  json={"callback_query_id": cb_id},
                  timeout=3,
              )

              if action == "BACK_MENU":
                menu_msg = (
                    "🎯 **OlympTrade Live AI Scanner**\n\n👇 **जिस पेयर को"
                    " स्कैन करना है उस पर क्लिक करें:**"
                )
                requests.post(
                    f"{API_URL}/editMessageText",
                    json={
                        "chat_id": cid,
                        "message_id": mid,
                        "text": menu_msg,
                        "reply_markup": get_main_menu(),
                        "parse_mode": "Markdown",
                    },
                    timeout=5,
                )

              elif action in ASSETS_MAP.values():
                current_pair = action
                name_lookup = [
                    k for k, v in ASSETS_MAP.items() if v == current_pair
                ]
                current_name = name_lookup[0] if name_lookup else current_pair
                price_history = []
                last_alert_type = None

                # 16 पेयर्स तुरंत गायब होंगे और यह लाइव कार्ड दिखेगा
                active_card = (
                    f"🚀 **स्कैनर एक्टिवेट हो चुका है!**\n\n"
                    f"📍 **एक्टिव पेयर:** `{current_name}` (`{current_pair}`)\n"
                    f"📡 **लाइव स्टेटस:** 24/7 डेटा स्ट्रीम स्कैनिंग ऑन है...\n"
                    f"⏱ **टाइमफ्रेम:** 1 मिनट AI Strategy\n\n"
                    f"⚡ जैसे ही सिग्नल बनेगा, तुरंत नीचे अलर्ट भेजा जाएगा।"
                )
                back_nav = {
                    "inline_keyboard": [[{
                        "text": "🔄 दूसरा पेयर चुनें (Menu)",
                        "callback_data": "BACK_MENU",
                    }]]
                }
                requests.post(
                    f"{API_URL}/editMessageText",
                    json={
                        "chat_id": cid,
                        "message_id": mid,
                        "text": active_card,
                        "reply_markup": back_nav,
                        "parse_mode": "Markdown",
                    },
                    timeout=5,
                )
    except Exception:
      pass


# --- 5. OlympTrade Live WebSocket Engine ---
async def websocket_worker():
  global price_history, current_pair
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
        print("✅ WebSocket Stream Live!")
        while True:
          raw = await ws.recv()
          try:
            payload = json.loads(raw)
          except Exception:
            continue

          if isinstance(payload, dict) and "d" in payload:
            for node in payload["d"]:
              if isinstance(node, dict) and "p" in node and "q" in node:
                p_code = node.get("p", "").upper()
                if (
                    current_pair in p_code
                    or p_code in current_pair
                    or p_code == current_pair
                ):
                  val = float(node["q"])
                  price_history.append(val)
                  if len(price_history) > 40:
                    price_history.pop(0)

                  check_signals(price_history, current_name)
    except Exception:
      await asyncio.sleep(2)


if __name__ == "__main__":
  threading.Thread(target=telegram_worker, daemon=True).start()
  asyncio.run(websocket_worker())
                
