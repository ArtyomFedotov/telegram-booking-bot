from telegram import Update
from telegram.ext import CallbackContext
from database.models import session, Client, Appointment
from keyboards import get_client_main_keyboard
from datetime import datetime

async def client_profile(update: Update, context: CallbackContext):
    """Профиль клиента"""
    # Ищем клиента по telegram_id
    client = session.query(Client).filter_by(telegram_id=update.effective_user.id).first()
    
    if not client:
        await update.message.reply_text(
            "👋 Для доступа к профилю клиента сначала запишитесь к мастеру через его ссылку.",
            reply_markup=get_client_main_keyboard()
        )
        return
    
    # Получаем будущие записи клиента
    appointments = session.query(Appointment).filter(
        Appointment.client_id == client.id,
        Appointment.datetime >= datetime.now(),
        Appointment.status == 'booked'
    ).order_by(Appointment.datetime).all()
    
    profile_text = (
        f"👤 Ваш профиль\n\n"
        f"📛 Имя: {client.name}\n"
        f"📞 Телефон: {client.phone}\n"
        f"🔔 Уведомления: {'✅ ВКЛЮЧЕНЫ' if client.telegram_id else '❌ ОТКЛЮЧЕНЫ'}\n\n"
    )
    
    if appointments:
        profile_text += "📅 Ваши ближайшие записи:\n"
        for appt in appointments[:3]:  # Показываем 3 ближайшие записи
            profile_text += f"• {appt.datetime.strftime('%d.%m.%Y %H:%M')}\n"
    else:
        profile_text += "📭 У вас нет активных записей\n"
    
    await update.message.reply_text(
        profile_text,
        reply_markup=get_client_main_keyboard()
    )