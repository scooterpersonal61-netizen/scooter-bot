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
        
        # Если есть совпадение по ключевым словам (мин. 2 слова, или один код типа 172FMM)
        if matches >= 2 or any(word in line_lower for word in words if len(word) > 4):
            scored_lines.append((matches, line.strip()))

    if not scored_lines:
        return "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ"

    # Сортируем по релевантности и берем лучшую строку
    scored_lines.sort(key=lambda x: x[0], reverse=True)
    return scored_lines[0][1]

@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    context = find_in_knowledge(message.text)
    
    system_prompt = f"""Ты — технически грамотный и ОСТОРОЖНЫЙ консультант магазина "Скутер Персонал".
Твоя задача — ответить покупателю.

Контекст из нашей Базы Знаний по этому запросу:
{context}

ИНСТРУКЦИЯ:
1. Если в контексте есть строка из таблицы (там есть символы |):
   - Найди статус ("Условно", "Подтверждено" или "Не подходит").
   - Если статус "Условно": Ответь строго шаблоном: "Здравствуйте! Деталь может подойти, если совпадают посадочные размеры и исполнение узла. Пожалуйста, сравните параметры в карточке с вашей старой деталью."
   - Если статус "Подтверждено": Ответь строго шаблоном: "Здравствуйте! По указанным параметрам деталь совместима с вашей моделью. Перед заказом рекомендуем сверить артикул и размеры."
   - Если статус "Не подходит": Ответь строго шаблоном: "Здравствуйте! Данная деталь не предназначена для указанного исполнения. Рекомендуем подобрать запчасть по маркировке двигателя."

2. Если контекст равен "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ":
   - Ты ОБЯЗАН использовать веб-поиск, чтобы найти информацию о деталях.
   - Если нашел информацию, дай осторожный ответ. НАЧНИ со слов: "Здравствуйте! Судя по найденным данным, деталь должна подойти, но рекомендуем сверить по фото." (или "может не подойти", если нашел обратное).
   - Если не нашел ничего: "Здравствуйте! Для точного ответа уточните маркировку двигателя и размеры старой детали."

КАТЕГОРИЧЕСКИЕ ЗАПРЕТЫ (Нарушение = штраф):
- НИКОГДА не пиши "100%", "гарантирую", "установка подтверждена", "точно подойдет".
- НИКОГДА не советуй читать инструкции, смотреть схемы или ехать в сервис ("заезжай", "приезжай").
- Никакой воды. Максимум 3-4 предложения.
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
        "tool_choice": "auto" # Позволяем боту самому решить: искать в сети или нет
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        response_data = response.json()
        
        if 'choices' in response_data:
            ai_reply = response_data['choices'][0]['message']['content'].strip()
            
            # --- БРОНЕБОЙНЫЙ ФИЛЬТР (страховка от галлюцинаций) ---
            ai_reply = re.sub(r'<[^>]+>', '', ai_reply)
            ai_reply = re.sub(r'http\S+|www\.\S+|[a-zA-Z0-9.-]+\.(ru|com|net|org|info|biz)', '', ai_reply)
            
            # Уничтожаем запрещенные фразы на уровне кода
            ai_reply = re.sub(r'(100%|гарантирую|установка подтверждена|точно подойдет)', 'скорее всего подойдет', ai_reply, flags=re.IGNORECASE)
            ai_reply = re.sub(r'(заезжай|приезжай|посмотрите схему|обратитесь к инструкции)', 'сверьте по фото', ai_reply, flags=re.IGNORECASE)
            
            ai_reply = re.sub(r'\s+', ' ', ai_reply).strip()
            
            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            bot.reply_to(message, "Здравствуйте! Для точного ответа уточните маркировку двигателя и размеры." + SIGNATURE)
            
    except Exception as e:
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("ГИБРИДНЫЙ БОТ (БАЗА + БЕЗОПАСНЫЙ ПОИСК) ЗАПУЩЕН!")
bot.polling(non_stop=True)
