import telebot
import os
import requests

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

# Умный промпт для генерации ответов
SYSTEM_PROMPT = """Ты — опытный, вежливый и тактичный продавец-консультант магазина запчастей для мототехники "Скутер Персонал" на Wildberries.
Твоя задача — генерировать ответы на вопросы покупателей.

Правила:
1. Отвечай кратко, по делу. Максимум 3-4 предложения.
2. Всегда будь вежлив.
3. Если спрашивают про совместимость: Сначала внимательно посмотри на название товара в вопросе. Если модель в вопросе покупателя СОВПАДАЕТ с моделью в названии товара (например, в вопросе "на Альфу", а товар "на мопед Alpha"), то уверенно ответь: "Да, этот товар подходит на вашу модель." Если модели разные или покупатель сомневается — вежливо скажи, что в карточке указана совместимость, и предложи сверить по фото.
4. Если спрашивают точные размеры (диаметр, длина): Если ты не знаешь точных цифр (а ты их не знаешь, если это не общеизвестный факт), вежливо скажи, что производитель не указывает точные размеры, и предложи ориентироваться на фото.
5. Если спрашивают про возврат денег, брак, где заказ: Отправляй в службу поддержки Wildberries.
6. Если спрашивают про наличие: Не обещай точных сроков, предложи добавить в избранное.
7. Если вопрос странный или не по теме — вежливо предложи уточнить вопрос.

Не пиши приветствие и подпись, они добавятся автоматически.
"""

@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openrouter/free", # Используем умный бесплатный роутер
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message.text}
        ]
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
        response_data = response.json()
        
        if 'choices' in response_data:
            ai_reply = response_data['choices'][0]['message']['content'].strip()
            # Страховка: добавляем "Здравствуйте!" если ИИ забыл
            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            # Если бесплатная модель перегружена, выдаем вежливую заглушку
            bot.reply_to(message, "Здравствуйте! Уточним информацию по вашему вопросу и вернемся с ответом в ближайшее время." + SIGNATURE)
            
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("БОТ-ГЕНЕРАТОР ЗАПУЩЕН!")
bot.polling(none_stop=True)





