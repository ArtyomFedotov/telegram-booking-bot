from datetime import datetime, timedelta, date, time
from database.models import WorkingSlot, Appointment, session
import math

def generate_simple_calendar_dates():
    """Генерирует список дат на ближайшие 14 дней"""
    dates = []
    today = date.today()
    
    for i in range(14):
        current_date = today + timedelta(days=i)
        dates.append([current_date.strftime("%d.%m.%Y (%A)")])
    
    dates.append(['🔙 Назад'])
    return dates

def get_available_dates(user_id, days_ahead=14):
    """Получает доступные даты для мастера"""
    available_dates = []
    today = date.today()
    
    for i in range(days_ahead):
        current_date = today + timedelta(days=i)
        
        # Проверяем есть ли рабочие слоты на эту дату (только не заблокированные)
        slots = session.query(WorkingSlot).filter_by(
            user_id=user_id, 
            date=current_date,
            is_blocked=False
        ).all()
        
        if slots:
            # Проверяем есть ли свободное время в этих слотах
            available_times = get_available_times(user_id, current_date)
            if available_times:
                available_dates.append(current_date)
    
    return available_dates

def get_available_times(user_id, selected_date, service_duration=60):
    """Получает доступное время для записи на указанную дату"""
    
    # Получаем только рабочие слоты (не заблокированные)
    working_slots = session.query(WorkingSlot).filter_by(
        user_id=user_id,
        date=selected_date,
        is_blocked=False
    ).order_by(WorkingSlot.start_time).all()
    
    if not working_slots:
        return []
    
    available_times = []
    
    for slot in working_slots:
        start_hour, start_minute = map(int, slot.start_time.split(':'))
        end_hour, end_minute = map(int, slot.end_time.split(':'))
        
        slot_start = datetime.combine(selected_date, time(start_hour, start_minute))
        slot_end = datetime.combine(selected_date, time(end_hour, end_minute))
        
        # Генерируем временные слоты с интервалом 30 минут
        current_time = slot_start
        while current_time + timedelta(minutes=service_duration) <= slot_end:
            # Проверяем не занято ли это время
            if is_time_available(user_id, current_time, service_duration):
                available_times.append(current_time)
            
            current_time += timedelta(minutes=30)
    
    return available_times

def is_time_available(user_id, appointment_time, service_duration=60):
    """Проверяет доступно ли время для записи"""
    
    # Проверяем существующие записи
    existing_appointments = session.query(Appointment).filter(
        Appointment.user_id == user_id,
        Appointment.datetime >= appointment_time - timedelta(minutes=service_duration - 1),
        Appointment.datetime < appointment_time + timedelta(minutes=service_duration),
        Appointment.status == 'booked'
    ).all()
    
    if existing_appointments:
        return False
    
    # Проверяем что время не заблокировано
    selected_date = appointment_time.date()
    appointment_end = appointment_time + timedelta(minutes=service_duration)
    
    # Проверяем пересечение с заблокированными слотами
    blocked_slots = session.query(WorkingSlot).filter(
        WorkingSlot.user_id == user_id,
        WorkingSlot.date == selected_date,
        WorkingSlot.is_blocked == True
    ).all()
    
    for slot in blocked_slots:
        slot_start = datetime.combine(selected_date, datetime.strptime(slot.start_time, '%H:%M').time())
        slot_end = datetime.combine(selected_date, datetime.strptime(slot.end_time, '%H:%M').time())
        
        # Если есть пересечение с заблокированным слотом - время недоступно
        if not (appointment_end <= slot_start or appointment_time >= slot_end):
            return False
    
    # Проверяем что время попадает в рабочий слот
    working_slots = session.query(WorkingSlot).filter(
        WorkingSlot.user_id == user_id,
        WorkingSlot.date == selected_date,
        WorkingSlot.is_blocked == False
    ).all()
    
    for slot in working_slots:
        slot_start = datetime.combine(selected_date, datetime.strptime(slot.start_time, '%H:%M').time())
        slot_end = datetime.combine(selected_date, datetime.strptime(slot.end_time, '%H:%M').time())
        
        # Проверяем что вся запись помещается в рабочий слот
        if (appointment_time >= slot_start and appointment_end <= slot_end):
            return True
    
    return False

def get_working_hours_for_date(user_id, selected_date):
    """Получает рабочие часы на конкретную дату"""
    slots = session.query(WorkingSlot).filter_by(
        user_id=user_id,
        date=selected_date,
        is_blocked=False
    ).order_by(WorkingSlot.start_time).all()
    
    return slots

def has_working_slots(user_id, selected_date):
    """Проверяет есть ли рабочие слоты на указанную дату"""
    slots = session.query(WorkingSlot).filter_by(
        user_id=user_id,
        date=selected_date,
        is_blocked=False
    ).first()
    
    return slots is not None