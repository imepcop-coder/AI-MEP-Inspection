from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.db import Base


class ReportTemplate(Base):
    __tablename__ = "report_templates"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if isinstance(self.fields, list):
            self.set_field_list(self.fields)
        elif self.fields is None:
            self.fields = "image,snag_description"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    fields = Column(Text, nullable=False, default="image,snag_description")
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    is_default = Column(Boolean, default=False)
    export_format = Column(String(50), default="excel")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", foreign_keys=[company_id])
    workspace = relationship("Workspace", foreign_keys=[workspace_id])

    def get_field_list(self) -> list[str]:
        if not self.fields:
            return []
        if isinstance(self.fields, list):
            return [str(field).strip() for field in self.fields if str(field).strip()]
        return [field.strip() for field in str(self.fields).split(",") if field.strip()]

    def set_field_list(self, fields: list[str]) -> None:
        self.fields = ",".join(str(field).strip() for field in fields if str(field).strip())
