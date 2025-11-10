from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from database.models import Client, Appointment, Service, session, User, PremiumSubscription
from keyboards import get_clients_keyboard, get_back_keyboard, get_cancel_keyboard, get_main_keyboard
from datetime import datetime, timedelta
import re

# States для добавления клиента
CLIENT_NAME, CLIENT_PHONE = range(2)

async def clients_menu(update: Update, context: CallbackContext):
    """Меню управления клиентами"""
    await update.message.reply_text(
        "👥 Управление клиентами и записями\n\n"
        "Здесь вы можете управлять клиентами и их записями",
        reply_markup=get_clients_keyboard()
    )

async def show_my_clients(update: Update, context: CallbackContext):
    """Показывает список клиентов пользователя"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    clients = session.query(Client).filter_by(user_id=user.id).all()
    
    if not clients:
        await update.message.reply_text(
            "📝 У вас пока нет клиентов\n\n"
            "Добавьте первого клиента с помощью кнопки '➕ Добавить клиента'",
            reply_markup=get_clients_keyboard()
        )
        return
    
    clients_text = "👥 Ваши клиенты:\n\n"
    for i, client in enumerate(clients, 1):
        clients_text += f"{i}. {client.name}\n"
        clients_text += f"   📞 {client.phone}\n"
        if client.notes:
            clients_text += f"   📝 {client.notes}\n"
        clients_text += "\n"
    
    await update.message.reply_text(clients_text, reply_markup=get_clients_keyboard())

async def add_client_start(update: Update, context: CallbackContext):
    """Начало процесса добавления клиента"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    # Проверяем лимит клиентов для бесплатных пользователей
    premium = session.query(PremiumSubscription).filter_by(user_id=user.id, is_active=True).first()
    if not premium:
        clients_count = session.query(Client).filter_by(user_id=user.id).count()
        if clients_count >= 10:  # Лимит 10 клиентов для бесплатной версии
            await update.message.reply_text(
                "❌ **Достигнут лимит клиентов!**\n\n"
                "В бесплатной версии можно добавить не более 10 клиентов.\n\n"
                "💎 **PRO версия включает:**\n"
                "• Неограниченное количество клиентов\n"
                "• Неограниченное количество услуг\n\n"
                "Всего за 299₽/мес!",
                reply_markup=get_clients_keyboard(),
                parse_mode='Markdown'
            )
            return ConversationHandler.END
    
    await update.message.reply_text(
        "➕ Добавление нового клиента\n\n"
        "Введите имя клиента:",
        reply_markup=get_cancel_keyboard()
    )
    return CLIENT_NAME

async def add_client_name(update: Update, context: CallbackContext):
    """Получаем имя клиента"""
    if update.message.text == '❌ Отмена':
        await clients_menu(update, context)
        return ConversationHandler.END
    
    context.user_data['client_name'] = update.message.text
    
    await update.message.reply_text(
        "📞 Введите номер телефона клиента:",
        reply_markup=get_cancel_keyboard()
    )
    return CLIENT_PHONE

async def add_client_phone(update: Update, context: CallbackContext):
    """Получаем телефон клиента"""
    if update.message.text == '❌ Отмена':
        await clients_menu(update, context)
        return ConversationHandler.END
    
    context.user_data['client_phone'] = update.message.text
    
    # Сохраняем клиента в базу
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    new_client = Client(
        user_id=user.id,
        name=context.user_data['client_name'],
        phone=context.user_data['client_phone']
    )
    
    session.add(new_client)
    session.commit()
    
    await update.message.reply_text(
        f"✅ Клиент добавлен!\n\n"
        f"👤 {new_client.name}\n"
        f"📞 {new_client.phone}",
        reply_markup=get_clients_keyboard()
    )
    
    # Очищаем временные данные
    context.user_data.clear()
    return ConversationHandler.END

async def show_all_appointments(update: Update, context: CallbackContext):
    """Показывает все записи пользователя"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    appointments = session.query(Appointment).filter_by(user_id=user.id).order_by(Appointment.datetime).all()
    
    if not appointments:
        await update.message.reply_text(
            "📅 У вас пока нет записей\n\n"
            "Записи появятся здесь после бронирования клиентов",
            reply_markup=get_clients_keyboard()
        )
        return
    
    appointments_text = "📅 Все записи:\n\n"
    for i, appointment in enumerate(appointments, 1):
        client = session.query(Client).filter_by(id=appointment.client_id).first()
        service = session.query(Service).filter_by(id=appointment.service_id).first()
        
        appointments_text += f"{i}. {client.name if client else 'Неизвестный клиент'}\n"
        appointments_text += f"   📌 {service.name if service else 'Неизвестная услуга'}\n"
        appointments_text += f"   🕐 {appointment.datetime.strftime('%d.%m.%Y %H:%M')}\n"
        appointments_text += f"   📊 Статус: {appointment.status}\n\n"
    
    await update.message.reply_text(appointments_text, reply_markup=get_clients_keyboard())

async def cancel_client_creation(update: Update, context: CallbackContext):
    """Отмена создания клиента"""
    await update.message.reply_text(
        "❌ Добавление клиента отменено",
        reply_markup=get_clients_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END