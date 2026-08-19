import os
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
from google import genai
from google.genai import types as genai_types

# 1. Render Keep-Alive (यह बॉट को 24/7 चालू रखेगा)
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Turbo Trader Active!")

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', int(os.environ.get("PORT", 8080))), DummyServer).serve_forever(), daemon=True).start()

# 2. Setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)

# Memory (याददाश्त फाइल)
DB_FILE = "trader_memory.json"

def get_mem():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {}

def set_mem(chat_id, duration):
    mem = get_mem()
    mem[str(chat_id)] = duration
    with open(DB_FILE, "w") as f: json.dump(mem, f)

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚀 Start trading")
    bot.reply_to(message, "⚡ MAGNATE TURBO AI ONLINE.\n\nI am ready to analyze market sentiment.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🚀 Start trading")
def setup(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("1 min", "2 min", "3 min", "5 min")
    bot.reply_to(message, "⏱️ Select Expiry:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["1 min", "2 min", "3 min", "5 min"])
def save(message):
    set_mem(message.chat.id, message.text)
    bot.reply_to(message, f"✅ Time locked: {message.text}. Send chart!")

def fast_analyze(file_id, chat_id, msg_id):
    try:
        mem = get_mem()
        dur = mem.get(str(chat_id), "1 min")
        
        file_info = bot.get_file(file_id)
        file_bytes = bot.download_file(file_info.file_path)
        
        # PROMPT: ट्रेडर की समझदारी + रफ़्तार
        prompt = f"Time:{dur}. Analyze momentum & trend. Output ONLY: UP or DOWN or SKIP. Reason: 3 words max."
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[genai_types.Part.from_bytes(data=file_bytes, mime_type="image/jpeg"), prompt],
            config=genai.GenerateContentConfig(max_output_tokens=30, temperature=0.1)
        )
        
        res = response.text.upper()
        # फॉर्मेटिंग
        if "UP" in res: card = "🟢 UP"
        elif "DOWN" in res: card = "🔴 DOWN"
        else: card = "⏸️ SKIP"
            
        bot.edit_message_text(f"{card} | {dur}\n⚡ {res.replace('SIGNAL:', '')}", chat_id, msg_id)
    except:
        bot.edit_message_text("❌ Network lag. Resend chart.", chat_id, msg_id)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    msg = bot.reply_to(message, "⚡...")
    threading.Thread(target=fast_analyze, args=(message.photo[-1].file_id, message.chat.id, msg.message_id)).start()

bot.infinity_polling()

