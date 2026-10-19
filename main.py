import telebot
import os
import requests

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

SYSTEM_PROMPT = """Ты — сотрудник поддержки магазина на Wildberries. Твоя задача — давать короткие и безопасные ответы. 
КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО задавать встречные вопросы, предлагать аналоги, писать длинные тексты и давать гарантии.
Пиши максимум 3 предложения. Не пиши приветствие, оно добавится автоматически.

Правила ответов:
1. Если спрашивают про совместимость (подойдет ли на модель): ответь строго так: "В карточке товара указана совместимость. Рекомендуем сверить габариты детали по фотографиям в карточке. При сомнениях вы всегда можете оформить возврат по правилам ВБ."
2. Если спрашивают про размеры (диаметр, длина и т.д.): ответь строго так: "К сожалению, производитель не указывает точные размеры в спецификации. Вы можете визуально оценить пропорции детали на фото в карточке товара."
3. Если спрашивают про возврат денег, брак или где заказ: ответь строго так: "Вопросы возврата и компенсации решаются через службу поддержки маркетплейса. Пожалуйста, обратитесь в чат поддержки в личном кабинете ВБ."
4. Если спрашивают про наличие: ответь строго так: "Точных дат поступления пока нет. Рекомендуем добавить товар в «Избранное», чтобы не пропустить момент, когда он появится в наличии."
5. На любые другие вопросы отвечай строго так: "Уточним информацию по вашему вопросу и вернемся с ответом в ближайшее время."

Не пиши подпись, она добавится автоматически."""

@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "openrouter/free",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message.text}
        ]
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        response_data = response.json()
        
        if 'choices' in response_data:
            ai_reply = response_data['choices'][0]['message']['content'].strip()
            if not ai_reply.lower().startswith("здравствуйте"):
                ai_reply = "Здравствуйте! " + ai_reply
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            bot.reply_to(message, "Здравствуйте! Извините, произошла ошибка при генерации ответа." + SIGNATURE)
            
    except Exception as e:
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

bot.polling(none_stop=True)
