from telegram import Update
from telegram.ext import CallbackContext
from database.models import session, User, Appointment, Client, Service
from utils.master_utils import generate_master_link, get_master_link
from keyboards import get_main_keyboard
from datetime import datetime

async def get_booking_link(update: Update, context: CallbackContext):
    """Показывает ссылку для записи клиентов"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    link_code = generate_master_link(user.id)
    bot_username = context.bot.username
    booking_link = f"https://t.me/{bot_username}?start={link_code}"
    
    await update.message.reply_text(
        f"🔗 Ваша ссылка для записи клиентов:\n\n"
        f"`{booking_link}`\n\n"
        f"Отправьте эту ссылку вашим клиентам для быстрой записи!\n\n"
        f"📊 Статистика:\n"
        f"• Клиенты могут выбирать услуги\n"
        f"• Видеть ваше расписание\n"
        f"• Записываться в удобное время\n"
        f"• Автоматически сохраняться в вашу базу",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )

async def show_client_appointments(update: Update, context: CallbackContext):
    """Показывает записи клиентов к мастеру"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    # Ближайшие записи
    upcoming_appointments = session.query(Appointment).filter(
        Appointment.user_id == user.id,
        Appointment.datetime >= datetime.now(),
        Appointment.status == 'booked'
    ).order_by(Appointment.datetime).all()
    
    if not upcoming_appointments:
        await update.message.reply_text(
            "📭 У вас нет предстоящих записей",
            reply_markup=get_main_keyboard()
        )
        return
    
    appointments_text = "📅 Ваши ближайшие записи:\n\n"
    
    for appt in upcoming_appointments[:10]:  # Показываем первые 10 записей
        client = session.query(Client).filter_by(id=appt.client_id).first()
        service = session.query(Service).filter_by(id=appt.service_id).first()
        
        appointments_text += (
            f"📌 {service.name}\n"
            f"👤 {client.name} ({client.phone})\n"
            f"📅 {appt.datetime.strftime('%d.%m.%Y %H:%M')}\n"
            f"💰 {service.price}₃\n"
            f"──────────────\n"
        )
    
    await update.message.reply_text(
        appointments_text,
        reply_markup=get_main_keyboard()
    )