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
    
    system_prompt = f"""Ты — технически грамотный консультант магазина "Скутер Персонал".
Контекст из Базы Знаний:
{context}

ИНСТРУКЦИЯ:
1. ОБЩАЙСЯ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ.
2. Если в контексте есть таблица (знаки |), найди статус:
   - "Условно": "Здравствуйте! Деталь может подойти, если совпадают посадочные размеры."
   - "Подтверждено": "Здравствуйте! По указанным параметрам деталь совместима с вашей моделью."
   - "Не подходит": "Здравствуйте! Данная деталь не предназначена для указанного исполнения."
3. Если контекст "НЕТ_СОВПАДЕНИЙ_В_БАЗЕ" — ищи в интернете. 
   - Если нашел цифры (например, 41-55 мм), напиши ТОЛЬКО их: "Здравствуйте! Судя по найденным данным, диаметр обычно составляет 41-55 мм."
   - Если не нашел ни одной цифры: "Здравствуйте! К сожалению, точные размеры производитель не указывает."
4. Если просят схему или инструкцию: "Здравствуйте! Подробные схемы и инструкции мы не предоставляем."

ЗАПРЕТЫ:
- НИКАКИХ скобок (квадратных, круглых), кавычек, смайликов и спецсимволов.
- Никаких ссылок.
- Никаких "100%", "гарантирую".
- Максимум 2 предложения.
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
            
            # --- ЯДЕРНАЯ ОЧИСТКА ---
            # Оставляем ТОЛЬКО русские/английские буквы, цифры, пробелы, точку, запятую, тире, вопрос и восклицание.
            # Всё остальное (все виды скобок, кавычки, звездочки, markdown-символы) уничтожается.
            ai_reply = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9\s.,!?-]', '', ai_reply)
            
            # Убираем возможные двойные знаки препинания после чистки
            ai_reply = re.sub(r'\.\s*\.', '.', ai_reply)
            ai_reply = re.sub(r'\s+', ' ', ai_reply).strip()
            
            if len(ai_reply) < 15:
                ai_reply = "К сожалению, точные размеры производитель не указывает."

            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            bot.reply_to(message, "Здравствуйте! Уточните маркировку двигателя и размеры." + SIGNATURE)
            
    except Exception as e:
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("БОТ (ЯДЕРНАЯ ОЧИСТКА) ЗАПУЩЕН!")
bot.polling(non_stop=True)
