from datetime import datetime

from sqlalchemy import Column, DateTime

from db.session import Base, MessageMixin


class Message(Base, MessageMixin):
    __tablename__ = "messages"

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
