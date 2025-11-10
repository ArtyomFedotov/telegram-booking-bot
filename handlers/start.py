from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from database.models import User, session
from keyboards import get_main_keyboard, get_specialty_keyboard

SPECIALTY, PHONE = range(2)

async def start(update: Update, context: CallbackContext) -> int:
    # ЕСЛИ ЕСТЬ АРГУМЕНТЫ - это клиент по ссылке
    if context.args:
        from handlers.client_booking import start_client_booking
        return await start_client_booking(update, context)
    
    # ЕСЛИ НЕТ АРГУМЕНТОВ - проверяем, мастер или новый пользователь
    user = update.effective_user
    telegram_id = user.id
    
    # Ищем пользователя в базе
    db_user = session.query(User).filter_by(telegram_id=telegram_id).first()
    
    if db_user:
        # Если пользователь найден - это мастер, показываем мастерское меню
        await update.message.reply_text(
            f'С возвращением, {db_user.full_name}! 👨‍💼\n'
            'Вы в панели мастера.',
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    else:
        # Если пользователь не найден - предлагаем зарегистрироваться как мастер
        await update.message.reply_text(
            f'Привет, {user.full_name}! 👋\n'
            'Я помогу вам управлять записями клиентов.\n\n'
            'Для начала зарегистрируйтесь как мастер.\n'
            'Чем вы занимаетесь?',
            reply_markup=get_specialty_keyboard()
        )
        return SPECIALTY

async def set_specialty(update: Update, context: CallbackContext) -> int:
    # ПРОВЕРЯЕМ, не зарегистрирован ли уже пользователь
    user = update.effective_user
    db_user = session.query(User).filter_by(telegram_id=user.id).first()
    
    if db_user:
        await update.message.reply_text(
            f'Вы уже зарегистрированы как мастер!',
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    specialty_text = update.message.text
    specialty_map = {'💄 Косметолог/Мастер': 'beauty', '👨‍🏫 Репетитор': 'tutor', '❓ Другое': 'other'}
    context.user_data['specialty'] = specialty_map.get(specialty_text, 'other')
    context.user_data['full_name'] = update.effective_user.full_name
    context.user_data['username'] = update.effective_user.username
    
    await update.message.reply_text(
        'Отлично! Теперь укажите ваш номер телефона для связи с клиентами:',
        reply_markup=None
    )
    return PHONE

async def set_phone(update: Update, context: CallbackContext) -> int:
    # ПРОВЕРЯЕМ, не зарегистрирован ли уже пользователь
    user = update.effective_user
    db_user = session.query(User).filter_by(telegram_id=user.id).first()
    
    if db_user:
        await update.message.reply_text(
            f'Вы уже зарегистрированы как мастер!',
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    phone = update.message.text
    
    try:
        new_user = User(
            telegram_id=update.effective_user.id,
            username=context.user_data['username'],
            full_name=context.user_data['full_name'],
            specialty=context.user_data['specialty'],
            phone=phone,
            is_master=True
        )
        
        session.add(new_user)
        session.commit()
        
        await update.message.reply_text(
            '🎉 Регистрация мастера завершена!\n\n'
            'Теперь вы можете:\n'
            '• Создавать услуги\n'
            '• Настраивать расписание\n'
            '• Получить ссылку для клиентов\n'
            '• Просматривать записи\n'
            '• Записываться к другим мастерам как клиент',
            reply_markup=get_main_keyboard()
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        session.rollback()
        await update.message.reply_text(
            '❌ Произошла ошибка при регистрации. Попробуйте снова.',
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END