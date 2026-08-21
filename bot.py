import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import google.generativeai as genai

# Render की Environment settings से कीज़ उठाना
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# सेटअप
genai.configure(api_key=GOOGLE_API_KEY)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# AI का सिस्टम इंस्ट्रक्शन
SYSTEM_INSTRUCTION = """
You are an expert binary options trading analyst. Analyze the provided chart screenshot.
Rules:
1. If the trend is clearly UP, reply with: "⬆️ UP - [Brief reason]"
2. If the trend is clearly DOWN, reply with: "⬇️ DOWN - [Brief reason]"
3. If the market is uncertain or sideways, reply with: "⏭️ SKIP - [Brief reason]"
Output only the signal and the reason. No extra text.
"""

# Gemini 1.5 Pro (आपके प्रो प्लान की पावर)
model = genai.GenerativeModel('gemini-1.5-pro', system_instruction=SYSTEM_INSTRUCTION)

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Trading Bot Ready! Send me a screenshot of your chart to analyze. 📊")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_data = await bot.download_file(file.file_path)
    
    try:
        # AI को फोटो और निर्देश भेजना
        response = model.generate_content([
            {"mime_type": "image/jpeg", "data": file_data.read()},
            "Analyze this chart now."
        ])
        
        # सिग्नल रिस्पॉन्स
        await message.reply(f"📈 **Analysis Result:**\n\n{response.text}")
        await message.answer("Waiting for the next chart... 📊")
        
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

async def main():
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
    
