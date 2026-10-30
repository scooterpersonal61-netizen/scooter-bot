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

СТРОГИЕ ПРАВИЛА (Нарушение недопустимо):
1. ФОРМАТ: Деловое общение. Максимум 3 предложения. Начинай с факта, без "Привет".
2. НИКАКИХ 100% ГАРАНТИЙ: Если в базе знаний или интернете нет прямого указания, что деталь подходит именно на этот двигатель, ты ОБЯЗАН написать: "Судя по параметрам, должен подойти, но точную совместимость нужно сверить по фото или маркировке".
3. ЧЕСТНОСТЬ: Если ты не нашел информацию на форумах или в других магазинах — так и скажи, не выдумывай.
4. ЗАПРЕЩЕННЫЕ ФРАЗЫ: "100%", "гарантирую", "точно подойдет", "заезжай", "приезжай".
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
                    "max_results": 5,
                    "search_context_size": "high"
                }
            }
        ],
        "tool_choice": "required" # Включаем принудительный поиск
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        response_data = response.json()
        
        if 'choices' in response_data:
            ai_reply = response_data['choices'][0]['message']['content'].strip()
            
            # 1. Чистим ссылки
            ai_reply = re.sub(r'http\S+|www\.\S+|[a-zA-Z0-9.-]+\.(ru|com|net|org|info|biz)', '', ai_reply)
            ai_reply = re.sub(r'\s+', ' ', ai_reply).strip()
            
            # 2. ХАРДКОРНЫЙ ФИЛЬТР: Уничтожаем любые 100% гарантии
            ai_reply = re.sub(r'(100%|100 процент|гарантирую|точно подойдет|100%-я)', 'скорее всего подойдет', ai_reply, flags=re.IGNORECASE)
            
            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            final_reply = ai_reply + SIGNATURE
            bot.reply_to(message, final_reply)
        else:
            print(f"Ошибка API: {response_data}")
            bot.reply_to(message, "Здравствуйте! Извините, произошла ошибка при генерации ответа." + SIGNATURE)
            
    except Exception as e:
        print(f"Ошибка соединения: {e}")
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("БОТ-ЭКСПЕРТ (С ФИЛЬТРОМ ГАРАНТИЙ) ЗАПУЩЕН!")
bot.polling(non_stop=True)
