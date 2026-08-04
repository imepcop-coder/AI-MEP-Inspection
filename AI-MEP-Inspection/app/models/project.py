from datetime import datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.db import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    project_code = Column(String(50), unique=True, nullable=False)
    project_name = Column(String(200), nullable=False)
    client_name = Column(String(200), nullable=False)
    consultant_name = Column(String(200), nullable=True)
    contractor_name = Column(String(200), nullable=True)
    location = Column(String(255), nullable=False)
    discipline = Column(String(100), default="MEP")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), default="Active")
    description = Column(Text, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    company = relationship("Company", foreign_keys=[company_id])
    workspace = relationship("Workspace", foreign_keys=[workspace_id])
    inspections = relationship("Inspection", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    observations = relationship("Observation", back_populates="project", cascade="all, delete-orphan")
    ncrs = relationship("NCR", back_populates="project", cascade="all, delete-orphan")