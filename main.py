import os
import telebot
import anthropic

bot = telebot.TeleBot(os.environ["TELEGRAM_TOKEN"])
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

@bot.message_handler(func=lambda message: True)
def handle(message):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": message.text}]
    )
    bot.reply_to(message, response.content[0].text)

bot.polling()
