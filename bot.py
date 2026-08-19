import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
from google import genai
from google.genai import types as genai_types

# 1. Render Keep-Alive (यह Render को स्लीप होने से रोकता है)
class HealthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Live and Active 24/7!")

def start_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthServer)
    server.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

# 2. Telegram & AI Setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)

@bot.message_handler(commands=['start'])
def start_cmd(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚀 Start trading")
    bot.reply_to(
        message, 
        "⚡ MAGNATE SNIPER AI\n\nSend chart screenshot for instant signal.", 
        reply_markup=markup
    )

@bot.message_handler(func=lambda m: m.text == "🚀 Start trading")
def start_trading(message):
    bot.reply_to(message, "📸 Send chart screenshot now!")

def analyze_image(file_id, chat_id, status_msg_id):
    try:
        file_info = bot.get_file(file_id)
        file_bytes = bot.download_file(file_info.file_path)
        
        part = genai_types.Part.from_bytes(data=file_bytes, mime_type="image/jpeg")
        prompt = "Analyze chart candlestick and levels. Output strictly only 1 word: UP, DOWN or SKIP."
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[part, prompt],
            config=genai_types.GenerateContentConfig(max_output_tokens=5, temperature=0.1)
        )
        
        res = response.text.strip().upper()
        
        if "UP" in res and "SKIP" not in res:
            card = "🟢 🟢 🟢 SIGNAL: CALL (UP) ⬆️ 🟢 🟢 🟢\n\n🎯 Action: BUY / HIGHER\n⚡ Instant 1s Signal"
        elif "DOWN" in res and "SKIP" not in res:
            card = "🔴 🔴 🔴 SIGNAL: PUT (DOWN) ⬇️ 🔴 🔴 🔴\n\n🎯 Action: SELL / LOWER\n⚡ Instant 1s Signal"
        else:
            card = "⏸️ ⏸️ ⏸️ SIGNAL: SKIP (NO TRADE) 🛑 ⏸️ ⏸️ ⏸️\n\n⚠️ Market choppy / uncertain"
            
        bot.edit_message_text(card, chat_id=chat_id, message_id=status_msg_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ Scan Error: {str(e)[:25]}", chat_id=chat_id, message_id=status_msg_id)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    status_msg = bot.reply_to(message, "⚡...")
    file_id = message.photo[-1].file_id
    threading.Thread(target=analyze_image, args=(file_id, message.chat.id, status_msg.message_id)).start()

if __name__ == "__main__":
    print("Bot starting live...")
    bot.infinity_polling(skip_pending=True)

