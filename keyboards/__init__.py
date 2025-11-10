from telegram import ReplyKeyboardMarkup

def get_main_keyboard():
    return get_master_main_keyboard()

def get_specialty_keyboard():
    return ReplyKeyboardMarkup([
        ['💄 Косметолог/Мастер', '👨‍🏫 Репетитор'],
        ['❓ Другое']
    ], resize_keyboard=True)

def get_services_keyboard():
    return ReplyKeyboardMarkup([
        ['📋 Мои услуги', '➕ Добавить услугу'],
        ['✏️ Редактировать услугу', '🗑️ Удалить услугу'],
        ['🔙 Главное меню']
    ], resize_keyboard=True)

def get_back_keyboard():
    return ReplyKeyboardMarkup([
        ['🔙 Назад']
    ], resize_keyboard=True)

def get_schedule_keyboard():
    return ReplyKeyboardMarkup([
        ['📅 Моё расписание', '⚙️ Настройка графика'],
        ['🚫 Заблокировать время', '📋 Свободные окна'],
        ['🔙 Главное меню']
    ], resize_keyboard=True)

def get_days_keyboard():
    return ReplyKeyboardMarkup([
        ['Понедельник', 'Вторник', 'Среда'],
        ['Четверг', 'Пятница', 'Суббота'],
        ['Воскресенье', '🔙 Назад']
    ], resize_keyboard=True)

def get_time_keyboard():
    return ReplyKeyboardMarkup([
        ['09:00', '10:00', '11:00'],
        ['12:00', '13:00', '14:00'],
        ['15:00', '16:00', '17:00'],
        ['18:00', '19:00', '20:00'],
        ['🔙 Назад']
    ], resize_keyboard=True)

def get_yes_no_keyboard():
    return ReplyKeyboardMarkup([
        ['✅ Работаю', '❌ Не работаю'],
        ['🔙 Назад']
    ], resize_keyboard=True)

def get_clients_keyboard():
    return ReplyKeyboardMarkup([
        ['👥 Мои клиенты', '➕ Добавить клиента'],
        ['📅 Записать клиента', '📋 Активные записи'],
        ['🗑️ Удалить запись', '🔙 Главное меню']
    ], resize_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([
        ['❌ Отмена']
    ], resize_keyboard=True)

def get_booking_keyboard():
    return ReplyKeyboardMarkup([
        ['📅 Записать клиента', '📋 Активные записи'],
        ['🔙 Главное меню']
    ], resize_keyboard=True)

def get_clients_choice_keyboard(clients):
    keyboard = []
    for client in clients:
        keyboard.append([f"👤 {client.name} - {client.phone}"])
    keyboard.append(['🔙 Назад'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_services_choice_keyboard(services):
    keyboard = []
    for service in services:
        keyboard.append([f"📌 {service.name} - {service.duration}мин"])
    keyboard.append(['🔙 Назад'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_confirm_keyboard():
    return ReplyKeyboardMarkup([
        ['✅ Подтвердить запись', '❌ Отменить']
    ], resize_keyboard=True)

def get_client_main_keyboard():
    return ReplyKeyboardMarkup([
        ['📅 Записаться на прием', '👤 Мой профиль'],
        ['📋 Мои записи', '📞 Связаться с мастером']
    ], resize_keyboard=True)

def get_dates_keyboard(available_dates):
    keyboard = []
    for date in available_dates:
        keyboard.append([date.strftime("%d.%m.%Y (%A)")])
    keyboard.append(['🔙 Назад'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_times_keyboard(available_times):
    keyboard = []
    row = []
    for i, time in enumerate(available_times):
        row.append(time.strftime("%H:%M"))
        if (i + 1) % 3 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append(['🔙 Назад'])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_master_main_keyboard():
    return ReplyKeyboardMarkup([
        ['📅 Управление расписанием', '👥 Клиенты'],
        ['💼 Услуги', '🔗 Получить ссылку'],
        ['📅 Мои записи', '⚙️ Настройки'],
        ['👤 Режим клиента']
    ], resize_keyboard=True)

def get_main_keyboard_with_admin():
    return ReplyKeyboardMarkup([
        ['📅 Управление расписанием', '👥 Клиенты'],
        ['💼 Услуги', '🔗 Получить ссылку'],
        ['📅 Мои записи', '⚙️ Настройки'],
        ['👤 Режим клиента', '👑 Админка']
    ], resize_keyboard=True)
    
def get_settings_keyboard():
    return ReplyKeyboardMarkup([
        ['💎 Премиум функции', '👤 Профиль'],
        ['📊 Статистика', '🔙 Главное меню']
    ], resize_keyboard=True)

def get_premium_keyboard():
    return ReplyKeyboardMarkup([
        ['💎 Премиум функции', '💰 Купить премиум'],
        ['🆓 Попробовать бесплатно', '🔙 Назад в настройки']
    ], resize_keyboard=True)

def get_premium_plans_keyboard():
    return ReplyKeyboardMarkup([
        ['💼 PRO - 299₽/мес', '📅 PRO ГОД - 2990₽/год'],
        ['🔙 Назад']
    ], resize_keyboard=True)

def get_admin_keyboard():
    return ReplyKeyboardMarkup([
        ['💎 Управление премиумом', '📊 Статистика системы'],
        ['👥 Все пользователи', '⚠️ Удалить ВСЕ премиумы'],
        ['🔙 Главное меню']
    ], resize_keyboard=True)

# Добавленные функции
def get_client_mode_keyboard():
    return ReplyKeyboardMarkup([
        ['🔍 Найти мастеров'],
        ['🔙 Назад к мастеру']
    ], resize_keyboard=True)

def get_calendar_schedule_keyboard():
    return ReplyKeyboardMarkup([
        ['📅 Моё расписание', '⚙️ Настройка графика'],
        ['🚫 Заблокировать время', '📋 Свободные окна'],
        ['🔙 Главное меню']
    ], resize_keyboard=True)

def get_custom_time_keyboard():
    return ReplyKeyboardMarkup([
        ['08:00', '09:00', '10:00'],
        ['11:00', '12:00', '13:00'],
        ['14:00', '15:00', '16:00'],
        ['17:00', '18:00', '19:00'],
        ['20:00', '21:00', '22:00'],
        ['🔙 Назад']
    ], resize_keyboard=True)

def get_edit_services_keyboard():
    return ReplyKeyboardMarkup([
        ['📋 Мои услуги', '➕ Добавить услугу'],
        ['✏️ Редактировать услугу', '🗑️ Удалить услугу'],
        ['🔙 Главное меню']
    ], resize_keyboard=True)