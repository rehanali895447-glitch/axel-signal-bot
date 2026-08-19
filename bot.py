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
        self.wfile.write(b"Magnate AI Fast Live!")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# 2. Telegram & AI Setup
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
    markup.row("⏱️ 1 min", "⏱️ 2 min")
    markup.row("⏱️ 3 min", "⏱️ 5 min")
    markup.row("🔙 Back")
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_data[message.chat.id] = {'duration': '1 min'}
    text = (
        "👋 Welcome to MAGNATE AI!\n\n"
        "Send a fresh candlestick chart screenshot to get instant probability signals (UP / DOWN / SKIP).\n\n"
        "👇 Click below to start."
    )
    bot.reply_to(message, text, reply_markup=start_menu())

@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def handle_back(message):
    send_welcome(message)

@bot.message_handler(func=lambda m: m.text == "🚀 Start trading")
def ask_duration(message):
    bot.reply_to(message, "⏱️ Choose the forecast duration:", reply_markup=duration_menu())

@bot.message_handler(func=lambda m: m.text in ["⏱️ 1 min", "⏱️ 2 min", "⏱️ 3 min", "⏱️ 5 min"])
def set_duration(message):
    user_data[message.chat.id] = {'duration': message.text.replace("⏱️ ", "")}
    bot.reply_to(message, f"✅ Expiry set to: {message.text}\n\n📸 Now send chart screenshot.")

def process_chart_fast(message, file_path, chat_id):
    try:
        downloaded_file = bot.download_file(file_path)
        img = Image.open(io.BytesIO(downloaded_file))
        img.thumbnail((700, 700))
        
        duration = user_data.get(chat_id, {}).get('duration', '1 min')
        
        prompt = (
            f"You are MAGNATE AI, expert binary options scanner. Expiry: {duration}. "
            f"Analyze raw candlestick action, trend momentum, and key levels. "
            f"Strictly reply in this short 3-line format without markdown asterisks:\n"
            f"SIGNAL: [UP or DOWN or SKIP]\n"
            f"CONFIDENCE: [e.g. 90%]\n"
            f"REASON: [Single short 1-line reason]"
        )
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[img, prompt]
        )
        
        raw = response.text.upper()
        
        # क्लीन और बड़ा सिग्नल कार्ड तैयार करना
        if "UP" in raw and "SKIP" not in raw:
            card = (
                f"🟢 🟢 🟢 SIGNAL: CALL (UP) ⬆️ 🟢 🟢 🟢\n\n"
                f"⏱️ Expiry: {duration}\n"
                f"🎯 Direction: BUY / UP 📈\n"
                f"⚡ Status: High Probability Setup"
            )
        elif "DOWN" in raw and "SKIP" not in raw:
            card = (
                f"🔴 🔴 🔴 SIGNAL: PUT (DOWN) ⬇️ 🔴 🔴 🔴\n\n"
                f"⏱️ Expiry: {duration}\n"
                f"🎯 Direction: SELL / DOWN 📉\n"
                f"⚡ Status: High Probability Setup"
            )
        else:
            card = (
                f"⏸️ ⏸️ ⏸️ SIGNAL: SKIP ⚠️ ⏸️ ⏸️ ⏸️\n\n"
                f"⏱️ Expiry: {duration}\n"
                f"🎯 Action: DO NOT TRADE 🛑\n"
                f"💡 Market is choppy or uncertain. Wait for next candle."
            )
            
        bot.reply_to(message, card)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Scan Error: {e}")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        user_data[chat_id] = {'duration': '1 min'}
        
    bot.reply_to(message, "⚡ Scanning chart...")
    file_info = bot.get_file(message.photo[-1].file_id)
    
    t = threading.Thread(target=process_chart_fast, args=(message, file_info.file_path, chat_id))
    t.start()

if __name__ == "__main__":
    print("Magnate AI Pro Running...")
    bot.polling(non_stop=True, skip_pending=True)

