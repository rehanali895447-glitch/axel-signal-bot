import os
import telebot
import google.generativeai as genai
from PIL import Image
import io

bot = telebot.TeleBot(os.environ["TELEGRAM_BOT_TOKEN"])
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

@bot.message_handler(commands=['start'])
def start(m):
    bot.reply_to(m, "बॉट ऑनलाइन है। फोटो भेजो।")

@bot.message_handler(content_types=['photo'])
def photo(m):
    try:
        file = bot.get_file(m.photo[-1].file_id)
        img = Image.open(io.BytesIO(bot.download_file(file.file_path)))
        res = model.generate_content(["Analyze. SIGNAL: UP/DOWN/SKIP. Reason in 3 words.", img])
        bot.reply_to(m, f"📊 {res.text}")
    except Exception as e:
        bot.reply_to(m, f"Error: {str(e)[:30]}")

bot.infinity_polling()

