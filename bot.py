import os
import io
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
from google import genai
from PIL import Image

# 1. Server Setup
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Magnate AI Online!")

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

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚀 Start trading")
    bot.reply_to(message, "👋 Welcome to MAGNATE AI!\nSend chart screenshot for analysis.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 Start trading")
def start_trading(message):
    user_data[message.chat.id] = {'state': 'WAITING_BALANCE'}
    bot.reply_to(message, "💰 Enter your current balance (e.g. 1000):")

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('state') == 'WAITING_BALANCE')
def save_balance(message):
    try:
        balance = float(message.text.strip())
        user_data[message.chat.id] = {'balance': balance, 'base_stake': balance*0.1, 'step': 0, 'state': 'TRADING'}
        bot.reply_to(message, f"✅ Balance: {balance} USD. Now send chart screenshot.")
    except:
        bot.reply_to(message, "❌ Invalid input.")

def process_image(message, file_path, chat_id):
    try:
        downloaded_file = bot.download_file(file_path)
        img = Image.open(io.BytesIO(downloaded_file))
        img.thumbnail((800, 800))
        
        prompt = "Analyze chart. Recommendation: UP, DOWN or SKIP. Give technical reason."
        
        # यहाँ gemini-3.6-flash अपडेट कर दिया गया है
        response = client.models.generate_content(
            model='gemini-3.6-flash', 
            contents=[img, prompt]
        )
        
        u = user_data.get(chat_id, {'step': 0, 'base_stake': 100})
        if "SKIP" not in response.text.upper():
            u['step'] += 1
            stake = u['base_stake'] * (2.2 ** (u['step'] - 1))
        else:
            stake = u['base_stake']
            
        final_text = f"{response.text}\n\n📊 Step: {u['step']}/15 | Next: {stake:.2f} USD"
        bot.reply_to(message, final_text)
    except Exception as e:
        bot.reply_to(message, f"❌ AI Error: {e}")

@bot.message_handler(content_types=['photo'])
def analyze_chart(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        bot.reply_to(message, "⚠️ Click '🚀 Start trading' first.")
        return
    bot.reply_to(message, "⏳ Analyzing...")
    t = threading.Thread(target=process_image, args=(message, bot.get_file(message.photo[-1].file_id).file_path, chat_id))
    t.start()

bot.polling(non_stop=True, skip_pending=True)

