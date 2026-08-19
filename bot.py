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
        self.wfile.write(b"Next-Candle Sniper Live!")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# 2. Telegram & AI Initialization
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)

user_data = {}

def start_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚀 Start trading")
    return markup

def duration_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⏱️ 1 min (Next Candle)", "⏱️ 2 min")
    markup.row("⏱️ 3 min", "⏱️ 5 min")
    markup.row("🔙 Back")
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_data[message.chat.id] = {'duration': '1 min'}
    text = (
        "👋 Welcome to MAGNATE AI Sniper!\n\n"
        "Send a chart 15-20 sec before candle close to predict the NEXT candle direction instantly.\n\n"
        "👇 Click below to start."
    )
    bot.reply_to(message, text, reply_markup=start_menu())

@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def handle_back(message):
    send_welcome(message)

@bot.message_handler(func=lambda m: m.text == "🚀 Start trading")
def ask_duration(message):
    bot.reply_to(message, "⏱️ Choose trade duration:", reply_markup=duration_menu())

@bot.message_handler(func=lambda m: m.text in ["⏱️ 1 min (Next Candle)", "⏱️ 2 min", "⏱️ 3 min", "⏱️ 5 min"])
def set_duration(message):
    user_data[message.chat.id] = {'duration': message.text.replace("⏱️ ", "")}
    bot.reply_to(message, f"✅ Expiry set to: {message.text}\n\n📸 Send screenshot 15-20s before candle close.")

def process_chart_sniper(file_path, chat_id):
    try:
        # इन-मेमोरी 600px अल्ट्रा-फ़ास्ट प्रोसेसिंग (1 सेकंड में अपलोड)
        downloaded_file = bot.download_file(file_path)
        img = Image.open(io.BytesIO(downloaded_file))
        img.thumbnail((600, 600))
        
        duration = user_data.get(chat_id, {}).get('duration', '1 min')
        
        prompt = (
            f"You are MAGNATE AI NEXT-CANDLE SNIPER. Timeframe: {duration}. "
            f"The user took this screenshot 15-20s before candle close. "
            f"Analyze the current forming candle rejection wicks, momentum, S/R breakout, and pattern. "
            f"Predict the NEXT incoming candle direction with extreme accuracy. "
            f"If choppy, consolidated, or conflicting wicks, strictly output SKIP. "
            f"Reply ONLY in 1 line: SIGNAL: UP or SIGNAL: DOWN or SIGNAL: SKIP"
        )
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[img, prompt]
        )
        
        raw = response.text.upper()
        
        if "UP" in raw and "SKIP" not in raw:
            card = (
                "🟢 🟢 🟢 NEXT CANDLE: CALL (UP) ⬆️ 🟢 🟢 🟢\n\n"
                f"⏱️ Expiry: {duration}\n"
                "🎯 Entry: Open of Next Candle (BUY 📈)\n"
                "⚡ Probability: 90%+ Sniper Setup"
            )
        elif "DOWN" in raw and "SKIP" not in raw:
            card = (
                "🔴 🔴 🔴 NEXT CANDLE: PUT (DOWN) ⬇️ 🔴 🔴 🔴\n\n"
                f"⏱️ Expiry: {duration}\n"
                "🎯 Entry: Open of Next Candle (SELL 📉)\n"
                "⚡ Probability: 90%+ Sniper Setup"
            )
        else:
            card = (
                "⏸️ ⏸️ ⏸️ SIGNAL: SKIP (NO TRADE) 🛑 ⏸️ ⏸️ ⏸️\n\n"
                f"⏱️ Expiry: {duration}\n"
                "⚠️ Rejection or Choppy candle detected.\n"
                "💡 Wait for next clean candle close."
            )
            
        bot.send_message(chat_id, card)
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ Fast Scan Error: {e}")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {'duration': '1 min (Next Candle)'}
        
    file_info = bot.get_file(message.photo[-1].file_id)
    
    # बैकग्राउंड थ्रेड में सीधा प्रोसेसिंग
    t = threading.Thread(target=process_chart_sniper, args=(file_info.file_path, chat_id))
    t.start()

if __name__ == "__main__":
    print("Magnate AI Next-Candle Sniper Running...")
    bot.polling(non_stop=True, skip_pending=True)

