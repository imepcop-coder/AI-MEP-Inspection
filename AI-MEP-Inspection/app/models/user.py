from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    role = Column(String(50), default="Engineer")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    company_name = Column(String(150), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True, index=True)
    subscription_plan = Column(String(50), default="Free")
    ai_usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    company = relationship("Company", foreign_keys=[company_id])
    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="owner", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    ai_requests = relationship("AIRequest", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    owned_company = relationship("Company", foreign_keys="Company.owner_id", back_populates="owner")

    @property
    def is_admin(self) -> bool:
        return self.role in {"Admin", "Super Admin", "Company Admin"}