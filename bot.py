import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types
from google import genai
from PIL import Image

# 1. Render Web Server Binding
class DummyServer(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Magnate AI Bot Live 24/7!")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyServer)
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# 2. Telegram & AI Setup
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=False)

user_data = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🚀 Start trading")
    return markup

def duration_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("⏱️ 1 minute", "⏱️ 3 minutes", "⏱️ 5 minutes")
    markup.row("🔙 Back")
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 Welcome to MAGNATE AI!\n\n"
        "Send a fresh candlestick-chart screenshot and the bot will return a "
        "probability-based recommendation: UP, DOWN, or SKIP.\n\n"
        "👇 Choose an option from the menu below."
    )
    bot.reply_to(message, welcome_text, reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def handle_back(message):
    user_data[message.chat.id] = {'state': 'IDLE'}
    send_welcome(message)

@bot.message_handler(func=lambda m: m.text == "🚀 Start trading")
def start_trading(message):
    user_data[message.chat.id] = {'state': 'WAITING_BALANCE'}
    msg = (
        "Set your balance before requesting a signal.\n\n"
        "💰 Enter your current balance. Example: 1000"
    )
    bot.reply_to(message, msg)

@bot.message_handler(func=lambda m: user_data.get(m.chat.id, {}).get('state') == 'WAITING_BALANCE')
def save_balance(message):
    try:
        balance = float(message.text.replace('$', '').replace(',', '').strip())
        base_stake = balance * 0.10
        user_data[message.chat.id] = {
            'balance': balance,
            'base_stake': base_stake,
            'step': 0,
            'wins': 0,
            'losses': 0,
            'net_result': 0.0,
            'state': 'SELECTING_DURATION'
        }
        
        bankroll_card = (
            "✅ Balance saved and the Martingale cycle was reset.\n\n"
            "💰 BANKROLL & MONEY MANAGEMENT\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Balance: {balance:,.2f} USD\n"
            "Platform payout: 92%\n"
            "Base stake: 10%\n"
            "Martingale step: BASE · 0/15\n"
            f"Cycle profit target: {base_stake * 0.92:,.2f} USD\n\n"
            f"🎯 Next stake: {base_stake:,.2f} USD\n"
            "Share of current balance: 10%\n\n"
            "Statistics: ✅ 0 · ❌ 0\n"
            "Net result: 0.00 USD\n\n"
            "⚠️ Large-stake limits are disabled. The bot stops the cycle only after step 15 or when the required stake exceeds the balance."
        )
        bot.reply_to(message, bankroll_card)
        bot.send_message(message.chat.id, "Choose the forecast duration:", reply_markup=duration_menu())
    except ValueError:
        bot.reply_to(message, "❌ Invalid number. Please enter only numbers (e.g. 1000).")

@bot.message_handler(func=lambda m: m.text in ["⏱️ 1 minute", "⏱️ 3 minutes", "⏱️ 5 minutes"])
def handle_duration(message):
    if message.chat.id not in user_data or 'balance' not in user_data[message.chat.id]:
        user_data[message.chat.id] = {'state': 'WAITING_BALANCE'}
        bot.reply_to(message, "⚠️ Please set your balance first.\n💰 Enter balance (e.g. 1000):")
        return
        
    user_data[message.chat.id]['duration'] = message.text
    user_data[message.chat.id]['state'] = 'AWAITING_CHART'
    bot.reply_to(message, f"✅ Duration set to {message.text}.\n\n📸 Now send a fresh chart screenshot.")

@bot.message_handler(content_types=['photo'])
def analyze_chart(message):
    chat_id = message.chat.id
    if chat_id not in user_data or 'balance' not in user_data[chat_id]:
        bot.reply_to(message, "⚠️ Set your balance before requesting a signal.\nClick 🚀 Start trading below.", reply_markup=main_menu())
        return

    bot.reply_to(message, "⏳ Analyzing chart screenshot, please wait...")
    image_path = f"chart_{chat_id}.jpg"
    
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open(image_path, 'wb') as f:
            f.write(downloaded_file)
            
        img = Image.open(image_path)
        duration = user_data[chat_id].get('duration', '1 minute')
        
        prompt = (
            f"You are MAGNATE AI, an institutional-grade binary options forecasting bot. "
            f"Forecast duration: {duration}. "
            f"Analyze the candlestick patterns, support/resistance, momentum, and indicators in this chart screenshot. "
            f"If market is choppy, flat, consolidating, or lacks a clear setup, strictly choose SKIP. "
            f"Format response strictly as:\n"
            f"Based on the chart analysis, here is your recommendation:\n\n"
            f"• Recommendation: UP / DOWN / SKIP\n"
            f"• Reason: 2-3 sentences explaining market conditions, key levels, and indicators."
        )
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[img, prompt]
        )
        
        res_text = response.text.replace('*', '') # Format conflict clear
        u = user_data[chat_id]
        
        if "SKIP" in res_text.upper():
            stake_info = (
                f"\n━━━━━━━━━━━━━━━━━━━━\n"
                f"⏸️ Status: Trade Skipped (No Clear Pattern)\n"
                f"🎯 Next Stake: {u['base_stake']:,.2f} USD\n"
                f"📊 Martingale Step: Hold ({u['step']}/15)\n"
                f"💡 Wait for next clean setup or change asset."
            )
        else:
            u['step'] += 1
            current_stake = u['base_stake'] * (2.2 ** (u['step'] - 1))
            stake_info = (
                f"\n━━━━━━━━━━━━━━━━━━━━\n"
                f"🎯 Next Stake: {current_stake:,.2f} USD\n"
                f"📊 Martingale Step: {u['step']}/15\n"
                f"⏱️ Expiry: {duration}"
            )
            
        bot.reply_to(message, f"{res_text}\n{stake_info}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ AI Error: {e}")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

if __name__ == "__main__":
    print("Magnate AI Bot running...")
    bot.polling(non_stop=True, skip_pending=True)

