import os
import io
import json
import base64
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot

# --- 1. Render Port Listener (ताकि Render सर्विस को किल न करे) ---
class HealthServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def start_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthServer)
    server.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

# --- 2. Token Reading Logic ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENROUTER_KEY")

if not TELEGRAM_TOKEN:
    print("FATAL ERROR: Telegram Token Not Found in Environment Variables!")

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)

# --- 3. Analysis Function ---
def analyze_chart_process(image_bytes):
    if not OPENROUTER_KEY:
        return "❌ Error: OPENROUTER_API_KEY Missing in Render Environment"

    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://render.com",
        "X-Title": "MagnateBot"
    }
    
    prompt = (
        "You are an expert binary trading analyst. Analyze this 1m chart for a 2m trade.\n"
        "Indicators: Parabolic SAR and Stochastic Oscillator.\n"
        "Rules:\n"
        "- CALL (UP): Parabolic SAR dot is BELOW candle AND Stochastic line is turning UP from <20 zone.\n"
        "- PUT (DOWN): Parabolic SAR dot is ABOVE candle AND Stochastic line is turning DOWN from >80 zone.\n"
        "- SKIPPED: Any conflicting or sideways conditions.\n\n"
        "Output format strictly:\n"
        "🎯 **SIGNAL:** [CALL (UP) 🟢 / PUT (DOWN) 🔴 / SKIPPED ⚪]\n"
        "🔥 **CONFIDENCE:** [Percentage]%\n"
        "⏱ **EXPIRY:** 2 Minutes\n"
        "📊 **INDICATORS:** [SAR & Stoch status]\n"
        "💡 **REASON:** [Direct technical reason]"
    )
    
    payload = {
        "model": "google/gemma-2-9b-it:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 150,
        "temperature": 0.0
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        res_json = res.json()
        if "choices" in res_json:
            return res_json["choices"][0]["message"]["content"]
        elif "error" in res_json:
            return f"❌ AI Error: {res_json['error'].get('message', 'Key issue')}"
        return "❌ Error: Invalid AI Response"
    except Exception as e:
        return f"❌ Connection Error: {str(e)}"

# --- 4. Bot Handlers ---
@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.send_message(
        message.chat.id, 
        "🚀 *Magnate AI (2-Min Expiry)*\n\nचार्ट का स्क्रीनशॉट भेजें।", 
        parse_mode="Markdown"
    )

@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    wait_msg = bot.reply_to(message, "⚡ *Scanning SAR + Stochastic...*", parse_mode="Markdown")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        result = analyze_chart_process(downloaded)
        bot.edit_message_text(result, chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"❌ Processing Error: {str(e)}", chat_id=message.chat.id, message_id=wait_msg.message_id)

if __name__ == "__main__":
    bot.infinity_polling()
    
