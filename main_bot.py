import google.generativeai as genai
import datetime
from calendar_manager import get_calendar_service, find_free_slots, create_event

# Вставь свой API ключ от Gemini
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY" 
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def get_bot_response(hr_message, free_slots):
    """Генерирует ответ HR-у с помощью Gemini."""
    
    # Это сердце нашего бота. Детальный промпт определяет его поведение.
    prompt = f"""
    Ты — мой вежливый и профессиональный AI-ассистент. Твоя задача — отвечать на сообщения от HR-менеджеров.

    Вот сообщение, которое я получил:
    ---
    {hr_message}
    ---

    Мои доступные временные слоты для интервью на ближайшие дни:
    {', '.join(free_slots)}

    Твои задачи:
    1.  Поблагодари за предложение и прояви интерес к вакансии.
    2.  Вежливо предложи доступные временные слоты для короткого онлайн-созвона (30 минут).
    3.  Заверши сообщение позитивной нотой, указав, что ждешь их ответа для подтверждения.
    4.  Твой ответ должен быть кратким, профессиональным и дружелюбным. Не используй сленг.
    
    Пример твоего ответа:
    "Здравствуйте! Спасибо большое за ваше сообщение и интерес к моей кандидатуре. Буду рад обсудить детали вакансии.
    Мне было бы удобно созвониться в один из следующих слотов: {free_slots[0]} или {free_slots[1]}.
    Пожалуйста, дайте знать, какой из вариантов вам больше подходит.
    Хорошего дня!"

    Сгенерируй только текст ответа, без лишних комментариев.
    """
    
    response = model.generate_content(prompt)
    return response.text

def main():
    # 1. Получаем входящее сообщение от HR
    hr_message = input("Вставьте сюда сообщение от HR:\n")
    
    # 2. Подключаемся к календарю
    service = get_calendar_service()
    
    # 3. Ищем свободные слоты на ближайшие 5 рабочих дней с 10:00 до 18:00
    now = datetime.datetime.now(datetime.timezone.utc).astimezone()
    start_search_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
    end_search_time = start_search_time + datetime.timedelta(days=5)
    
    available_slots = find_free_slots(service, start_search_time, end_search_time)
    
    if not available_slots:
        print("Не найдено свободных слотов в календаре на ближайшие дни.")
        return
        
    # 4. Генерируем ответ с помощью Gemini
    bot_reply = get_bot_response(hr_message, available_slots)
    
    print("\n--- Сгенерированный ответ для HR ---\n")
    print(bot_reply)
    print("\n------------------------------------\n")
    
    # 5. Спрашиваем, назначать ли встречу
    confirm = input("Отправить этот ответ и назначить встречу, как только HR ответит? (да/нет): ")
    if confirm.lower() == 'да':
        print("Отлично! После того как HR подтвердит время, ты можешь запустить этот скрипт снова, чтобы создать событие.")
        # Здесь в будущем можно добавить логику для автоматического создания события
        # после парсинга ответа от HR, но для начала сделаем это вручную.

if __name__ == '__main__':
    main()
    