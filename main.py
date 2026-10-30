import telebot
import os
import requests
import re

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

def find_in_knowledge(user_text):
    """Умный поиск по табличной базе знаний"""
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return "Файл базы знаний не найден."
    
    # Разбиваем вопрос на слова, убираем короткие
    words = [w.lower() for w in re.findall(r'\w+', user_text) if len(w) > 2]
    if not words:
        return "Нет ключевых слов для поиска."

    scored_lines = []
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        # Считаем, сколько ключевых слов из вопроса есть в строке
        matches = sum(1 for word in words if word in line_lower)
        
        # Если совпало 2 и более слов, или это точное совпадение кода двигателя (например AF34)
        if matches >= 2 or any(word in line_lower for word in words if len(word) > 4):
            scored_lines.append((matches, i, line.strip()))

    # Сортируем по количеству совпадений (сначала самые релевантные)
    scored_lines.sort(key=lambda x: x[0], reverse=True)
    
    if not scored_lines:
        return "В базе знаний нет точной информации по этому запросу."

    # Берем топ-5 самых релевантных строк
    top_results = []
    for score, idx, text in scored_lines[:5]:
        top_results.append(text)
        
    return "\n".join(top_results)

@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    found_context = find_in_knowledge(message.text)
    
    # ОБУЧАЕМ НЕЙРОСЕТЬ ПОНИМАТЬ ТВОЮ ТАБЛИЦУ
    system_prompt = f"""Ты — технически грамотный онлайн-консультант магазина запчастей "Скутер Персонал" на Wildberries.
Твоя задача — дать покупателю ответ, используя нашу Базу Знаний.

Вот выдержка из базы (формат: ID | Категория | Деталь | Двигатель/Модель | Статус | Условие совместимости | ...):
{found_context}

ПРАВИЛА ОТВЕТА:
1. Внимательно изучи найденные строки. Найди колонку "Статус".
2. Если статус "Условно" — НЕ ГОВОРИ "100% подходит". Скажи, что деталь может подойти при совпадении размеров.
3. Если статус "Подтверждено" — можешь сказать, что подходит.
4. В самом конце файла есть раздел "=== ОТВЕТЫ WB OZON ===". Используй шаблоны из этого раздела для формирования финального ответа (подставь нужный статус: Подтверждено, Условно или Недостаточно данных).
5. Если в найденном контексте нет нужной информации — вежливо попроси покупателя уточнить маркировку двигателя (например, 139QMB или AF34) и год выпуска.
6. СТИЛЬ: Вежливо, профессионально, без воды. Максимум 3-4 предложения.
7. ЗАПРЕЩЕННЫЕ ФРАЗЫ: "заезжай", "приезжай", "100% гарантирую".
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek/deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message.text}
        ],
        "tools": [
            {
                "type": "openrouter:web_search",
                "parameters": {
                    "max_results": 3
                }
            }
        ],
        "tool_choice": "auto" # Если база не дала ответ, он пойдет в интернет
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        response_data = response.json()
        
        if 'choices' in response_data:
            ai_reply = response_data['choices'][0]['message']['content'].strip()
            
            # Чистим технические символы и ссылки
            ai_reply = re.sub(r'<[^>]+>', '', ai_reply)
            ai_reply = re.sub(r'http\S+|www\.\S+|[a-zA-Z0-9.-]+\.(ru|com|net|org|info|biz)', '', ai_reply)
            ai_reply = re.sub(r'\s+', ' ', ai_reply).strip()
            
            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            bot.reply_to(message, "Здравствуйте! Извините, произошла ошибка при генерации ответа." + SIGNATURE)
            
    except Exception as e:
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("УМНЫЙ БОТ С ТАБЛИЧНОЙ БАЗОЙ ЗАПУЩЕН!")
bot.polling(non_stop=True)
