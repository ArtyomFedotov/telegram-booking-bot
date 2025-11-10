from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from telegram import ReplyKeyboardMarkup
from database.models import Client, Service, Appointment, session, User, WorkingSlot
from keyboards import get_booking_keyboard, get_clients_choice_keyboard, get_services_choice_keyboard, get_confirm_keyboard, get_back_keyboard, get_clients_keyboard
from datetime import datetime, timedelta
import re

# States для процесса записи
SELECT_CLIENT, SELECT_SERVICE, SELECT_DATE, SELECT_TIME, CONFIRM_BOOKING = range(5)

async def booking_menu(update: Update, context: CallbackContext):
    """Меню управления записями"""
    await update.message.reply_text(
        "📅 Управление записями клиентов\n\n"
        "Здесь вы можете записывать клиентов на услуги",
        reply_markup=get_booking_keyboard()
    )

async def start_booking(update: Update, context: CallbackContext):
    """Начало процесса записи клиента"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    # Получаем список клиентов
    clients = session.query(Client).filter_by(user_id=user.id).all()
    
    if not clients:
        await update.message.reply_text(
            "❌ У вас пока нет клиентов\n\n"
            "Сначала добавьте клиентов в разделе '👥 Клиенты'",
            reply_markup=get_clients_keyboard()
        )
        return ConversationHandler.END
    
    # Получаем список услуг
    services = session.query(Service).filter_by(user_id=user.id).all()
    
    if not services:
        await update.message.reply_text(
            "❌ У вас пока нет услуг\n\n"
            "Сначала добавьте услуги в разделе '💼 Услуги'",
            reply_markup=get_clients_keyboard()
        )
        return ConversationHandler.END
    
    # Сохраняем клиентов и услуги в context
    context.user_data['clients'] = {f"👤 {client.name} - {client.phone}": client.id for client in clients}
    context.user_data['services'] = {f"📌 {service.name} - {service.duration}мин": service.id for service in services}
    
    await update.message.reply_text(
        "👥 Выберите клиента для записи:",
        reply_markup=get_clients_choice_keyboard(clients)
    )
    return SELECT_CLIENT

async def select_client(update: Update, context: CallbackContext):
    """Обработка выбора клиента"""
    if update.message.text == '🔙 Назад':
        await booking_menu(update, context)
        return ConversationHandler.END
    
    client_text = update.message.text
    if client_text not in context.user_data['clients']:
        await update.message.reply_text("Пожалуйста, выберите клиента из списка:")
        return SELECT_CLIENT
    
    context.user_data['selected_client_id'] = context.user_data['clients'][client_text]
    context.user_data['selected_client_text'] = client_text
    
    # Получаем услуги для клавиатуры
    services = [session.query(Service).get(service_id) for service_id in context.user_data['services'].values()]
    
    await update.message.reply_text(
        "📌 Выберите услугу:",
        reply_markup=get_services_choice_keyboard(services)
    )
    return SELECT_SERVICE

async def select_service(update: Update, context: CallbackContext):
    """Обработка выбора услуги"""
    if update.message.text == '🔙 Назад':
        # Получаем список клиентов заново
        user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
        clients = session.query(Client).filter_by(user_id=user.id).all()
        await update.message.reply_text(
            "👥 Выберите клиента для записи:",
            reply_markup=get_clients_choice_keyboard(clients)
        )
        return SELECT_CLIENT
    
    service_text = update.message.text
    if service_text not in context.user_data['services']:
        await update.message.reply_text("Пожалуйста, выберите услугу из списка:")
        return SELECT_SERVICE
    
    context.user_data['selected_service_id'] = context.user_data['services'][service_text]
    context.user_data['selected_service_text'] = service_text
    
    # Получаем доступные даты
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    from utils.calendar_utils import get_available_dates
    available_dates = get_available_dates(user.id, days_ahead=30)
    
    if not available_dates:
        await update.message.reply_text(
            "❌ На ближайшие 30 дней нет рабочих дней\n\n"
            "Сначала настройте расписание в разделе '📅 Управление расписанием'",
            reply_markup=get_clients_keyboard()
        )
        return ConversationHandler.END
    
    # Предлагаем выбрать дату
    date_options = []
    for i, available_date in enumerate(available_dates[:5]):  # Показываем первые 5 доступных дат
        date_options.append([f"📅 {available_date.strftime('%d.%m.%Y (%A)')}"])
    
    date_options.append(['🔙 Назад'])
    
    await update.message.reply_text(
        "📅 Выберите дату записи:",
        reply_markup=ReplyKeyboardMarkup(date_options, resize_keyboard=True)
    )
    
    context.user_data['available_dates'] = available_dates
    return SELECT_DATE

async def select_date(update: Update, context: CallbackContext):
    """Обработка выбора даты"""
    if update.message.text == '🔙 Назад':
        # Возвращаем к выбору услуги
        services = [session.query(Service).get(service_id) for service_id in context.user_data['services'].values()]
        await update.message.reply_text(
            "📌 Выберите услугу:",
            reply_markup=get_services_choice_keyboard(services)
        )
        return SELECT_SERVICE
    
    date_text = update.message.text
    
    try:
        if date_text.startswith('📅 '):
            date_text = date_text[2:]  # Убираем эмодзи
        
        # Ищем дату в доступных датах
        selected_date = None
        for available_date in context.user_data['available_dates']:
            if available_date.strftime('%d.%m.%Y (%A)') == date_text:
                selected_date = available_date
                break
        
        if not selected_date:
            await update.message.reply_text("❌ Выбранная дата недоступна. Выберите дату из списка:")
            return SELECT_DATE
        
        context.user_data['selected_date'] = selected_date
        
        # Получаем доступное время для выбранной даты с учетом длительности услуги
        user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
        service_id = context.user_data['selected_service_id']
        service = session.query(Service).filter_by(id=service_id).first()
        service_duration = service.duration if service else 60
        
        from utils.calendar_utils import get_available_times
        available_times = get_available_times(user.id, selected_date, service_duration)
        
        if not available_times:
            await update.message.reply_text(
                "❌ На выбранную дату нет свободного времени для услуги такой длительности\n"
                "Выберите другую дату:",
                reply_markup=ReplyKeyboardMarkup([
                    ['🔙 Назад']
                ], resize_keyboard=True)
            )
            return SELECT_DATE
        
        # Формируем клавиатуру с временными слотами
        keyboard = []
        row = []
        for i, time_slot in enumerate(available_times):
            row.append(f"🕐 {time_slot.strftime('%H:%M')}")
            if (i + 1) % 3 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append(['🔙 Назад'])
        
        await update.message.reply_text(
            f"🕐 Выберите время записи на {selected_date.strftime('%d.%m.%Y')} "
            f"(услуга: {service_duration} мин):",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        
        context.user_data['available_times'] = available_times
        return SELECT_TIME
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат даты. Выберите дату из списка:")
        return SELECT_DATE

async def select_time(update: Update, context: CallbackContext):
    """Обработка выбора времени и подтверждение записи с учетом длительности услуги"""
    if update.message.text == '🔙 Назад':
        await select_date(update, context)
        return SELECT_DATE
    
    time_text = update.message.text
    if time_text.startswith('🕐 '):
        time_text = time_text[2:]  # Убираем эмодзи
    
    try:
        selected_time = datetime.strptime(time_text, '%H:%M').time()
        selected_date = context.user_data['selected_date']
        appointment_datetime = datetime.combine(selected_date, selected_time)
        
        # Получаем длительность выбранной услуги
        service_id = context.user_data['selected_service_id']
        service = session.query(Service).filter_by(id=service_id).first()
        service_duration = service.duration if service else 60
        
        # Проверяем что время не в прошлом
        if appointment_datetime < datetime.now():
            await update.message.reply_text("❌ Нельзя записать на прошедшее время. Выберите другое время:")
            return SELECT_TIME
        
        # Проверяем доступность времени с учетом длительности услуги
        user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
        from utils.calendar_utils import is_time_available
        if not is_time_available(user.id, appointment_datetime, service_duration):
            await update.message.reply_text(
                f"❌ Время {time_text} уже занято или не подходит для услуги длительностью {service_duration} мин! "
                "Выберите другое время:",
                reply_markup=get_back_keyboard()
            )
            return SELECT_TIME
        
        context.user_data['appointment_datetime'] = appointment_datetime
        context.user_data['service_duration'] = service_duration
        
        # Получаем информацию о клиенте и услуге
        client = session.query(Client).get(context.user_data['selected_client_id'])
        service = session.query(Service).get(context.user_data['selected_service_id'])
        
        confirmation_text = (
            "✅ Подтвердите запись:\n\n"
            f"👤 Клиент: {client.name}\n"
            f"📞 Телефон: {client.phone}\n"
            f"📌 Услуга: {service.name}\n"
            f"⏱️ Продолжительность: {service.duration} мин.\n"
            f"💰 Стоимость: {service.price}₽\n"
            f"📅 Дата: {appointment_datetime.strftime('%d.%m.%Y')}\n"
            f"🕐 Время: {appointment_datetime.strftime('%H:%M')}\n"
            f"⏰ Окончание: {(appointment_datetime + timedelta(minutes=service_duration)).strftime('%H:%M')}\n\n"
            "Подтверждаете запись?"
        )
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=get_confirm_keyboard()
        )
        return CONFIRM_BOOKING
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат времени. Выберите время из списка:")
        return SELECT_TIME

async def confirm_booking(update: Update, context: CallbackContext):
    """Подтверждение и сохранение записи"""
    if update.message.text == '❌ Отменить':
        await booking_menu(update, context)
        context.user_data.clear()
        return ConversationHandler.END
    
    if update.message.text != '✅ Подтвердить запись':
        await update.message.reply_text("Пожалуйста, подтвердите или отмените запись:")
        return CONFIRM_BOOKING
    
    # ПРОВЕРЯЕМ, не занято ли это время (дополнительная проверка)
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    appointment_datetime = context.user_data['appointment_datetime']
    service_duration = context.user_data.get('service_duration', 60)
    
    from utils.calendar_utils import is_time_available
    if not is_time_available(user.id, appointment_datetime, service_duration):
        client = session.query(Client).get(context.user_data['selected_client_id'])
        service = session.query(Service).get(context.user_data['selected_service_id'])
        
        await update.message.reply_text(
            f"❌ Время {appointment_datetime.strftime('%d.%m.%Y %H:%M')} уже занято!\n\n"
            f"Пожалуйста, выберите другое время для записи клиента {client.name} на услугу '{service.name}'.",
            reply_markup=get_clients_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Сохраняем запись в базу
    new_appointment = Appointment(
        user_id=user.id,
        client_id=context.user_data['selected_client_id'],
        service_id=context.user_data['selected_service_id'],
        datetime=appointment_datetime,
        status='booked'
    )
    
    session.add(new_appointment)
    session.commit()
    
    # Получаем информацию для подтверждения
    client = session.query(Client).get(context.user_data['selected_client_id'])
    service = session.query(Service).get(context.user_data['selected_service_id'])
    
    await update.message.reply_text(
        f"🎉 Запись успешно создана!\n\n"
        f"👤 {client.name}\n"
        f"📌 {service.name}\n"
        f"⏱️ {service.duration} мин.\n"
        f"📅 {appointment_datetime.strftime('%d.%m.%Y %H:%M')}\n"
        f"⏰ Окончание: {(appointment_datetime + timedelta(minutes=service.duration)).strftime('%H:%M')}\n\n"
        "Не забудьте напомнить клиенту о записи!",
        reply_markup=get_clients_keyboard()
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def show_active_appointments(update: Update, context: CallbackContext):
    """Показывает активные записи"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    # Получаем будущие записи
    appointments = session.query(Appointment).filter(
        Appointment.user_id == user.id,
        Appointment.datetime >= datetime.now(),
        Appointment.status == 'booked'
    ).order_by(Appointment.datetime).all()
    
    if not appointments:
        await update.message.reply_text(
            "📅 У вас пока нет активных записей\n\n"
            "Создайте первую запись с помощью кнопки '📅 Записать клиента'",
            reply_markup=get_clients_keyboard()
        )
        return
    
    appointments_text = "📅 Активные записи:\n\n"
    for i, appointment in enumerate(appointments, 1):
        client = session.query(Client).filter_by(id=appointment.client_id).first()
        service = session.query(Service).filter_by(id=appointment.service_id).first()
        
        appointments_text += f"{i}. {client.name if client else 'Неизвестный клиент'}\n"
        appointments_text += f"   📌 {service.name if service else 'Неизвестная услуга'}\n"
        appointments_text += f"   ⏱️ {service.duration if service else '?'} мин.\n"
        appointments_text += f"   🕐 {appointment.datetime.strftime('%d.%m.%Y %H:%M')}\n"
        appointments_text += f"   📞 {client.phone if client else 'Нет телефона'}\n\n"
    
    await update.message.reply_text(appointments_text, reply_markup=get_clients_keyboard())

async def cancel_booking_process(update: Update, context: CallbackContext):
    """Отмена процесса записи"""
    await update.message.reply_text(
        "❌ Процесс записи отменен",
        reply_markup=get_clients_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END