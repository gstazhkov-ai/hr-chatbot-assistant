import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Область доступа: чтение и запись в календарь
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    """Подключается к API и возвращает сервис для работы с календарем."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES) # Убедись, что файл credentials.json лежит рядом
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return build('calendar', 'v3', credentials=creds)

def find_free_slots(service, start_time, end_time, duration_minutes=30):
    """Находит свободные слоты в календаре."""
    time_min = start_time.isoformat()
    time_max = end_time.isoformat()

    events_result = service.events().list(
        calendarId='primary', 
        timeMin=time_min,
        timeMax=time_max, 
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    
    free_slots = []
    check_time = start_time

    while check_time + datetime.timedelta(minutes=duration_minutes) <= end_time:
        is_free = True
        slot_end_time = check_time + datetime.timedelta(minutes=duration_minutes)

        for event in events:
            event_start = datetime.datetime.fromisoformat(event['start'].get('dateTime').replace('Z', '+00:00'))
            event_end = datetime.datetime.fromisoformat(event['end'].get('dateTime').replace('Z', '+00:00'))

            if max(check_time, event_start) < min(slot_end_time, event_end):
                is_free = False
                break
        
        if is_free:
            free_slots.append(check_time.strftime("%d %B %Y в %H:%M"))
            if len(free_slots) >= 3: # Предложим 3 варианта
                break
        
        check_time += datetime.timedelta(minutes=duration_minutes)
        
    return free_slots

def create_event(service, start_time, end_time, summary, description, attendees_emails):
    """Создает событие в календаре."""
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Europe/Moscow', # Укажи свой часовой пояс
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'Europe/Moscow',
        },
        'attendees': [{'email': email} for email in attendees_emails],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 30},
            ],
        },
    }
    
    created_event = service.events().insert(calendarId='primary', body=event).execute()
    print(f"Встреча создана: {created_event.get('htmlLink')}")
    return created_event