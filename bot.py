import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
import google.generativeai as genai
from PIL import Image

# 1. Web Port Server
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running Alive 24/7!")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# 2. Gemini & Bot Setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

# यहाँ मॉडल का नाम 'gemini-1.5-flash-latest' सेट किया है
model = genai.GenerativeModel("gemini-1.5-flash-latest")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Welcome to MAGNATE AI!\nSend a fresh chart screenshot and the bot will analyze it.")

@bot.message_handler(content_types=['photo'])
def handle_chart_photo(message):
    bot.reply_to(message, "⏳ Analyzing chart screenshot, please wait...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        image_path = "chart.jpg"
        with open(image_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        img = Image.open(image_path)
        
        prompt = (
            "You are Magnate AI, an expert binary options trading assistant. "
            "Analyze this chart screenshot. Look at the candles, trend, and indicators. "
            "Give a clear recommendation: UP, DOWN, or SKIP, with a short reason."
        )
        
        response = model.generate_content([img, prompt])
        
        bot.reply_to(message, response.text)
        
        if os.path.exists(image_path):
            os.remove(image_path)

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
    
