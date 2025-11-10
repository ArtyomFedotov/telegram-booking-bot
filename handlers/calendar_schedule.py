from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler
from database.models import session, User, WorkingSlot
from keyboards import get_calendar_schedule_keyboard, get_back_keyboard, get_custom_time_keyboard, get_main_keyboard
from utils.calendar_utils import generate_simple_calendar_dates, get_available_times, get_available_dates
from datetime import datetime, date, timedelta
import re
from telegram import ReplyKeyboardMarkup

# States для настройки расписания
CALENDAR_SELECT_DATE, CALENDAR_SET_TIME, CALENDAR_ADD_ANOTHER = range(3)
# States для блокировки времени
BLOCK_SELECT_DATE, BLOCK_SET_TIME = range(3, 5)

async def calendar_schedule_menu(update: Update, context: CallbackContext):
    """Меню календарного расписания"""
    await update.message.reply_text(
        "📅 **Управление расписанием**\n\n"
        "Выберите действие:\n"
        "• 📅 Моё расписание - просмотр вашего текущего расписания\n"
        "• ⚙️ Настройка графика - добавление рабочих часов\n"
        "• 🚫 Заблокировать время - блокировка времени для отдыха\n"
        "• 📋 Свободные окна - просмотр свободных слотов",
        reply_markup=get_calendar_schedule_keyboard(),
        parse_mode='Markdown'
    )

async def show_my_schedule(update: Update, context: CallbackContext):
    """Показывает текущее расписание пользователя"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    # Получаем расписание на ближайшие 7 дней
    today = date.today()
    next_week = today + timedelta(days=7)
    
    working_slots = session.query(WorkingSlot).filter(
        WorkingSlot.user_id == user.id,
        WorkingSlot.date >= today,
        WorkingSlot.date <= next_week
    ).order_by(WorkingSlot.date, WorkingSlot.start_time).all()
    
    if not working_slots:
        await update.message.reply_text(
            "📅 У вас нет настроенного расписания на ближайшую неделю.\n\n"
            "Используйте кнопку '⚙️ Настройка графика' чтобы добавить рабочие часы.",
            reply_markup=get_calendar_schedule_keyboard()
        )
        return
    
    schedule_text = "📅 **Ваше расписание на неделю:**\n\n"
    
    current_date = None
    for slot in working_slots:
        if slot.date != current_date:
            if current_date is not None:
                schedule_text += "\n"
            schedule_text += f"**{slot.date.strftime('%d.%m.%Y (%A)')}:**\n"
            current_date = slot.date
        
        emoji = "🚫" if slot.is_blocked else "🕐"
        schedule_text += f"{emoji} {slot.start_time} - {slot.end_time}"
        if slot.is_blocked:
            schedule_text += " (заблокировано)"
        schedule_text += "\n"
    
    await update.message.reply_text(
        schedule_text,
        reply_markup=get_calendar_schedule_keyboard(),
        parse_mode='Markdown'
    )

async def setup_schedule_start(update: Update, context: CallbackContext):
    """Начало настройки расписания"""
    calendar_keyboard = generate_simple_calendar_dates()
    
    await update.message.reply_text(
        "⚙️ **Настройка рабочего графика**\n\n"
        "Выберите дату для добавления рабочих часов:",
        reply_markup=ReplyKeyboardMarkup(calendar_keyboard, resize_keyboard=True)
    )
    
    # Устанавливаем флаг что это настройка графика, а не блокировка
    context.user_data['blocking_time'] = False
    return CALENDAR_SELECT_DATE

async def setup_schedule_select_date(update: Update, context: CallbackContext):
    """Обработка выбора даты для настройки расписания"""
    user_input = update.message.text
    
    if user_input == '🔙 Назад':
        await calendar_schedule_menu(update, context)
        return ConversationHandler.END
    
    # Если используется простой календарь с датами в формате "dd.mm.YYYY (Day)"
    if re.match(r'\d{2}\.\d{2}\.\d{4} \(\w+\)', user_input):
        try:
            date_str = user_input.split(' (')[0]  # Берем только дату
            selected_date = datetime.strptime(date_str, "%d.%m.%Y").date()
            
            if selected_date < date.today():
                await update.message.reply_text(
                    "❌ Нельзя выбрать прошедшую дату. Выберите другую дату:",
                    reply_markup=ReplyKeyboardMarkup(generate_simple_calendar_dates(), resize_keyboard=True)
                )
                return CALENDAR_SELECT_DATE
            
            context.user_data['selected_date'] = selected_date
            context.user_data['selected_date_str'] = selected_date.strftime('%d.%m.%Y')
            
            # Показываем существующие слоты на эту дату
            user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
            existing_slots = session.query(WorkingSlot).filter_by(
                user_id=user.id,
                date=selected_date
            ).order_by(WorkingSlot.start_time).all()
            
            if existing_slots:
                slots_text = "📅 **Существующие слоты на этот день:**\n"
                for slot in existing_slots:
                    emoji = "🚫" if slot.is_blocked else "🕐"
                    slots_text += f"{emoji} {slot.start_time} - {slot.end_time}"
                    if slot.is_blocked:
                        slots_text += " (заблокировано)"
                    slots_text += "\n"
                await update.message.reply_text(slots_text, parse_mode='Markdown')
            
            await update.message.reply_text(
                f"📅 **{selected_date.strftime('%d.%m.%Y')}**\n\n"
                f"🕐 Введите время начала работы (например 09:00):",
                reply_markup=get_custom_time_keyboard()
            )
            return CALENDAR_SET_TIME
            
        except ValueError as e:
            await update.message.reply_text(
                "❌ Ошибка формата даты. Выберите дату из списка:",
                reply_markup=ReplyKeyboardMarkup(generate_simple_calendar_dates(), resize_keyboard=True)
            )
            return CALENDAR_SELECT_DATE
    
    await update.message.reply_text(
        "❌ Пожалуйста, выберите дату из списка:",
        reply_markup=ReplyKeyboardMarkup(generate_simple_calendar_dates(), resize_keyboard=True)
    )
    return CALENDAR_SELECT_DATE

async def block_time_start(update: Update, context: CallbackContext):
    """Блокировка времени (отдых/перерыв)"""
    calendar_keyboard = generate_simple_calendar_dates()
    
    await update.message.reply_text(
        "🚫 **Блокировка времени**\n\n"
        "Выберите дату для блокировки времени (отдых/перерыв):",
        reply_markup=ReplyKeyboardMarkup(calendar_keyboard, resize_keyboard=True)
    )
    
    # Устанавливаем флаг что это блокировка времени
    context.user_data['blocking_time'] = True
    return BLOCK_SELECT_DATE

async def block_time_select_date(update: Update, context: CallbackContext):
    """Обработка выбора даты для блокировки времени"""
    user_input = update.message.text
    
    if user_input == '🔙 Назад':
        await calendar_schedule_menu(update, context)
        return ConversationHandler.END
    
    # Если используется простой календарь с датами в формате "dd.mm.YYYY (Day)"
    if re.match(r'\d{2}\.\d{2}\.\d{4} \(\w+\)', user_input):
        try:
            date_str = user_input.split(' (')[0]  # Берем только дату
            selected_date = datetime.strptime(date_str, "%d.%m.%Y").date()
            
            if selected_date < date.today():
                await update.message.reply_text(
                    "❌ Нельзя выбрать прошедшую дату. Выберите другую дату:",
                    reply_markup=ReplyKeyboardMarkup(generate_simple_calendar_dates(), resize_keyboard=True)
                )
                return BLOCK_SELECT_DATE
            
            context.user_data['selected_date'] = selected_date
            context.user_data['selected_date_str'] = selected_date.strftime('%d.%m.%Y')
            
            await update.message.reply_text(
                f"📅 **{selected_date.strftime('%d.%m.%Y')}**\n\n"
                f"🕐 Введите время начала блокировки (например 13:00):",
                reply_markup=get_custom_time_keyboard()
            )
            return BLOCK_SET_TIME
            
        except ValueError as e:
            await update.message.reply_text(
                "❌ Ошибка формата даты. Выберите дату из списка:",
                reply_markup=ReplyKeyboardMarkup(generate_simple_calendar_dates(), resize_keyboard=True)
            )
            return BLOCK_SELECT_DATE
    
    await update.message.reply_text(
        "❌ Пожалуйста, выберите дату из списка:",
        reply_markup=ReplyKeyboardMarkup(generate_simple_calendar_dates(), resize_keyboard=True)
    )
    return BLOCK_SELECT_DATE

async def calendar_set_time(update: Update, context: CallbackContext):
    """Установка времени работы"""
    if update.message.text == '🔙 Назад':
        await calendar_schedule_menu(update, context)
        return ConversationHandler.END
    
    time_text = update.message.text
    
    # Проверяем формат времени
    if re.match(r'^[0-2][0-9]:[0-5][0-9]$', time_text):
        try:
            hours, minutes = map(int, time_text.split(':'))
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                if 'start_time' not in context.user_data:
                    context.user_data['start_time'] = time_text
                    
                    is_blocking = context.user_data.get('blocking_time', False)
                    if is_blocking:
                        action_text = "блокировки"
                    else:
                        action_text = "работы"
                    
                    await update.message.reply_text(
                        f"🕐 Введите время окончания {action_text} (например 18:00):",
                        reply_markup=get_custom_time_keyboard()
                    )
                    return CALENDAR_SET_TIME
                else:
                    context.user_data['end_time'] = time_text
                    
                    # Проверяем корректность временного промежутка
                    start_hour, start_minute = map(int, context.user_data['start_time'].split(':'))
                    end_hour, end_minute = map(int, time_text.split(':'))
                    
                    start_total = start_hour * 60 + start_minute
                    end_total = end_hour * 60 + end_minute
                    
                    if end_total <= start_total:
                        await update.message.reply_text(
                            "❌ Время окончания должно быть позже времени начала\n"
                            "Введите время окончания:",
                            reply_markup=get_custom_time_keyboard()
                        )
                        return CALENDAR_SET_TIME
                    
                    # Сохраняем слот
                    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
                    selected_date = context.user_data['selected_date']
                    
                    is_blocking = context.user_data.get('blocking_time', False)
                    
                    slot = WorkingSlot(
                        user_id=user.id,
                        date=selected_date,
                        start_time=context.user_data['start_time'],
                        end_time=context.user_data['end_time'],
                        is_blocked=is_blocking  # Устанавливаем флаг блокировки
                    )
                    
                    session.add(slot)
                    session.commit()
                    
                    if is_blocking:
                        success_message = (
                            f"✅ **Время заблокировано!**\n\n"
                            f"📅 {context.user_data['selected_date_str']}\n"
                            f"🚫 {context.user_data['start_time']} - {context.user_data['end_time']}\n\n"
                            f"Это время будет недоступно для записи клиентов."
                        )
                        await update.message.reply_text(
                            success_message,
                            reply_markup=get_calendar_schedule_keyboard()
                        )
                        context.user_data.clear()
                        return ConversationHandler.END
                    else:
                        success_message = (
                            f"✅ **Рабочие часы добавлены!**\n\n"
                            f"📅 {context.user_data['selected_date_str']}\n"
                            f"🕐 {context.user_data['start_time']} - {context.user_data['end_time']}\n\n"
                            f"Хотите добавить еще один временной промежуток на этот же день?"
                        )
                        await update.message.reply_text(
                            success_message,
                            reply_markup=ReplyKeyboardMarkup([
                                ['✅ Да', '❌ Нет']
                            ], resize_keyboard=True)
                        )
                        return CALENDAR_ADD_ANOTHER
                    
            else:
                await update.message.reply_text("❌ Неверное время. Часы должны быть 00-23, минуты 00-59")
                return CALENDAR_SET_TIME
        except ValueError:
            await update.message.reply_text("❌ Неверный формат времени")
            return CALENDAR_SET_TIME
    else:
        await update.message.reply_text("❌ Неверный формат. Используйте ЧЧ:ММ (например 09:00)")
        return CALENDAR_SET_TIME

async def block_set_time(update: Update, context: CallbackContext):
    """Установка времени для блокировки - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    if update.message.text == '🔙 Назад':
        await calendar_schedule_menu(update, context)
        return ConversationHandler.END
    
    time_text = update.message.text
    
    # Проверяем формат времени
    if re.match(r'^[0-2][0-9]:[0-5][0-9]$', time_text):
        try:
            hours, minutes = map(int, time_text.split(':'))
            if 0 <= hours <= 23 and 0 <= minutes <= 59:
                if 'start_time' not in context.user_data:
                    context.user_data['start_time'] = time_text
                    
                    await update.message.reply_text(
                        f"🕐 Введите время окончания блокировки (например 14:00):",
                        reply_markup=get_custom_time_keyboard()
                    )
                    return BLOCK_SET_TIME
                else:
                    context.user_data['end_time'] = time_text
                    
                    # Проверяем корректность временного промежутка
                    start_hour, start_minute = map(int, context.user_data['start_time'].split(':'))
                    end_hour, end_minute = map(int, time_text.split(':'))
                    
                    start_total = start_hour * 60 + start_minute
                    end_total = end_hour * 60 + end_minute
                    
                    if end_total <= start_total:
                        await update.message.reply_text(
                            "❌ Время окончания должно быть позже времени начала\n"
                            "Введите время окончания:",
                            reply_markup=get_custom_time_keyboard()
                        )
                        return BLOCK_SET_TIME
                    
                    # Сохраняем слот блокировки
                    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
                    selected_date = context.user_data['selected_date']
                    
                    slot = WorkingSlot(
                        user_id=user.id,
                        date=selected_date,
                        start_time=context.user_data['start_time'],
                        end_time=context.user_data['end_time'],
                        is_blocked=True  # Помечаем как заблокированное время
                    )
                    
                    session.add(slot)
                    session.commit()
                    
                    success_message = (
                        f"✅ **Время заблокировано!**\n\n"
                        f"📅 {context.user_data['selected_date_str']}\n"
                        f"🚫 {context.user_data['start_time']} - {context.user_data['end_time']}\n\n"
                        f"Это время будет недоступно для записи клиентов."
                    )
                    
                    await update.message.reply_text(
                        success_message,
                        reply_markup=get_calendar_schedule_keyboard()
                    )
                    
                    context.user_data.clear()
                    return ConversationHandler.END
                    
            else:
                await update.message.reply_text("❌ Неверное время. Часы должны быть 00-23, минуты 00-59")
                return BLOCK_SET_TIME
        except ValueError:
            await update.message.reply_text("❌ Неверный формат времени")
            return BLOCK_SET_TIME
    else:
        await update.message.reply_text("❌ Неверный формат. Используйте ЧЧ:ММ (например 09:00)")
        return BLOCK_SET_TIME

async def calendar_add_another(update: Update, context: CallbackContext):
    """Обработка добавления еще одного слота"""
    if update.message.text == '✅ Да':
        # Очищаем временные данные для нового слота
        context.user_data.pop('start_time', None)
        context.user_data.pop('end_time', None)
        
        await update.message.reply_text(
            f"📅 {context.user_data['selected_date_str']}\n\n"
            "🕐 Введите время начала следующего рабочего промежутка:",
            reply_markup=get_custom_time_keyboard()
        )
        return CALENDAR_SET_TIME
    
    elif update.message.text == '❌ Нет':
        await update.message.reply_text(
            f"✅ Расписание на {context.user_data['selected_date_str']} сохранено!",
            reply_markup=get_calendar_schedule_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    else:
        await update.message.reply_text("Пожалуйста, выберите вариант из списка:")
        return CALENDAR_ADD_ANOTHER

async def show_free_slots_handler(update: Update, context: CallbackContext):
    """Показывает свободные окна - РАБОЧАЯ ВЕРСИЯ"""
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if not user:
        await update.message.reply_text("Сначала завершите регистрацию через /start")
        return
    
    # Получаем расписание на ближайшие 3 дня
    today = date.today()
    free_slots_text = "📋 **Свободные окна на ближайшие дни:**\n\n"
    
    has_slots = False
    for i in range(3):
        current_date = today + timedelta(days=i)
        
        # Получаем доступное время
        available_times = get_available_times(user.id, current_date)
        
        if available_times:
            has_slots = True
            free_slots_text += f"**{current_date.strftime('%d.%m.%Y (%A)')}:**\n"
            
            # Группируем время по часам для лучшего отображения
            time_groups = {}
            for time_slot in available_times:
                hour = time_slot.strftime('%H:00')
                if hour not in time_groups:
                    time_groups[hour] = []
                time_groups[hour].append(time_slot.strftime('%H:%M'))
            
            for hour, times in time_groups.items():
                free_slots_text += f"   🕐 {', '.join(times[:3])}"
                if len(times) > 3:
                    free_slots_text += f" ... (+{len(times)-3})"
                free_slots_text += "\n"
            
            free_slots_text += f"   ✅ Свободных слотов: {len(available_times)}\n\n"
    
    if not has_slots:
        free_slots_text += "❌ На ближайшие дни нет свободных окон.\nНастройте расписание с помощью кнопки '⚙️ Настройка графика'"
    
    await update.message.reply_text(
        free_slots_text,
        reply_markup=get_calendar_schedule_keyboard(),
        parse_mode='Markdown'
    )

async def cancel_calendar_setup(update: Update, context: CallbackContext):
    """Отмена настройки расписания"""
    await update.message.reply_text(
        "❌ Настройка расписания отменена",
        reply_markup=get_calendar_schedule_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_block_time(update: Update, context: CallbackContext):
    """Отмена блокировки времени"""
    await update.message.reply_text(
        "❌ Блокировка времени отменена",
        reply_markup=get_calendar_schedule_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END