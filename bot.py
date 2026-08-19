import os
import telebot
import google.generativeai as genai
from PIL import Image
import io

# 1. API Keys (ये Render के Environment Variables में होने चाहिए)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# 2. Setup
genai.configure(api_key=GEMINI_KEY)
# 'gemini-1.5-flash' सबसे स्टेबल मॉडल है
model = genai.GenerativeModel('gemini-1.5-flash')
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "⚡ मैग्नेट एआई एक्टिव है। बस चार्ट का स्क्रीनशॉट भेजो, मैं सिग्नल दूँगा।")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        # फोटो डाउनलोड
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        img = Image.open(io.BytesIO(downloaded))
        
        # प्रॉम्प्ट - साफ़ और छोटा
        prompt = "Analyze this chart. Reply strictly with: SIGNAL: UP or SIGNAL: DOWN or SIGNAL: SKIP. Give a reason in 3 words."
        
        # एआई एनालिसिस
        response = model.generate_content([prompt, img])
        
        # रिप्लाई
        bot.reply_to(message, response.text)
        
    except Exception as e:
        bot.reply_to(message, f"❌ एरर आया: {str(e)[:50]}")

print("बॉट चालू हो गया...")
bot.polling(non_stop=True)

