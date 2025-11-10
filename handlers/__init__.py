from .start import start, set_specialty, set_phone, SPECIALTY, PHONE
from .services import (services_menu, show_my_services, add_service_start, 
                      add_service_name, add_service_duration, add_service_price, 
                      cancel_service_creation, SERVICE_NAME, SERVICE_DURATION, SERVICE_PRICE)
from .client_booking import (start_client_booking, choose_service, choose_date, choose_time,
                           get_client_name, get_client_phone, confirm_booking, cancel_booking,
                           CHOOSE_SERVICE, CHOOSE_DATE, CHOOSE_TIME, CONFIRM_BOOKING, CLIENT_NAME, CLIENT_PHONE)
from .master_tools import get_booking_link, show_client_appointments
from .clients_handlers import (clients_menu, show_my_clients, show_client_appointments, 
                              show_all_appointments, show_my_appointments_handler)
from .settings_handler import (
    settings_menu, premium_features, buy_premium, process_premium_purchase,
    show_statistics, user_profile, try_free_trial  # ДОБАВЬТЕ try_free_trial
)
from .booking import (start_booking, select_client, select_service, select_date, 
                     select_time, confirm_booking, show_active_appointments,
                     SELECT_CLIENT, SELECT_SERVICE, SELECT_DATE, SELECT_TIME, CONFIRM_BOOKING)
from .appointment_handlers import delete_appointment_menu, delete_appointment
from .clients import (add_client_start, add_client_name, add_client_phone, 
                     cancel_client_creation,
                     CLIENT_NAME, CLIENT_PHONE)
from .calendar_schedule import (calendar_schedule_menu, show_my_schedule, setup_schedule_start, 
                               block_time_start, show_free_slots_handler, setup_schedule_select_date,
                               calendar_set_time, calendar_add_another, block_time_select_date,
                               block_set_time, cancel_calendar_setup, cancel_block_time,
                               CALENDAR_SELECT_DATE, CALENDAR_SET_TIME, CALENDAR_ADD_ANOTHER,
                               BLOCK_SELECT_DATE, BLOCK_SET_TIME)
from .client_mode import (switch_to_client_mode, client_select_master, 
                         show_available_masters, switch_back_to_master_mode, 
                         cancel_client_mode, CLIENT_SELECT_MASTER)
from .admin_handlers import (admin_panel, manage_premium, give_premium_to_user, 
                            remove_premium, remove_all_premiums, view_system_stats, view_all_users)
from .client_commands import client_profile