#!/usr/bin/env python3
from flask import Flask, request, jsonify
import sqlite3
import json
import logging
import requests
from datetime import datetime, timedelta
from config import BOT_TOKEN

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/webhook/yookassa', methods=['POST'])
def yookassa_webhook():
    try:
        # Получаем данные от ЮKassa
        data = request.get_json()
        logger.info(f"Получен вебхук: {json.dumps(data, ensure_ascii=False)}")
        
        # Обрабатываем успешный платеж
        if data.get('event') == 'payment.succeeded':
            payment_data = data.get('object', {})
            metadata = payment_data.get('metadata', {})
            
            # 🔽 ДОБАВЛЯЕМ ПРОВЕРКУ ОТ ДУБЛЕЙ
            payment_id = payment_data.get('id')
            
            # Проверяем не обрабатывали ли мы уже ЭТОТ платеж
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM premium_subscriptions WHERE payment_id = ?', (payment_id,))
            existing_payment = cursor.fetchone()
            
            if existing_payment:
                logger.info(f"Игнорируем ДУБЛЬ платежа {payment_id}")
                conn.close()
                return jsonify({'status': 'duplicate_payment'}), 200
            # 🔼 КОНЕЦ ПРОВЕРКИ
            
            # Проверяем тип продукта
            product_type = metadata.get('product_type')
            user_id = metadata.get('user_id')
            
            if product_type == 'premium' and user_id:
                # Активируем премиум подписку
                duration_days = int(metadata.get('duration_days', 30))
                
                # Определяем тип плана по количеству дней
                if duration_days == 30:
                    plan_type = 'pro'
                elif duration_days == 365:
                    plan_type = 'pro_year'
                else:
                    plan_type = 'pro'  # fallback
                
                # Рассчитываем дату окончания подписки
                expires_at = (datetime.now() + timedelta(days=duration_days)).strftime('%Y-%m-%d %H:%M:%S')
                
                # Сохраняем в базу данных С payment_id
                cursor.execute('''
                    INSERT OR REPLACE INTO premium_subscriptions 
                    (user_id, plan_type, is_active, expires_at, created_at, payment_id) 
                    VALUES (?, ?, ?, ?, datetime('now'), ?)
                ''', (user_id, plan_type, 1, expires_at, payment_id))
                
                conn.commit()
                conn.close()
                
                logger.info(f"Премиум подписка {plan_type} активирована для пользователя {user_id}, expires: {expires_at}")
                
                # Отправляем уведомление пользователю в Telegram
                try:
                    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                    
                    if plan_type == 'pro_year':
                        period_text = "годовая"
                    else:
                        period_text = "месячная"
                    
                    message_text = (
                        f"🎉 **Ваша PRO подписка активирована!**\n\n"
                        f"✅ {period_text.capitalize()} подписка успешно активирована!\n"
                        f"📅 Действует до: {expires_at.split()[0]}\n\n"
                        f"Теперь вам доступны все PRO функции!"
                    )
                    
                    

                    response = requests.post(telegram_url, json={
                        "chat_id": user_id,
                        "text": message_text,
                        "parse_mode": "Markdown",
                        "reply_markup": keyboard
                    })
                    
                    if response.status_code == 200:
                        logger.info(f"Уведомление отправлено пользователю {user_id}")
                    else:
                        logger.error(f"Ошибка отправки уведомления: {response.text}")
                        
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления: {str(e)}")
                
            else:
                logger.warning(f"Неизвестный тип продукта или отсутствует user_id: {product_type}")
                conn.close()
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {str(e)}")
        return jsonify({'status': 'error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)