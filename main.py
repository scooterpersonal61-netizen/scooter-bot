import telebot
import os
import requests
import re

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

# --- ЖЕСТКИЕ ОТВЕТЫ (БЕЗ НЕЙРОСЕТИ) ---
EXACT_ANSWERS = {
    "цпг stels skif": "Здравствуйте! На Stels Skif 50 с двухтактным двигателем семейства 1E40QMB применяются ЦПГ диаметром 40 мм. При выборе важны также исполнение выпускного фланца и размеры поршневого пальца: ориентируйтесь на параметры установленной ЦПГ.",
    "коленвал honling titan": "Здравствуйте! Коленвал 139QMB 16T рассчитан на исполнение двигателя с 16 зубьями привода масляного насоса. У Honling Titan по одному названию модели это исполнение определить нельзя, поэтому ориентируйтесь на число зубьев установленного коленвала.",
    "карбюратор stels skif": "Здравствуйте! Карбюратор для четырехтактного 139QMB не является штатной заменой для двухтактного Stels Skif 50 с двигателем 1E40QMB. Для него нужен карбюратор соответствующего двухтактного исполнения."
}

def clean_text(text):
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'\b\w+\.(ru|ua|com|net|org|info|biz|eu)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Источник|источник|Ссылка|ссылка', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9\s.,!?-]', '', text) 
    text = re.sub(r'\.\s*\.', '.', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def check_exact_answers(user_text):
    search_text = user_text.lower()
    if "цпг" in search_text and ("скиф" in search_text or "skif" in search_text or "stels" in search_text):
        return EXACT_ANSWERS["цпг stels skif"]
    if "коленвал" in search_text and ("титан" in search_text or "titan" in search_text or "honling" in search_text):
        return EXACT_ANSWERS["коленвал honling titan"]
    if "карбюратор" in search_text and ("скиф" in search_text or "skif" in search_text):
        return EXACT_ANSWERS["карбюратор stels skif"]
    return None

def get_context_for_ai(user_text):
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        return "База не найдена"

    words = [w.lower() for w in re.findall(r'\w+', user_text) if len(w) > 2]
    scored_lines = []
    
    for line in lines:
        if not line.strip() or line.strip().startswith("==="): continue
        clean_line = re.sub(r'https?://\S+', '', line.strip())
        line_lower = clean_line.lower()
        matches = sum(1 for word in words if word in line_lower)
        if matches >= 2:
            scored_lines.append((matches, clean_line))

    scored_lines.sort(key=lambda x: x[0], reverse=True)
    context = "\n".join([text for _, text in scored_lines[:5]])
    templates = "\n".join([line.strip() for line in lines if "ШАБЛОН_" in line])
    
    return f"КОНТЕКСТ ИЗ БАЗЫ:\n{context}\n\nДОСТУПНЫЕ ШАБЛОНЫ:\n{templates}"

@bot.message_handler(content_types=['text'])
def handle_message(message):
    print(f"ПОЛУЧЕНО СООБЩЕНИЕ: {message.text}") # Лог для отладки
    bot.send_chat_action(message.chat.id, 'typing')
    
    exact_reply = check_exact_answers(message.text)
    if exact_reply:
        bot.reply_to(message, exact_reply + SIGNATURE)
        return

    context = get_context_for_ai(message.text)
    
    system_prompt = f"""Ты — строгий консультант магазина "Скутер Персонал".
Отвечай, используя ТОЛЬКО предоставленный контекст.

{context}

КРИТИЧЕСКИЕ ПРАВИЛА:
1. НИКОГДА не превращай коды двигателей (например, 1E40QMB, 139QMB) в цифры (140, 139).
2. НЕ ЗАДАВАЙ ВОПРОСОВ.
3. Если точной информации нет, используй ШАБЛОН_НЕИЗВЕСТНО.
4. Ответ — максимум 3 предложения.
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
        ]
    }
    
    try:
        # СНИЖАЕМ ТАЙМАУТ ДО 30 СЕКУНД, ЧТОБЫ НЕ ВИСЕТЬ ВЕЧНО
        print("Отправляем запрос в OpenRouter...")
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
        print(f"Статус ответа: {response.status_code}")
        response_data = response.json()
        
        if 'choices' in response_data:
            ai_reply = response_data['choices'][0]['message']['content'].strip()
            ai_reply = clean_text(ai_reply)
            
            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            bot.reply_to(message, ai_reply + SIGNATURE)
        else:
            print(f"Ошибка в ответе API: {response_data}")
            bot.reply_to(message, "Здравствуйте! По этому вопросу информация уточняется. Напишите, пожалуйста, маркировку двигателя." + SIGNATURE)
            
    except requests.exceptions.Timeout:
        print("ОШИБКА: Таймаут запроса к OpenRouter!")
        bot.reply_to(message, "Здравствуйте! Нейросеть задумалась слишком надолго. Пожалуйста, переформулируйте вопрос или уточните маркировку двигателя." + SIGNATURE)
    except Exception as e:
        print(f"ОШИБКА: {e}")
        bot.reply_to(message, "Здравствуйте! Извините, произошла техническая ошибка. Попробуйте еще раз." + SIGNATURE)

print("СТАБИЛЬНЫЙ БОТ V9 ЗАПУЩЕН!")
bot.polling(non_stop=True)
