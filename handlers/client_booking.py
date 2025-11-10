from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from datetime import datetime, timedelta
from database.models import session, User, Service, Appointment, Client, MasterLink
from keyboards import (
    get_client_main_keyboard, get_services_choice_keyboard, 
    get_dates_keyboard, get_times_keyboard, get_confirm_keyboard,
    get_back_keyboard
)
from utils.calendar_utils import get_available_dates, get_available_times, is_time_available
from telegram import ReplyKeyboardMarkup

# States для процесса записи
CHOOSE_SERVICE, CHOOSE_DATE, CHOOSE_TIME, CONFIRM_BOOKING, CLIENT_NAME, CLIENT_PHONE = range(6)

async def start_client_booking(update: Update, context: CallbackContext):
    """Начало процесса записи для клиента"""
    # Проверяем, перешел ли клиент по специальной ссылке
    if context.args:
        link_code = context.args[0]
        master_link = session.query(MasterLink).filter_by(link_code=link_code, is_active=True).first()
        
        if master_link:
            context.user_data['master_id'] = master_link.user_id
            master = session.query(User).filter_by(id=master_link.user_id).first()
            context.user_data['master_name'] = master.full_name
        else:
            await update.message.reply_text("❌ Ссылка недействительна или устарела")
            return ConversationHandler.END
    else:
        # Если нет ссылки, используем первого мастера (для демо)
        master = session.query(User).first()
        if not master:
            await update.message.reply_text("❌ В системе пока нет мастеров")
            return ConversationHandler.END
        context.user_data['master_id'] = master.id
        context.user_data['master_name'] = master.full_name
    
    master_id = context.user_data['master_id']
    services = session.query(Service).filter_by(user_id=master_id).all()
    
    if not services:
        await update.message.reply_text(
            f"❌ У мастера {context.user_data['master_name']} пока нет услуг\n"
            "Пожалуйста, свяжитесь с мастером для уточнения деталей."
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"👋 Добро пожаловать!\n"
        f"Вы записываетесь к мастеру: {context.user_data['master_name']}\n\n"
        "📋 Выберите услугу:",
        reply_markup=get_services_choice_keyboard(services)
    )
    
    context.user_data['services'] = {f"📌 {s.name} - {s.price}₽": s.id for s in services}
    return CHOOSE_SERVICE

async def choose_service(update: Update, context: CallbackContext):
    """Обработка выбора услуги"""
    if update.message.text == '🔙 Назад':
        await update.message.reply_text("❌ Запись отменена")
        return ConversationHandler.END
    
    service_text = update.message.text
    services_map = context.user_data['services']
    
    if service_text not in services_map:
        await update.message.reply_text("❌ Пожалуйста, выберите услугу из списка")
        return CHOOSE_SERVICE
    
    context.user_data['selected_service_id'] = services_map[service_text]
    selected_service = session.query(Service).filter_by(id=context.user_data['selected_service_id']).first()
    context.user_data['selected_service_name'] = selected_service.name
    context.user_data['selected_service_price'] = selected_service.price
    context.user_data['selected_service_duration'] = selected_service.duration
    
    # Получаем доступные даты
    available_dates = get_available_dates(context.user_data['master_id'])
    
    if not available_dates:
        await update.message.reply_text(
            "❌ К сожалению, на ближайшие 2 недели нет свободных дат\n"
            "Пожалуйста, свяжитесь с мастером для уточнения расписания."
        )
        return ConversationHandler.END
    
    dates_text = "\n".join([f"• {date.strftime('%d.%m.%Y (%A)')}" for date in available_dates[:5]])
    
    await update.message.reply_text(
        f"📅 Выберите дату:\n\n{dates_text}",
        reply_markup=get_dates_keyboard(available_dates[:5])
    )
    
    context.user_data['available_dates'] = available_dates
    return CHOOSE_DATE

async def choose_date(update: Update, context: CallbackContext):
    """Обработка выбора даты"""
    if update.message.text == '🔙 Назад':
        services = session.query(Service).filter_by(user_id=context.user_data['master_id']).all()
        await update.message.reply_text(
            "📋 Выберите услугу:",
            reply_markup=get_services_choice_keyboard(services)
        )
        return CHOOSE_SERVICE
    
    try:
        date_text = update.message.text
        selected_date = datetime.strptime(date_text.split(' (')[0], "%d.%m.%Y").date()
        
        # Проверяем, что дата доступна
        available_dates = context.user_data['available_dates']
        if selected_date not in available_dates:
            await update.message.reply_text("❌ Выбранная дата недоступна. Выберите из списка.")
            return CHOOSE_DATE
        
        context.user_data['selected_date'] = selected_date
        
        # Получаем доступное время с учетом длительности услуги
        service_duration = context.user_data['selected_service_duration']
        available_times = get_available_times(context.user_data['master_id'], selected_date, service_duration)
        
        if not available_times:
            await update.message.reply_text(
                "❌ На выбранную дату нет свободного времени для услуги такой длительности\n"
                "Пожалуйста, выберите другую дату."
            )
            return CHOOSE_DATE
        
        times_text = "\n".join([f"• {time.strftime('%H:%M')}" for time in available_times[:6]])
        
        await update.message.reply_text(
            f"⏰ Выберите время (услуга: {service_duration} мин):\n\n{times_text}",
            reply_markup=get_times_keyboard(available_times[:6])
        )
        
        context.user_data['available_times'] = available_times
        return CHOOSE_TIME
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат даты. Выберите дату из списка.")
        return CHOOSE_DATE

async def choose_time(update: Update, context: CallbackContext):
    """Обработка выбора времени с учетом длительности услуги"""
    if update.message.text == '🔙 Назад':
        available_dates = context.user_data['available_dates']
        dates_text = "\n".join([f"• {date.strftime('%d.%m.%Y (%A)')}" for date in available_dates[:5]])
        await update.message.reply_text(
            f"📅 Выберите дату:\n\n{dates_text}",
            reply_markup=get_dates_keyboard(available_dates[:5])
        )
        return CHOOSE_DATE
    
    try:
        time_text = update.message.text
        selected_date = context.user_data['selected_date']
        selected_datetime = datetime.combine(selected_date, datetime.strptime(time_text, "%H:%M").time())
        
        # Получаем длительность выбранной услуги
        service_duration = context.user_data['selected_service_duration']
        
        # Проверяем доступность времени с учетом длительности услуги
        available_times = context.user_data['available_times']
        if selected_datetime not in available_times:
            await update.message.reply_text("❌ Выбранное время недоступно. Выберите из списка.")
            return CHOOSE_TIME
        
        # Дополнительная проверка доступности
        if not is_time_available(context.user_data['master_id'], selected_datetime, service_duration):
            await update.message.reply_text(
                f"❌ Время {time_text} недоступно для услуги длительностью {service_duration} мин. "
                "Выберите другое время:",
                reply_markup=get_times_keyboard(available_times[:6])
            )
            return CHOOSE_TIME
        
        context.user_data['selected_datetime'] = selected_datetime
        
        # Запрашиваем данные клиента
        await update.message.reply_text(
            "👤 Для завершения записи введите ваше имя:",
            reply_markup=get_back_keyboard()
        )
        return CLIENT_NAME
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат времени. Выберите время из списка.")
        return CHOOSE_TIME

async def get_client_name(update: Update, context: CallbackContext):
    """Получаем имя клиента"""
    if update.message.text == '🔙 Назад':
        available_times = context.user_data['available_times']
        times_text = "\n".join([f"• {time.strftime('%H:%M')}" for time in available_times[:6]])
        await update.message.reply_text(
            f"⏰ Выберите время:\n\n{times_text}",
            reply_markup=get_times_keyboard(available_times[:6])
        )
        return CHOOSE_TIME
    
    context.user_data['client_name'] = update.message.text
    
    await update.message.reply_text(
        "📞 Введите ваш номер телефона:",
        reply_markup=get_back_keyboard()
    )
    return CLIENT_PHONE

async def get_client_phone(update: Update, context: CallbackContext):
    """Получаем телефон клиента"""
    if update.message.text == '🔙 Назад':
        await update.message.reply_text(
            "👤 Введите ваше имя:",
            reply_markup=get_back_keyboard()
        )
        return CLIENT_NAME
    
    context.user_data['client_phone'] = update.message.text
    
    return await show_booking_confirmation(update, context)

async def show_booking_confirmation(update: Update, context: CallbackContext):
    """Показывает подтверждение записи"""
    # Формируем информацию о записи
    master = session.query(User).filter_by(id=context.user_data['master_id']).first()
    service = session.query(Service).filter_by(id=context.user_data['selected_service_id']).first()
    service_duration = context.user_data['selected_service_duration']
    end_time = context.user_data['selected_datetime'] + timedelta(minutes=service_duration)
    
    booking_info = (
        f"📋 Детали записи:\n\n"
        f"👨‍💼 Мастер: {master.full_name}\n"
        f"📌 Услуга: {service.name}\n"
        f"💰 Стоимость: {service.price}₽\n"
        f"⏱️ Длительность: {service.duration} мин.\n"
        f"📅 Дата: {context.user_data['selected_datetime'].strftime('%d.%m.%Y')}\n"
        f"⏰ Время: {context.user_data['selected_datetime'].strftime('%H:%M')} - {end_time.strftime('%H:%M')}\n"
        f"👤 Ваше имя: {context.user_data['client_name']}\n"
        f"📞 Телефон: {context.user_data['client_phone']}\n\n"
        f"✅ Подтвердите запись:"
    )
    
    await update.message.reply_text(
        booking_info,
        reply_markup=get_confirm_keyboard()
    )
    return CONFIRM_BOOKING

async def confirm_booking(update: Update, context: CallbackContext):
    """Подтверждение и сохранение записи"""
    if update.message.text == '❌ Отменить':
        await update.message.reply_text(
            "❌ Запись отменена",
            reply_markup=get_client_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    if update.message.text != '✅ Подтвердить запись':
        await update.message.reply_text("❌ Пожалуйста, подтвердите или отмените запись")
        return CONFIRM_BOOKING
    
    # Финальная проверка доступности времени
    service_duration = context.user_data['selected_service_duration']
    if not is_time_available(context.user_data['master_id'], context.user_data['selected_datetime'], service_duration):
        await update.message.reply_text(
            "❌ К сожалению, это время уже занято. Пожалуйста, начните запись заново.",
            reply_markup=get_client_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Сохраняем клиента
    client = Client(
        name=context.user_data['client_name'],
        phone=context.user_data['client_phone'],
        user_id=context.user_data['master_id']
    )
    session.add(client)
    session.flush()  # Получаем ID клиента
    
    # Сохраняем запись
    appointment = Appointment(
        user_id=context.user_data['master_id'],
        client_id=client.id,
        service_id=context.user_data['selected_service_id'],
        datetime=context.user_data['selected_datetime'],
        status='booked'
    )
    session.add(appointment)
    session.commit()
    
    # Отправляем подтверждение
    service = session.query(Service).filter_by(id=context.user_data['selected_service_id']).first()
    end_time = context.user_data['selected_datetime'] + timedelta(minutes=service_duration)
    
    success_message = (
        f"🎉 Запись успешно создана!\n\n"
        f"📋 Детали:\n"
        f"• Услуга: {service.name}\n"
        f"• Длительность: {service.duration} мин.\n"
        f"• Дата: {context.user_data['selected_datetime'].strftime('%d.%m.%Y')}\n"
        f"• Время: {context.user_data['selected_datetime'].strftime('%H:%M')} - {end_time.strftime('%H:%M')}\n"
        f"• Стоимость: {service.price}₽\n\n"
        f"📞 Мастер свяжется с вами для подтверждения.\n"
        f"Если у вас есть вопросы, используйте кнопку 'Связаться с мастером'"
    )
    
    await update.message.reply_text(
        success_message,
        reply_markup=get_client_main_keyboard()
    )
    
    # Очищаем временные данные
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_booking(update: Update, context: CallbackContext):
    """Отмена процесса записи"""
    await update.message.reply_text(
        "❌ Запись отменена",
        reply_markup=get_client_main_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END