import telebot
import os
import requests
import re

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

def find_in_knowledge(user_text):
    """Ищет совпадения в базе знаний"""
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ"
    
    words = [w.lower() for w in re.findall(r'\w+', user_text) if len(w) > 2]
    if not words:
        return "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ"

    scored_lines = []
    for line in lines:
        if not line.strip() or line.strip().startswith("==="):
            continue
            
        clean_line = re.sub(r'https?://\S+', '', line.strip())
        line_lower = clean_line.lower()
        
        matches = sum(1 for word in words if word in line_lower)
        
        if matches >= 2 or (matches == 1 and any(len(w) > 4 for w in words if w in line_lower)):
            scored_lines.append((matches, clean_line))

    if not scored_lines:
        return "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ"

    scored_lines.sort(key=lambda x: x[0], reverse=True)
    
    unique_results = []
    for score, text in scored_lines:
        if text not in unique_results:
            unique_results.append(text)
        if len(unique_results) >= 4: # Берем 4 лучшие строки для контекста
            break
            
    return "\n---\n".join(unique_results)

@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    context = find_in_knowledge(message.text)
    
    # УМНЫЙ ПРОМПТ: Разрешаем поиск, но запрещаем выдумывать и ломать текст
    system_prompt = f"""Ты — профессиональный и ОСТОРОЖНЫЙ консультант магазина "Скутер Персонал".
Твоя задача — дать точный ответ, используя нашу Базу Знаний или веб-поиск (если в базе пусто).

Вот что мы нашли в НАШЕЙ БАЗЕ по этому запросу:
{context}

АЛГОРИТМ ОТВЕТА:
1. Если в контексте есть точный ответ (шаблон или конкретная деталь) — используй его.
2. Если контекст равен "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ" — используй веб-поиск. 
   ВАЖНО: Если ты берешь данные из интернета, ты ОБЯЗАН писать "Судя по открытым источникам..." или "Обычно...". Ты не имеешь права утверждать это как 100% факт.
3. Если покупатель спрашивает про совместимость (например, трос TTR 250 на Kayo K2R), а в базе нет прямого подтверждения — отвечай: "Точных данных по этой модели нет, но если параметры совпадают, деталь может подойти. Рекомендуем сверить по фото или старой детали."
4. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО выдумывать конкретные цифры (1010 мм, M10, 90-95 мм), если их нет в контексте базы. Если ты нашел их в интернете, пиши: "Стандартная длина обычно составляет около X, но лучше уточнить".
5. СТИЛЬ: Вежливо, профессионально, четко. Максимум 3 предложения.

ЗАПРЕТЫ:
- Никаких ссылок (http, .ru, .com) и обрывков (scooter-).
- Никаких скобок.
- Никаких фраз "посмотрите в карточке", "сверьте по фото в карточке" (клиент уже в карточке).
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek/deepseek-chat:online", # Включаем интернет, но с жесткими правилами
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
            
            # --- ИДЕАЛЬНАЯ ЧИСТКА (Хирургия) ---
            # 1. Вырезаем все ссылки и мусор типа "scooter-"
            ai_reply = re.sub(r'https?://\S+|www\.\S+', '', ai_reply)
            ai_reply = re.sub(r'\b\w+\.(ru|ua|com|net|org|info|biz|eu)\b', '', ai_reply, flags=re.IGNORECASE)
            ai_reply = re.sub(r'scooter-|http|www', '', ai_reply, flags=re.IGNORECASE)
            
            # 2. Оставляем ТОЛЬКО русские буквы, цифры и базовые знаки (убираем все скобки и спецсимволы)
            ai_reply = re.sub(r'[^а-яА-ЯёЁ0-9\s.,!?-]', '', ai_reply)
            
            # 3. Убираем висящие предлоги (с , на .)
            ai_reply = re.sub(r'\b(с|со|на|из|от)\s*[,.]', '', ai_reply, flags=re.IGNORECASE)
            
            # 4. Убираем дублирующиеся точки
            ai_reply = re.sub(r'\.\s*\.', '.', ai_reply)
            ai_reply = re.sub(r'\s+', ' ', ai_reply).strip()
            
            if len(ai_reply) < 15:
                ai_reply = "Уточните, пожалуйста, маркировку двигателя и год выпуска."

            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            bot.reply_to(message, "Здравствуйте! Уточните маркировку двигателя." + SIGNATURE)
            
    except Exception as e:
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("ИДЕАЛЬНЫЙ ГИБРИДНЫЙ БОТ ЗАПУЩЕН!")
bot.polling(non_stop=True)
