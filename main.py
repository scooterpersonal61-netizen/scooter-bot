import telebot
import os
import requests
import re

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')

bot = telebot.TeleBot(TOKEN)
SIGNATURE = "\n\nС уважением, представители магазина Скутер Персонал."

def clean_text(text):
    """Очистка от мусора, ссылок и лишних символов"""
    text = re.sub(r'https?://\S+|www\.\S+', '', text)
    text = re.sub(r'\b\w+\.(ru|ua|com|net|org|info|biz|eu)\b', '', text, flags=re.IGNORECASE)
    # Оставляем только русские буквы, цифры и базовую пунктуацию
    text = re.sub(r'[^а-яА-ЯёЁ0-9\s.,!?-]', '', text)
    text = re.sub(r'\.\s*\.', '.', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def find_exact_answer(user_text):
    """Ищет точный ответ в разделе ГОТОВЫЕ АВТОНОМНЫЕ ОТВЕТЫ"""
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Ищем блок с готовыми ответами
        if "=== ГОТОВЫЕ АВТОНОМНЫЕ ОТВЕТЫ" in content:
            answers_block = content.split("=== ГОТОВЫЕ АВТОНОМНЫЕ ОТВЕТЫ")[1].split("===")[0]
            lines = answers_block.split('\n')
            
            # Приводим вопрос пользователя к нижнему регистру для поиска
            search_text = user_text.lower()
            
            for line in lines:
                if "ВОПРОС |" in line and "ОТВЕТ |" in line:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        db_question = parts[1].strip().lower()
                        db_answer = parts[2].replace("ОТВЕТ", "").strip()
                        
                        # Если ключевые слова из базы совпадают с вопросом пользователя
                        # (проверяем, есть ли в вопросе пользователя 2+ слова из базы)
                        db_words = [w for w in re.findall(r'\w+', db_question) if len(w) > 2]
                        matches = sum(1 for w in db_words if w in search_text)
                        
                        if matches >= 2 or (len(db_words) > 0 and db_words[0] in search_text and len(db_words) <= 2):
                            return db_answer
    except Exception as e:
        print(f"Ошибка чтения базы: {e}")
    return None

def get_context_for_ai(user_text):
    """Если точного ответа нет, собирает контекст из правил и шаблонов"""
    try:
        with open('knowledge.txt', 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        return "База не найдена"

    words = [w.lower() for w in re.findall(r'\w+', user_text) if len(w) > 2]
    scored_lines = []
    
    for line in lines:
        # Пропускаем пустые строки и ссылки
        if not line.strip() or line.strip().startswith("==="): continue
        clean_line = re.sub(r'https?://\S+', '', line.strip())
        line_lower = clean_line.lower()
        
        matches = sum(1 for word in words if word in line_lower)
        if matches >= 2 or (matches == 1 and any(len(w) > 4 for w in words if w in line_lower)):
            scored_lines.append((matches, clean_line))

    scored_lines.sort(key=lambda x: x[0], reverse=True)
    
    # Берем топ-5 строк + добавляем шаблоны, чтобы ИИ знал, как отвечать
    context = "\n".join([text for _, text in scored_lines[:5]])
    templates = "\n".join([line.strip() for line in lines if "ШАБЛОН_" in line])
    
    return f"КОНТЕКСТ ИЗ БАЗЫ:\n{context}\n\nДОСТУПНЫЕ ШАБЛОНЫ ДЛЯ ОТВЕТА:\n{templates}"

@bot.message_handler(content_types=['text'])
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    # 1. ПЫТАЕМСЯ НАЙТИ ГОТОВЫЙ ОТВЕТ (БЕЗ НЕЙРОСЕТИ)
    exact_answer = find_exact_answer(message.text)
    
    if exact_answer:
        # Если нашли готовый ответ, просто отправляем его
        final_reply = clean_text(exact_answer) + SIGNATURE
        bot.reply_to(message, final_reply)
        return

    # 2. ЕСЛИ ГОТОВОГО НЕТ, ИДЕМ В НЕЙРОСЕТЬ С ЖЕСТКИМИ ПРАВИЛАМИ
    context = get_context_for_ai(message.text)
    
    system_prompt = f"""Ты — робот-консультант магазина "Скутер Персонал".
Твоя задача — дать ответ, используя ТОЛЬКО предоставленный контекст и шаблоны.

{context}

КРИТИЧЕСКИЕ ПРАВИЛА (Нарушение недопустимо):
1. ПРАВИЛО_12: НИКОГДА не задавай встречных вопросов. Не проси фото, VIN или замеры.
2. ПРАВИЛО_6: НЕ ВЫДУМЫВАЙ цифры, объемы (например, "140 кубов") или маркировки, если их нет в контексте.
3. ПРАВИЛО_10: В ответе 1-3 предложения, без воды.
4. Если ты не знаешь точного ответа, используй ШАБЛОН_НЕИЗВЕСТНО или ШАБЛОН_УСЛОВНО из списка выше. Подставь нужную модель.
5. Если деталь конструктивно не подходит (2Т vs 4Т), используй ШАБЛОН_НЕТ.

КАТЕГОРИЧЕСКИЕ ЗАПРЕТЫ:
- Никаких ссылок.
- Никаких скобок и английских слов.
- Никаких фраз "уточните", "пришлите фото".
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek/deepseek-chat", # Отключаем поиск в интернете, чтобы не было мусора
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

print("ИДЕАЛЬНЫЙ БОТ С БАЗОЙ V5 ЗАПУЩЕН!")
bot.polling(non_stop=True)
