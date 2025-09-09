# app.py

import os
import re
import datetime
from flask import Flask, render_template, request, jsonify

# Импортируем наши функции и Gemini
import google.generativeai as genai
from calendar_manager import get_calendar_service, find_free_slots

app = Flask(__name__)

# --- НАСТРОЙКИ ---
# Использую предоставленный вами ключ API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-pro') # Используем стабильную версию модели
# --- КОНЕЦ НАСТРОЕК ---

def parse_time_from_message(message):
    """Ищет в сообщении время в формате ЧЧ:ММ или ЧЧ-ММ."""
    match = re.search(r'в (\d{1,2}[:\-]\d{2})|(\d{1,2}) часов', message)
    if match:
        time_str = match.group(1) or f"{match.group(2)}:00"
        try:
            return datetime.datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            return None
    return None

def is_slot_free(service, check_time):
    """Проверяет, свободен ли конкретный 30-минутный слот."""
    start_time = check_time
    end_time = start_time + datetime.timedelta(minutes=30)
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_time.isoformat(), # Исправлено: убран 'Z'
        timeMax=end_time.isoformat(),   # Исправлено: убран 'Z'
        singleEvents=True
    ).execute()
    
    return not events_result.get('items', [])

def get_smart_response(message):
    """
    Обрабатывает сообщение с эмпатией: сначала простые правила, 
    затем анализ намерения, и только потом Gemini.
    """
    message_lower = message.lower()
    
    # --- Шаг 1: Простые и быстрые ответы ---
    
    # Ответ на простое приветствие
    if message_lower.strip() in ["здравствуйте", "добрый день", "приветствую"]:
        return "Здравствуйте!"
        
    # Ответ на социальный вопрос
    if "как дела" in message_lower:
        return "Спасибо, все отлично! Как ваши дела?"

    # Ответ на прощание
    if any(word in message_lower for word in ["до свидания", "всего доброго"]):
        return "Всего доброго!"

    # --- Шаг 2: Анализ намерения (нужно ли назначать встречу?) ---

    # Ключевые слова, указывающие на желание назначить встречу
    scheduling_keywords = [
        "созвониться", "встретиться", "интервью", "собеседование", 
        "удобно", "время", "слот", "календарь", "обсудить голосом"
    ]

    is_scheduling_request = any(keyword in message_lower for keyword in scheduling_keywords)

    # --- Шаг 3: Вызов Gemini с правильным контекстом ---
    
    prompt = ""
    if is_scheduling_request:
        # Если HR хочет назначить встречу, находим слоты и просим Gemini их предложить
        print("Обнаружен запрос на планирование встречи. Ищу слоты...")
        try:
            service = get_calendar_service()
            now = datetime.datetime.now(datetime.timezone.utc).astimezone()
            start_search = now.replace(hour=10, minute=0, second=0)
            end_search = start_search + datetime.timedelta(days=7)
            free_slots = find_free_slots(service, start_search, end_search)

            if not free_slots:
                return "К сожалению, в календаре нет свободных слотов на ближайшую неделю."

            prompt = f"""
            Ты — мой вежливый и профессиональный AI-ассистент. Твоя задача — отвечать на сообщения от HR.
            HR хочет назначить встречу.

            Сообщение от HR:
            ---
            {message}
            ---

            Мои доступные слоты: {', '.join(free_slots)}

            Твоя задача:
            1. Ответь на сообщение HR вежливо и по существу.
            2. Естественно впиши в свой ответ предложение о встрече, используя доступные слоты. 
            3. Не вываливай все слоты списком. Предложи 2-3 варианта в формате живого диалога.
               Например: "Да, конечно. Мне было бы удобно, например, в Понедельник в 11:00 или в Среду в 14:30. Подходит ли вам один из этих вариантов?"
            4. Будь дружелюбным и профессиональным. Сгенерируй только текст ответа.
            """
        except Exception as e:
            print(f"Ошибка при работе с календарем: {e}")
            return "Произошла ошибка при доступе к календарю. Пожалуйста, проверьте настройки."
    else:
        # Если это простое сообщение (описание вакансии, вопрос и т.д.), отвечаем без предложения слотов
        print("Обычное сообщение. Отвечаю без поиска слотов...")
        prompt = f"""
        Ты — мой вежливый и профессиональный AI-ассистент. Твоя задача — отвечать на сообщения от HR.
        Это НЕ запрос на назначение встречи.

        Сообщение от HR:
        ---
        {message}
        ---

        Твоя задача:
        1. Внимательно прочти сообщение и ответь на него по существу.
        2. Прояви интерес и будь позитивным.
        3. НЕ ПРЕДЛАГАЙ время для встречи или созвона, если об этом прямо не просят.
        4. Задай уточняющий вопрос, если это уместно.
        5. Сгенерируй только текст ответа.
        """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Ошибка при вызове Gemini API: {e}")
        return "Произошла ошибка при обработке вашего запроса. Пожалуйста, убедитесь, что ваш API ключ действителен и активен."


@app.route('/')
def index():
    """Отображает главную страницу."""
    return render_template('index.html')

@app.route('/process_message', methods=['POST'])
def process_message():
    """Принимает сообщение от пользователя и возвращает ответ бота."""
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'reply': 'Пожалуйста, введите сообщение.'}), 400
    
    bot_reply = get_smart_response(user_message)
    return jsonify({'reply': bot_reply})

if __name__ == '__main__':
    app.run(debug=True)