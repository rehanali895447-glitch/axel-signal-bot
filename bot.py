import os
import io
import json
import base64
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

# --- 1. Render Keep-Alive Server ---
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Magnate AI 95% Precision Engine Live!")

def run_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- 2. Keys & Bot Setup ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True)

# --- 3. Strict 2-Min Expiry Analysis Engine ---
def analyze_chart_process(image_bytes):
    b64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://render.com",
        "X-Title": "MagnateBot"
    }
    
    prompt = (
        "You are an Elite Binary Options Bot specialized in 1-Minute Candles with 2-Minute Expiry.\n"
        "Analyze the provided chart image strictly on two indicators: Parabolic SAR and Stochastic Oscillator.\n\n"
        "STRICT EXECUTION RULES:\n"
        "1. CALL (UP 🟢): Valid ONLY if Parabolic SAR dot is BELOW current price candle AND Stochastic is emerging up from Oversold zone (<20).\n"
        "2. PUT (DOWN 🔴): Valid ONLY if Parabolic SAR dot is ABOVE current price candle AND Stochastic is emerging down from Overbought zone (>80).\n"
        "3. SKIPPED ⚪: If market is sideways, Parabolic SAR is flipping rapidly, or Stochastic is hovering neutrally (between 30-70) without clear extreme reversal.\n\n"
        "Format output clearly and strictly as:\n"
        "🎯 **SIGNAL:** [CALL (UP) 🟢 / PUT (DOWN) 🔴 / SKIPPED ⚪]\n"
        "🔥 **ACCURACY:** [Percentage]%\n"
        "⏱ **EXPIRY:** 2 Minutes (1m Candle)\n"
        "📊 **SAR & STOCH:** [Exact reading of SAR position and Stochastic %K/%D zone]\n"
        "💡 **TECHNICAL CONFIRMATION:** [Direct reason for entry or skip]"
    )
    
    payload = {
        "model": "google/gemma-4-31b-it:free",
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
        "max_tokens": 250,
        "temperature": 0.0
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        res_data = response.json()
        if "choices" in res_data:
            return res_data["choices"][0]["message"]["content"]
        else:
            return f"❌ Error: {res_data.get('error', {}).get('message', 'Key issue')}"
    except Exception as e:
        return f"❌ Error: {str(e)}"

# --- 4. Handlers ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    welcome_text = (
        "🚀 *Magnate AI Pro (2-Min Expiry Engine)*\n\n"
        "📊 *Active Strategy:* Parabolic SAR + Stochastic Dual-Filter\n"
        "🕯 *Chart Timeframe:* 1 Minute\n"
        "⏱ *Trade Expiry:* 2 Minutes\n\n"
        "📸 *बस अपने ट्रेडिंग चार्ट का स्क्रीनशॉट भेजें और तुरंत सिग्नल पाएं!*"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    wait_msg = bot.reply_to(message, "⚡ *Scanning SAR + Stochastic Levels...*", parse_mode="Markdown")
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        result_text = analyze_chart_process(downloaded_file)
        bot.edit_message_text(result_text, chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"❌ Error: {str(e)}", chat_id=message.chat.id, message_id=wait_msg.message_id)

if __name__ == "__main__":
    bot.infinity_polling()
    
