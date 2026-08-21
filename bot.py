import os
import json
import time
import threading
import asyncio
import http.server
import socketserver
import requests
import websockets

# 1. Render Port Listener (24/7 Alive Keep-Alive)
PORT = int(os.environ.get("PORT", 8080))

class ServerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Live WebSocket AI Trading Engine Live")
    def log_message(self, format, *args):
        return

def run_http_server():
    try:
        with socketserver.TCPServer(("", PORT), ServerHandler) as httpd:
            httpd.serve_forever()
    except Exception:
        pass

threading.Thread(target=run_http_server, daemon=True).start()

# 2. Config & Asset Settings
TELEGRAM_BOT_TOKEN = "7979146076:AAGA4DhgxgWVcdeWBkaoa0ewWGWmPOv5OnQ"
API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
WS_URL = "wss://ws.olymptrade.com/otp?cid_ver=1&cid_app=web%40OlympTrade%402026.3.2396554%402396554&cid_device=%40%40phone&cid_os=android%4010"

GROQ_API_KEY = "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"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

INDEX_MAP = {
    "🌏 Asia Composite": "ASIA_X",
    "💧 Compound Index": "CMDTY_X",
    "⚽ Football 2026": "FOOTBALL_2026_X"
}

# Live Real-Tick Memory (Continuously updated by WebSocket)
market_ticks = {
    "ASIA_X": [],
    "CMDTY_X": [],
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
        [{"text": f"⚡ 1 MIN 🟢 {clean}", "callback_data": f"SIG_1_{pair_code}"}],
        [{"text": f"⚡ 2 MIN 🟢 {clean}", "callback_data": f"SIG_2_{pair_code}"}],
        [{"text": "🔄 दूसरा पेयर चुनें (Change Pair)", "callback_data": "MENU_MAIN"}]
    ]
    return {"inline_keyboard": buttons}

def get_signal_followup_menu(pair_code, pair_name):
    clean = pair_name.replace("🌏 ", "").replace("💧 ", "").replace("⚽ ", "")
    buttons = [
        [
            {"text": f"⚡ Next 1 MIN", "callback_data": f"SIG_1_{pair_code}"},
            {"text": f"⚡ Next 2 MIN", "callback_data": f"SIG_2_{pair_code}"}
        ],
        [{"text": "🔄 दूसरा पेयर चुनें (Change Pair)", "callback_data": "MENU_MAIN"}]
    ]
    return {"inline_keyboard": buttons}

# 3. High-Speed 1-Minute Win Groq AI Engine
def ask_groq_ai(ticks, asset_name, tf_min):
    if not ticks:
        return "SKIP"
    
    ticks_str = ", ".join([str(round(x, 4)) for x in ticks[-15:]])
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = (
        f"You are a High Frequency Binary Trading AI. Real-time live ticks for {asset_name}: [{ticks_str}].\n"
        f"Predict if the IMMEDIATE NEXT 1-MINUTE CANDLE will strictly close HIGHER (CALL) or LOWER (PUT) than current price.\n"
        f"- Output 'CALL' if strong upward pressure guarantees the next candle closes GREEN.\n"
        f"- Output 'PUT' if strong downward pressure guarantees the next candle closes RED.\n"
        f"- Output 'SKIP' if market is choppy, flat, or has high wick rejection.\n\n"
        f"Strict JSON output only: {{\"signal\": \"CALL\" or \"PUT\" or \"SKIP\"}}"
    )

    # Active 2026 Production Groq Models
    models = ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.6-27b"]

    for m in models:
        try:
            payload = {
                "model": m,
                "messages": [
                    {"role": "system", "content": "You are a low-latency AI predicting immediate binary candle closes in valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.05,
                "max_tokens": 50,
                "response_format": {"type": "json_object"}
            }
            res = requests.post(GROQ_URL, headers=headers, json=payload, timeout=1.8)
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                return parsed.get("signal", "CALL").upper()
        except Exception:
            continue

    # Zero-Lag Fallback Engine
    if len(ticks) >= 3:
        if ticks[-1] > ticks[-2] and ticks[-2] >= ticks[-3]:
            return "CALL"
        elif ticks[-1] < ticks[-2] and ticks[-2] <= ticks[-3]:
            return "PUT"
    return "SKIP"

def generate_clean_signal(pair_code, tf_min):
    ticks = market_ticks.get(pair_code, [])
    pair_name = [k for k, v in INDEX_MAP.items() if v == pair_code]
    display_name = pair_name[0] if pair_name else pair_code
    curr_price = round(float(ticks[-1]), 4) if ticks else 7458.79

    signal = ask_groq_ai(ticks, display_name, tf_min)

    if signal == "CALL":
        msg = (
            f"🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩\n"
            f"⬆️ **CALL (UP)** 🟢 🔥\n\n"
            f"⏱ `{tf_min} MIN` • `{display_name}`\n"
            f"💵 **PRICE :** `{curr_price}`\n"
            f"🎯 *Next 1-Min Candle Win*\n"
            f"🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩"
        )
    elif signal == "PUT":
        msg = (
            f"🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥\n"
            f"⬇️ **PUT (DOWN)** 🔴 ⚡\n\n"
            f"⏱ `{tf_min} MIN` • `{display_name}`\n"
            f"💵 **PRICE :** `{curr_price}`\n"
            f"🎯 *Next 1-Min Candle Win*\n"
            f"🟥🟥🟥🟥🟥🟥🟥🟥🟥🟥"
        )
    else:
        msg = (
            f"🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨\n"
            f"✋ **SKIP / WAIT** 🟡 ⏳\n\n"
            f"⏱ `{tf_min} MIN` • `{display_name}`\n"
            f"💵 **PRICE :** `{curr_price}`\n"
            f"💡 *मार्केट फंसा हुआ है, अगला सिग्नल लें!*\n"
            f"🟨🟨🟨🟨🟨🟨🟨🟨🟨🟨"
        )
    return msg, display_name

# 4. Telegram Worker
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

                        if "message" in update and "text" in update["message"]:
                            t = update["message"]["text"]
                            cid = update["message"]["chat"]["id"]
                            if t in ["/start", "/menu"]:
                                requests.post(f"{API_URL}/sendMessage", json={
                                    "chat_id": cid,
                                    "text": "🤖 **MAGNATE AI PRO**\n\n👇 **ट्रेडिंग के लिए पेयर चुनें:**",
                                    "reply_markup": get_main_menu(),
                                    "parse_mode": "Markdown"
                                }, timeout=5)

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
                                    "text": "🤖 **MAGNATE AI PRO**\n\n👇 **ट्रेडिंग के लिए पेयर चुनें:**",
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
                                    "text": f"📊 **{display_name}**\n👇 **टाइम चुनें:**",
                                    "reply_markup": get_time_menu(pair_code, display_name),
                                    "parse_mode": "Markdown"
                                }, timeout=5)

                            elif action.startswith("SIG_"):
                                parts = action.split("_")
                                tf = parts[1]
                                pair_code = "_".join(parts[2:])

                                sig_msg, disp_name = generate_clean_signal(pair_code, tf)
                                
                                requests.post(f"{API_URL}/editMessageText", json={
                                    "chat_id": cid,
                                    "message_id": mid,
                                    "text": sig_msg,
                                    "reply_markup": get_signal_followup_menu(pair_code, disp_name),
                                    "parse_mode": "Markdown"
                                }, timeout=5)
            time.sleep(0.1)
        except Exception:
            time.sleep(1)

# 5. Live Millisecond WebSocket Engine (Continuous Real-Tick Capture)
async def websocket_worker():
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        "Origin": "https://olymptrade.com"
    }

    while True:
        try:
            async with websockets.connect(WS_URL, extra_headers=headers, ping_interval=10, ping_timeout=10) as ws:
                # Active Subscription for OlympTrade Pairs
                sub_payload = [{"t": 2, "e": 90, "d": [{"p": "ASIA_X"}, {"p": "CMDTY_X"}, {"p": "FOOTBALL_2026_X"}]}]
                await ws.send(json.dumps(sub_payload))

                while True:
                    raw = await ws.recv()
                    try:
                        payload = json.loads(raw)
                    except Exception:
                        continue

                    # List Payloads
                    if isinstance(payload, list):
                        for item in payload:
                            if isinstance(item, dict) and "d" in item:
                                for node in item["d"]:
                                    if isinstance(node, dict) and "p" in node and "q" in node:
                                        p_code = str(node.get("p", "")).upper()
                                        val = float(node["q"])
                                        for k in market_ticks.keys():
                                            if k in p_code or p_code in k:
                                                market_ticks[k].append(val)
                                                if len(market_ticks[k]) > 60:
                                                    market_ticks[k].pop(0)

                    # Dict Payloads
                    elif isinstance(payload, dict) and "d" in payload:
                        for node in payload["d"]:
                            if isinstance(node, dict) and "p" in node and "q" in node:
                                p_code = str(node.get("p", "")).upper()
                                val = float(node["q"])
                                for k in market_ticks.keys():
                                    if k in p_code or p_code in k:
                                        market_ticks[k].append(val)
                                        if len(market_ticks[k]) > 60:
                                            market_ticks[k].pop(0)
        except Exception:
            await asyncio.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=telegram_worker, daemon=True).start()
    asyncio.run(websocket_worker())
    
