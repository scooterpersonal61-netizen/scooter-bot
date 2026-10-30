import telebot
import os
import requests
import re

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

def find_in_knowledge(user_text):
    """Умный поиск по файлу knowledge.txt"""
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        return "Файл базы знаний не найден."
    
    # Очищаем вопрос от лишних символов и делаем список слов
    words = re.findall(r'\w+', user_text.lower())
    # Убираем короткие слова (предлоги, союзы)
    search_words = [w for w in words if len(w) > 2]
    
    if not search_words:
        return "База знаний пуста по этому запросу."

    relevant_lines = []
    for i, line in enumerate(lines):
        line_lower = line.lower()
        # Если в строке есть хотя бы 1-2 слова из вопроса
        matches = sum(1 for word in search_words if word in line_lower)
        
        if matches >= 2 or (len(search_words) == 1 and search_words[0] in line_lower):
            # Берем саму строку и пару строк вокруг нее (на случай, если описание разбито)
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            chunk = "".join(lines[start:end])
            if chunk not in relevant_lines:
                relevant_lines.append(chunk)
                
    if relevant_lines:
        # Возвращаем максимум 5 найденных блоков, чтобы не перегружать нейросеть
        return "\n---\n".join(relevant_lines[:5])
    else:
        return "В базе знаний нет точной информации по этому запросу."

@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Ищем инфу в нашей огромной базе
    found_context = find_in_knowledge(message.text)
    
    system_prompt = f"""Ты — дерзкий, но профессиональный эксперт по мототехнике магазина "Скутер Персонал". 
Твоя цель — дать покупателю максимально точный ответ. 

Вот фрагменты из нашей базы знаний, которые подходят к вопросу:
{found_context}

ЖЕЛЕЗНЫЕ ПРАВИЛА:
1. Если в фрагментах выше есть ответ (цифры, совместимость) — используй его и ответь уверенно.
2. Если информации нет — используй веб-поиск. Ищи внимательно.
3. ЗАПРЕЩЕННЫЕ ФРАЗЫ: "Рекомендуем уточнить в карточке товара", "Обратитесь в службу поддержки". 
4. СТИЛЬ ОТВЕТА: Отвечай как мастер. Коротко (2-3 предложения).
5. БЕЗ ССЫЛОК: Никаких http:// и .ru.
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
        "tool_choice": "auto" # Если есть в базе - не ищет. Если нет - идет в интернет.
    }
    
    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        response_data = response.json()
        
        if 'choices' in response_data:
            ai_reply = response_data['choices'][0]['message']['content'].strip()
            
            # Чистим ссылки
            ai_reply = re.sub(r'http\S+|www\.\S+|[a-zA-Z0-9.-]+\.(ru|com|net|org|info|biz)', '', ai_reply)
            ai_reply = re.sub(r'\s+', ' ', ai_reply).strip()
            
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

print("ГИБРИДНЫЙ БОТ С УМНЫМ ПОИСКОМ ЗАПУЩЕН!")
bot.polling(non_stop=True)
