import telebot
import os
import requests

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

SYSTEM_PROMPT = """Ты — профессиональный продавец-консультант магазина запчастей для мототехники "Скутер Персонал" на Wildberries.
Твоя задача — отвечать на вопросы покупателей кратко и точно.

КРИТИЧЕСКИЕ ПРАВИЛА:
1. Отвечай максимум в 3-4 предложения.
2. СТРОГО ЗАПРЕЩЕНО писать любые ссылки на сайты (URL, http://, https://, домены вроде .ru, .com). Мы работаем на Wildberries, здесь нельзя отправлять внешние ссылки. Если ты нашел информацию в интернете, перескажи её СВОИМИ СЛОВАМИ без ссылок.
3. Если тебя спрашивают о наличии функции (например, "есть ли отсечка"), ОБЯЗАТЕЛЬНО используй инструмент веб-поиска. 
4. Если поиск в интернете не дал точного ответа, вежливо ответь: "К сожалению, мы не располагаем точной информацией по этой детали. Рекомендуем уточнить этот момент в карточке товара или у службы поддержки."
5. Если спрашивают про совместимость: Сравни модель из вопроса с названием товара. Если они СОВПАДАЮТ — уверенно ответь "Да, подходит". Если модели РАЗНЫЕ — скажи, что модели отличаются, и рекомендуй сверить по фото.
6. Если вопрос про возврат денег, брак или доставку — отправляй в службу поддержки Wildberries.
7. Никогда не придумывай технические термины (например, у скутеров не бывает "педалей газа").

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
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message.text}
        ],
        "tools": [
            {
                "type": "openrouter:web_search",
                "parameters": {
                    "max_results": 3
                }
            }
        ]
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        response_data = response.json()
        
        if 'choices' in response_data:
            ai_reply = response_data['choices'][0]['message']['content'].strip()
            
            # Страховка от ссылок: если нейросеть вдруг забыла правило
            import re
            ai_reply = re.sub(r'http\S+', '', ai_reply) # Удаляет все http ссылки
            
            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            print(f"Ошибка API: {response_data}")
            bot.reply_to(message, "Здравствуйте! Уточним информацию по вашему вопросу и вернемся с ответом в ближайшее время." + SIGNATURE)
            
    except Exception as e:
        print(f"Ошибка соединения: {e}")
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("БОТ С ПОИСКОМ (БЕЗ ССЫЛОК) ЗАПУЩЕН!")
bot.polling(none_stop=True)
