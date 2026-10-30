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
        return "Файл базы знаний не найден."
    
    words = [w for w in re.findall(r'\w+', user_text.lower()) if len(w) > 3]
    if not words:
        return "База знаний пуста по этому запросу."

    relevant_lines = []
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(word in line_lower for word in words):
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            chunk = "".join(lines[start:end]).strip()
            if chunk not in relevant_lines:
                relevant_lines.append(chunk)
                
    if relevant_lines:
        return "\n---\n".join(relevant_lines[:10])
    else:
        return "В базе знаний нет точной информации по этому запросу."

@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    found_context = find_in_knowledge(message.text)
    
    system_prompt = f"""Ты — технически грамотный онлайн-консультант интернет-магазина запчастей "Скутер Персонал" на Wildberries.

Вот информация из нашей базы, которая подходит к вопросу:
{found_context}

СТРОГИЕ ПРАВИЛА:
1. Если информация есть в базе выше — используй её, это САМЫЙ точный источник.
2. Если информации нет, ищи в интернете. Учитывай, что в мире запчастей существуют универсальные аналоги, которые могут подходить на разные двигатели.
3. Если точных данных нет, пиши: "Судя по параметрам, должен подойти, но точную совместимость лучше сверить по фото или маркировке".
4. НИКАКИХ 100% ГАРАНТИЙ.
5. Деловой стиль. Максимум 3-4 предложения. Без ссылок и технических символов.
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
        "tool_choice": "auto" # Теперь он не будет ломаться и выплевывать символы
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        response_data = response.json()
        
        if 'choices' in response_data:
            ai_reply = response_data['choices'][0]['message']['content'].strip()
            
            # 1. ЖЕСТКАЯ ЧИСТКА ОТ ВСЕХ ТЕХНИЧЕСКИХ СИМВОЛОВ И ССЫЛОК
            ai_reply = re.sub(r'<[^>]+>', '', ai_reply) # Убирает любые скобки < >
            ai_reply = re.sub(r'http\S+|www\.\S+|[a-zA-Z0-9.-]+\.(ru|com|net|org|info|biz)', '', ai_reply)
            ai_reply = re.sub(r'\s+', ' ', ai_reply).strip()
            
            # 2. Уничтожаем 100% гарантии
            ai_reply = re.sub(r'(100%|гарантирую|точно подойдет)', 'скорее всего подойдет', ai_reply, flags=re.IGNORECASE)
            
            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            bot.reply_to(message, "Здравствуйте! Извините, произошла ошибка при генерации ответа." + SIGNATURE)
            
    except Exception as e:
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("БОТ (ЧИСТЫЙ И УМНЫЙ) ЗАПУЩЕН!")
bot.polling(non_stop=True)
