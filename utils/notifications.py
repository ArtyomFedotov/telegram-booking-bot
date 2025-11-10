from datetime import datetime, timedelta
from database.models import session, Appointment, UserSettings
import asyncio

async def send_reminders(context):
    """Отправка напоминаний о записях"""
    from telegram import Bot
    from database.models import Client, Service, User
    
    # Находим записи, до которых осталось X часов
    now = datetime.now()
    appointments = session.query(Appointment).filter(
        Appointment.datetime >= now,
        Appointment.status == 'booked'
    ).all()
    
    for appointment in appointments:
        # Получаем настройки мастера
        settings = session.query(UserSettings).filter_by(user_id=appointment.user_id).first()
        if not settings or not settings.notifications_enabled:
            continue
        
        # Проверяем время до записи
        time_diff = appointment.datetime - now
        hours_diff = time_diff.total_seconds() / 3600
        
        if 0 < hours_diff <= settings.reminder_before_hours:
            # Отправляем напоминание
            client = session.query(Client).filter_by(id=appointment.client_id).first()
            service = session.query(Service).filter_by(id=appointment.service_id).first()
            master = session.query(User).filter_by(id=appointment.user_id).first()
            
            reminder_text = (
                f"⏰ Напоминание о записи!\n\n"
                f"📅 {appointment.datetime.strftime('%d.%m.%Y')}\n"
                f"🕐 {appointment.datetime.strftime('%H:%M')}\n"
                f"📌 {service.name}\n"
                f"👨‍💼 {master.full_name}\n"
                f"📞 {master.phone}\n\n"
                f"Не забудьте о визите!"
            )
            
            # Здесь нужно добавить логику отправки клиенту
            # Для этого нужно хранить telegram_id клиентов
            print(f"REMINDER: {reminder_text}")  # Заглушка

def setup_scheduler(application):
    """Настройка планировщика для уведомлений"""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_reminders, 'interval', hours=1, args=[application])
    scheduler.start()