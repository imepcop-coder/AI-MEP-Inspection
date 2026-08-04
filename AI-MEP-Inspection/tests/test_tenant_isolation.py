import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.tenant import apply_tenant_filter, ensure_tenant_access
from app.database.db import Base
from app.models.chat import Chat
from app.models.company import Company
from app.models.inspection import Inspection
from app.models.project import Project
from app.models.report_template import ReportTemplate
from app.models.user import User
from app.models.workspace import Workspace


def test_tenant_filters_scope_queries_to_the_current_company():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    try:
        company_a = Company(name="Company A", slug="company-a", is_active=True)
        company_b = Company(name="Company B", slug="company-b", is_active=True)
        db.add_all([company_a, company_b])
        db.flush()

        workspace_a = Workspace(name="Workspace A", slug="workspace-a", company_id=company_a.id, is_active=True)
        workspace_b = Workspace(name="Workspace B", slug="workspace-b", company_id=company_b.id, is_active=True)
        db.add_all([workspace_a, workspace_b])
        db.flush()

        user_a = User(
            full_name="Alice",
            email="alice@example.com",
            phone="+971111111111",
            password="hashed",
            role="Admin",
            company_id=company_a.id,
            workspace_id=workspace_a.id,
            is_active=True,
            is_verified=True,
        )
        user_b = User(
            full_name="Bob",
            email="bob@example.com",
            phone="+971222222222",
            password="hashed",
            role="Engineer",
            company_id=company_b.id,
            workspace_id=workspace_b.id,
            is_active=True,
            is_verified=True,
        )
        db.add_all([user_a, user_b])
        db.flush()

        project_a = Project(
            project_code="PRJ-A",
            project_name="Project A",
            client_name="Client A",
            location="Dubai",
            company_id=company_a.id,
            workspace_id=workspace_a.id,
            user_id=user_a.id,
        )
        project_b = Project(
            project_code="PRJ-B",
            project_name="Project B",
            client_name="Client B",
            location="Abu Dhabi",
            company_id=company_b.id,
            workspace_id=workspace_b.id,
            user_id=user_b.id,
        )
        db.add_all([project_a, project_b])
        db.flush()

        inspection_a = Inspection(
            inspection_no="INV-A",
            project_id=project_a.id,
            user_id=user_a.id,
            discipline="HVAC",
            company_id=company_a.id,
            workspace_id=workspace_a.id,
            status="Open",
        )
        inspection_b = Inspection(
            inspection_no="INV-B",
            project_id=project_b.id,
            user_id=user_b.id,
            discipline="MEP",
            company_id=company_b.id,
            workspace_id=workspace_b.id,
            status="Open",
        )
        chat_a = Chat(user_id=user_a.id, title="Chat A", company_id=company_a.id, workspace_id=workspace_a.id)
        chat_b = Chat(user_id=user_b.id, title="Chat B", company_id=company_b.id, workspace_id=workspace_b.id)
        template_a = ReportTemplate(name="Template A", company_id=company_a.id, workspace_id=workspace_a.id, fields="image")
        template_b = ReportTemplate(name="Template B", company_id=company_b.id, workspace_id=workspace_b.id, fields="image")

        db.add_all([inspection_a, inspection_b, chat_a, chat_b, template_a, template_b])
        db.commit()

        projects = apply_tenant_filter(db.query(Project), user_a).all()
        inspections = apply_tenant_filter(db.query(Inspection), user_a).all()
        chats = apply_tenant_filter(db.query(Chat), user_a).all()
        templates = apply_tenant_filter(db.query(ReportTemplate), user_a).all()

        assert [item.id for item in projects] == [project_a.id]
        assert [item.id for item in inspections] == [inspection_a.id]
        assert [item.id for item in chats] == [chat_a.id]
        assert [item.id for item in templates] == [template_a.id]

        ensure_tenant_access(project_a, user_a)
        with pytest.raises(PermissionError):
            ensure_tenant_access(project_b, user_a)
    finally:
        db.close()
