from telegram import Update
from telegram.ext import CallbackContext
from database.models import session, User, PremiumSubscription, Client, Service, Appointment
from keyboards import (
    get_main_keyboard, get_settings_keyboard,
    get_premium_keyboard, get_premium_plans_keyboard
)
from datetime import datetime, timedelta
from sqlalchemy import func
from telegram import KeyboardButton, ReplyKeyboardMarkup
from utils.payment_utils import create_premium_payment, activate_premium_subscription

async def settings_menu(update: Update, context: CallbackContext):
    """Меню настроек"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    # Проверяем премиум статус
    premium = session.query(PremiumSubscription).filter_by(user_id=user.id, is_active=True).first()
    premium_status = "✅ АКТИВЕН" if premium else "❌ НЕ АКТИВЕН"
    
    settings_text = (
        "⚙️ **Настройки**\n\n"
        f"💎 Премиум статус: {premium_status}\n\n"
        "Выберите раздел для настройки:"
    )
    
    await update.message.reply_text(
        settings_text,
        reply_markup=get_settings_keyboard(),
        parse_mode='Markdown'
    )

async def premium_features(update: Update, context: CallbackContext):
    """Премиум функции с ОБЫЧНЫМИ кнопками"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    premium = session.query(PremiumSubscription).filter_by(user_id=user.id, is_active=True).first()
    
    if premium:
        premium_status = "✅ Активен (PRO)"
        if premium.expires_at:
            days_left = (premium.expires_at - datetime.now()).days
            status_text = f"Действует до: {premium.expires_at.strftime('%d.%m.%Y')}\nОсталось дней: {days_left}"
        else:
            status_text = "Бессрочная"
        
        premium_text = (
            "💎 **PRO версия**\n\n"
            f"**Статус:** {premium_status}\n"
            f"**{status_text}**\n\n"
            "✅ Все PRO функции активны!"
        )
        
        # ОБЫЧНЫЕ КНОПКИ вместо инлайн
        keyboard = [
            [KeyboardButton("🔙 Назад в настройки")]
        ]
        
        await update.message.reply_text(
            premium_text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode='Markdown'
        )
        
    else:
        premium_status = "❌ Не активен"
        clients_count = session.query(Client).filter_by(user_id=user.id).count()
        services_count = session.query(Service).filter_by(user_id=user.id).count()
        status_text = f"Использовано: {clients_count}/10 клиентов, {services_count}/5 услуг"
        
        premium_text = (
            "💎 **PRO версия**\n\n"
            f"**Статус:** {premium_status}\n"
            f"**{status_text}**\n\n"
            "**🚀 PRO включает:**\n"
            "• 👥 Неограниченное количество клиентов\n"
            "• 💼 Неограниченное количество услуг\n"
            "• 📊 Доступ к статистике\n\n"
            "**Выберите тариф:**"
        )
        
        # ОБЫЧНЫЕ КНОПКИ вместо инлайн
        keyboard = [
            [KeyboardButton("💼 PRO - 299₽/мес"), KeyboardButton("📅 PRO ГОД - 2990₽/год")],
            [KeyboardButton("🆓 Попробовать бесплатно")],
            [KeyboardButton("🔙 Назад в настройки")]
        ]
        
        await update.message.reply_text(
            premium_text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode='Markdown'
        )

async def process_premium_purchase(update: Update, context: CallbackContext):
    """Обработка покупки премиума - СОХРАНЯЕМ ДАННЫЕ ДЛЯ ОПЛАТЫ"""
    user_message = update.message.text
    
    if user_message == '💼 PRO - 299₽/мес':
        plan_type = 'pro'
        amount = 299
        duration_days = 30
        period = "1 месяц"
    elif user_message == '📅 PRO ГОД - 2990₽/год':
        plan_type = 'pro_year'
        amount = 2990
        duration_days = 365
        period = "1 год"
    elif user_message == '🆓 Попробовать бесплатно':
        return await try_free_trial(update, context)
    elif user_message == '🔙 Назад в настройки':
        return await settings_menu(update, context)
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите вариант из списка:",
            reply_markup=get_premium_plans_keyboard()
        )
        return
    
    # Сохраняем данные для оплаты
    context.user_data['plan_type'] = plan_type
    context.user_data['amount'] = amount
    context.user_data['duration_days'] = duration_days
    
    # Показываем подтверждение
    text = (
        f"💎 **Оформление PRO подписки**\n\n"
        f"📋 Тариф: PRO {'ГОД' if plan_type == 'pro_year' else ''}\n"
        f"💰 Стоимость: {amount}₽\n"
        f"📅 Срок: {period}\n\n"
        f"После оплаты вам будут доступны:\n"
        f"• 👥 Неограниченное количество клиентов\n"
        f"• 💼 Неограниченное количество услуг\n"
        f"• 📊 Полная статистика\n\n"
        f"Для оплаты нажмите кнопку '✅ Перейти к оплате'"
    )
    
    keyboard = [
        [KeyboardButton("✅ Перейти к оплате")],
        [KeyboardButton("❌ Отменить")]
    ]
    
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode='Markdown'
    )

async def show_statistics(update: Update, context: CallbackContext):
    """Показывает статистику мастера - ТОЛЬКО ДЛЯ PRO"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    # ПРОВЕРКА ПРЕМИУМА
    premium = session.query(PremiumSubscription).filter_by(user_id=user.id, is_active=True).first()
    if not premium:
        await update.message.reply_text(
            "❌ **Статистика доступна только в PRO версии!**\n\n"
            "💎 **PRO версия включает:**\n"
            "• Неограниченное количество клиентов\n"
            "• Неограниченное количество услуг\n"
            "• Полный доступ к статистике\n\n"
            "Всего от 299₽/мес!",
            reply_markup=get_premium_keyboard(),
            parse_mode='Markdown'
        )
        return
    
    # СТАТИСТИКА ДЛЯ PRO ПОЛЬЗОВАТЕЛЕЙ
    clients_count = session.query(Client).filter_by(user_id=user.id).count()
    services_count = session.query(Service).filter_by(user_id=user.id).count()
    appointments_count = session.query(Appointment).filter_by(user_id=user.id).count()
    
    active_appointments = session.query(Appointment).filter(
        Appointment.user_id == user.id,
        Appointment.datetime >= datetime.now(),
        Appointment.status == 'booked'
    ).count()
    
    stats_text = (
        "📊 **Ваша статистика PRO**\n\n"
        f"👥 **Клиенты:** {clients_count}\n"
        f"💼 **Услуги:** {services_count}\n"
        f"📅 **Всего записей:** {appointments_count}\n"
        f"🟢 **Активные записи:** {active_appointments}\n"
    )
    
    await update.message.reply_text(
        stats_text,
        reply_markup=get_settings_keyboard(),
        parse_mode='Markdown'
    )

async def user_profile(update: Update, context: CallbackContext):
    """Профиль пользователя"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    premium = session.query(PremiumSubscription).filter_by(user_id=user.id, is_active=True).first()
    
    profile_text = (
        "👤 **Ваш профиль**\n\n"
        f"📛 Имя: {user.full_name}\n"
        f"💼 Специальность: {user.specialty}\n"
        f"📞 Телефон: {user.phone}\n"
        f"📅 В системе с: {user.created_at.strftime('%d.%m.%Y')}\n"
        f"💎 PRO версия: {'✅ АКТИВЕН' if premium else '❌ НЕ АКТИВЕН'}\n"
    )
    
    if premium:
        plan_name = "PRO ГОД" if premium.plan_type == 'pro_year' else "PRO"
        profile_text += f"📋 Тариф: {plan_name}\n"
        if premium.expires_at:
            days_left = (premium.expires_at - datetime.now()).days
            profile_text += f"📅 Действует до: {premium.expires_at.strftime('%d.%m.%Y')}\n"
            profile_text += f"⏰ Осталось дней: {days_left}\n"
    
    await update.message.reply_text(
        profile_text,
        reply_markup=get_settings_keyboard(),
        parse_mode='Markdown'
    )

async def try_free_trial(update: Update, context: CallbackContext):
    """Активация бесплатного пробного периода"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    # Проверяем, есть ли уже активная подписка
    existing_premium = session.query(PremiumSubscription).filter_by(user_id=user.id, is_active=True).first()
    if existing_premium:
        await update.message.reply_text(
            "✅ У вас уже активирована PRO версия!",
            reply_markup=get_premium_keyboard()
        )
        return
    
    # Проверяем, использовал ли пользователь уже пробный период
    used_trial = session.query(PremiumSubscription).filter_by(user_id=user.id).first()
    if used_trial:
        await update.message.reply_text(
            "❌ Вы уже использовали бесплатный пробный период.\n\n"
            "Приобретите PRO версию для доступа ко всем функциям!",
            reply_markup=get_premium_keyboard()
        )
        return
    
    # Активируем пробный период на 14 дней
    trial_sub = PremiumSubscription(
        user_id=user.id,
        plan_type='trial',
        is_active=True,
        expires_at=datetime.now() + timedelta(days=14)
    )
    session.add(trial_sub)
    session.commit()
    
    await update.message.reply_text(
        "🎉 **Бесплатный пробный период активирован!**\n\n"
        "Теперь вам доступны все PRO функции на 14 дней:\n"
        "• 👥 Неограниченное количество клиентов\n"
        "• 💼 Неограниченное количество услуг\n"
        "• 📊 Полная статистика\n\n"
        "Пробный период действует до: " + trial_sub.expires_at.strftime('%d.%m.%Y'),
        reply_markup=get_premium_keyboard(),
        parse_mode='Markdown'
    )

async def start_payment_from_settings(update: Update, context: CallbackContext):
    """Запуск процесса оплаты из настроек"""
    from utils.payment_utils import create_premium_payment
    
    plan_type = context.user_data.get('plan_type')
    amount = context.user_data.get('amount')
    duration_days = context.user_data.get('duration_days')
    user_id = update.effective_user.id
    
    if not all([plan_type, amount, duration_days]):
        await update.message.reply_text("❌ Ошибка: данные оплаты не найдены")
        return await settings_menu(update, context)
    
    # Создаем платеж
    description = f"PRO подписка ({'год' if plan_type == 'pro_year' else 'месяц'})"
    payment = await create_premium_payment(user_id, amount, description, duration_days)
    
    if not payment:
        await update.message.reply_text(
            "❌ Ошибка при создании платежа. Попробуйте позже.",
            parse_mode='Markdown'
        )
        return await settings_menu(update, context)
    
    # Получаем ссылку для оплаты
    payment_url = payment.confirmation.confirmation_url
    
    keyboard = [
        [KeyboardButton("✅ Я оплатил")],
        [KeyboardButton("❌ Отменить")]
    ]
    
    text = (
        f"💳 **Оплата PRO подписки**\n\n"
        f"Для завершения оплаты:\n"
        f"1. Перейдите по ссылке: {payment_url}\n"
        f"2. Оплатите заказ\n"
        f"3. Вернитесь в бот и нажмите '✅ Я оплатил'\n\n"
        f"Ссылка для оплаты действительна 24 часа."
    )
    
    context.user_data['payment_id'] = payment.id
    
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode='Markdown'
    )

async def check_payment_status_from_settings(update: Update, context: CallbackContext):
    """Проверка статуса платежа из настроек"""
    from utils.payment_utils import get_payment_info, check_premium_status
    from database.models import PremiumSubscription
    from keyboards import get_main_keyboard
    
    payment_id = context.user_data.get('payment_id')
    user_id = update.effective_user.id
    
    if not payment_id:
        await update.message.reply_text("❌ Информация о платеже не найдена")
        return await settings_menu(update, context)
    
    # Проверяем статус платежа
    payment_info = get_payment_info(payment_id)
    
    if not payment_info:
        await update.message.reply_text("❌ Не удалось проверить статус платежа")
        return await settings_menu(update, context)
    
    # Проверяем статус платежа
    if payment_info.status == 'succeeded' or check_premium_status(user_id):
        # Платеж успешен или подписка уже активирована
        user = session.query(User).filter_by(telegram_id=user_id).first()
        premium = session.query(PremiumSubscription).filter_by(user_id=user.id, is_active=True).first()
        
        if premium:
            days_left = (premium.expires_at - datetime.now()).days
            text = (
                f"🎉 **Оплата успешно завершена!**\n\n"
                f"✅ PRO подписка активирована!\n"
                f"📅 Действует до: {premium.expires_at.strftime('%d.%m.%Y')}\n"
                f"⏰ Осталось дней: {days_left}\n\n"
                f"Теперь вам доступны все PRO функции!"
            )
        else:
            text = "🎉 **Оплата успешно завершена!**\n\n✅ PRO подписка активирована!"
            
    elif payment_info.status == 'pending':
        text = "⏳ Платеж еще обрабатывается. Попробуйте проверить статус через несколько минут."
    elif payment_info.status == 'canceled':
        text = "❌ Платеж отменен."
    else:
        text = f"📊 Статус платежа: {payment_info.status}. Попробуйте позже."
    
    await update.message.reply_text(text, parse_mode='Markdown')
    
    # Возвращаем в главное меню
    await update.message.reply_text(
        "Возвращаемся в главное меню:",
        reply_markup=get_main_keyboard()
    )
    
    context.user_data.clear()

async def cancel_payment_from_settings(update: Update, context: CallbackContext):
    """Отмена процесса оплаты из настроек"""
    from keyboards import get_main_keyboard
    
    await update.message.reply_text(
        "❌ Процесс оплаты отменен.",
        parse_mode='Markdown'
    )
    
    # Возвращаем в главное меню
    await update.message.reply_text(
        "Возвращаемся в главное меню:",
        reply_markup=get_main_keyboard()
    )
    
    context.user_data.clear()