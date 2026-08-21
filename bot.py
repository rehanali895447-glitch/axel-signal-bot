import os
import io
import json
import base64
import requests
import telebot
from telebot import types

# --- Keys Setup (Hardcoded check) ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)

def analyze_chart_process(image_bytes):
    if not OPENROUTER_KEY:
        return "❌ एरर: OPENROUTER_API_KEY सेट नहीं है! Render के Environment में चेक करें।"
    
    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://render.com",
        "X-Title": "MagnateBot"
    }
    
    prompt = (
        "Analyze this chart for 1m candle/2m expiry. Rules: CALL if SAR below price & Stoch <20; PUT if SAR above price & Stoch >80. Else SKIPPED."
        "Format: SIGNAL | CONFIDENCE | REASON"
    )
    
    payload = {
        "model": "google/gemma-2-9b-it:free",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
        ]}],
        "max_tokens": 100,
        "temperature": 0.0
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        res_data = response.json()
        
        # एरर चेकिंग
        if "error" in res_data:
            return f"❌ AI Error: {res_data['error'].get('message', 'Unknown Error')}"
        return res_data["choices"][0]["message"]["content"]
        
    except Exception as e:
        return f"❌ Connection Error: {str(e)}"

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    wait_msg = bot.reply_to(message, "⚡ Analyzing...")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        result = analyze_chart_process(downloaded_file)
        bot.edit_message_text(result, chat_id=message.chat.id, message_id=wait_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=message.chat.id, message_id=wait_msg.message_id)

bot.infinity_polling()
