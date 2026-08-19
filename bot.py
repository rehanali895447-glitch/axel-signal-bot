import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
import google.generativeai as genai
from PIL import Image

# 1. Simple Web Server (Render Port Binding)
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

# 2. Telegram & Gemini Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Welcome to MAGNATE AI!\nSend a fresh chart screenshot and the bot will analyze it.")

@bot.message_handler(content_types=['photo'])
def handle_chart_photo(message):
    bot.reply_to(message, "⏳ Analyzing chart screenshot, please wait...")
    image_path = "chart.jpg"
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open(image_path, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        img = Image.open(image_path)
        
        prompt = (
            "You are Magnate AI, an expert binary options trading assistant. "
            "Analyze this chart screenshot. Look at the candles, trend, indicators, and support/resistance. "
            "Give a clear recommendation: UP, DOWN, or SKIP, with a short crisp reason."
        )
        
        # ऑटो-मॉडल फॉलबैक ताकि 404 कभी न आए
        response = None
        models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash-8b", "gemini-1.5-pro", "gemini-pro-vision"]
        
        for m in models_to_try:
            try:
                model_inst = genai.GenerativeModel(m)
                response = model_inst.generate_content([img, prompt])
                if response and response.text:
                    break
            except Exception:
                continue
                
        if response and response.text:
            bot.reply_to(message, response.text)
        else:
            bot.reply_to(message, "❌ Chart analysis failed. Please check if API key is active.")

    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

if __name__ == "__main__":
    print("Bot is running...")
    bot.polling(non_stop=True, skip_pending=True)
    
