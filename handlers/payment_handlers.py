from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from utils.payment_utils import create_premium_payment, activate_premium_subscription, get_payment_info
from database.models import session, User
import asyncio
from datetime import datetime, timedelta

# States для процесса оплаты
PAYMENT_CONFIRM, PAYMENT_PROCESS = range(2)

async def start_payment_process(update: Update, context: CallbackContext):
    """Начало процесса оплаты"""
    query = update.callback_query
    await query.answer()
    
    plan_type = query.data.replace('buy_', '')
    
    if plan_type not in ['pro', 'pro_year']:
        await query.edit_message_text("❌ Неверный тип подписки")
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
    
    keyboard = [
        [InlineKeyboardButton("✅ Перейти к оплате", callback_data=f"confirm_payment_{plan_type}")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_payment")]
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
        f"Для оплаты нажмите кнопку ниже:"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return PAYMENT_CONFIRM

async def confirm_payment(update: Update, context: CallbackContext):
    """Подтверждение оплаты и создание платежа"""
    query = update.callback_query
    await query.answer()
    
    plan_type = context.user_data['plan_type']
    amount = context.user_data['amount']
    duration_days = context.user_data['duration_days']
    user_id = update.effective_user.id
    
    # Создаем платеж с правильными аргументами
    description = f"PRO подписка ({'год' if plan_type == 'pro_year' else 'месяц'})"
    payment = await create_premium_payment(user_id, amount, description, duration_days)
    
    if not payment:
        await query.edit_message_text(
            "❌ Ошибка при создании платежа. Попробуйте позже.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Получаем ссылку для оплаты
    payment_url = payment.confirmation.confirmation_url
    
    keyboard = [
        [InlineKeyboardButton("💳 Перейти к оплате", url=payment_url)],
        [InlineKeyboardButton("✅ Я оплатил", callback_data="check_payment")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel_payment")]
    ]
    
    text = (
        f"💳 **Оплата PRO подписки**\n\n"
        f"Для завершения оплаты:\n"
        f"1. Нажмите '💳 Перейти к оплате'\n"
        f"2. Оплатите заказ\n"
        f"3. Вернитесь в бот и нажмите '✅ Я оплатил'\n\n"
        f"Ссылка для оплаты действительна 24 часа."
    )
    
    context.user_data['payment_id'] = payment.id
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return PAYMENT_PROCESS

async def check_payment_status(update: Update, context: CallbackContext):
    """Проверка статуса платежа"""
    query = update.callback_query
    await query.answer()
    
    payment_id = context.user_data.get('payment_id')
    user_id = update.effective_user.id
    duration_days = context.user_data.get('duration_days')
    
    if not payment_id:
        await query.edit_message_text("❌ Информация о платеже не найдена")
        return ConversationHandler.END
    
    # Проверяем статус платежа
    payment_info = get_payment_info(payment_id)
    
    if not payment_info:
        await query.edit_message_text("❌ Не удалось проверить статус платежа")
        return ConversationHandler.END
    
    # Проверяем статус платежа И наличие активной подписки
    from utils.payment_utils import check_premium_status
    
    if payment_info.status == 'succeeded' or check_premium_status(user_id):
        # Если подписка еще не активирована - активируем
        if not check_premium_status(user_id):
            success = await activate_premium_subscription(user_id, duration_days)
        else:
            success = True
        
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
        text = f"📊 Статус платежа: {payment_info.status}"
    
    await query.edit_message_text(text, parse_mode='Markdown')
    return ConversationHandler.END

async def cancel_payment(update: Update, context: CallbackContext):
    """Отмена процесса оплаты"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "❌ Процесс оплаты отменен.",
        parse_mode='Markdown'
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
            return premium.end_date
    return None

# Регистрация обработчиков
def setup_payment_handlers(application):
    payment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_payment_process, pattern='^buy_(pro|pro_year)$')],
        states={
            PAYMENT_CONFIRM: [
                CallbackQueryHandler(confirm_payment, pattern='^confirm_payment_'),
                CallbackQueryHandler(cancel_payment, pattern='^cancel_payment$')
            ],
            PAYMENT_PROCESS: [
                CallbackQueryHandler(check_payment_status, pattern='^check_payment$'),
                CallbackQueryHandler(cancel_payment, pattern='^cancel_payment$')
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel_payment, pattern='^cancel_payment$')]
    )
    
    application.add_handler(payment_conv)