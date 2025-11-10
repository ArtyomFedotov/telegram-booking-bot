from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from database.models import Service, session, User, PremiumSubscription
from keyboards import get_services_keyboard, get_back_keyboard, get_main_keyboard
from telegram import ReplyKeyboardMarkup

# States для создания услуги
SERVICE_NAME, SERVICE_DURATION, SERVICE_PRICE = range(3)
# States для редактирования услуги
EDIT_SELECT_SERVICE, EDIT_SERVICE_NAME, EDIT_SERVICE_DURATION, EDIT_SERVICE_PRICE = range(4, 8)
# States для удаления услуги
DELETE_SELECT_SERVICE = 8

async def services_menu(update: Update, context: CallbackContext):
    """Меню управления услугами"""
    await update.message.reply_text(
        "🛠️ Управление услугами\n\n"
        "Здесь вы можете добавлять, редактировать и удалять ваши услуги",
        reply_markup=get_services_keyboard()
    )

async def show_my_services(update: Update, context: CallbackContext):
    """Показывает список услуг пользователя"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    services = session.query(Service).filter_by(user_id=user.id).all()
    
    if not services:
        await update.message.reply_text(
            "📝 У вас пока нет услуг\n\n"
            "Добавьте первую услугу с помощью кнопки '➕ Добавить услугу'",
            reply_markup=get_services_keyboard()
        )
        return
    
    services_text = "📋 Ваши услуги:\n\n"
    for i, service in enumerate(services, 1):
        services_text += f"{i}. {service.name}\n"
        services_text += f"   ⏱️ {service.duration} мин.\n"
        services_text += f"   💰 {service.price}₽\n\n"
    
    await update.message.reply_text(services_text, reply_markup=get_services_keyboard())

async def add_service_start(update: Update, context: CallbackContext):
    """Начало процесса добавления услуги"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    # Проверяем лимит услуг для бесплатных пользователей
    premium = session.query(PremiumSubscription).filter_by(user_id=user.id, is_active=True).first()
    if not premium:
        services_count = session.query(Service).filter_by(user_id=user.id).count()
        if services_count >= 5:  # Лимит 5 услуг для бесплатной версии
            await update.message.reply_text(
                "❌ **Достигнут лимит услуг!**\n\n"
                "В бесплатной версии можно добавить не более 5 услуг.\n\n"
                "💎 **PRO версия включает:**\n"
                "• Неограниченное количество клиентов\n"
                "• Неограниченное количество услуг\n\n"
                "Всего за 299₽/мес!",
                reply_markup=get_services_keyboard(),
                parse_mode='Markdown'
            )
            return ConversationHandler.END
    
    await update.message.reply_text(
        "➕ Добавление новой услуги\n\n"
        "Введите название услуги:",
        reply_markup=get_back_keyboard()
    )
    return SERVICE_NAME

async def add_service_name(update: Update, context: CallbackContext):
    """Получаем название услуги"""
    if update.message.text == '🔙 Назад':
        await services_menu(update, context)
        return ConversationHandler.END
    
    context.user_data['service_name'] = update.message.text
    
    await update.message.reply_text(
        "⏱️ Введите продолжительность услуги в минутах:\n"
        "Например: 60",
        reply_markup=get_back_keyboard()
    )
    return SERVICE_DURATION

async def add_service_duration(update: Update, context: CallbackContext):
    """Получаем продолжительность услуги"""
    if update.message.text == '🔙 Назад':
        await services_menu(update, context)
        return ConversationHandler.END
    
    try:
        duration = int(update.message.text)
        if duration <= 0:
            await update.message.reply_text("Продолжительность должна быть больше 0 минут")
            return SERVICE_DURATION
    except ValueError:
        await update.message.reply_text("Введите число (минуты)")
        return SERVICE_DURATION
    
    context.user_data['service_duration'] = duration
    
    await update.message.reply_text(
        "💰 Введите стоимость услуги в рублях:\n"
        "Например: 1500",
        reply_markup=get_back_keyboard()
    )
    return SERVICE_PRICE

async def add_service_price(update: Update, context: CallbackContext):
    """Получаем стоимость услуги и сохраняем"""
    if update.message.text == '🔙 Назад':
        await services_menu(update, context)
        return ConversationHandler.END
    
    try:
        price = int(update.message.text)
        if price <= 0:
            await update.message.reply_text("Стоимость должна быть больше 0")
            return SERVICE_PRICE
    except ValueError:
        await update.message.reply_text("Введите число (рубли)")
        return SERVICE_PRICE
    
    # Сохраняем услугу в базу
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    new_service = Service(
        user_id=user.id,
        name=context.user_data['service_name'],
        duration=context.user_data['service_duration'],
        price=price
    )
    
    session.add(new_service)
    session.commit()
    
    await update.message.reply_text(
        f"✅ Услуга добавлена!\n\n"
        f"📌 {new_service.name}\n"
        f"⏱️ {new_service.duration} мин.\n"
        f"💰 {new_service.price}₽",
        reply_markup=get_services_keyboard()
    )
    
    # Очищаем временные данные
    context.user_data.clear()
    return ConversationHandler.END

async def edit_service_start(update: Update, context: CallbackContext):
    """Начало процесса редактирования услуги"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    services = session.query(Service).filter_by(user_id=user.id).all()
    
    if not services:
        await update.message.reply_text(
            "📝 У вас пока нет услуг для редактирования",
            reply_markup=get_services_keyboard()
        )
        return ConversationHandler.END
    
    # Создаем клавиатуру с услугами
    keyboard = []
    for service in services:
        keyboard.append([f"✏️ {service.name} - {service.duration}мин - {service.price}₽"])
    keyboard.append(['🔙 Назад'])
    
    await update.message.reply_text(
        "✏️ Выберите услугу для редактирования:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    
    context.user_data['services'] = {f"✏️ {service.name} - {service.duration}мин - {service.price}₽": service.id for service in services}
    return EDIT_SELECT_SERVICE

async def edit_select_service(update: Update, context: CallbackContext):
    """Обработка выбора услуги для редактирования"""
    if update.message.text == '🔙 Назад':
        await services_menu(update, context)
        return ConversationHandler.END
    
    service_text = update.message.text
    if service_text not in context.user_data['services']:
        await update.message.reply_text("Пожалуйста, выберите услугу из списка:")
        return EDIT_SELECT_SERVICE
    
    context.user_data['edit_service_id'] = context.user_data['services'][service_text]
    
    await update.message.reply_text(
        "Введите новое название услуги (или отправьте '-' чтобы оставить без изменений):",
        reply_markup=get_back_keyboard()
    )
    return EDIT_SERVICE_NAME

async def edit_service_name(update: Update, context: CallbackContext):
    """Редактирование названия услуги"""
    if update.message.text == '🔙 Назад':
        await edit_service_start(update, context)
        return EDIT_SELECT_SERVICE
    
    new_name = update.message.text
    if new_name != '-':
        context.user_data['new_name'] = new_name
    
    await update.message.reply_text(
        "Введите новую продолжительность в минутах (или отправьте '-' чтобы оставить без изменений):",
        reply_markup=get_back_keyboard()
    )
    return EDIT_SERVICE_DURATION

async def edit_service_duration(update: Update, context: CallbackContext):
    """Редактирование продолжительности услуги"""
    if update.message.text == '🔙 Назад':
        await edit_service_start(update, context)
        return EDIT_SELECT_SERVICE
    
    if update.message.text != '-':
        try:
            duration = int(update.message.text)
            if duration <= 0:
                await update.message.reply_text("Продолжительность должна быть больше 0 минут")
                return EDIT_SERVICE_DURATION
            context.user_data['new_duration'] = duration
        except ValueError:
            await update.message.reply_text("Введите число (минуты) или '-'")
            return EDIT_SERVICE_DURATION
    
    await update.message.reply_text(
        "Введите новую стоимость в рублях (или отправьте '-' чтобы оставить без изменений):",
        reply_markup=get_back_keyboard()
    )
    return EDIT_SERVICE_PRICE

async def edit_service_price(update: Update, context: CallbackContext):
    """Редактирование стоимости услуги и сохранение"""
    if update.message.text == '🔙 Назад':
        await edit_service_start(update, context)
        return EDIT_SELECT_SERVICE
    
    if update.message.text != '-':
        try:
            price = int(update.message.text)
            if price <= 0:
                await update.message.reply_text("Стоимость должна быть больше 0")
                return EDIT_SERVICE_PRICE
            context.user_data['new_price'] = price
        except ValueError:
            await update.message.reply_text("Введите число (рубли) или '-'")
            return EDIT_SERVICE_PRICE
    
    # Сохраняем изменения
    service = session.query(Service).filter_by(id=context.user_data['edit_service_id']).first()
    
    if 'new_name' in context.user_data:
        service.name = context.user_data['new_name']
    if 'new_duration' in context.user_data:
        service.duration = context.user_data['new_duration']
    if 'new_price' in context.user_data:
        service.price = context.user_data['new_price']
    
    session.commit()
    
    await update.message.reply_text(
        f"✅ Услуга обновлена!\n\n"
        f"📌 {service.name}\n"
        f"⏱️ {service.duration} мин.\n"
        f"💰 {service.price}₽",
        reply_markup=get_services_keyboard()
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def delete_service_start(update: Update, context: CallbackContext):
    """Начало процесса удаления услуги"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    services = session.query(Service).filter_by(user_id=user.id).all()
    
    if not services:
        await update.message.reply_text(
            "📝 У вас пока нет услуг для удаления",
            reply_markup=get_services_keyboard()
        )
        return ConversationHandler.END
    
    # Создаем клавиатуру с услугами
    keyboard = []
    for service in services:
        keyboard.append([f"🗑️ {service.name} - {service.duration}мин - {service.price}₽"])
    keyboard.append(['🔙 Назад'])
    
    await update.message.reply_text(
        "🗑️ Выберите услугу для удаления:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    
    context.user_data['services'] = {f"🗑️ {service.name} - {service.duration}мин - {service.price}₽": service.id for service in services}
    return DELETE_SELECT_SERVICE

async def delete_select_service(update: Update, context: CallbackContext):
    """Обработка удаления услуги"""
    if update.message.text == '🔙 Назад':
        await services_menu(update, context)
        return ConversationHandler.END
    
    service_text = update.message.text
    if service_text not in context.user_data['services']:
        await update.message.reply_text("Пожалуйста, выберите услугу из списка:")
        return DELETE_SELECT_SERVICE
    
    service_id = context.user_data['services'][service_text]
    service = session.query(Service).filter_by(id=service_id).first()
    
    if service:
        session.delete(service)
        session.commit()
        
        await update.message.reply_text(
            f"✅ Услуга удалена!\n\n"
            f"📌 {service.name}\n"
            f"⏱️ {service.duration} мин.\n"
            f"💰 {service.price}₽",
            reply_markup=get_services_keyboard()
        )
    else:
        await update.message.reply_text("❌ Услуга не найдена")
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_service_creation(update: Update, context: CallbackContext):
    """Отмена создания услуги"""
    await update.message.reply_text(
        "❌ Создание услуги отменено",
        reply_markup=get_services_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END