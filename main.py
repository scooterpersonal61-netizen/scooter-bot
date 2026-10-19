import telebot
import os
import requests

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

# Читаем базу знаний из файла
def get_knowledge_base():
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "База знаний пока пуста."

# Функция поиска по ключевым словам
def find_relevant_info(user_text):
    knowledge = get_knowledge_base()
    if knowledge == "База знаний пока пуста.":
        return knowledge
    
    # Разбиваем базу на строки (товары)
    lines = knowledge.split('\n')
    relevant_lines = []
    
    # Ищем совпадения слов из вопроса пользователя в базе знаний
    user_words = user_text.lower().split()
    for line in lines:
        if len(line.strip()) < 3: continue
        line_lower = line.lower()
        # Если хотя бы 2 значимых слова из вопроса есть в строке — берем её
        matches = sum(1 for word in user_words if len(word) > 3 and word in line_lower)
        if matches >= 2 or (len(user_words) == 1 and user_words[0] in line_lower):
            relevant_lines.append(line)
            
    if relevant_lines:
        return "\n".join(relevant_lines)
    else:
        return "В базе знаний нет точной информации по этому запросу."

def ask_ai(user_text):
    # Ищем инфу в базе
    context = find_relevant_info(user_text)
    print(f"Найденный контекст: {context}") # Для логов

    system_prompt = f"""Ты — сотрудник поддержки магазина мототехники. Твоя задача — давать короткие и безопасные ответы.
КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО задавать встречные вопросы и писать длинные тексты.
Пиши максимум 3-4 предложения. Не пиши приветствие, оно добавится автоматически.

Вот информация, которую мы нашли в нашей базе знаний по запросу покупателя:
{context}

Правила ответов:
1. Если в найденной информации есть ответ на вопрос (размеры, совместимость) — используй её и дай четкий ответ.
2. Если информации нет (в контексте написано "нет точной информации") и спрашивают про совместимость — ответь: "В карточке товара указана совместимость. Рекомендуем сверить габариты детали по фотографиям в карточке. При сомнениях вы всегда можете оформить возврат по правилам ВБ."
3. Если спрашивают про размеры, а инфы нет — ответь: "К сожалению, производитель не указывает точные размеры в спецификации. Вы можете визуально оценить пропорции детали на фото."
4. Если спрашивают про возврат денег, брак или где заказ — ответь: "Вопросы возврата и компенсации решаются через службу поддержки маркетплейса. Пожалуйста, обратитесь в чат поддержки в личном кабинете ВБ."
5. Если спрашивают про наличие — ответь: "Точных дат поступления пока нет. Рекомендуем добавить товар в «Избранное»."

Не пиши подпись, она добавится автоматически.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        # ТУТ МЫ ВКЛЮЧАЕМ УМНУЮ ПЛАТНУЮ МОДЕЛЬ DEEPSEEK
        "model": "deepseek/deepseek-chat", 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
        response_data = response.json()
        
        if 'choices' in response_data:
            return response_data['choices'][0]['message']['content'].strip()
        else:
            error_msg = response_data.get('error', {}).get('message', 'Неизвестная ошибка')
            print(f"Ошибка API: {error_msg}")
            return f"Извините, сервис временно недоступен (Ошибка ИИ)."
            
    except Exception as e:
        print(f"Ошибка соединения: {e}")
        return "Извините, сервис временно недоступен."

@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    ai_reply = ask_ai


message.text)
    
    if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
        ai_reply = "Здравствуйте! " + ai_reply
        
    final_reply = ai_reply + SIGNATURE
    bot.reply_to(message, final_reply)

print("УМНЫЙ БОТ С БАЗОЙ ЗНАНИЙ ЗАПУЩЕН!")
bot.polling(none_stop=True)(


import telebot
import os
import requests

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

# Читаем базу знаний из файла
def get_knowledge_base():
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "База знаний пока пуста."

# Функция поиска по ключевым словам
def find_relevant_info(user_text):
    knowledge = get_knowledge_base()
    if knowledge == "База знаний пока пуста.":
        return knowledge
    
    # Разбиваем базу на строки (товары)
    lines = knowledge.split('\n')
    relevant_lines = []
    
    # Ищем совпадения слов из вопроса пользователя в базе знаний
    user_words = user_text.lower().split()
    for line in lines:
        if len(line.strip()) < 3: continue
        line_lower = line.lower()
        # Если хотя бы 2 значимых слова из вопроса есть в строке — берем её
        matches = sum(1 for word in user_words if len(word) > 3 and word in line_lower)
        if matches >= 2 or (len(user_words) == 1 and user_words[0] in line_lower):
            relevant_lines.append(line)
            
    if relevant_lines:
        return "\n".join(relevant_lines)
    else:
        return "В базе знаний нет точной информации по этому запросу."

def ask_ai(user_text):
    # Ищем инфу в базе
    context = find_relevant_info(user_text)
    print(f"Найденный контекст: {context}") # Для логов

    system_prompt = f"""Ты — сотрудник поддержки магазина мототехники. Твоя задача — давать короткие и безопасные ответы.
КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО задавать встречные вопросы и писать длинные тексты.
Пиши максимум 3-4 предложения. Не пиши приветствие, оно добавится автоматически.

Вот информация, которую мы нашли в нашей базе знаний по запросу покупателя:
{context}

Правила ответов:
1. Если в найденной информации есть ответ на вопрос (размеры, совместимость) — используй её и дай четкий ответ.
2. Если информации нет (в контексте написано "нет точной информации") и спрашивают про совместимость — ответь: "В карточке товара указана совместимость. Рекомендуем сверить габариты детали по фотографиям в карточке. При сомнениях вы всегда можете оформить возврат по правилам ВБ."
3. Если спрашивают про размеры, а инфы нет — ответь: "К сожалению, производитель не указывает точные размеры в спецификации. Вы можете визуально оценить пропорции детали на фото."
4. Если спрашивают про возврат денег, брак или где заказ — ответь: "Вопросы возврата и компенсации решаются через службу поддержки маркетплейса. Пожалуйста, обратитесь в чат поддержки в личном кабинете ВБ."
5. Если спрашивают про наличие — ответь: "Точных дат поступления пока нет. Рекомендуем добавить товар в «Избранное»."

Не пиши подпись, она добавится автоматически.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        # ТУТ МЫ ВКЛЮЧАЕМ УМНУЮ ПЛАТНУЮ МОДЕЛЬ DEEPSEEK
        "model": "deepseek/deepseek-chat", 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
        response_data = response.json()
        
        if 'choices' in response_data:
            return response_data['choices'][0]['message']['content'].strip()
        else:
            error_msg = response_data.get('error', {}).get('message', 'Неизвестная ошибка')
            print(f"Ошибка API: {error_msg}")
            return f"Извините, сервис временно недоступен (Ошибка ИИ)."
            
    except Exception as e:
        print(f"Ошибка соединения: {e}")
        return "Извините, сервис временно недоступен."

@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    ai_reply = ask_ai


message.text)
    
    if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
        ai_reply = "Здравствуйте! " + ai_reply
        
    final_reply = ai_reply + SIGNATURE
    bot.reply_to(message, final_reply)

print("УМНЫЙ БОТ С БАЗОЙ ЗНАНИЙ ЗАПУЩЕН!")
bot.polling(none_stop=True)

