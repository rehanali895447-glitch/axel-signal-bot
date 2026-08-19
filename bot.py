import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
from google import genai
from google.genai import types as genai_types

# 1. Server Setup (Keep Alive)
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Alive!")

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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚀 Start trading")
    bot.reply_to(message, "⚡ MAGNATE SNIPER: Send chart for 1-sec signal.", reply_markup=markup)

def get_signal(file_id, chat_id, msg_id):
    try:
        # फोटो डाउनलोड करना
        file_info = bot.get_file(file_id)
        file_bytes = bot.download_file(file_info.file_path)
        
        part = genai_types.Part.from_bytes(data=file_bytes, mime_type="image/jpeg")
        
        # फास्ट एनालिसिस
        prompt = "Analyze chart. Only reply: UP, DOWN or SKIP."
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[part, prompt]
        )
        
        res = response.text.upper()
        
        if "UP" in res: card = "🟢 SIGNAL: UP ⬆️"
        elif "DOWN" in res: card = "🔴 SIGNAL: DOWN ⬇️"
        else: card = "⏸️ SIGNAL: SKIP"
            
        bot.edit_message_text(card, chat_id, msg_id)
    except Exception as e:
        # अब एरर बताएगा कि क्या दिक्कत है
        bot.edit_message_text(f"❌ Error: {str(e)[:20]}", chat_id, msg_id)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    msg = bot.reply_to(message, "⚡ Analyzing...")
    threading.Thread(target=get_signal, args=(message.photo[-1].file_id, message.chat.id, msg.message_id)).start()

if __name__ == "__main__":
    bot.polling(non_stop=True, skip_pending=True)

