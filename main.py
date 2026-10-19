import telebot
import os
import requests
import base64

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

# --- БАЗА ЗНАНИЙ (ШПАРГАЛКА) ---
# Сюда мы будем вписывать точные данные товаров.
KNOWLEDGE_BASE = """
- Сепаратор пальца 12 мм на скутер Stels 50cc: внешний диаметр 18 мм, внутренний 12 мм.
- Блоки кнопок руля Zongshen F5: подходят на моторы MN172 300cc.
- Карбюратор PZ19: в комплекте идет дроссельная заслонка и игла.
"""

SYSTEM_PROMPT = f"""Ты — сотрудник поддержки магазина на Wildberries. Твоя задача — давать короткие и безопасные ответы. 
КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО задавать встречные вопросы и писать длинные тексты.
Пиши максимум 3 предложения. Не пиши приветствие, оно добавится автоматически.

Вот база знаний по нашим товарам (используй её, если вопрос совпадает):
{KNOWLEDGE_BASE}

Правила ответов:
1. Если спрашивают про товар из базы знаний — дай точный ответ из базы.
2. Если спрашивают про совместимость, но товара нет в базе — ответь: "В карточке товара указана совместимость. Рекомендуем сверить габариты детали по фотографиям в карточке. При сомнениях вы всегда можете оформить возврат по правилам ВБ."
3. Если спрашивают про размеры, но товара нет в базе — ответь: "К сожалению, производитель не указывает точные размеры в спецификации. Вы можете визуально оценить пропорции детали на фото в карточке товара."
4. Если спрашивают про возврат денег, брак или где заказ — ответь: "Вопросы возврата и компенсации решаются через службу поддержки маркетплейса. Пожалуйста, обратитесь в чат поддержки в личном кабинете ВБ."
5. Если спрашивают про наличие — ответь: "Точных дат поступления пока нет. Рекомендуем добавить товар в «Избранное», чтобы не пропустить момент, когда он появится в наличии."
6. На любые другие вопросы — ответь: "Уточним информацию по вашему вопросу и вернемся с ответом в ближайшее время."
"""

def ask_ai(messages):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "google/gemini-flash-1.5", # Эта модель умеет видеть картинки
        "messages": messages
    }
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=40)
        response_data = response.json()
        if 'choices' in response_data:
            return response_data['choices'][0]['message']['content'].strip()
        else:
            print(f"Ошибка API: {response_data}")
            return "Извините, произошла ошибка при генерации ответа."
    except Exception as e:
        print(f"Ошибка соединения: {e}")
        return "Извините, сервис временно недоступен."

@bot.message_handler(content_types=['text', 'photo'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    user_content = []
    
    if message.text:
        user_content.append({"type": "text", "text": message.text})
    
    if message.photo:
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')
        user_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
        })
    
    if not user_content:
        return

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content}
    ]

    ai_reply = ask_ai(messages)
    
    if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
        ai_reply = "Здравствуйте! " + ai_reply
        
    final_reply = ai_reply + SIGNATURE
    bot.reply_to(message, final_reply)

print("БОТ С КАРТИНКАМИ ЗАПУЩЕН!")
bot.polling(none_stop=True)
