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
    
    system_prompt = f"""Ты — эксперт по мототехнике магазина "Скутер Персонал". Твоя задача — дать точный ответ покупателю.
Контекст из Базы Знаний:
{context}

ИНСТРУКЦИЯ:
1. Если в вопросе упоминается конкретная модель скутера (например, Honling Titan, Honda Dio, K2R), а в базе есть двигатель (например, 139QMB) — ИСПОЛЬЗУЙ ВЕБ-ПОИСК. Проверь в интернете, какой двигатель стоит на этом скутере.
2. Если окажется, что на Honling Titan стоит двигатель 139QMB — пиши смело: "Здравствуйте! Да, этот коленвал подойдет, так как на Honling Titan устанавливается двигатель 139QMB."
3. Если в контексте из базы есть статус "Условно", но веб-поиск подтвердил совместимость — ОТВЕЧАЙ "Подходит", игнорируя статус "Условно".
4. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать фразы: "Уточните диаметры", "Уточните ширину", "Сверьте по фото", "Проверьте размеры". Покупатель не имеет микрометра, чтобы мерить коленвал.
5. Если база и интернет не дают ответа, пиши: "Здравствуйте! По этому артикулу информация уточняется."

ЗАПРЕТЫ:
- НИКАКИХ ссылок, доменов (типа .ua, .ru), скобок и спецсимволов.
- Никаких "100%", "гарантирую".
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
            
            # --- УМНАЯ ОЧИСТКА ---
            ai_reply = re.sub(r'\!?\[.*?\]\(.*?\)', '', ai_reply)
            ai_reply = re.sub(r'https?://\S+|www\.\S+', '', ai_reply)
            ai_reply = re.sub(r'\b\w+\.(ru|ua|com|net|org|info|biz)\b', '', ai_reply, flags=re.IGNORECASE)
            # Оставляем только буквы, цифры и базовые знаки
            ai_reply = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9\s.,!?-]', '', ai_reply)
            ai_reply = re.sub(r'\.\s*\.', '.', ai_reply)
            ai_reply = re.sub(r'\s+', ' ', ai_reply).strip()
            
            if len(ai_reply) < 15:
                ai_reply = "По этому артикулу информация уточняется."

            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            bot.reply_to(message, "Здравствуйте! Уточните маркировку двигателя." + SIGNATURE)
            
    except Exception as e:
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("БОТ С ЛОГИКОЙ И ВЕБ-ПОИСКОМ ЗАПУЩЕН!")
bot.polling(non_stop=True)
