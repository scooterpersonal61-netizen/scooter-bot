import telebot
import os
import requests
import re

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

def find_in_knowledge(user_text):
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ"
    
    words = [w.lower() for w in re.findall(r'\w+', user_text) if len(w) > 2]
    if not words:
        return "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ"

    scored_lines = []
    for i, line in enumerate(lines):
        if "=== ОТВЕТЫ WB OZON ===" in line:
            break
        line_lower = line.lower()
        matches = sum(1 for word in words if word in line_lower)
        if matches >= 2 or any(word in line_lower for word in words if len(word) > 4):
            scored_lines.append((matches, line.strip()))

    if not scored_lines:
        return "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ"

    scored_lines.sort(key=lambda x: x[0], reverse=True)
    return scored_lines[0][1]

@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    context = find_in_knowledge(message.text)
    
    system_prompt = f"""Ты — технически грамотный и ОСТОРОЖНЫЙ консультант магазина "Скутер Персонал".
Твоя задача — ответить покупателю.

Контекст из нашей Базы Знаний:
{context}

ИНСТРУКЦИЯ:
1. ОБЩАЙСЯ ИСКЛЮЧИТЕЛЬНО НА РУССКОМ ЯЗЫКЕ.
2. Если в контексте есть строка из таблицы (со знаками |):
   - Найди статус ("Условно", "Подтверждено" или "Не подходит").
   - Если "Условно": "Здравствуйте! Деталь может подойти, если совпадают посадочные размеры и исполнение узла. Пожалуйста, сравните параметры в карточке с вашей старой деталью."
   - Если "Подтверждено": "Здравствуйте! По указанным параметрам деталь совместима с вашей моделью. Перед заказом рекомендуем сверить артикул и размеры."
   - Если "Не подходит": "Здравствуйте! Данная деталь не предназначена для указанного исполнения. Рекомендуем подобрать запчасть по маркировке двигателя."
3. Если контекст "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ":
   - Используй интернет (поиск включен автоматически).
   - Если нашел инфу, начни так: "Здравствуйте! Судя по найденным данным, деталь должна подойти, но рекомендуем сверить по фото."
   - Если не нашел: "Здравствуйте! Для точного ответа уточните маркировку двигателя и размеры."
4. ЕСЛИ ПРОСЯТ СХЕМУ, ФОТО ИЛИ ИНСТРУКЦИЮ: Ответь строго: "Здравствуйте! Все доступные фотографии и характеристики уже размещены в карточке товара. Дополнительных схем или инструкций у нас нет."

КАТЕГОРИЧЕСКИЕ ЗАПРЕТЫ (Штраф за нарушение):
- НИКАКИХ КАРТИНОК! Запрещено использовать формат Markdown (![]()). Только текст.
- НИКАКИХ ССЫЛОК.
- НИКАКИХ английских слов (Here, Image, Please).
- Никаких "100%", "гарантирую".
Максимум 3-4 предложения.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek/deepseek-chat:online", 
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message.text}
        ]
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        response_data = response.json()
        
        if 'choices' in response_data:
            ai_reply = response_data['choices'][0]['message']['content'].strip()
            
            # --- БРОНЕБОЙНАЯ ЧИСТКА ---
            # Удаляем markdown картинки (![alt](url))
            ai_reply = re.sub(r'!\[.*?\]\(.*?\)', '', ai_reply)
            # Удаляем любые ссылки
            ai_reply = re.sub(r'http\S+|www\.\S+|[a-zA-Z0-9.-]+\.(ru|com|net|org|info|biz)', '', ai_reply)
            # Удаляем системный мусор
            ai_reply = re.sub(r'<[^>]+>', '', ai_reply)
            ai_reply = re.sub(r'\{[^}]+\}', '', ai_reply)
            
            # Если проскочили английские фразы из поиска - вырезаем их (оставляем только кириллицу и базовую пунктуацию)
            # (Опционально, но лучше перестраховаться)
            
            ai_reply = re.sub(r'(100%|гарантирую|установка подтверждена|точно подойдет)', 'скорее всего подойдет', ai_reply, flags=re.IGNORECASE)
            
            ai_reply = re.sub(r'\s+', ' ', ai_reply).strip()
            
            if len(ai_reply) < 10:
                ai_reply = "Все доступные фотографии и характеристики уже размещены в карточке товара. Дополнительных схем у нас нет."

            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            bot.reply_to(message, "Здравствуйте! Уточните маркировку двигателя и размеры." + SIGNATURE)
            
    except Exception as e:
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("БОТ (РУССКИЙ, БЕЗ КАРТИНОК) ЗАПУЩЕН!")
bot.polling(non_stop=True)
