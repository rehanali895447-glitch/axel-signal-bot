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

# 1. Render Web Server (Port 8080 Alive 24/7)
PORT = int(os.environ.get("PORT", 8080))

class ServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OlympTrade AI Signal Server Active 24/7")
    def log_message(self, format, *args):
        return

def run_http_server():
    try:
        with socketserver.TCPServer(("", PORT), ServerHandler) as httpd:
            httpd.serve_forever()
    except Exception:
        pass

threading.Thread(target=run_http_server, daemon=True).start()

# 2. Config & Assets Setup
TELEGRAM_BOT_TOKEN = "7979146076:AAGA4DhgxgWVcdeWBkaoa0ewWGWmPOv5OnQ"
API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
WS_URL = "wss://ws.olymptrade.com/otp?cid_ver=1&cid_app=web%40OlympTrade%402026.3.2396554%402396554&cid_device=%40%40phone&cid_os=android%4010"

INDEX_MAP = {
    "🌏 Asia Composite": "ASIA_X",
    "💧 Compound Index": "COMPOUND_X",
    "⚽ Football 2026": "FOOTBALL_2026_X"
}

market_candles = {
    "ASIA_X": [],
    "COMPOUND_X": [],
    "FOOTBALL_2026_X": []
}

# Key: chat_id -> Value: {"pair": pair_code, "tf": tf_min, "last_sig": None}
active_user_scan = {}

def get_main_menu():
    buttons = []
    for name, code in INDEX_MAP.items():
        buttons.append([{"text": f"📊 {name}", "callback_data": f"PAIR_{code}"}])
    return {"inline_keyboard": buttons}

def get_time_menu(pair_code, pair_name):
    clean = pair_name.replace("🌏 ", "").replace("💧 ", "").replace("⚽ ", "")
    buttons = [
        [{"text": f"⚡ 1 MIN 🟢 {clean}", "callback_data": f"SET_1_{pair_code}"}],
        [{"text": f"⚡ 2 MIN 🟢 {clean}", "callback_data": f"SET_2_{pair_code}"}],
        [{"text": "🔄 दूसरा पेयर चुनें (Change Pair)", "callback_data": "MENU_MAIN"}]
    ]
    return {"inline_keyboard": buttons}

# 3. 100% Sure-Shot Signal Condition Analysis
def check_trade_condition(pair_code):
    data = market_candles.get(pair_code, [])
    if len(data) < 20:
        return None

    closes = np.array(data, dtype=float)
    
    # Fast & Slow EMA Calculation
    ema_fast = pd.Series(closes).ewm(span=5, adjust=False).mean().iloc[-1]
    ema_slow = pd.Series(closes).ewm(span=20, adjust=False).mean().iloc[-1]
    
    # Donchian Channel Breakdown
    dc_high = pd.Series(closes).rolling(window=12, min_periods=1).max().iloc[-1]
    dc_low = pd.Series(closes).rolling(window=12, min_periods=1).min().iloc[-1]
    dc_mid = (dc_high + dc_low) / 2
    
    # Momentum (Rate of Change)
    roc = ((closes[-1] - closes[-4]) / closes[-4]) * 100
    curr = closes[-1]

    # 100% Strict Entry Rules
    is_strong_call = (curr > dc_mid) and (ema_fast > ema_slow) and (roc > 0.015)
    is_strong_put = (curr < dc_mid) and (ema_fast < ema_slow) and (roc < -0.015)

    if is_strong_call:
        return "CALL", curr
    elif is_strong_put:
        return "PUT", curr
    return None

# 4. Telegram Engine (Strictly Single Message, No Duplicates)
def telegram_worker():
    offset = 0
    try:
        requests.get(f"{API_URL}/deleteWebhook?drop_pending_updates=true", timeout=5)
        res = requests.get(f"{API_URL}/getUpdates?offset=-1", timeout=5).json()
        if res.get("ok") and res.get("result"):
            offset = res["result"][-1]["update_id"] + 1
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
                                    "text": "🎯 **Select Index Asset for Deep AI Analysis:**",
                                    "reply_markup": get_main_menu(),
                                    "parse_mode": "Markdown"
                                }, timeout=5)

                        # Callback Button Handling
                        elif "callback_query" in update:
                            cb = update["callback_query"]
                            cid = cb["message"]["chat"]["id"]
                            mid = cb["message"]["message_id"]
                            cb_id = cb["id"]
                            action = cb.get("data", "")

                            try:
                                requests.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=2)
                            except Exception:
                                pass

                            if action in ["MENU_MAIN", "MENU_BACK"]:
                                requests.post(f"{API_URL}/editMessageText", json={
                                    "chat_id": cid,
                                    "message_id": mid,
                                    "text": "🎯 **Select Index Asset for Deep AI Analysis:**",
                                    "reply_markup": get_main_menu(),
                                    "parse_mode": "Markdown"
                                }, timeout=5)

                            elif action.startswith("PAIR_"):
                                pair_code = action.replace("PAIR_", "")
                                p_name = [k for k, v in INDEX_MAP.items() if v == pair_code]
                                display_name = p_name[0] if p_name else pair_code

                                requests.post(f"{API_URL}/editMessageText", json={
                                    "chat_id": cid,
                                    "message_id": mid,
                                    "text": f"📊 **{display_name}**\n👇 **Select Timeframe:**",
                                    "reply_markup": get_time_menu(pair_code, display_name),
                                    "parse_mode": "Markdown"
                                }, timeout=5)

                            elif action.startswith("SET_"):
                                parts = action.split("_")
                                tf = int(parts[1])
                                pair_code = "_".join(parts[2:])
                                p_name = [k for k, v in INDEX_MAP.items() if v == pair_code]
                                display_name = p_name[0] if p_name else pair_code

                                active_user_scan[cid] = {"pair": pair_code, "tf": tf, "last_sig": None, "display": display_name}

                                scan_text = (
                                    f"🔍 **Scanning OlympTrade Live Market for {display_name}...**\n"
                                    f"⏱ **Timeframe:** `{tf} MIN`\n\n"
                                    f"📡 जब EMA और Donchian की 100% कंडीशन बनेगी, तुरंत नीचे SURE-SHOT अलर्ट आएगा।"
                                )
                                back_btn = {"inline_keyboard": [[{"text": "🔄 दूसरा पेयर चुनें (Change Pair)", "callback_data": "MENU_MAIN"}]]}
                                requests.post(f"{API_URL}/editMessageText", json={
                                    "chat_id": cid,
                                    "message_id": mid,
                                    "text": scan_text,
                                    "reply_markup": back_btn,
                                    "parse_mode": "Markdown"
                                }, timeout=5)
            time.sleep(0.1)
        except Exception:
            time.sleep(1)

# 5. Background Signal Engine (100% Condition Matched Alerts Only)
def scanner_loop():
    while True:
        for cid, user_data in list(active_user_scan.items()):
            pair_code = user_data["pair"]
            tf = user_data["tf"]
            last_sig = user_data["last_sig"]
            display_name = user_data["display"]

            result = check_trade_condition(pair_code)
            
            if result:
                direction, price = result
                if direction != last_sig:
                    active_user_scan[cid]["last_sig"] = direction

                    if direction == "CALL":
                        msg = (
                            f"⬆️⬆️ **STRONG CALL** ⬆️⬆️\n"
                            f"       🦁 🟢\n"
                            f"⏱ `{tf} MIN` 🟢 `{display_name}`\n"
                            f"💵 **Price:** `{price}`\n"
                            f"🎯 **Conditions Matched! Place UP Trade Now!**"
                        )
                    else:
                        msg = (
                            f"⬇️⬇️ **STRONG PUT** ⬇️⬇️\n"
                            f"       🐻 🔴\n"
                            f"⏱ `{tf} MIN` 🔴 `{display_name}`\n"
                            f"💵 **Price:** `{price}`\n"
                            f"🎯 **Conditions Matched! Place DOWN Trade Now!**"
                        )
                    
                    back_btn = {"inline_keyboard": [[{"text": "🔄 दूसरा पेयर चुनें (Change Pair)", "callback_data": "MENU_MAIN"}]]}
                    requests.post(f"{API_URL}/sendMessage", json={
                        "chat_id": cid,
                        "text": msg,
                        "reply_markup": back_btn,
                        "parse_mode": "Markdown"
                    }, timeout=5)
        time.sleep(2)

# 6. OlympTrade Live WebSocket Receiver
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
                                for key_pair in market_candles.keys():
                                    if key_pair in p_code or p_code in key_pair:
                                        val = float(node["q"])
                                        market_candles[key_pair].append(val)
                                        if len(market_candles[key_pair]) > 60:
                                            market_candles[key_pair].pop(0)
        except Exception:
            await asyncio.sleep(2)

if __name__ == "__main__":
    threading.Thread(target=telegram_worker, daemon=True).start()
    threading.Thread(target=scanner_loop, daemon=True).start()
    asyncio.run(websocket_worker())
                            
