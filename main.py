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
        
        if matches >= 2 or (matches == 1 and any(len(w) > 4 for w in words if w in line_lower)):
            scored_lines.append((matches, clean_line))

    if not scored_lines:
        return "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ"

    scored_lines.sort(key=lambda x: x[0], reverse=True)
    
    unique_results = []
    for score, text in scored_lines:
        if text not in unique_results:
            unique_results.append(text)
        if len(unique_results) >= 4:
            break
            
    return "\n---\n".join(unique_results)

@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    context = find_in_knowledge(message.text)
    
    system_prompt = f"""Ты — профессиональный консультант магазина "Скутер Персонал".
Твоя задача — дать точный ответ.

КОНТЕКСТ ИЗ БАЗЫ:
{context}

ЖЕЛЕЗНЫЕ ПРАВИЛА:
1. ПРАВИЛО ПРЯМОГО СОВПАДЕНИЯ: Если модель в вопросе (Stels Skif 50) совпадает с моделью в названии товара (Stels 50cc) — отвечай "Да, подходит". Не нужно уточнять код двигателя, если это очевидно.
2. ЗАПРЕТ НА ВЫДУМКИ: Никогда не пиши объемы двигателей (например, "140 кубов"), если этой цифры нет в вопросе или в контексте. Используй только то, что написано.
3. Если в контексте есть статус "ПОДТВЕРЖДЕНО" — используй его.
4. Если данных нет ни в базе, ни в вопросе — пиши "Для точного ответа уточните маркировку двигателя".
5. СТИЛЬ: Вежливо, четко, максимум 3 предложения.

ЗАПРЕТЫ:
- Никаких ссылок (http, .ru, .com).
- Никаких скобок.
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
            
            # Очистка от мусора, ссылок и скобок
            ai_reply = re.sub(r'https?://\S+|www\.\S+', '', ai_reply)
            ai_reply = re.sub(r'\b\w+\.(ru|ua|com|net|org|info|biz|eu)\b', '', ai_reply, flags=re.IGNORECASE)
            ai_reply = re.sub(r'[^а-яА-ЯёЁ0-9\s.,!?-]', '', ai_reply)
            
            ai_reply = re.sub(r'\s+', ' ', ai_reply).strip()
            
            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            bot.reply_to(message, ai_reply + SIGNATURE)
        else:
            bot.reply_to(message, "Здравствуйте! Уточните маркировку двигателя." + SIGNATURE)
            
    except Exception as e:
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("БОТ ЗАПУЩЕН!")
bot.polling(non_stop=True)
