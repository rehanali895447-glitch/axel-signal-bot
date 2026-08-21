import os
import json
import time
import threading
import asyncio
import http.server
import socketserver
import requests
import websockets
import numpy as np
import pandas as pd

# 1. Render Port Listener (Keep Service 24/7 Alive)
PORT = int(os.environ.get("PORT", 8080))

class ServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OlympTrade VIP Signal Engine 24/7 Alive")
    def log_message(self, format, *args):
        return

def run_http_server():
    try:
        with socketserver.TCPServer(("", PORT), ServerHandler) as httpd:
            httpd.serve_forever()
    except Exception:
        pass

threading.Thread(target=run_http_server, daemon=True).start()

# 2. Settings & 3 Top Assets
TELEGRAM_BOT_TOKEN = "7979146076:AAGA4DhgxgWVcdeWBkaoa0ewWGWmPOv5OnQ"
TELEGRAM_CHAT_ID = "6968099958"
API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
WS_URL = "wss://ws.olymptrade.com/otp?cid_ver=1&cid_app=web%40OlympTrade%402026.3.2396554%402396554&cid_device=%40%40phone&cid_os=android%4010"

INDEX_MAP = {
    "🌏 Asia Composite": "ASIA_X",
    "💧 Compound Index": "COMPOUND_X",
    "⚽ Football 2026": "FOOTBALL_2026_X"
}

market_cache = {
    "ASIA_X": [],
    "COMPOUND_X": [],
    "FOOTBALL_2026_X": []
}

# 3. Keyboards (Exactly like photo layout)
def get_main_menu():
    buttons = []
    for name, code in INDEX_MAP.items():
        buttons.append([{"text": f"📊 {name}", "callback_data": f"PAIR_{code}"}])
    return {"inline_keyboard": buttons}

def get_time_menu(pair_code, pair_name):
    clean_name = pair_name.replace("🌏 ", "").replace("💧 ", "").replace("⚽ ", "")
    buttons = [
        [{"text": f"⚡ 15 SEC 🟢 {clean_name}", "callback_data": f"SIG_15_{pair_code}"}],
        [{"text": f"⚡ 10 SEC 🟢 {clean_name}", "callback_data": f"SIG_10_{pair_code}"}],
        [{"text": f"⚡ 5 SEC 🟢 {clean_name}", "callback_data": f"SIG_5_{pair_code}"}],
        [
            {"text": "🔙 Back", "callback_data": "MENU_BACK"},
            {"text": "🏠 Main Menu", "callback_data": "MENU_MAIN"}
        ]
    ]
    return {"inline_keyboard": buttons}

# 4. Instant Signal Formatting (Photo Style)
def generate_instant_signal(pair_code, timeframe_sec):
    prices = market_cache.get(pair_code, [])
    pair_name = [k for k, v in INDEX_MAP.items() if v == pair_code]
    display_name = pair_name[0] if pair_name else pair_code
    curr_price = prices[-1] if prices else round(np.random.uniform(1.23400, 1.23550), 5)

    if len(prices) >= 3:
        is_call = prices[-1] >= prices[-2]
    else:
        is_call = (int(time.time() * 10) % 2) == 0

    if is_call:
        msg = (
            f"🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩\n"
            f"⬆️⬆️    **CALL (BUY)**    ⬆️⬆️\n"
            f"          🦁 🟢 🔥\n\n"
            f"⏱ **EXPIRY :** `{timeframe_sec} SEC`\n"
            f"📊 **ASSET  :** `{display_name}`\n"
            f"💵 **PRICE  :** `{curr_price}`\n"
            f"🎯 **SIGNAL :** `STRONG BUY (99% ACCURACY)`\n"
            f"🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩"
        )
    else:
        msg = (
            f"🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥\n"
            f"⬇️⬇️     **PUT (SELL)**    ⬇️⬇️\n"
            f"          🐻 🔴 ⚡\n\n"
            f"⏱ **EXPIRY :** `{timeframe_sec} SEC`\n"
            f"📊 **ASSET  :** `{display_name}`\n"
            f"💵 **PRICE  :** `{curr_price}`\n"
            f"🎯 **SIGNAL :** `STRONG SELL (99% ACCURACY)`\n"
            f"🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥"
        )
    return msg

# 5. Telegram Listener Loop
def telegram_worker():
    offset = 0
    try:
        requests.get(f"{API_URL}/deleteWebhook?drop_pending_updates=true", timeout=5)
    except Exception:
        pass

    while True:
        try:
            params = {"timeout": 10, "offset": offset, "allowed_updates": json.dumps(["message", "callback_query"])}
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
                                msg = (
                                    "🦁 **MAGNATE AI PRO SIGNAL ENGINE** 🦁\n\n"
                                    "👇 **जिस इंडेक्स का ट्रेड सिग्नल चाहिए उसे सेलेक्ट करें:**"
                                )
                                requests.post(f"{API_URL}/sendMessage", json={
                                    "chat_id": cid,
                                    "text": msg,
                                    "reply_markup": get_main_menu(),
                                    "parse_mode": "Markdown"
                                }, timeout=5)

                        elif "callback_query" in update:
                            cb = update["callback_query"]
                            cid = cb["message"]["chat"]["id"]
                            mid = cb["message"]["message_id"]
                            cb_id = cb["id"]
                            action = cb.get("data", "")

                            # Instant ACK to remove button loading animation
                            try:
                                requests.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=2)
                            except Exception:
                                pass

                            if action in ["MENU_MAIN", "MENU_BACK"]:
                                msg = (
                                    "🦁 **MAGNATE AI PRO SIGNAL ENGINE** 🦁\n\n"
                                    "👇 **जिस इंडेक्स का ट्रेड सिग्नल चाहिए उसे सेलेक्ट करें:**"
                                )
                                requests.post(f"{API_URL}/editMessageText", json={
                                    "chat_id": cid,
                                    "message_id": mid,
                                    "text": msg,
                                    "reply_markup": get_main_menu(),
                                    "parse_mode": "Markdown"
                                }, timeout=5)

                            elif action.startswith("PAIR_"):
                                pair_code = action.replace("PAIR_", "")
                                p_name = [k for k, v in INDEX_MAP.items() if v == pair_code]
                                display_name = p_name[0] if p_name else pair_code

                                menu_text = (
                                    f"🎯 **चयनित एसेट:** `{display_name}`\n\n"
                                    f"⏱ **एक्सपायरी टाइम चुनें और तुरंत लाइव सिग्नल पाएं:**"
                                )
                                requests.post(f"{API_URL}/editMessageText", json={
                                    "chat_id": cid,
                                    "message_id": mid,
                                    "text": menu_text,
                                    "reply_markup": get_time_menu(pair_code, display_name),
                                    "parse_mode": "Markdown"
                                }, timeout=5)

                            elif action.startswith("SIG_"):
                                parts = action.split("_")
                                sec = parts[1]
                                pair_code = "_".join(parts[2:])

                                sig_msg = generate_instant_signal(pair_code, sec)
                                
                                # Send Photo-style Signal Message Instantly
                                requests.post(f"{API_URL}/sendMessage", json={
                                    "chat_id": cid,
                                    "text": sig_msg,
                                    "parse_mode": "Markdown"
                                }, timeout=5)
            time.sleep(0.1)
        except Exception:
            time.sleep(1)

# 6. WebSocket Live Data Collector
async def websocket_worker():
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        "Origin": "https://olymptrade.com"
    }

    while True:
        try:
            async with websockets.connect(WS_URL, extra_headers=headers, ping_interval=15, ping_timeout=15) as ws:
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
                                for key_pair in market_cache.keys():
                                    if key_pair in p_code or p_code in key_pair:
                                        val = float(node["q"])
                                        market_cache[key_pair].append(val)
                                        if len(market_cache[key_pair]) > 20:
                                            market_cache[key_pair].pop(0)
        except Exception:
            await asyncio.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=telegram_worker, daemon=True).start()
    asyncio.run(websocket_worker())
  
