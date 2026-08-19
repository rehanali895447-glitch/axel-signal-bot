import os
import telebot
from google import genai
from PIL import Image
import io

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🚀 Start trading")
    bot.reply_to(message, "⚡ MAGNATE SNIPER: Send chart for 1-sec signal.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🚀 Start trading")
def trading(message):
    bot.reply_to(message, "📸 Now send the chart screenshot!")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.reply_to(message, "⚡ Analyzing...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        file_bytes = bot.download_file(file_info.file_path)
        
        prompt = "Analyze. Only reply: UP or DOWN or SKIP."
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[genai.types.Part.from_bytes(data=file_bytes, mime_type="image/jpeg"), prompt]
        )
        
        res = response.text.upper()
        if "UP" in res: bot.reply_to(message, "🟢 SIGNAL: UP ⬆️")
        elif "DOWN" in res: bot.reply_to(message, "🔴 SIGNAL: DOWN ⬇️")
        else: bot.reply_to(message, "⏸️ SIGNAL: SKIP")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:15]}")

bot.infinity_polling()

