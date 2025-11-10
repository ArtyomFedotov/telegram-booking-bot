from telegram import Update
from telegram.ext import CallbackContext
from database.models import session, User, PremiumSubscription
from keyboards import get_admin_keyboard, get_main_keyboard
from datetime import datetime, timedelta
from telegram import ReplyKeyboardMarkup

# ID администратора
ADMIN_IDS = [1653869832]  # ⚠️ ЗАМЕНИТЕ ЭТОТ ID НА ВАШ НАСТОЯЩИЙ TELEGRAM ID

def is_admin(user_id):
    """Проверяет является ли пользователь администратором"""
    return user_id in ADMIN_IDS

async def admin_panel(update: Update, context: CallbackContext):
    """Панель администратора"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    stats = get_admin_stats()
    
    admin_text = (
        "👑 **Панель администратора**\n\n"
        f"📊 **Статистика системы:**\n"
        f"• 👥 Всего пользователей: {stats['total_users']}\n"
        f"• 💎 PRO пользователей: {stats['premium_users']}\n"
        f"• 📅 Активных записей: {stats['active_appointments']}\n\n"
        "**Действия:**\n"
        "• Управление PRO подписками\n"
        "• Просмотр статистики\n"
        "• Управление пользователями"
    )
    
    await update.message.reply_text(
        admin_text,
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )

async def manage_premium(update: Update, context: CallbackContext):
    """Управление PRO подписками"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    # Получаем список пользователей
    users = session.query(User).all()
    
    if not users:
        await update.message.reply_text("❌ В системе нет пользователей")
        return
    
    users_text = "👥 **Управление PRO подписками:**\n\n"
    keyboard = []
    
    for user in users[:10]:  # Показываем первых 10 пользователей
        premium = session.query(PremiumSubscription).filter_by(user_id=user.id, is_active=True).first()
        premium_status = "💎" if premium else "🔹"
        username = f"@{user.username}" if user.username else "нет username"
        
        if premium:
            users_text += f"{premium_status} {user.full_name} ({username}) - PRO\n"
            # Кнопки для пользователей с PRO
            keyboard.append([f"❌ Удалить PRO: {user.full_name}"])
        else:
            users_text += f"{premium_status} {user.full_name} ({username})\n"
            # Кнопки для пользователей без PRO
            keyboard.append([f"💎 Выдать PRO: {user.full_name}"])
    
    keyboard.append(['🔙 Назад в админку'])
    
    await update.message.reply_text(
        users_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def give_premium_to_user(update: Update, context: CallbackContext):
    """Выдача PRO выбранному пользователю"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    user_text = update.message.text
    if not user_text.startswith('💎 Выдать PRO: '):
        await update.message.reply_text("❌ Неверный формат команды")
        return
    
    # Извлекаем имя пользователя из текста
    user_name = user_text.replace('💎 Выдать PRO: ', '')
    
    # Ищем пользователя в базе
    user = session.query(User).filter_by(full_name=user_name).first()
    
    if not user:
        await update.message.reply_text(f"❌ Пользователь {user_name} не найден")
        return
    
    # Создаем клавиатуру для выбора типа подписки
    keyboard = [
        ['💼 PRO - 299₽/мес'],
        ['📅 PRO ГОД - 2990₽/год'],
        ['🔙 Назад в админку']
    ]
    
    context.user_data['premium_user_id'] = user.id
    context.user_data['premium_user_name'] = user_name
    
    await update.message.reply_text(
        f"👤 Пользователь: {user_name}\n\n"
        "Выберите тип PRO подписки:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def process_premium_type_selection(update: Update, context: CallbackContext):
    """Обработка выбора типа PRO подписки администратором"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    if update.message.text == '🔙 Назад в админку':
        await admin_panel(update, context)
        return
    
    user_id = context.user_data.get('premium_user_id')
    user_name = context.user_data.get('premium_user_name')
    
    if not user_id:
        await update.message.reply_text("❌ Ошибка: пользователь не найден")
        return
    
    if update.message.text == '💼 PRO - 299₽/мес':
        plan_type = 'pro'
        price = 299
        days = 30
        plan_name = "PRO"
    elif update.message.text == '📅 PRO ГОД - 2990₽/год':
        plan_type = 'pro_year'
        price = 2990
        days = 365
        plan_name = "PRO ГОД"
    else:
        await update.message.reply_text("❌ Пожалуйста, выберите тип подписки из списка")
        return
    
    # Удаляем старую подписку если есть
    old_sub = session.query(PremiumSubscription).filter_by(user_id=user_id).first()
    if old_sub:
        session.delete(old_sub)
    
    # Создаем новую подписку
    new_sub = PremiumSubscription(
        user_id=user_id,
        plan_type=plan_type,
        is_active=True,
        expires_at=datetime.now() + timedelta(days=days)
    )
    session.add(new_sub)
    session.commit()
    
    await update.message.reply_text(
        f"✅ **{plan_name} версия успешно выдана!**\n\n"
        f"👤 Пользователь: {user_name}\n"
        f"💎 Тариф: {plan_name}\n"
        f"💰 Стоимость: {price}₽\n"
        f"📅 Действует до: {new_sub.expires_at.strftime('%d.%m.%Y')}\n\n"
        "PRO функции активированы!",
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )
    
    # Очищаем временные данные
    context.user_data.pop('premium_user_id', None)
    context.user_data.pop('premium_user_name', None)

async def remove_premium(update: Update, context: CallbackContext):
    """Удаление PRO у конкретного пользователя"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    user_text = update.message.text
    if not user_text.startswith('❌ Удалить PRO: '):
        await update.message.reply_text("❌ Неверный формат команды")
        return
    
    # Извлекаем имя пользователя из текста
    user_name = user_text.replace('❌ Удалить PRO: ', '')
    
    # Ищем пользователя в базе
    user = session.query(User).filter_by(full_name=user_name).first()
    
    if not user:
        await update.message.reply_text(f"❌ Пользователь {user_name} не найден")
        return
    
    # Удаляем PRO подписку пользователя
    premium = session.query(PremiumSubscription).filter_by(user_id=user.id).first()
    
    if premium:
        session.delete(premium)
        session.commit()
        
        await update.message.reply_text(
            f"✅ **PRO удален у пользователя!**\n\n"
            f"👤 Пользователь: {user.full_name}\n"
            f"🗑️ PRO подписка удалена\n\n"
            "Пользователь переведен на базовый тариф.",
            reply_markup=get_admin_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ У пользователя {user.full_name} нет активной PRO подписки",
            reply_markup=get_admin_keyboard()
        )

async def remove_all_premiums(update: Update, context: CallbackContext):
    """Удаление ВСЕХ PRO подписок"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    # Получаем всех пользователей с PRO
    premium_users = session.query(PremiumSubscription).filter_by(is_active=True).all()
    
    if not premium_users:
        await update.message.reply_text("❌ В системе нет активных PRO подписок")
        return
    
    # Удаляем все PRO подписки
    for premium in premium_users:
        session.delete(premium)
    
    session.commit()
    
    await update.message.reply_text(
        f"⚠️ **Все PRO подписки удалены!**\n\n"
        f"🗑️ Удалено подписок: {len(premium_users)}\n"
        f"👥 Затронуто пользователей: {len(premium_users)}\n\n"
        "Все пользователи переведены на базовый тариф.",
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )

async def view_system_stats(update: Update, context: CallbackContext):
    """Просмотр системной статистики"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    stats = get_admin_stats()
    
    stats_text = (
        "📊 **Системная статистика**\n\n"
        f"👥 **Пользователи:**\n"
        f"• Всего пользователей: {stats['total_users']}\n"
        f"• PRO пользователей: {stats['premium_users']}\n"
        f"• Обычных пользователей: {stats['total_users'] - stats['premium_users']}\n"
        f"• Конверсия в PRO: {round((stats['premium_users'] / stats['total_users']) * 100, 1) if stats['total_users'] > 0 else 0}%\n\n"
        f"📅 **Активность:**\n"
        f"• Активных записей: {stats['active_appointments']}\n\n"
        f"🔄 **Обновлено:** {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    
    await update.message.reply_text(
        stats_text,
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )

async def view_all_users(update: Update, context: CallbackContext):
    """Просмотр всех пользователей"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Доступ запрещен")
        return
    
    users = session.query(User).all()
    
    if not users:
        await update.message.reply_text("❌ В системе нет пользователей")
        return
    
    users_text = "👥 **Все пользователи системы:**\n\n"
    
    for user in users[:20]:  # Показываем первых 20 пользователей
        premium = session.query(PremiumSubscription).filter_by(user_id=user.id, is_active=True).first()
        premium_status = "💎" if premium else "🔹"
        username = f"@{user.username}" if user.username else "нет username"
        users_text += f"{premium_status} **{user.full_name}** ({username})\n"
        users_text += f"   📞 {user.phone} | 💼 {user.specialty}\n"
        users_text += f"   📅 Зарегистрирован: {user.created_at.strftime('%d.%m.%Y')}\n\n"
    
    users_text += f"\n📊 Всего: {len(users)} пользователей"
    
    await update.message.reply_text(
        users_text,
        reply_markup=get_admin_keyboard(),
        parse_mode='Markdown'
    )

def get_admin_stats():
    """Получение статистики для админ-панели"""
    from database.models import Appointment
    
    total_users = session.query(User).count()
    premium_users = session.query(PremiumSubscription).filter_by(is_active=True).count()
    active_appointments = session.query(Appointment).filter(
        Appointment.datetime >= datetime.now(),
        Appointment.status == 'booked'
    ).count()
    
    return {
        'total_users': total_users,
        'premium_users': premium_users,
        'active_appointments': active_appointments
    }