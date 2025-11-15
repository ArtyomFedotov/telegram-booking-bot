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
    """Обработка покупки премиума - ПЕРЕНАПРАВЛЯЕМ В ПРОЦЕСС ОПЛАТЫ"""
    from handlers.payment_handlers import start_payment_process
    
    user_message = update.message.text
    
    if user_message == '💼 PRO - 299₽/мес':
        # ПЕРЕНАПРАВЛЯЕМ в процесс оплаты из payment_handlers.py
        context.user_data['plan_type'] = 'pro'
        return await start_payment_process(update, context)
        
    elif user_message == '📅 PRO ГОД - 2990₽/год':
        # ПЕРЕНАПРАВЛЯЕМ в процесс оплаты из payment_handlers.py
        context.user_data['plan_type'] = 'pro_year' 
        return await start_payment_process(update, context)
        
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