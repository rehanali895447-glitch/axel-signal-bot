import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
from google import genai
from google.genai import types as genai_types

# 1. Server Setup
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Turbo Bot Live!")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# 2. Setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)

user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "⚡ MAGNATE SNIPER: Send chart for 1-sec signal.", 
                 reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).row("🚀 Start trading"))

@bot.message_handler(func=lambda m: m.text == "🚀 Start trading")
def ask_duration(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⏱️ 1 min", "⏱️ 5 min")
    bot.reply_to(message, "Select Expiry:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["⏱️ 1 min", "⏱️ 5 min"])
def set_duration(message):
    user_data[message.chat.id] = {'duration': message.text}
    bot.reply_to(message, "✅ Set. Send screenshot now.")

def get_signal(file_id, chat_id, msg_id):
    try:
        file_info = bot.get_file(file_id)
        file_bytes = bot.download_file(file_info.file_path)
        
        part = genai_types.Part.from_bytes(data=file_bytes, mime_type="image/jpeg")
        
        # PROMPT एकदम छोटा और घातक
        prompt = "Analyze. Output only: UP or DOWN or SKIP."
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[part, prompt],
            config=genai_types.GenerateContentConfig(max_output_tokens=3, temperature=0.1)
        )
        
        res = response.text.upper()
        
        if "UP" in res:
            card = "🟢 SIGNAL: UP ⬆️"
        elif "DOWN" in res:
            card = "🔴 SIGNAL: DOWN ⬇️"
        else:
            card = "⏸️ SIGNAL: SKIP"
            
        bot.edit_message_text(card, chat_id, msg_id)
    except Exception:
        bot.edit_message_text("❌ Retry...", chat_id, msg_id)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    msg = bot.reply_to(message, "⚡...")
    threading.Thread(target=get_signal, args=(message.photo[-1].file_id, message.chat.id, msg.message_id)).start()

if __name__ == "__main__":
    bot.polling(non_stop=True, skip_pending=True)

