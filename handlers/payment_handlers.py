from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import CallbackContext, MessageHandler, filters, ConversationHandler
from utils.payment_utils import create_premium_payment, activate_premium_subscription, get_payment_info
from database.models import session, User
import asyncio
from datetime import datetime, timedelta

# States для процесса оплаты
PAYMENT_CONFIRM, PAYMENT_PROCESS = range(2)

async def start_payment_process(update: Update, context: CallbackContext):
    """Начало процесса оплаты"""
    # Получаем тип плана из контекста (из settings_handler.py)
    plan_type = context.user_data.get('plan_type')
    
    if not plan_type:
        # Если plan_type не передан, определяем по тексту сообщения
        message_text = update.message.text
        if "PRO ГОД" in message_text or "2990" in message_text:
            plan_type = 'pro_year'
        else:
            plan_type = 'pro'
    
    if plan_type not in ['pro', 'pro_year']:
        await update.message.reply_text("❌ Неверный тип подписки")
        return ConversationHandler.END
    
    context.user_data['plan_type'] = plan_type
    
    if plan_type == 'pro':
        amount = 299
        period = "1 месяц"
        duration_days = 30
    else:
        amount = 2990
        period = "1 год"
        duration_days = 365
    
    context.user_data['amount'] = amount
    context.user_data['duration_days'] = duration_days
    
    # ОБЫЧНЫЕ КНОПКИ вместо инлайн
    keyboard = [
        [KeyboardButton("✅ Перейти к оплате")],
        [KeyboardButton("❌ Отменить")]
    ]
    
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
    
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode='Markdown'
    )
    
    return PAYMENT_CONFIRM

async def confirm_payment(update: Update, context: CallbackContext):
    """Подтверждение оплаты и создание платежа"""
    user_message = update.message.text
    
    if user_message == "❌ Отменить":
        return await cancel_payment(update, context)
    
    plan_type = context.user_data['plan_type']
    amount = context.user_data['amount']
    duration_days = context.user_data['duration_days']
    user_id = update.effective_user.id
    
    # Создаем платеж с правильными аргументами
    description = f"PRO подписка ({'год' if plan_type == 'pro_year' else 'месяц'})"
    payment = await create_premium_payment(user_id, amount, description, duration_days)
    
    if not payment:
        await update.message.reply_text(
            "❌ Ошибка при создании платежа. Попробуйте позже.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Получаем ссылку для оплаты
    payment_url = payment.confirmation.confirmation_url
    payment_id = payment.id
    
    # Сохраняем payment_id для проверки статуса
    context.user_data['payment_id'] = payment_id
    
    # ОБЫЧНЫЕ КНОПКИ вместо инлайн
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
    
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode='Markdown'
    )
    
    return PAYMENT_PROCESS

async def check_payment_status(update: Update, context: CallbackContext):
    """Проверка статуса платежа"""
    payment_id = context.user_data.get('payment_id')
    user_id = update.effective_user.id
    
    if not payment_id:
        await update.message.reply_text("❌ Информация о платеже не найдена")
        return ConversationHandler.END
    
    # Проверяем статус платежа
    payment_info = get_payment_info(payment_id)
    
    if not payment_info:
        await update.message.reply_text("❌ Не удалось проверить статус платежа")
        return ConversationHandler.END
    
    # Проверяем статус платежа
    if payment_info.status == 'succeeded':
        # Платеж успешен - активируем подписку
        duration_days = context.user_data.get('duration_days', 30)
        success = await activate_premium_subscription(user_id, duration_days)
        
        if success:
            expiry_date = await get_premium_expiry(user_id)
            if expiry_date:
                text = (
                    f"🎉 **Оплата успешно завершена!**\n\n"
                    f"✅ PRO подписка активирована!\n"
                    f"📅 Действует до: {expiry_date.strftime('%d.%m.%Y')}\n\n"
                    f"Теперь вам доступны все PRO функции!"
                )
            else:
                text = "🎉 **Оплата успешно завершена!**\n\n✅ PRO подписка активирована!"
        else:
            text = "⏳ Подписка активируется, попробуйте через минуту"
            
    elif payment_info.status == 'pending':
        text = "⏳ Платеж еще обрабатывается. Попробуйте проверить статус через несколько минут."
    elif payment_info.status == 'canceled':
        text = "❌ Платеж отменен."
    else:
        text = f"📊 Статус платежа: {payment_info.status}. Попробуйте позже."
    
    await update.message.reply_text(text, parse_mode='Markdown')
    
    # Возвращаем главное меню
    from keyboards import get_main_keyboard
    await update.message.reply_text(
        "Возвращаемся в главное меню:",
        reply_markup=get_main_keyboard()
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_payment(update: Update, context: CallbackContext):
    """Отмена процесса оплаты"""
    await update.message.reply_text(
        "❌ Процесс оплаты отменен.",
        parse_mode='Markdown'
    )
    
    # Возвращаем главное меню
    from keyboards import get_main_keyboard
    await update.message.reply_text(
        "Возвращаемся в главное меню:",
        reply_markup=get_main_keyboard()
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def get_premium_expiry(user_id):
    """Получает дату окончания подписки"""
    from database.models import PremiumSubscription, User
    user = session.query(User).filter_by(telegram_id=user_id).first()
    if user:
        premium = session.query(PremiumSubscription).filter_by(user_id=user.id, is_active=True).first()
        if premium:
            return premium.expires_at
    return None

# Регистрация обработчиков
def setup_payment_handlers(application):
    payment_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Text(["💰 Купить PRO", "💼 PRO - 299₽/мес", "📅 PRO ГОД - 2990₽/год"]), start_payment_process)
        ],
        states={
            PAYMENT_CONFIRM: [
                MessageHandler(filters.Text(["✅ Перейти к оплате", "❌ Отменить"]), confirm_payment)
            ],
            PAYMENT_PROCESS: [
                MessageHandler(filters.Text(["✅ Я оплатил", "❌ Отменить"]), check_payment_status)
            ]
        },
        fallbacks=[MessageHandler(filters.Text(["❌ Отменить"]), cancel_payment)]
    )
    
    application.add_handler(payment_conv)