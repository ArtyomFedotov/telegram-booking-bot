from telegram import Update
from telegram.ext import CallbackContext
from database.models import session, User, Client, Appointment, Service
from keyboards import get_clients_keyboard, get_main_keyboard
from datetime import datetime

async def clients_menu(update: Update, context: CallbackContext):
    """Меню управления клиентами"""
    await update.message.reply_text(
        "👥 Управление клиентами\n\n"
        "Выберите действие:",
        reply_markup=get_clients_keyboard()
    )

async def show_my_clients(update: Update, context: CallbackContext):
    """Показывает список клиентов мастера"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    clients = session.query(Client).filter_by(user_id=user.id).all()
    
    if not clients:
        await update.message.reply_text(
            "👥 У вас пока нет клиентов\n\n"
            "Клиенты появятся здесь после их первой записи",
            reply_markup=get_clients_keyboard()
        )
        return
    
    clients_text = "👥 Ваши клиенты:\n\n"
    
    for i, client in enumerate(clients, 1):
        # Считаем количество записей клиента
        appointments_count = session.query(Appointment).filter_by(
            user_id=user.id, 
            client_id=client.id
        ).count()
        
        # Последняя запись
        last_appointment = session.query(Appointment).filter_by(
            user_id=user.id, 
            client_id=client.id
        ).order_by(Appointment.datetime.desc()).first()
        
        clients_text += f"{i}. {client.name}\n"
        clients_text += f"   📞 {client.phone}\n"
        clients_text += f"   📅 Записей: {appointments_count}\n"
        
        if last_appointment:
            clients_text += f"   🗓️ Последняя: {last_appointment.datetime.strftime('%d.%m.%Y')}\n"
        
        clients_text += "\n"
    
    await update.message.reply_text(
        clients_text,
        reply_markup=get_clients_keyboard()
    )

async def show_client_appointments(update: Update, context: CallbackContext):
    """Показывает все записи клиентов"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    # Активные записи (будущие)
    active_appointments = session.query(Appointment).filter(
        Appointment.user_id == user.id,
        Appointment.datetime >= datetime.now(),
        Appointment.status == 'booked'
    ).order_by(Appointment.datetime).all()
    
    if not active_appointments:
        await update.message.reply_text(
            "📭 У вас нет активных записей\n\n"
            "Новые записи появятся здесь после бронирования клиентов",
            reply_markup=get_clients_keyboard()
        )
        return
    
    appointments_text = "📅 Активные записи:\n\n"
    
    for appt in active_appointments:
        client = session.query(Client).filter_by(id=appt.client_id).first()
        
        appointments_text += f"👤 {client.name} ({client.phone})\n"
        appointments_text += f"📅 {appt.datetime.strftime('%d.%m.%Y %H:%M')}\n"
        appointments_text += f"──────────────\n"
    
    await update.message.reply_text(
        appointments_text,
        reply_markup=get_clients_keyboard()
    )

async def show_all_appointments(update: Update, context: CallbackContext):
    """Показывает все записи (историю)"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    # Все записи
    all_appointments = session.query(Appointment).filter_by(
        user_id=user.id
    ).order_by(Appointment.datetime.desc()).limit(10).all()
    
    if not all_appointments:
        await update.message.reply_text(
            "📋 У вас пока нет записей",
            reply_markup=get_clients_keyboard()
        )
        return
    
    appointments_text = "📋 История записей:\n\n"
    
    for appt in all_appointments:
        client = session.query(Client).filter_by(id=appt.client_id).first()
        status_emoji = "✅" if appt.status == 'completed' else "📅" if appt.status == 'booked' else "❌"
        
        appointments_text += f"{status_emoji} {client.name}\n"
        appointments_text += f"   📅 {appt.datetime.strftime('%d.%m.%Y %H:%M')}\n"
        appointments_text += f"   🏷️ {appt.status}\n"
        appointments_text += f"──────────────\n"
    
    await update.message.reply_text(
        appointments_text,
        reply_markup=get_clients_keyboard()
    )

async def show_my_appointments_handler(update: Update, context: CallbackContext):
    """Обработчик для кнопки 'Мои записи' в главном меню"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    # Активные записи (будущие)
    active_appointments = session.query(Appointment).filter(
        Appointment.user_id == user.id,
        Appointment.datetime >= datetime.now(),
        Appointment.status == 'booked'
    ).order_by(Appointment.datetime).all()
    
    if not active_appointments:
        await update.message.reply_text(
            "📭 У вас нет активных записей\n\n"
            "Новые записи появятся здесь после бронирования клиентов",
            reply_markup=get_main_keyboard()
        )
        return
    
    appointments_text = "📅 Ваши ближайшие записи:\n\n"
    
    for appt in active_appointments:
        client = session.query(Client).filter_by(id=appt.client_id).first()
        service = session.query(Service).filter_by(id=appt.service_id).first()
        
        appointments_text += (
            f"📌 {service.name if service else 'Услуга не найдена'}\n"
            f"👤 {client.name if client else 'Клиент не найден'} ({client.phone if client else 'Нет телефона'})\n"
            f"📅 {appt.datetime.strftime('%d.%m.%Y %H:%M')}\n"
            f"──────────────\n"
        )
    
    await update.message.reply_text(
        appointments_text,
        reply_markup=get_main_keyboard()
    )