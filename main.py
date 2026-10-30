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
    for line in lines:
        if not line.strip() or line.strip().startswith("==="):
            continue
            
        clean_line = re.sub(r'https?://\S+', '', line.strip())
        line_lower = clean_line.lower()
        
        matches = sum(1 for word in words if word in line_lower)
        
        # Если совпало 2 и более слов, или одно длинное (например, код двигателя)
        if matches >= 2 or (matches == 1 and any(len(w) > 4 for w in words if w in line_lower)):
            scored_lines.append((matches, clean_line))

    if not scored_lines:
        return "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ"

    scored_lines.sort(key=lambda x: x[0], reverse=True)
    
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
    
    system_prompt = f"""Ты — строгий технический консультант магазина "Скутер Персонал".
Твоя задача — ответить на вопрос покупателя, используя ТОЛЬКО нашу Базу Знаний.

Вот отрывки из базы, которые подходят к вопросу:
{context}

СТРОГИЕ ПРАВИЛА:
1. Если в контексте есть готовый ответ (раздел "ШАБЛОН ОТВЕТА" или "ОТВЕТЫ WB OZON") — используй его ДОСЛОВНО.
2. Если в контексте есть нужная деталь (например, "Трос газа"), но нет информации о совместимости с конкретной моделью (например, K2R) — ответь строго по шаблону из раздела "Недостаточно данных": "Здравствуйте! Для точного ответа уточните маркировку двигателя, год выпуска и размеры старой детали. Только по названию модели совместимость подтвердить нельзя."
3. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО выдумывать цифры (длину, диаметр, количество зубьев), если их НЕТ в предоставленном контексте. Не ищи их в интернете!
4. Если контекст пуст — отвечай: "Здравствуйте! Уточните маркировку двигателя и размеры."
5. СТИЛЬ: Сухо, четко, без "воды". Максимум 3 предложения.
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek/deepseek-chat", # ОТКЛЮЧИЛИ ПОИСК, чтобы он не тащил мусор из сети
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
            
            # --- ЖЕСТКАЯ ОЧИСТКА ---
            ai_reply = re.sub(r'https?://\S+|www\.\S+', '', ai_reply)
            ai_reply = re.sub(r'\b\w+\.(ru|ua|com|net|org|info|biz|eu)\b', '', ai_reply, flags=re.IGNORECASE)
            # Удаляем любые английские слова и обрывки ссылок типа "scooter-"
            ai_reply = re.sub(r'\b[a-zA-Z]+\b', '', ai_reply) 
            # Удаляем скобки и спецсимволы
            ai_reply = re.sub(r'[^а-яА-ЯёЁ0-9\s.,!?-]', '', ai_reply)
            
            ai_reply = re.sub(r'\b(с|со|на|из|от)\s*[,.]', '', ai_reply, flags=re.IGNORECASE)
            ai_reply = re.sub(r'(сверьте|посмотрите|уточните|сравните).{0,30}(карточке|фото|описании|деталью)', '', ai_reply, flags=re.IGNORECASE)
            
            ai_reply = re.sub(r'\.\s*\.', '.', ai_reply)
            ai_reply = re.sub(r'\s+', ' ', ai_reply).strip()
            
            if len(ai_reply) < 15:
                ai_reply = "Для точного ответа уточните маркировку двигателя."

            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            bot.reply_to(message, "Здравствуйте! Уточните маркировку двигателя." + SIGNATURE)
            
    except Exception as e:
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("СТРОГИЙ БОТ ЗАПУЩЕН!")
bot.polling(non_stop=True)
