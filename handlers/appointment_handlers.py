from telegram import Update
from telegram.ext import CallbackContext
from database.models import session, User, Appointment, Client, Service
from keyboards import get_clients_keyboard, get_main_keyboard
from datetime import datetime

async def delete_appointment_menu(update: Update, context: CallbackContext):
    """Меню удаления записей"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    # Получаем будущие записи
    appointments = session.query(Appointment).filter(
        Appointment.user_id == user.id,
        Appointment.datetime >= datetime.now(),
        Appointment.status == 'booked'
    ).order_by(Appointment.datetime).all()
    
    if not appointments:
        await update.message.reply_text(
            "📭 У вас нет активных записей для удаления",
            reply_markup=get_clients_keyboard()
        )
        return
    
    appointments_text = "🗑️ Выберите запись для удаления:\n\n"
    keyboard = []
    
    for i, appointment in enumerate(appointments, 1):
        client = session.query(Client).filter_by(id=appointment.client_id).first()
        service = session.query(Service).filter_by(id=appointment.service_id).first()
        
        appointments_text += f"{i}. {client.name} - {service.name}\n"
        appointments_text += f"   📅 {appointment.datetime.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        keyboard.append([f"🗑️ {i}. {client.name} - {appointment.datetime.strftime('%d.%m.%Y %H:%M')}"])
    
    keyboard.append(['🔙 Назад'])
    
    from telegram import ReplyKeyboardMarkup
    await update.message.reply_text(
        appointments_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    
    context.user_data['appointments_to_delete'] = {i: appointment.id for i, appointment in enumerate(appointments, 1)}

async def delete_appointment(update: Update, context: CallbackContext):
    """Удаление выбранной записи"""
    if update.message.text == '🔙 Назад':
        await update.message.reply_text(
            "Возврат в меню клиентов",
            reply_markup=get_clients_keyboard()
        )
        return
    
    try:
        # Извлекаем номер из текста (формат: "🗑️ 1. Имя - Дата")
        appointment_number = int(update.message.text.split('.')[0].replace('🗑️', '').strip())
        
        if appointment_number not in context.user_data['appointments_to_delete']:
            await update.message.reply_text("❌ Неверный номер записи. Выберите из списка:")
            return
        
        appointment_id = context.user_data['appointments_to_delete'][appointment_number]
        appointment = session.query(Appointment).filter_by(id=appointment_id).first()
        
        if appointment:
            client = session.query(Client).filter_by(id=appointment.client_id).first()
            service = session.query(Service).filter_by(id=appointment.service_id).first()
            
            session.delete(appointment)
            session.commit()
            
            await update.message.reply_text(
                f"✅ Запись удалена!\n\n"
                f"👤 {client.name}\n"
                f"📌 {service.name}\n"
                f"📅 {appointment.datetime.strftime('%d.%m.%Y %H:%M')}",
                reply_markup=get_clients_keyboard()
            )
        else:
            await update.message.reply_text("❌ Запись не найдена")
            
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Неверный формат. Выберите запись из списка:")