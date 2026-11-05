import asyncio
from pathlib import Path

from fastapi import Request
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.db import Base
from app.main import analytics as analytics_page, app
from app.models.company import Company
from app.models.inspection import Inspection
from app.models.notification import Notification
from app.models.project import Project
from app.models.user import User
from app.models.workspace import Workspace
from app.routes.notifications import mark_all_notifications_read
from app.routes.project import project_list
from app.routes.report import _csv_safe_value, export_inspections_csv
from app.services.workspace_service import WorkspaceService


def _request(path: str, user_id: int, query_string: str = "") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 1234),
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": query_string.encode("ascii"),
            "headers": [(b"host", b"testserver")],
            "session": {"user": {"id": user_id}},
            "state": {"current_user": None, "unread_notification_count": 0},
            "app": app,
        }
    )


def _create_tenant(db, suffix: str):
    company = Company(name=f"Company {suffix}", slug=f"company-{suffix}", is_active=True)
    db.add(company)
    db.flush()
    workspace = Workspace(
        name=f"Workspace {suffix}",
        slug=f"workspace-{suffix}",
        company_id=company.id,
        is_active=True,
    )
    db.add(workspace)
    db.flush()
    user = User(
        full_name=f"User {suffix}",
        email=f"user-{suffix}@example.com",
        password="test-password-hash",
        phone=f"+971555000{suffix}",
        role="Engineer",
        company_id=company.id,
        workspace_id=workspace.id,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.flush()
    return company, workspace, user


def _create_inspection(db, user, project, inspection_no: str, status: str, description: str = ""):
    inspection = Inspection(
        inspection_no=inspection_no,
        project_id=project.id,
        user_id=user.id,
        company_id=user.company_id,
        workspace_id=user.workspace_id,
        discipline="HVAC",
        status=status,
        description=description,
    )
    db.add(inspection)
    return inspection


def test_dashboard_status_summary_counts_only_the_current_tenant():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        company_a, workspace_a, user_a = _create_tenant(db, "a")
        company_b, workspace_b, user_b = _create_tenant(db, "b")
        project_a = Project(
            project_code="A-1",
            project_name="Project A",
            client_name="Client A",
            location="Dubai",
            company_id=company_a.id,
            workspace_id=workspace_a.id,
            user_id=user_a.id,
        )
        project_b = Project(
            project_code="B-1",
            project_name="Project B",
            client_name="Client B",
            location="Abu Dhabi",
            company_id=company_b.id,
            workspace_id=workspace_b.id,
            user_id=user_b.id,
        )
        db.add_all([project_a, project_b])
        db.flush()
        _create_inspection(db, user_a, project_a, "A-OPEN", "Open")
        _create_inspection(db, user_a, project_a, "A-APPROVED", "Approved")
        _create_inspection(db, user_b, project_b, "B-CLOSED", "Closed")
        db.commit()

        context = WorkspaceService(db).get_dashboard_context(user_a)

        assert context["inspection_completion_percent"] == 50
        assert context["inspection_status_breakdown"] == [
            {"status": "Approved", "count": 1, "percent": 50},
            {"status": "Open", "count": 1, "percent": 50},
        ]
        analytics_response = asyncio.run(analytics_page(_request("/analytics", user_a.id), db))
        analytics_html = analytics_response.body.decode("utf-8")
        assert "A-APPROVED" in analytics_html
        assert "B-CLOSED" not in analytics_html
        assert "1,325" not in analytics_html
        assert "Predictive analytics" not in analytics_html
    finally:
        db.close()
        engine.dispose()


def test_project_search_filters_by_query_and_status_within_tenant():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        company_a, workspace_a, user_a = _create_tenant(db, "a")
        company_b, workspace_b, user_b = _create_tenant(db, "b")
        project_a = Project(
            project_code="HVAC-001",
            project_name="Harbor Tower HVAC",
            client_name="Harbor Group",
            location="Dubai",
            discipline="HVAC",
            status="Active",
            company_id=company_a.id,
            workspace_id=workspace_a.id,
            user_id=user_a.id,
        )
        project_other_status = Project(
            project_code="HVAC-002",
            project_name="Harbor Tower Upgrade",
            client_name="Harbor Group",
            location="Dubai",
            discipline="HVAC",
            status="On Hold",
            company_id=company_a.id,
            workspace_id=workspace_a.id,
            user_id=user_a.id,
        )
        project_b = Project(
            project_code="HVAC-003",
            project_name="Harbor Tower Confidential",
            client_name="Other Client",
            location="Dubai",
            discipline="HVAC",
            status="Active",
            company_id=company_b.id,
            workspace_id=workspace_b.id,
            user_id=user_b.id,
        )
        db.add_all([project_a, project_other_status, project_b])
        db.commit()

        request = _request("/projects", user_a.id, "q=Harbor&status=Active")
        response = asyncio.run(project_list(request, db))
        html = response.body.decode("utf-8")

        assert "Harbor Tower HVAC" in html
        assert "Harbor Tower Upgrade" not in html
        assert "Harbor Tower Confidential" not in html
    finally:
        db.close()
        engine.dispose()


def test_calculator_hub_offers_favorites_and_history():
    client = TestClient(app)
    response = client.get("/calculators")

    assert response.status_code == 200
    assert 'id="favoritesOnlyToggle"' in response.text
    assert 'id="calculationHistoryList"' in response.text
    assert "Recently Opened" in response.text

    calculation = client.post(
        "/calculators/airflow",
        data={"length": "4", "width": "5", "height": "3", "air_changes": "6"},
        headers={"Origin": "http://testserver"},
    )
    assert calculation.status_code == 200
    assert 'data-calculation-complete="true"' in calculation.text
    script = Path("app/static/js/calculator-card.js").read_text(encoding="utf-8")
    assert "mepCalculatorHistory" in script
    assert "recordCompletedCalculation" in script


def test_inspection_csv_export_is_tenant_scoped_and_formula_safe():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        company_a, workspace_a, user_a = _create_tenant(db, "a")
        company_b, workspace_b, user_b = _create_tenant(db, "b")
        project_a = Project(
            project_code="A-1",
            project_name="Project A",
            client_name="Client A",
            location="Dubai",
            company_id=company_a.id,
            workspace_id=workspace_a.id,
            user_id=user_a.id,
        )
        project_b = Project(
            project_code="B-1",
            project_name="Project B",
            client_name="Client B",
            location="Abu Dhabi",
            company_id=company_b.id,
            workspace_id=workspace_b.id,
            user_id=user_b.id,
        )
        db.add_all([project_a, project_b])
        db.flush()
        _create_inspection(db, user_a, project_a, "A-1-INS", "Open", "=HYPERLINK(\"bad\")")
        _create_inspection(db, user_b, project_b, "B-1-INS", "Open")
        db.commit()

        response = asyncio.run(
            export_inspections_csv(
                _request("/reports/export.csv", user_a.id),
                template_id=None,
                db=db,
            )
        )
        assert isinstance(response, StreamingResponse)

        async def read_body():
            return "".join([chunk async for chunk in response.body_iterator])

        content = asyncio.run(read_body())
        assert "A-1-INS" in content
        assert "B-1-INS" not in content
        assert "'=HYPERLINK" in content
        assert _csv_safe_value("normal text") == "normal text"
    finally:
        db.close()
        engine.dispose()


def test_marking_notifications_read_only_updates_current_user():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        company_a, workspace_a, user_a = _create_tenant(db, "a")
        company_b, workspace_b, user_b = _create_tenant(db, "b")
        notification_a = Notification(
            user_id=user_a.id,
            company_id=company_a.id,
            workspace_id=workspace_a.id,
            title="Inspection update",
            message="Your inspection was updated.",
            is_read=False,
        )
        notification_b = Notification(
            user_id=user_b.id,
            company_id=company_b.id,
            workspace_id=workspace_b.id,
            title="Private update",
            message="Another tenant notification.",
            is_read=False,
        )
        db.add_all([notification_a, notification_b])
        db.commit()

        asyncio.run(
            mark_all_notifications_read(
                _request("/notifications/read-all", user_a.id), db
            )
        )
        db.refresh(notification_a)
        db.refresh(notification_b)

        assert notification_a.is_read is True
        assert notification_b.is_read is False
    finally:
        db.close()
        engine.dispose()
