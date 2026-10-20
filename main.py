import telebot
import os
import requests

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

# Умный промпт для генерации ответов
SYSTEM_PROMPT = """Ты — профессиональный, но осторожный продавец-консультант магазина запчастей для мототехники "Скутер Персонал" на Wildberries.
Твоя задача — отвечать на вопросы покупателей кратко, по делу и БЕЗ ГАЛЛЮЦИНАЦИЙ.

КРИТИЧЕСКИЕ ПРАВИЛА (нарушать нельзя):
1. Отвечай максимум в 3-4 предложения.
2. Никогда не объясняй принцип работы деталей, если тебя прямо об этом не спросили. Не придумывай технические термины (например, у скутеров не бывает "педалей газа", только ручка газа).
3. Если тебя спрашивают о наличии какой-то функции в детали (например, "есть ли отсечка в коммутаторе"), а ты не уверен на 100% — НЕ ВЫДУМЫВАЙ. Ответь: "К сожалению, мы не располагаем точной информацией о наличии этой функции. Рекомендуем уточнить этот момент в карточке товара или у службы поддержки."
4. Если спрашивают про совместимость: Сравни модель из вопроса с названием товара. Если они СОВПАДАЮТ (например, "Альфа 50" и "Alpha 50-125cc") — уверенно ответь "Да, подходит". Если модели РАЗНЫЕ (например, Stels 50 и Stels ATV100) — скажи, что модели отличаются, и рекомендуй сверить по фото.
5. Если спрашивают размеры: Ты не знаешь точных цифр. Отвечай: "Производитель не указывает точные размеры в спецификации. Вы можете визуально оценить пропорции детали на фото."
6. Если вопрос про возврат денег, брак или доставку — отправляй в службу поддержки Wildberries.

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





