from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from database.models import session, User, MasterLink
from keyboards import get_client_mode_keyboard, get_main_keyboard
from handlers.client_booking import start_client_booking
from telegram import ReplyKeyboardMarkup

# States для переключения в режим клиента
CLIENT_SELECT_MASTER = range(1)

async def switch_to_client_mode(update: Update, context: CallbackContext):
    """Переключение в режим клиента"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    await update.message.reply_text(
        "👤 Режим клиента\n\n"
        "Вы можете записаться к другим мастерам.\n"
        "Введите ссылку мастера или выберите действие:",
        reply_markup=get_client_mode_keyboard()
    )
    return CLIENT_SELECT_MASTER

async def client_select_master(update: Update, context: CallbackContext):
    """Обработка выбора мастера"""
    if update.message.text == '🔙 Назад к мастеру':
        await switch_back_to_master_mode(update, context)
        return ConversationHandler.END
    
    if update.message.text == '🔙 Назад':
        await update.message.reply_text(
            "Возврат в главное меню",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    if update.message.text == '🔍 Найти мастеров':
        await show_available_masters(update, context)
        return CLIENT_SELECT_MASTER
    
    # Предполагаем, что введена ссылка
    link_text = update.message.text
    if link_text.startswith('https://t.me/'):
        # Извлекаем код ссылки
        link_code = link_text.split('?start=')[-1] if '?start=' in link_text else link_text.split('/')[-1]
    else:
        link_code = link_text
    
    # Ищем мастера по коду ссылки
    master_link = session.query(MasterLink).filter_by(link_code=link_code, is_active=True).first()
    
    if master_link:
        context.user_data['master_id'] = master_link.user_id
        master = session.query(User).filter_by(id=master_link.user_id).first()
        context.user_data['master_name'] = master.full_name
        
        # Запускаем процесс записи
        return await start_client_booking(update, context)
    else:
        await update.message.reply_text(
            "❌ Ссылка недействительна или мастер не найден\n"
            "Попробуйте другую ссылку или найдите мастеров через '🔍 Найти мастеров'",
            reply_markup=get_client_mode_keyboard()
        )
        return CLIENT_SELECT_MASTER

async def show_available_masters(update: Update, context: CallbackContext):
    """Показывает доступных мастеров"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    # Ищем всех мастеров (кроме себя)
    masters = session.query(User).filter(
        User.is_master == True,
        User.id != user.id
    ).all()
    
    if not masters:
        await update.message.reply_text(
            "❌ Пока нет других мастеров в системе\n"
            "Вы можете стать первым мастером или попросить других мастеров поделиться ссылкой",
            reply_markup=get_client_mode_keyboard()
        )
        return
    
    masters_text = "🔍 Доступные мастера:\n\n"
    keyboard = []
    
    for master in masters:
        masters_text += f"👤 {master.full_name}\n"
        masters_text += f"   💼 {master.specialty}\n"
        masters_text += f"   📞 {master.phone}\n\n"
        
        # Создаем временную ссылку для этого мастера
        from utils.master_utils import get_master_link
        link_code = get_master_link(master.id)
        if link_code:
            keyboard.append([f"👤 {master.full_name} - 📅 Записаться"])
    
    keyboard.append(['🔙 Назад'])
    
    await update.message.reply_text(
        masters_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    
    # Сохраняем mapping мастеров
    context.user_data['available_masters'] = {f"👤 {master.full_name} - 📅 Записаться": master.id for master in masters}

async def switch_back_to_master_mode(update: Update, context: CallbackContext):
    """Переключение обратно в режим мастера"""
    await update.message.reply_text(
        "👨‍💼 Возврат в режим мастера",
        reply_markup=get_main_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_client_mode(update: Update, context: CallbackContext):
    """Отмена режима клиента"""
    await update.message.reply_text(
        "❌ Режим клиента отменен",
        reply_markup=get_main_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END