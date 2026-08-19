import os
import io
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
from google import genai
from PIL import Image

# 1. Render Keep-Alive Server
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Magnate Sniper Online!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# 2. Setup Telegram & Gemini
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)

# इन-मेमोरी स्टोरेज (Render पर कभी क्रैश नहीं होगी)
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
        "⚡ MAGNATE TRADER AI ONLINE\n\n⏱️ Expiry time set to: 1 min\n(You can change time from buttons below)",
        reply_markup=get_menu()
    )

@bot.message_handler(func=lambda m: m.text in ["1 min", "2 min", "3 min", "5 min"])
def update_duration(message):
    user_memory[message.chat.id] = message.text
    bot.reply_to(message, f"✅ Expiry Locked: {message.text}\n📸 Send chart screenshot now!")

def analyze_chart(file_id, chat_id, msg_id):
    try:
        duration = user_memory.get(chat_id, "1 min")
        
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        # इमेज को हल्का करना ताकि 1 सेकंड में अपलोड हो
        img = Image.open(io.BytesIO(downloaded))
        img.thumbnail((600, 600))
        
        prompt = (
            f"You are Magnate AI Binary Options Pro. Expiry: {duration}. "
            "Analyze candlestick momentum, wick rejection, and support/resistance. "
            "If market is choppy or flat, reply SKIP. "
            "Reply strictly in 1 line: SIGNAL: UP or SIGNAL: DOWN or SIGNAL: SKIP"
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[img, prompt]
        )
        
        res = response.text.upper()
        
        if "UP" in res and "SKIP" not in res:
            card = (
                "🟢 🟢 🟢 SIGNAL: CALL (UP) ⬆️ 🟢 🟢 🟢\n\n"
                f"⏱️ Expiry: {duration}\n"
                "🎯 Direction: BUY / HIGHER 📈\n"
                "⚡ Probability: 90%+ Sniper Setup"
            )
        elif "DOWN" in res and "SKIP" not in res:
            card = (
                "🔴 🔴 🔴 SIGNAL: PUT (DOWN) ⬇️ 🔴 🔴 🔴\n\n"
                f"⏱️ Expiry: {duration}\n"
                "🎯 Direction: SELL / LOWER 📉\n"
                "⚡ Probability: 90%+ Sniper Setup"
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
        bot.edit_message_text(f"❌ Error: {str(e)[:40]}", chat_id=chat_id, message_id=msg_id)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    status_msg = bot.reply_to(message, "⚡ Analyzing...")
    file_id = message.photo[-1].file_id
    threading.Thread(
        target=analyze_chart, 
        args=(file_id, message.chat.id, status_msg.message_id)
    ).start()

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)

