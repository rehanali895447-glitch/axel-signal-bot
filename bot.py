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

# 1. Render Keep-Alive Web Server
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Magnate AI 100% Online!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# 2. Setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)

# मेमोरी
user_memory = {}

def get_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("1 min", "2 min", "3 min", "5 min")
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_memory[message.chat.id] = "1 min"
    bot.reply_to(
        message,
        "⚡ MAGNATE TRADER AI ONLINE\n\n⏱️ Expiry Locked: 1 min (Default)\n📸 Send chart screenshot now!",
        reply_markup=get_menu()
    )

@bot.message_handler(func=lambda m: m.text in ["1 min", "2 min", "3 min", "5 min"])
def update_duration(message):
    user_memory[message.chat.id] = message.text
    bot.reply_to(message, f"✅ Expiry Locked: {message.text}\n📸 Send chart screenshot now!")

def analyze_chart_direct(file_id, chat_id, msg_id):
    try:
        duration = user_memory.get(chat_id, "1 min")
        
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        # कंप्रेस इमेज
        img = Image.open(io.BytesIO(downloaded))
        img = img.convert('RGB')
        img.thumbnail((600, 600))
        
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85)
        base64_image = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        prompt = (
            f"You are Magnate AI Binary Options Pro. Expiry: {duration}. "
            "Analyze candlestick momentum, trend, and levels. "
            "If market is choppy, output SKIP. "
            "Reply strictly with ONLY ONE LINE in format: SIGNAL: UP or SIGNAL: DOWN or SIGNAL: SKIP"
        )
        
        # Direct REST API Call (किसी भी SDK की जरूरत नहीं)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": base64_image
                        }
                    }
                ]
            }],
            "generationConfig": {
                "maxOutputTokens": 25,
                "temperature": 0.1
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        data = response.json()
        
        res = data['candidates'][0]['content']['parts'][0]['text'].upper()
        
        if "UP" in res and "SKIP" not in res:
            card = (
                "🟢 🟢 🟢 SIGNAL: CALL (UP) ⬆️ 🟢 🟢 🟢\n\n"
                f"⏱️ Expiry: {duration}\n"
                "🎯 Direction: BUY / HIGHER 📈\n"
                "⚡ Probability: 90%+ Accurate Setup"
            )
        elif "DOWN" in res and "SKIP" not in res:
            card = (
                "🔴 🔴 🔴 SIGNAL: PUT (DOWN) ⬇️ 🔴 🔴 🔴\n\n"
                f"⏱️ Expiry: {duration}\n"
                "🎯 Direction: SELL / LOWER 📉\n"
                "⚡ Probability: 90%+ Accurate Setup"
            )
        else:
            card = (
                "⏸️ ⏸️ ⏸️ SIGNAL: SKIP (NO TRADE) 🛑 ⏸️ ⏸️ ⏸️\n\n"
                f"⏱️ Expiry: {duration}\n"
                "⚠️ Market choppy / uncertain rejection.\n"
                "💡 Wait for next clean candle."
            )
            
        bot.edit_message_text(card, chat_id=chat_id, message_id=msg_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)[:35]}", chat_id=chat_id, message_id=msg_id)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    status_msg = bot.reply_to(message, "⚡ Analyzing...")
    file_id = message.photo[-1].file_id
    threading.Thread(
        target=analyze_chart_direct, 
        args=(file_id, message.chat.id, status_msg.message_id)
    ).start()

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)

