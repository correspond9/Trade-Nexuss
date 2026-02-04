
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from .db import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor = Column(String)
    action = Column(String)
    target = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
