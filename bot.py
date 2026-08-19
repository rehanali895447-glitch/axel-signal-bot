import os
import threading
import io
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
from google import genai
from PIL import Image

# 1. Render Keep-Alive (यह बॉट को 24/7 जगाए रखेगा)
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Magnate Sniper Active!")

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), DummyServer).serve_forever(), daemon=True).start()

# 2. Setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)

# मेमोरी: इसमें आपकी सेटिंग हमेशा याद रहेगी
user_memory = {}

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚀 Start trading")
    bot.reply_to(message, "🧠 MAGNATE TRADER AI (V3.0 - STABLE).\n\nClick start to begin session.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 Start trading")
def setup(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("1 min", "2 min", "3 min", "5 min")
    bot.reply_to(message, "⏱️ Select Expiry:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["1 min", "2 min", "3 min", "5 min"])
def save(message):
    user_memory[message.chat.id] = message.text
    bot.reply_to(message, f"✅ Expiry locked: {message.text}. Send chart!")

def trade_analysis(file_id, chat_id, msg_id):
    try:
        # अगर टाइमिंग नहीं मिली तो डिफ़ॉल्ट 1 min
        duration = user_memory.get(chat_id, "1 min")
        
        file_info = bot.get_file(file_id)
        file_bytes = bot.download_file(file_info.file_path)
        
        img = Image.open(io.BytesIO(file_bytes))
        img.thumbnail((512, 512)) # फास्ट स्कैनिंग के लिए साइज कम
        
        # एआई को ट्रेडर की तरह सोचने पर मजबूर करने वाला प्रॉम्प्ट
        prompt = (
            f"Expiry:{duration}. Analyze trend, candle, and support. "
            "Output strictly: SIGNAL: UP or SIGNAL: DOWN or SIGNAL: SKIP. "
            "Reason: 1 sentence."
        )
        
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=[img, prompt]
        )
        
        res = response.text.upper()
        # क्विक फ़ॉर्मेटिंग
        if "UP" in res: card = f"🟢 SIGNAL: CALL (UP) | {duration}"
        elif "DOWN" in res: card = f"🔴 SIGNAL: PUT (DOWN) | {duration}"
        else: card = f"⏸️ SIGNAL: SKIP | {duration}"
            
        bot.edit_message_text(f"{card}\n\n⚡ {res}", chat_id, msg_id)
        
    except Exception as e:
        bot.edit_message_text("❌ Setup reset. Press /start.", chat_id, msg_id)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if message.chat.id not in user_memory:
        bot.reply_to(message, "⚠️ Press '🚀 Start trading' first!")
        return
    msg = bot.reply_to(message, "⚡ Analyzing...")
    threading.Thread(target=trade_analysis, args=(message.photo[-1].file_id, message.chat.id, msg.message_id)).start()

bot.infinity_polling(skip_pending=True)

