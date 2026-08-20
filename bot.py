import os
import io
import json
import base64
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
from PIL import Image

# --- 1. Render Keep-Alive Port Binding (No Deploy Fail) ---
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

# --- 2. Bot & Gemini Setup ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)

# डिफ़ॉल्ट सेटिंग्स (App UI के अनुसार)
user_settings = {}

def get_default_settings():
    return {
        "duration": "1 min",
        "indicator": "MACD",
        "strategy": "Optimal (Medium Risk)",
        "asset": "Asia Composite / OTC (85%-90%)"
    }

# --- मेन्यू कीबोर्ड्स ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("⏱️ Duration", "📊 Indicator", "🛡️ Strategy", "⚙️ Current Settings")
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
        types.InlineKeyboardButton("🛡️ Conservative (Low Risk)", callback_data="strat_Conservative (Low Risk)"),
        types.InlineKeyboardButton("♞ Optimal (Medium Risk)", callback_data="strat_Optimal (Medium Risk)"),
        types.InlineKeyboardButton("⚡ Aggressive (High Risk)", callback_data="strat_Aggressive (High Risk)")
    )
    return markup

# --- कमांड्स और बटन्स ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_settings[message.chat.id] = get_default_settings()
    text = (
        "🤖 **MAGNATE ROBOT PRO ONLINE**\n\n"
        "📱 **Current Robot Settings:**\n"
        f"⏱️ Duration: `1 min`\n"
        f"📊 Indicator: `MACD`\n"
        f"♞ Strategy: `Optimal (Medium risk)`\n\n"
        "📸 **बस चार्ट का स्क्रीनशॉट भेजें, बॉट तुरंत सिग्नल देगा!**"
    )
    bot.reply_to(message, text, reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "⏱️ Duration")
def set_duration(message):
    bot.reply_to(message, "⏱️ **Select Trading Duration:**", reply_markup=duration_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📊 Indicator")
def set_indicator(message):
    bot.reply_to(message, "📊 **Select Technical Indicator:**", reply_markup=indicator_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🛡️ Strategy")
def set_strategy(message):
    bot.reply_to(message, "🛡️ **Select Risk Management Strategy:**", reply_markup=strategy_menu(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "⚙️ Current Settings")
def view_settings(message):
    cfg = user_settings.get(message.chat.id, get_default_settings())
    text = (
        "⚙️ **Active Configuration:**\n"
        f"• ⏱️ **Duration:** {cfg['duration']}\n"
        f"• 📊 **Indicator Focus:** {cfg['indicator']}\n"
        f"• 🛡️ **Strategy:** {cfg['strategy']}\n"
        f"• 📈 **Asset Target:** {cfg['asset']}"
    )
    bot.reply_to(message, text, parse_mode="Markdown")

# --- इनलाइन बटन्स हैंडलर ---
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message.chat.id not in user_settings:
        user_settings[call.message.chat.id] = get_default_settings()
        
    if call.data.startswith("dur_"):
        val = call.data.split("_")[1]
        user_settings[call.message.chat.id]["duration"] = val
        bot.answer_callback_query(call.id, f"Duration set: {val}")
        bot.edit_message_text(f"✅ Duration Locked: **{val}**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        
    elif call.data.startswith("ind_"):
        val = call.data.split("_")[1]
        user_settings[call.message.chat.id]["indicator"] = val
        bot.answer_callback_query(call.id, f"Indicator set: {val}")
        bot.edit_message_text(f"✅ Indicator Locked: **{val}**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        
    elif call.data.startswith("strat_"):
        val = call.data.split("_")[1]
        user_settings[call.message.chat.id]["strategy"] = val
        bot.answer_callback_query(call.id, f"Strategy set: {val}")
        bot.edit_message_text(f"✅ Strategy Locked: **{val}**", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

# --- चार्ट एनालिसिस और सिग्नल जनरेटर ---
def analyze_chart_process(file_id, chat_id, msg_id):
    try:
        cfg = user_settings.get(chat_id, get_default_settings())
        
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        img = Image.open(io.BytesIO(downloaded)).convert('RGB')
        img.thumbnail((600, 600))
        
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        base64_image = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        prompt = (
            f"You are Magnate AI Pro Binary Options Robot. "
            f"Active Settings: Expiry={cfg['duration']}, Technical Indicator Focus={cfg['indicator']}, Strategy Mode={cfg['strategy']}. "
            "Analyze candlestick momentum, trend direction, support/resistance, and indicator behavior on this chart. "
            "Strict Rule: If market is choppy/unclear, reply SKIP. "
            "Reply strictly in this EXACT format:\n"
            "SIGNAL: [UP or DOWN or SKIP]\n"
            "CONFIDENCE: [Percentage like 92%]\n"
            "ANALYSIS: [Short 1-sentence reason]"
        )
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": base64_image}}
                ]
            }],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 100}
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        data = response.json()
        
        raw_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
        lines = raw_text.split("\n")
        
        signal = "SKIP"
        conf = "85%"
        reason = "Market consolidating"
        
        for line in lines:
            if "SIGNAL:" in line.upper():
                if "UP" in line.upper(): signal = "CALL (UP) ⬆️"
                elif "DOWN" in line.upper(): signal = "PUT (DOWN) ⬇️"
                else: signal = "SKIP (NO TRADE) 🛑"
            elif "CONFIDENCE:" in line.upper():
                conf = line.split(":")[-1].strip()
            elif "ANALYSIS:" in line.upper():
                reason = line.split(":")[-1].strip()

        if "UP" in signal:
            card = (
                "🟢 🟢 🟢 **MAGNATE ROBOT SIGNAL** 🟢 🟢 🟢\n\n"
                f"🎯 **Direction:** `BUY / CALL 📈`\n"
                f"⏱️ **Duration:** `{cfg['duration']}`\n"
                f"📊 **Indicator:** `{cfg['indicator']}`\n"
                f"🛡️ **Strategy:** `{cfg['strategy']}`\n"
                f"⚡ **Confidence:** `{conf}`\n\n"
                f"💡 **Reason:** {reason}"
            )
        elif "DOWN" in signal:
            card = (
                "🔴 🔴 🔴 **MAGNATE ROBOT SIGNAL** 🔴 🔴 🔴\n\n"
                f"🎯 **Direction:** `SELL / PUT 📉`\n"
                f"⏱️ **Duration:** `{cfg['duration']}`\n"
                f"📊 **Indicator:** `{cfg['indicator']}`\n"
                f"🛡️ **Strategy:** `{cfg['strategy']}`\n"
                f"⚡ **Confidence:** `{conf}`\n\n"
                f"💡 **Reason:** {reason}"
            )
        else:
            card = (
                "⏸️ ⏸️ ⏸️ **MAGNATE ROBOT: SKIP** ⏸️ ⏸️ ⏸️\n\n"
                f"⏱️ **Duration:** `{cfg['duration']}`\n"
                f"⚠️ **Market Choppy / Low Accuracy Setup**\n"
                f"💡 **Reason:** {reason}\n"
                "🛑 **Next clear candle ka wait karein.**"
            )
            
        bot.edit_message_text(card, chat_id=chat_id, message_id=msg_id, parse_mode="Markdown")
        
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)[:45]}", chat_id=chat_id, message_id=msg_id)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    status_msg = bot.reply_to(message, "⚡ **Scanning Chart with Magnate AI Engine...**", parse_mode="Markdown")
    file_id = message.photo[-1].file_id
    threading.Thread(
        target=analyze_chart_process, 
        args=(file_id, message.chat.id, status_msg.message_id)
    ).start()

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)
        
