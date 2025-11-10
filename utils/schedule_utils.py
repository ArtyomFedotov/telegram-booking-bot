from datetime import datetime, date, timedelta, time
from database.models import session, WorkingSlot, Appointment
import math

def get_available_times(user_id, selected_date, service_duration=60):
    """Получает доступное время для записи на указанную дату"""
    
    # Получаем рабочие слоты на эту дату
    working_slots = session.query(WorkingSlot).filter_by(
        user_id=user_id,
        date=selected_date
    ).order_by(WorkingSlot.start_time).all()
    
    if not working_slots:
        return []
    
    available_times = []
    
    for slot in working_slots:
        start_hour, start_minute = map(int, slot.start_time.split(':'))
        end_hour, end_minute = map(int, slot.end_time.split(':'))
        
        slot_start = datetime.combine(selected_date, time(start_hour, start_minute))
        slot_end = datetime.combine(selected_date, time(end_hour, end_minute))
        
        # Генерируем временные слоты с интервалом service_duration минут
        current_time = slot_start
        while current_time + timedelta(minutes=service_duration) <= slot_end:
            # Проверяем не занято ли это время
            if is_time_available(user_id, current_time, service_duration):
                available_times.append(current_time)
            
            current_time += timedelta(minutes=30)  # Шаг 30 минут
    
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
    
    return len(existing_appointments) == 0

def get_available_dates(user_id, days_ahead=14):
    """Получает доступные даты для записи (упрощенная версия)"""
    today = date.today()
    available_dates = []
    
    for i in range(days_ahead):
        check_date = today + timedelta(days=i)
        
        # Проверяем есть ли рабочие слоты на эту дату
        working_slots = session.query(WorkingSlot).filter_by(
            user_id=user_id,
            date=check_date
        ).all()
        
        if working_slots:
            # Для упрощения считаем дату доступной если есть рабочие слоты
            available_dates.append(check_date)
    
    return available_dates