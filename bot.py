import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from config import BOT_TOKEN
from handlers.start import start, set_specialty, set_phone, SPECIALTY, PHONE
from handlers.services import (
    services_menu, show_my_services, add_service_start, add_service_name, 
    add_service_duration, add_service_price, cancel_service_creation, 
    SERVICE_NAME, SERVICE_DURATION, SERVICE_PRICE,
    edit_service_start, edit_select_service, edit_service_name, 
    edit_service_duration, edit_service_price, delete_service_start, 
    delete_select_service, EDIT_SELECT_SERVICE, EDIT_SERVICE_NAME, 
    EDIT_SERVICE_DURATION, EDIT_SERVICE_PRICE, DELETE_SELECT_SERVICE
)
from handlers.client_booking import start_client_booking, choose_service, choose_date, choose_time, get_client_name, get_client_phone, confirm_booking, cancel_booking, CHOOSE_SERVICE, CHOOSE_DATE, CHOOSE_TIME, CONFIRM_BOOKING, CLIENT_NAME, CLIENT_PHONE
from handlers.master_tools import get_booking_link, show_client_appointments
from database.models import Base, engine
from keyboards import get_main_keyboard, get_main_keyboard_with_admin
from handlers.clients_handlers import (
    clients_menu, show_my_clients, show_client_appointments, show_all_appointments,
    show_my_appointments_handler
)
from handlers.settings_handler import (
    settings_menu, premium_features, process_premium_purchase,
    show_statistics, user_profile, try_free_trial
)
from handlers.booking import start_booking, select_client, select_service, select_date, select_time, confirm_booking, show_active_appointments, SELECT_CLIENT, SELECT_SERVICE, SELECT_DATE, SELECT_TIME, CONFIRM_BOOKING
from handlers.appointment_handlers import delete_appointment_menu, delete_appointment
from handlers.clients import add_client_start, add_client_name, add_client_phone, cancel_client_creation, CLIENT_NAME, CLIENT_PHONE
from handlers.calendar_schedule import (
    calendar_schedule_menu, show_my_schedule, setup_schedule_start, 
    block_time_start, show_free_slots_handler, setup_schedule_select_date,
    calendar_set_time, calendar_add_another, block_time_select_date,
    block_set_time, cancel_calendar_setup, cancel_block_time,
    CALENDAR_SELECT_DATE, CALENDAR_SET_TIME, CALENDAR_ADD_ANOTHER,
    BLOCK_SELECT_DATE, BLOCK_SET_TIME
)
from handlers.client_mode import (
    switch_to_client_mode, client_select_master, show_available_masters,
    switch_back_to_master_mode, cancel_client_mode, CLIENT_SELECT_MASTER
)
from handlers.admin_handlers import (
    admin_panel, manage_premium, give_premium_to_user, 
    remove_premium, remove_all_premiums, view_system_stats, view_all_users
)
from handlers.client_commands import client_profile
from handlers.payment_handlers import setup_payment_handlers


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    # Создаем таблицы в базе данных
    Base.metadata.create_all(engine)
    print("✅ База данных создана!")
    
    application = Application.builder().token(BOT_TOKEN).build()
    print("✅ Бот инициализирован!")
    
    print("✅ Бот запущен!")
    
    # ОСНОВНОЙ обработчик команды /start (и для мастеров, и для клиентов)
    start_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SPECIALTY: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_specialty)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_phone)],
        },
        fallbacks=[]
    )
    
    # Обработчик записи клиентов (через ссылку)
    client_booking_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^📅 Записаться на прием$'), start_client_booking)],
        states={
            CHOOSE_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_service)],
            CHOOSE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_date)],
            CHOOSE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_time)],
            CLIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_client_name)],
            CLIENT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_client_phone)],
            CONFIRM_BOOKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_booking)],
        },
        fallbacks=[MessageHandler(filters.Regex('^🔙 Назад$|^❌ Отменить$'), cancel_booking)]
    )
    
    # Обработчик создания услуг
    service_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^➕ Добавить услугу$'), add_service_start)],
        states={
            SERVICE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_service_name)],
            SERVICE_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_service_duration)],
            SERVICE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_service_price)],
        },
        fallbacks=[MessageHandler(filters.Regex('^🔙 Назад$'), cancel_service_creation)]
    )
    
    # Обработчик редактирования услуг
    edit_service_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^✏️ Редактировать услугу$'), edit_service_start)],
        states={
            EDIT_SELECT_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_select_service)],
            EDIT_SERVICE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_service_name)],
            EDIT_SERVICE_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_service_duration)],
            EDIT_SERVICE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_service_price)],
        },
        fallbacks=[MessageHandler(filters.Regex('^🔙 Назад$'), services_menu)]
    )
    
    # Обработчик удаления услуг
    delete_service_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🗑️ Удалить услугу$'), delete_service_start)],
        states={
            DELETE_SELECT_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_select_service)],
        },
        fallbacks=[MessageHandler(filters.Regex('^🔙 Назад$'), services_menu)]
    )
    
    # Обработчик записи клиентов мастером
    master_booking_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^📅 Записать клиента$'), start_booking)],
        states={
            SELECT_CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_client)],
            SELECT_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_service)],
            SELECT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_date)],
            SELECT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_time)],
            CONFIRM_BOOKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_booking)],
        },
        fallbacks=[MessageHandler(filters.Regex('^🔙 Назад$'), show_active_appointments)]
    )
    
    # Обработчик добавления клиентов
    add_client_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^➕ Добавить клиента$'), add_client_start)],
        states={
            CLIENT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_client_name)],
            CLIENT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_client_phone)],
        },
        fallbacks=[MessageHandler(filters.Regex('^❌ Отмена$'), cancel_client_creation)]
    )
    
    # Обработчик календарного расписания
    calendar_schedule_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^📅 Управление расписанием$'), calendar_schedule_menu)],
        states={
            CALENDAR_SELECT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_schedule_select_date)],
            CALENDAR_SET_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, calendar_set_time)],
            CALENDAR_ADD_ANOTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, calendar_add_another)],
        },
        fallbacks=[MessageHandler(filters.Regex('^🔙 Назад$'), cancel_calendar_setup)]
    )

    # Обработчик режима клиента
    client_mode_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^👤 Режим клиента$'), switch_to_client_mode)],
        states={
            CLIENT_SELECT_MASTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, client_select_master)],
        },
        fallbacks=[
            MessageHandler(filters.Regex('^🔙 Назад к мастеру$'), switch_back_to_master_mode),
            MessageHandler(filters.Regex('^🔙 Назад$'), cancel_client_mode)
        ]
    )

    # ConversationHandler для настройки графика
    setup_schedule_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^⚙️ Настройка графика$'), setup_schedule_start)],
        states={
            CALENDAR_SELECT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, setup_schedule_select_date)],
            CALENDAR_SET_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, calendar_set_time)],
            CALENDAR_ADD_ANOTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, calendar_add_another)],
        },
        fallbacks=[MessageHandler(filters.Regex('^🔙 Назад$'), cancel_calendar_setup)]
    )

    # ConversationHandler для блокировки времени
    block_time_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🚫 Заблокировать время$'), block_time_start)],
        states={
            BLOCK_SELECT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, block_time_select_date)],
            BLOCK_SET_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, block_set_time)],
        },
        fallbacks=[MessageHandler(filters.Regex('^🔙 Назад$'), cancel_block_time)]
    )

    # Добавляем ВСЕ обработчики ConversationHandler
    application.add_handler(start_conv)
    application.add_handler(client_booking_conv)
    application.add_handler(service_conv)
    application.add_handler(edit_service_conv)
    application.add_handler(delete_service_conv)
    application.add_handler(master_booking_conv)
    application.add_handler(add_client_conv)
    application.add_handler(calendar_schedule_conv)
    application.add_handler(client_mode_conv)
    application.add_handler(setup_schedule_conv)
    application.add_handler(block_time_conv)
    
    # Обработчики меню для мастеров
    application.add_handler(MessageHandler(filters.Regex('^💼 Услуги$'), services_menu))
    application.add_handler(MessageHandler(filters.Regex('^📋 Мои услуги$'), show_my_services))
    application.add_handler(MessageHandler(filters.Regex('^🔗 Получить ссылку$'), get_booking_link))
    application.add_handler(MessageHandler(filters.Regex('^📅 Мои записи$'), show_my_appointments_handler))
    
    # Обработчики для клиентов
    application.add_handler(MessageHandler(filters.Regex('^📅 Записаться на прием$'), start_client_booking))
    application.add_handler(MessageHandler(filters.Regex('^📋 Мои записи$'), show_client_appointments))
    application.add_handler(MessageHandler(filters.Regex('^👤 Мой профиль$'), client_profile))
    application.add_handler(MessageHandler(filters.Regex('^📞 Связаться с мастером$'), lambda u, c: u.message.reply_text("📞 Телефон мастера: +7 XXX XXX-XX-XX")))
    
    # Обработчики расписания
    application.add_handler(MessageHandler(filters.Regex('^📅 Управление расписанием$'), calendar_schedule_menu))
    application.add_handler(MessageHandler(filters.Regex('^📅 Моё расписание$'), show_my_schedule))
    application.add_handler(MessageHandler(filters.Regex('^📋 Свободные окна$'), show_free_slots_handler))
    
    # Обработчики для клиентов
    application.add_handler(MessageHandler(filters.Regex('^👥 Клиенты$'), clients_menu))
    application.add_handler(MessageHandler(filters.Regex('^👥 Мои клиенты$'), show_my_clients))
    application.add_handler(MessageHandler(filters.Regex('^📅 Записи клиентов$'), show_client_appointments))
    application.add_handler(MessageHandler(filters.Regex('^📋 Все записи$'), show_all_appointments))
    application.add_handler(MessageHandler(filters.Regex('^📋 Активные записи$'), show_active_appointments))
    application.add_handler(MessageHandler(filters.Regex('^🗑️ Удалить запись$'), delete_appointment_menu))
    application.add_handler(MessageHandler(filters.Regex('^🗑️'), delete_appointment))
    
    # Обработчики для настроек
    application.add_handler(MessageHandler(filters.Regex('^⚙️ Настройки$'), settings_menu))
    application.add_handler(MessageHandler(filters.Regex('^💎 Премиум функции$'), premium_features))
    application.add_handler(MessageHandler(filters.Regex('^👤 Профиль$'), user_profile))
    application.add_handler(MessageHandler(filters.Regex('^📊 Статистика$'), lambda update, context: show_statistics(update, context)))
    
    # Обработчики премиума
    application.add_handler(MessageHandler(filters.Regex('^💰 Купить премиум$'), premium_features))  # Изменено с buy_premium на premium_features
    application.add_handler(MessageHandler(filters.Regex('^💼 PRO - 299₽/мес$|^📅 PRO ГОД - 2990₽/год$'), process_premium_purchase))
    application.add_handler(MessageHandler(filters.Regex('^🆓 Попробовать бесплатно$'), try_free_trial))
    
    # Обработчики для админ-панели
    application.add_handler(MessageHandler(filters.Regex('^👑 Админка$'), admin_panel))
    application.add_handler(MessageHandler(filters.Regex('^💎 Управление премиумом$'), manage_premium))
    application.add_handler(MessageHandler(filters.Regex('^💎 Выдать премиум:'), give_premium_to_user))
    application.add_handler(MessageHandler(filters.Regex('^❌ Удалить премиум:'), remove_premium))
    application.add_handler(MessageHandler(filters.Regex('^⚠️ Удалить ВСЕ премиумы$'), remove_all_premiums))
    application.add_handler(MessageHandler(filters.Regex('^📊 Статистика системы$'), view_system_stats))
    application.add_handler(MessageHandler(filters.Regex('^👥 Все пользователи$'), view_all_users))
    application.add_handler(MessageHandler(filters.Regex('^🔙 Назад в админку$'), admin_panel))
    application.add_handler(MessageHandler(filters.Regex('^💎 Выдать PRO:'), give_premium_to_user))
    application.add_handler(MessageHandler(filters.Regex('^❌ Удалить PRO:'), remove_premium))
    
    # Добавляем обработчики платежей
    setup_payment_handlers(application)
    
    # Обработчики навигации в настройках
    application.add_handler(MessageHandler(filters.Regex('^🔙 Назад в настройки$'), settings_menu))
    
    # Общие обработчики
    application.add_handler(MessageHandler(filters.Regex('^🔙 Главное меню$'), lambda u, c: u.message.reply_text("Главное меню", reply_markup=get_main_keyboard_with_admin())))
    application.add_handler(MessageHandler(filters.Regex('^🔙 Назад$'), lambda u, c: u.message.reply_text("Возврат", reply_markup=get_main_keyboard_with_admin())))

    print("✅ Обработчики добавлены!")
    print("🚀 Запускаю бота...")
    
    application.run_polling()

if __name__ == '__main__':
    main()