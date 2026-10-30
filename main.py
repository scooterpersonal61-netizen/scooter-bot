import telebot
import os
import requests
import re

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

SYSTEM_PROMPT = """Ты — дерзкий, но профессиональный эксперт по мототехнике магазина "Скутер Персонал". 
Твоя цель — дать покупателю максимально точный ответ. Ты не имеешь права отмалчиваться.

ЖЕЛЕЗНЫЕ ПРАВИЛА:
1. ЗАПРЕЩЕННЫЕ ФРАЗЫ: "Рекомендуем уточнить в карточке товара", "Обратитесь в службу поддержки Wildberries", "Мы не располагаем точной информацией". Использовать их можно только если вопрос вообще не касается товара (например, про политику).
2. ОБЯЗАТЕЛЬНЫЙ ПОИСК: Если тебя спрашивают о совместимости, размерах, шлицах, конкретной модели или функции детали — ты ОБЯЗАН найти ответ. 
3. СТИЛЬ ОТВЕТА: Отвечай как мастер в гараже. Уверенно, коротко (2-3 предложения). Если нашел инфу на форуме — перескажи её своими словами.
4. ЕСЛИ ПОИСК НЕ ДАЛ РЕЗУЛЬТАТОВ: Напиши прямо: "Точных данных по этой модели в сети нет. Скорее всего, подойдет от аналога, но лучше сверить по фото." Не перекладывай ответственность на поддержку.
5. БЕЗ ССЫЛОК: Никаких http://, https://, .ru, .com. Только текст.

Твоя задача — быть авторитетом, который знает всё о скутерах.
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
                    "max_results": 5,
                    "search_context_size": "high" 
                }
            }
        ],
        "tool_choice": "required" # Заставляем искать в интернете ВСЕГДА
    }
    
    try:
        # Увеличили таймаут, так как поиск занимает время
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        response_data = response.json()
        
        if 'choices' in response_data:
            ai_reply = response_data['choices'][0]['message']['content'].strip()
            
            # Страховка от ссылок: удаляем всё, что похоже на URL или домен
            ai_reply = re.sub(r'http\S+|www\.\S+|[a-zA-Z0-9.-]+\.(ru|com|net|org|info|biz)', '', ai_reply)
            
            # Убираем возможные двойные пробелы после удаления ссылок
            ai_reply = re.sub(r'\s+', ' ', ai_reply).strip()
            
            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            print(f"Ошибка API: {response_data}")
            bot.reply_to(message, "Здравствуйте! Извините, произошла ошибка при поиске информации." + SIGNATURE)
            
    except Exception as e:
        print(f"Ошибка соединения: {e}")
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("БОТ-ЭКСПЕРТ С ОБЯЗАТЕЛЬНЫМ ВЕБ-ПОИСКОМ ЗАПУЩЕН!")
bot.polling(none_stop=True)
