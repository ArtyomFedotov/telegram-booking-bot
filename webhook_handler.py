#!/usr/bin/env python3
from flask import Flask, request, jsonify
import sqlite3
import json
import logging
import requests
from datetime import datetime, timedelta
from config import BOT_TOKEN

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/webhook/yookassa', methods=['POST'])
def yookassa_webhook():
    try:
        data = request.get_json()
        logger.info(f"Получен вебхук: {json.dumps(data, ensure_ascii=False)}")
        
        if data.get('event') == 'payment.succeeded':
            payment_data = data.get('object', {})
            metadata = payment_data.get('metadata', {})
            
            payment_id = payment_data.get('id')
            product_type = metadata.get('product_type')
            telegram_id = metadata.get('user_id')  # это telegram_id
            
            if product_type == 'premium' and telegram_id:
                conn = sqlite3.connect('bot.db')
                cursor = conn.cursor()
                
                # 🔽 ИСПРАВЛЕНИЕ: Находим user_id из таблицы users
                cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
                user = cursor.fetchone()
                if not user:
                    logger.error(f"User with telegram_id {telegram_id} not found")
                    conn.close()
                    return jsonify({'status': 'user_not_found'}), 200
                
                user_id = user[0]  # правильный user_id из таблицы users
                # 🔼 КОНЕЦ ИСПРАВЛЕНИЯ
                
                # 🛡️ ЗАЩИТА ОТ ДУБЛЕЙ: Проверяем есть ли активная подписка
                cursor.execute('''
                    SELECT id FROM premium_subscriptions 
                    WHERE user_id = ? AND expires_at > datetime('now')
                ''', (user_id,))
                
                if cursor.fetchone():
                    logger.warning(f"У user_id {user_id} уже есть активная подписка. Пропускаем платеж {payment_id}")
                    conn.close()
                    return jsonify({'status': 'already_active'}), 200
                
                # Дополнительная проверка на дубли payment_id (на всякий случай)
                cursor.execute('SELECT id FROM premium_subscriptions WHERE payment_id = ?', (payment_id,))
                if cursor.fetchone():
                    logger.info(f"Дубль платежа {payment_id}")
                    conn.close()
                    return jsonify({'status': 'duplicate'}), 200
                
                duration_days = int(metadata.get('duration_days', 30))
                plan_type = 'pro_year' if duration_days == 365 else 'pro'
                expires_at = (datetime.now() + timedelta(days=duration_days)).strftime('%Y-%m-%d %H:%M:%S')
                
                # Активируем подписку с правильным user_id
                cursor.execute('''
                    INSERT OR REPLACE INTO premium_subscriptions 
                    (user_id, plan_type, is_active, expires_at, created_at, payment_id) 
                    VALUES (?, ?, ?, ?, datetime('now'), ?)
                ''', (user_id, plan_type, 1, expires_at, payment_id))
                
                conn.commit()
                conn.close()
                
                logger.info(f"Подписка активирована для user_id {user_id} (telegram: {telegram_id})")
                
                # Отправляем уведомление
                try:
                    message_text = f"🎉 **Ваша PRO подписка активирована!**\n\n✅ Подписка действительна до: {expires_at.split()[0]}"
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                        "chat_id": telegram_id,  # отправляем на telegram_id
                        "text": message_text,
                        "parse_mode": "Markdown"
                    })
                    logger.info(f"Уведомление отправлено {telegram_id}")
                except Exception as e:
                    logger.error(f"Ошибка уведомления: {str(e)}")
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"Ошибка вебхука: {str(e)}")
        return jsonify({'status': 'error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)