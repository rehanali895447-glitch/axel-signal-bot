import os
import io
import json
import base64
import requests
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

# --- 1. Render Keep-Alive Port Binding ---
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Magnate Pro Bot Live!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- 2. Keys & Bot Setup ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)

user_settings = {}

def get_default_settings():
    return {
        "duration": "1 min",
        "indicator": "MACD",
        "strategy": "Optimal (Medium Risk)",
        "asset": "Asia Composite / OTC (85%-90%)"
    }

# --- 3. Keyboards & Menu ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("⏱ Duration", "📊 Indicator", "🛡 Strategy", "⚙️ Current Settings")
    return markup

def duration_menu():
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("1 min", callback_data="dur_1 min"),
        types.InlineKeyboardButton("5 min", callback_data="dur_5 min"),
        types.InlineKeyboardButton("15 min", callback_data="dur_15 min")
    )
    return markup

def indicator_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("MACD", callback_data="ind_MACD"),
        types.InlineKeyboardButton("Stochastic", callback_data="ind_Stochastic"),
        types.InlineKeyboardButton("Bollinger Bands", callback_data="ind_Bollinger Bands"),
        types.InlineKeyboardButton("RSI", callback_data="ind_RSI"),
        types.InlineKeyboardButton("CCI", callback_data="ind_CCI"),
        types.InlineKeyboardButton("Close price", callback_data="ind_Close price")
    )
    return markup

def strategy_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🛡 Conservative (Low Risk)", callback_data="strat_Conservative (Low Risk)"),
        types.InlineKeyboardButton("⚖️ Optimal (Medium Risk)", callback_data="strat_Optimal (Medium Risk)"),
        types.InlineKeyboardButton("⚡ Aggressive (High Risk)", callback_data="strat_Aggressive (High Risk)")
    )
    return markup

# --- 4. Bot Commands & Settings Handlers ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.chat.id
    if user_id not in user_settings:
        user_settings[user_id] = get_default_settings()
    
    st = user_settings[user_id]
    text = (
        f"⚙️ *Active Configuration:*\n"
        f"• ⏱ *Duration:* {st['duration']}\n"
        f"• 📊 *Indicator Focus:* {st['indicator']}\n"
        f"• 🛡 *Strategy:* {st['strategy']}\n"
        f"• 📈 *Asset Target:* {st['asset']}"
    )
    bot.send_message(user_id, text, parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(func=lambda msg: msg.text == "⏱ Duration")
def set_duration(message):
    bot.send_message(message.chat.id, "Select trading duration:", reply_markup=duration_menu())

@bot.message_handler(func=lambda msg: msg.text == "📊 Indicator")
def set_indicator(message):
    bot.send_message(message.chat.id, "Select primary indicator:", reply_markup=indicator_menu())

@bot.message_handler(func=lambda msg: msg.text == "🛡 Strategy")
def set_strategy(message):
    bot.send_message(message.chat.id, "Select strategy risk profile:", reply_markup=strategy_menu())

@bot.message_handler(func=lambda msg: msg.text == "⚙️ Current Settings")
def view_settings(message):
    start_cmd(message)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    user_id = call.message.chat.id
    if user_id not in user_settings:
        user_settings[user_id] = get_default_settings()
    
    data = call.data
    if data.startswith("dur_"):
        val = data.replace("dur_", "")
        user_settings[user_id]["duration"] = val
        bot.answer_callback_query(call.id, f"Duration: {val}")
        bot.send_message(user_id, f"✅ Duration Locked: {val}")
    elif data.startswith("ind_"):
        val = data.replace("ind_", "")
        user_settings[user_id]["indicator"] = val
        bot.answer_callback_query(call.id, f"Indicator: {val}")
        bot.send_message(user_id, f"✅ Indicator Locked: {val}")
    elif data.startswith("strat_"):
        val = data.replace("strat_", "")
        user_settings[user_id]["strategy"] = val
        bot.answer_callback_query(call.id, f"Strategy: {val}")
        bot.send_message(user_id, f"✅ Strategy Locked: {val}")

# --- 5. High-Accuracy AI Analysis Engine (With Auto-Retry) ---
def analyze_chart_process(image_bytes, settings):
    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    
    prompt = (
        f"You are a World-Class High-Accuracy Binary Options Technical Analyst.\n"
        f"Analyze the attached trading chart screenshot carefully.\n"
        f"Settings: Duration={settings.get('duration', '1 min')}, Indicator={settings.get('indicator', 'MACD')}, Strategy={settings.get('strategy', 'Optimal')}.\n\n"
        f"CRITICAL TRADING RULES:\n"
        f"1. Check Trend, S/R Levels, Candlestick Price Action, and Indicator confirmation.\n"
        f"2. If the market is choppy, sideways, uncertain, or indicators show no clear confirmation, YOU MUST OUTPUT 'SKIPPED ⚪'.\n"
        f"3. Only give 'CALL (UP) 🟢' or 'PUT (DOWN) 🔴' if the setup has clear high accuracy.\n\n"
        f"Provide direct output strictly in this clean format:\n"
        f"🎯 **SIGNAL:** [CALL (UP) 🟢 / PUT (DOWN) 🔴 / SKIPPED ⚪]\n"
        f"🔥 **CONFIDENCE:** [Percentage]%\n"
        f"⏱ **TIMEFRAME:** {settings.get('duration', '1 min')}\n"
        f"📈 **TREND & S/R:** [Short analysis of Trend and Support/Resistance level]\n"
        f"💡 **AI REASONING:** [Key reason for trade entry or why it was skipped]"
    )
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": b64_image
                    }
                }
            ]
        }],
        "generationConfig": {
            "maxOutputTokens": 250,
            "temperature": 0.1
        }
    }
    
    headers = {"Content-Type": "application/json"}

    # ऑटो-रीट्राई सिस्टम: सर्वर लोड होने पर खुद 2-3 बार कोशिश करेगा
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=20)
            res_data = response.json()
            if "candidates" in res_data:
                return res_data["candidates"][0]["content"]["parts"][0]["text"]
            elif "error" in res_data and ("demand" in str(res_data["error"]).lower() or "quota" in str(res_data["error"]).lower()):
                time.sleep(2)
                continue
        except Exception:
            time.sleep(2)
            continue
            
    return "❌ Error: AI server busy. Please try again in 1 minute."

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.chat.id
    if user_id not in user_settings:
        user_settings[user_id] = get_default_settings()
    
    wait_msg = bot.reply_to(message, "🧠 *Analyzing Chart with High-Accuracy AI...*", parse_mode="Markdown")
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        result_text = analyze_chart_process(downloaded_file, user_settings[user_id])
        bot.edit_message_text(result_text, chat_id=user_id, message_id=wait_msg.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=user_id, message_id=wait_msg.message_id)

if __name__ == "__main__":
    print("Bot is starting...")
    bot.infinity_polling()
        
