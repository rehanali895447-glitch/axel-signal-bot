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

# 1. Render Uptime Web Server (Port 8080)
PORT = int(os.environ.get("PORT", 8080))

class ServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot Active 24/7")
    def log_message(self, format, *args):
        return

def run_http_server():
    try:
        with socketserver.TCPServer(("", PORT), ServerHandler) as httpd:
            httpd.serve_forever()
    except Exception:
        pass

threading.Thread(target=run_http_server, daemon=True).start()

# 2. Config & Index Setup
TELEGRAM_BOT_TOKEN = "7979146076:AAGA4DhgxgWVcdeWBkaoa0ewWGWmPOv5OnQ"
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

def get_main_menu():
    buttons = []
    for name, code in INDEX_MAP.items():
        buttons.append([{"text": f"📊 {name}", "callback_data": f"PAIR_{code}"}])
    return {"inline_keyboard": buttons}

def get_time_menu(pair_code, pair_name):
    clean = pair_name.replace("🌏 ", "").replace("💧 ", "").replace("⚽ ", "")
    buttons = [
        [{"text": f"⚡ 45 SEC 🟢 {clean}", "callback_data": f"SIG_45_{pair_code}"}],
        [{"text": f"⚡ 30 SEC 🟢 {clean}", "callback_data": f"SIG_30_{pair_code}"}],
        [{"text": f"⚡ 15 SEC 🟢 {clean}", "callback_data": f"SIG_15_{pair_code}"}],
        [{"text": "🔄 दूसरा पेयर चुनें (Change Pair)", "callback_data": "MENU_MAIN"}]
    ]
    return {"inline_keyboard": buttons}

# 3. Fast Analysis Engine (EMA + Momentum)
def generate_instant_signal(pair_code, timeframe_sec):
    prices = market_cache.get(pair_code, [])
    pair_name = [k for k, v in INDEX_MAP.items() if v == pair_code]
    display_name = pair_name[0] if pair_name else pair_code
    
    if len(prices) >= 5:
        closes = np.array(prices, dtype=float)
        ema_fast = pd.Series(closes).ewm(span=3, adjust=False).mean().iloc[-1]
        ema_slow = pd.Series(closes).ewm(span=8, adjust=False).mean().iloc[-1]
        momentum = closes[-1] - closes[-3]
        is_call = (ema_fast >= ema_slow) and (momentum >= 0)
    elif len(prices) >= 2:
        is_call = prices[-1] >= prices[-2]
    else:
        is_call = (int(time.time() * 10) % 2) == 0

    if is_call:
        msg = (
            f"⬆️⬆️ **CALL** ⬆️⬆️\n"
            f"       🦁 🟢\n"
            f"⏱ `{timeframe_sec} SEC` 🟢 `{display_name}`"
        )
    else:
        msg = (
            f"⬇️⬇️ **PUT** ⬇️⬇️\n"
            f"       🐻 🔴\n"
            f"⏱ `{timeframe_sec} SEC` 🔴 `{display_name}`"
        )
    return msg, display_name

# 4. Telegram Worker Loop (Clean & No Double Trigger)
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

                        # /start command
                        if "message" in update and "text" in update["message"]:
                            t = update["message"]["text"]
                            cid = update["message"]["chat"]["id"]
                            if t in ["/start", "/menu"]:
                                requests.post(f"{API_URL}/sendMessage", json={
                                    "chat_id": cid,
                                    "text": "🎯 **Select Index Asset:**",
                                    "reply_markup": get_main_menu(),
                                    "parse_mode": "Markdown"
                                }, timeout=5)

                        # Callback query (Button clicks)
                        elif "callback_query" in update:
                            cb = update["callback_query"]
                            cid = cb["message"]["chat"]["id"]
                            mid = cb["message"]["message_id"]
                            cb_id = cb["id"]
                            action = cb.get("data", "")

                            # Instant ACK to Telegram
                            try:
                                requests.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=2)
                            except Exception:
                                pass

                            # Return to Main Menu
                            if action in ["MENU_MAIN", "MENU_BACK"]:
                                requests.post(f"{API_URL}/editMessageText", json={
                                    "chat_id": cid,
                                    "message_id": mid,
                                    "text": "🎯 **Select Index Asset:**",
                                    "reply_markup": get_main_menu(),
                                    "parse_mode": "Markdown"
                                }, timeout=5)

                            # Pair Selected -> Show 15s/30s/45s buttons
                            elif action.startswith("PAIR_"):
                                pair_code = action.replace("PAIR_", "")
                                p_name = [k for k, v in INDEX_MAP.items() if v == pair_code]
                                display_name = p_name[0] if p_name else pair_code

                                requests.post(f"{API_URL}/editMessageText", json={
                                    "chat_id": cid,
                                    "message_id": mid,
                                    "text": f"📊 **{display_name}**\n👇 **Select Timeframe to Get Signal:**",
                                    "reply_markup": get_time_menu(pair_code, display_name),
                                    "parse_mode": "Markdown"
                                }, timeout=5)

                            # Signal Clicked -> Send Signal with Permanent Next-Buttons
                            elif action.startswith("SIG_"):
                                parts = action.split("_")
                                sec = parts[1]
                                pair_code = "_".join(parts[2:])

                                sig_msg, disp_name = generate_instant_signal(pair_code, sec)
                                
                                requests.post(f"{API_URL}/sendMessage", json={
                                    "chat_id": cid,
                                    "text": sig_msg,
                                    "reply_markup": get_time_menu(pair_code, disp_name),
                                    "parse_mode": "Markdown"
                                }, timeout=5)
            time.sleep(0.1)
        except Exception:
            time.sleep(1)

# 5. Live WebSocket Receiver
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
                                        if len(market_cache[key_pair]) > 30:
                                            market_cache[key_pair].pop(0)
        except Exception:
            await asyncio.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=telegram_worker, daemon=True).start()
    asyncio.run(websocket_worker())
                            
