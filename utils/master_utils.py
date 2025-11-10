import secrets
from database.models import session, MasterLink

def generate_master_link(user_id):
    """Генерирует уникальную ссылку для мастера"""
    
    # Проверяем есть ли уже активная ссылка
    existing_link = session.query(MasterLink).filter_by(
        user_id=user_id,
        is_active=True
    ).first()
    
    if existing_link:
        return existing_link.link_code
    
    # Генерируем новую ссылку
    link_code = secrets.token_urlsafe(16)
    
    new_link = MasterLink(
        user_id=user_id,
        link_code=link_code,
        is_active=True
    )
    
    session.add(new_link)
    session.commit()
    
    return link_code

def get_master_link(user_id):
    """Получает ссылку мастера"""
    link = session.query(MasterLink).filter_by(
        user_id=user_id,
        is_active=True
    ).first()
    
    return link.link_code if link else None