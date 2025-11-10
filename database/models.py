from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, date
from config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)
session = Session()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String(100))
    full_name = Column(String(200))
    specialty = Column(String(100))
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.now)
    is_master = Column(Boolean, default=True)
    
    # Связи
    services = relationship("Service", back_populates="user", cascade="all, delete-orphan")
    clients = relationship("Client", back_populates="user", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="user", cascade="all, delete-orphan")
    working_slots = relationship("WorkingSlot", back_populates="user", cascade="all, delete-orphan")
    premium_subscription = relationship("PremiumSubscription", back_populates="user", cascade="all, delete-orphan", uselist=False)

class Service(Base):
    __tablename__ = 'services'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    name = Column(String(100))
    duration = Column(Integer)
    price = Column(Integer)
    
    user = relationship("User", back_populates="services")

class Client(Base):
    __tablename__ = 'clients'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    name = Column(String(100))
    phone = Column(String(20))
    notes = Column(Text, nullable=True)
    telegram_id = Column(Integer, nullable=True)
    telegram_username = Column(String(100), nullable=True)
    
    user = relationship("User", back_populates="clients")
    appointments = relationship("Appointment", back_populates="client")

class Appointment(Base):
    __tablename__ = 'appointments'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    client_id = Column(Integer, ForeignKey('clients.id'))
    service_id = Column(Integer, ForeignKey('services.id'))
    datetime = Column(DateTime)
    status = Column(String(20), default='booked')
    
    user = relationship("User", back_populates="appointments")
    client = relationship("Client", back_populates="appointments")
    service = relationship("Service")

class MasterLink(Base):
    __tablename__ = 'master_links'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    link_code = Column(String(50), unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User")

class WorkingSlot(Base):
    __tablename__ = 'working_slots'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    date = Column(Date)
    start_time = Column(String(5))
    end_time = Column(String(5))
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="working_slots")

class PremiumSubscription(Base):
    __tablename__ = 'premium_subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    plan_type = Column(String(20), default='basic')
    is_active = Column(Boolean, default=False)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    
    user = relationship("User", back_populates="premium_subscription")

def create_tables():
    Base.metadata.create_all(engine)

def drop_and_create_tables():
    """Удаляет и пересоздает все таблицы"""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("✅ Таблицы пересозданы!")

if __name__ == '__main__':
    drop_and_create_tables()