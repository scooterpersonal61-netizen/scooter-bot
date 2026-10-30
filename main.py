import telebot
import os
import requests
import re

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

def find_in_knowledge(user_text):
    """Умный поиск по базе с очисткой от ссылок и мусора"""
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ"
    
    # Разбиваем вопрос на слова
    words = [w.lower() for w in re.findall(r'\w+', user_text) if len(w) > 2]
    if not words:
        return "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ"

    scored_lines = []
    for line in lines:
        # Пропускаем пустые строки и разделители
        if not line.strip() or line.strip().startswith("==="):
            continue
            
        # Очищаем строку от ссылок, чтобы нейросеть их не видела
        clean_line = re.sub(r'https?://\S+', '', line.strip())
        
        line_lower = clean_line.lower()
        matches = sum(1 for word in words if word in line_lower)
        
        # Если есть совпадения (минимум 1, если слово длинное, или 2+)
        if matches >= 2 or (matches == 1 and any(len(w) > 4 for w in words if w in line_lower)):
            scored_lines.append((matches, clean_line))

    if not scored_lines:
        return "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ"

    # Сортируем по релевантности и берем ТОП-5 лучших строк для контекста
    scored_lines.sort(key=lambda x: x[0], reverse=True)
    
    # Убираем дубликаты и берем 5 штук
    unique_results = []
    for score, text in scored_lines:
        if text not in unique_results:
            unique_results.append(text)
        if len(unique_results) >= 5:
            break
            
    return "\n---\n".join(unique_results)

@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    context = find_in_knowledge(message.text)
    
    system_prompt = f"""Ты — технически грамотный эксперт магазина "Скутер Персонал".
Твоя задача — ответить покупателю на основе нашей Базы Знаний.

Вот отрывки из базы, которые подходят к вопросу:
{context}

ИНСТРУКЦИЯ:
1. Изучи контекст. Если в нем есть "ШАБЛОН ОТВЕТА" или "ГОТОВЫЙ ОТВЕТ" на похожий вопрос — используй его ПОЧТИ ДОСЛОВНО.
2. Если статус "ПОДТВЕРЖДЕНО" — уверенно пиши, что деталь подходит.
3. Если статус "УСЛОВНО" или "НЕ ПОДТВЕРЖДЕНО" — пиши, что деталь может подойти, но нужно проверить конкретные параметры (например, количество зубьев или шлицов). Не используй фразу "сверьте по фото", вместо этого попроси назвать маркировку двигателя или количество зубьев.
4. Если в контексте нет ответа, но есть веб-поиск — найди информацию и дай осторожный ответ.
5. СТИЛЬ: Профессионально, четко, по делу.

КАТЕГОРИЧЕСКИЕ ЗАПРЕТЫ:
- НИКАКИХ ссылок и упоминаний сайтов.
- НИКАКИХ фраз "уточните в карточке", "посмотрите в описании", "сверьте по фото".
- Максимум 3-4 предложения.
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
            
            # --- АБСОЛЮТНАЯ ОЧИСТКА ---
            # 1. Удаляем ссылки
            ai_reply = re.sub(r'https?://\S+|www\.\S+', '', ai_reply)
            ai_reply = re.sub(r'\b\w+\.(ru|ua|com|net|org|info|biz|eu)\b', '', ai_reply, flags=re.IGNORECASE)
            # 2. Удаляем скобки и спецсимволы (разрешаем только буквы, цифры, базовую пунктуацию)
            ai_reply = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9\s.,!?-]', '', ai_reply)
            # 3. Убираем висящие предлоги/запятые
            ai_reply = re.sub(r'\b(с|со|на|из|от)\s*[,.]', '', ai_reply, flags=re.IGNORECASE)
            # 4. Вырезаем фразы-паразиты
            ai_reply = re.sub(r'(сверьте|посмотрите|уточните|сравните).{0,30}(карточке|фото|описании|деталью)', '', ai_reply, flags=re.IGNORECASE)
            
            ai_reply = re.sub(r'\.\s*\.', '.', ai_reply)
            ai_reply = re.sub(r'\s+', ' ', ai_reply).strip()
            
            if len(ai_reply) < 15:
                ai_reply = "Для точного ответа уточните маркировку двигателя и количество зубьев на старой детали."

            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            bot.reply_to(message, "Здравствуйте! Уточните маркировку двигателя." + SIGNATURE)
            
    except Exception as e:
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("МОЩНЫЙ БОТ С УМНЫМ ПОИСКОМ ЗАПУЩЕН!")
bot.polling(non_stop=True)
