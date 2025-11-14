import logging
from yookassa import Configuration, Payment
from database.models import User, PremiumSubscription, Session
from datetime import datetime, timedelta
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY

# Настройка конфигурации ЮKassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

logger = logging.getLogger(__name__)

async def create_premium_payment(user_id: int, amount: float, description: str, duration_days: int):
    try:
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                logger.error(f"User {user_id} not found")
                return None

            # Создаем платеж без чека (для тестового режима)
            payment_data = {
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/ClientsBookBot"
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": str(user_id),
                    "duration_days": str(duration_days),
                    "product_type": "premium"
                },
                "receipt": {
                    "customer": {
                        "email": user.username + "@telegram.org" if user.username else f"user{user_id}@telegram.org"
                    },
                    "items": [
                        {
                            "description": description,
                            "quantity": "1",
                            "amount": {
                                "value": str(amount),
                                "currency": "RUB"
                            },
                            "vat_code": "1",  # НДС 20%
                            "payment_mode": "full_payment",
                            "payment_subject": "service"
                        }
                    ]
                }
            }

            payment = Payment.create(payment_data, idempotency_key=str(user_id) + str(datetime.now().timestamp()))

            logger.info(f"Payment created successfully: {payment.id}")
            return payment
            
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        return None

async def activate_premium_subscription(user_id: int, duration_days: int):
    try:
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                logger.error(f"User {user_id} not found for premium activation")
                return False

            # Проверяем существующую подписку
            existing_sub = session.query(PremiumSubscription).filter_by(user_id=user.id).first()
            
            start_date = datetime.now()
            if existing_sub and existing_sub.end_date > start_date:
                # Продлеваем существующую подписку
                end_date = existing_sub.end_date + timedelta(days=duration_days)
            else:
                # Создаем новую подписку
                end_date = start_date + timedelta(days=duration_days)
                if not existing_sub:
                    existing_sub = PremiumSubscription(user_id=user.id)
                    session.add(existing_sub)

            existing_sub.start_date = start_date
            existing_sub.end_date = end_date
            existing_sub.is_active = True

            session.commit()
            logger.info(f"Premium activated for user {user_id} until {end_date}")
            return True
            
    except Exception as e:
        logger.error(f"Error activating premium: {e}")
        session.rollback()
        return False

def check_premium_status(user_id: int):
    try:
        with Session() as session:
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                return False

            premium = session.query(PremiumSubscription).filter_by(user_id=user.id).first()
            if premium and premium.is_active and premium.end_date > datetime.now():
                return True
            return False
            
    except Exception as e:
        logger.error(f"Error checking premium status: {e}")
        return False

def get_payment_info(payment_id: str):
    """
    Получить информацию о платеже по ID
    """
    try:
        payment = Payment.find_one(payment_id)
        return payment
    except Exception as e:
        logger.error(f"Error getting payment info: {e}")
        return None
