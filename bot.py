import os
import telebot
import google.generativeai as genai

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Welcome to 🤖 MAGNATE AI!\n\nSend a fresh chart screenshot and the bot will return a recommendation: UP, DOWN, or SKIP.")

@bot.message_handler(content_types=['photo'])
def handle_chart_photo(message):
    bot.reply_to(message, "🔄 Analyzing chart screenshot, please wait...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        image_path = "chart.jpg"
        with open(image_path, 'wb') as new_file:
            new_file.write(downloaded_file)

        sample_file = genai.upload_file(image_path)
        prompt = (
            "You are Magnate AI, an expert binary options trading assistant. "
            "Analyze this chart screenshot. Look at the candles, trend, and indicators. "
            "Give a clear recommendation: UP, DOWN, or SKIP, with a short reason."
        )
        response = model.generate_content([sample_file, prompt])
        
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
  
