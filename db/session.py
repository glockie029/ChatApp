from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from core.config import settings


connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class MessageMixin:
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True, default="Anonymous")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime)
    ip_address = Column(String, nullable=True)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
