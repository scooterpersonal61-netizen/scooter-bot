import telebot
import os
import requests
import re

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

def clean_text(text):
    """Умная очистка (не трогает коды двигателей)"""
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'\b\w+\.(ru|ua|com|net|org|info|biz|eu)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Источник|источник|Ссылка|ссылка', '', text, flags=re.IGNORECASE)
    
    # ТЕПЕРЬ МЫ ОСТАВЛЯЕМ АНГЛИЙСКИЕ БУКВЫ (a-zA-Z), чтобы не ломать коды вроде 1E40QMB
    text = re.sub(r'[^a-zA-Zа-яА-ЯёЁ0-9\s.,!?-]', '', text) 
    
    text = re.sub(r'\.\s*\.', '.', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def find_exact_answer(user_text):
    """Ищет точный ответ в разделе ГОТОВЫЕ АВТОНОМНЫЕ ОТВЕТЫ"""
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            
        if "=== ГОТОВЫЕ АВТОНОМНЫЕ ОТВЕТЫ" in content:
            answers_block = content.split("=== ГОТОВЫЕ АВТОНОМНЫЕ ОТВЕТЫ")[1].split("===")[0]
            lines = answers_block.split('\n')
            
            search_text = user_text.lower()
            
            # 1. Спец-проверка для ЦПГ (чтобы точно сработало)
            if "цпг" in search_text and "40" in search_text and ("stels" in search_text or "стелс" in search_text or "скиф" in search_text):
                for line in lines:
                    if "ЦПГ 40 мм на Stels Skif 50" in line:
                        return line.split("|")[3].strip()

            # 2. Общий поиск по другим вопросам
            for line in lines:
                if "ВОПРОС" in line and "ОТВЕТ" in line:
                    parts = line.split("|")
                    if len(parts) >= 4:
                        db_question = parts[1].strip().lower()
                        db_answer = parts[3].strip()
                        
                        db_words = [w for w in re.findall(r'\w+', db_question) if len(w) > 2]
                        if not db_words: continue
                        
                        matches = sum(1 for w in db_words if w in search_text)
                        # Если 60% слов из базы есть в вопросе
                        if matches >= len(db_words) * 0.6:
                            return db_answer
    except Exception as e:
        print(f"Ошибка чтения базы: {e}")
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
    bot.send_chat_action(message.chat.id, 'typing')
    
    # 1. ИЩЕМ ГОТОВЫЙ ОТВЕТ
    exact_answer = find_exact_answer(message.text)
    
    if exact_answer:
        final_reply = clean_text(exact_answer) + SIGNATURE
        bot.reply_to(message, final_reply)
        return

    # 2. ЕСЛИ НЕТ, ИДЕМ В НЕЙРОСЕТЬ
    context = get_context_for_ai(message.text)
    
    system_prompt = f"""Ты — строгий консультант магазина "Скутер Персонал".
Отвечай, используя ТОЛЬКО предоставленный контекст и шаблоны.

{context}

КРИТИЧЕСКИЕ ПРАВИЛА:
1. НИКОГДА не превращай коды двигателей (например, 1E40QMB, 139QMB) в цифры (140, 139). Это коды, а не объем.
2. НЕ ЗАДАВАЙ ВОПРОСОВ. Не проси фото или замеры.
3. Если точной информации нет, используй ШАБЛОН_НЕИЗВЕСТНО из списка выше.
4. Ответ — максимум 3 предложения.

ЗАПРЕТЫ: Никаких ссылок, скобок и слова "Источник".
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
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60)
        response_data = response.json()
        
        if 'choices' in response_data:
            ai_reply = response_data['choices'][0]['message']['content'].strip()
            ai_reply = clean_text(ai_reply)
            
            if len(ai_reply) < 15:
                ai_reply = "По названию модели нельзя достоверно установить исполнение. Этот товар рассчитан на параметры, указанные в карточке."

            if not ai_reply.lower().startswith("здравствуйте") and not ai_reply.lower().startswith("извините"):
                ai_reply = "Здравствуйте! " + ai_reply
                
            bot.reply_to(message, ai_reply + SIGNATURE)
        else:
            bot.reply_to(message, "Здравствуйте! По названию модели нельзя достоверно установить исполнение." + SIGNATURE)
            
    except Exception as e:
        bot.reply_to(message, "Здравствуйте! Извините, сервис временно недоступен." + SIGNATURE)

print("БОТ V7 ЗАПУЩЕН!")
bot.polling(non_stop=True)
