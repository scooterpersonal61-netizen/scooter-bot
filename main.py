import telebot
import os
import requests

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

SYSTEM_PROMPT = """Ты — профессиональный, но осторожный продавец-консультант магазина запчастей для мототехники "Скутер Персонал" на Wildberries.
Твоя задача — отвечать на вопросы покупателей кратко, по делу и БЕЗ ГАЛЛЮЦИНАЦИЙ.

ПРАВИЛА:
1. Отвечай максимум в 3-4 предложения.
2. Никогда не придумывай технические термины (например, у скутеров не бывает "педалей газа", только ручка газа).
3. Если тебя спрашивают о наличии какой-то функции (например, "есть ли отсечка") или точных размерах, а ты не уверен на 100%, ИСПОЛЬЗУЙ ВЕБ-ПОИСК. Ищи информацию по названию товара и модели в интернете.
4. Если поиск не дал точного ответа, вежливо ответь: "К сожалению, мы не располагаем точной информацией по этой детали."
5. Если спрашивают про совместимость: Сравни модель из вопроса с названием товара. Если они СОВПАДАЮТ — уверенно ответь "Да, подходит". Если модели РАЗНЫЕ — скажи, что модели отличаются, и рекомендуй сверить по фото.
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
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message.text}
        ],
        "plugins": [{"id": "web"}] # ВОТ ЭТА СТРОЧКА ВКЛЮЧАЕТ ПОИСК В ИНТЕРНЕТЕ
    }
    
    try:
        # Ждем до 45 секунд, так как поиск в интернете занимает время
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=45)
        response_data = response.json()
        
        if 'choices' in response_data:
            ai_reply = response_data['choices'][0]['message']['content'].strip()
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

print("БОТ С ВЕБ-ПОИСКОМ ЗАПУЩЕН!")
bot.polling(none_stop=True)
