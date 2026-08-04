from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.db import Base
from app.models.user import User
from app.services.workspace_service import WorkspaceService


def test_create_default_workspace_for_user():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    try:
        user = User(
            full_name="Test User",
            email="test@example.com",
            phone="+971000000000",
            password="hashed",
            role="Engineer",
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        service = WorkspaceService(db)
        workspace = service.create_default_workspace(user)

        assert workspace is not None
        assert workspace.name == f"{user.full_name}'s Workspace"
        assert workspace.company is not None
        assert workspace.company.name == f"{user.full_name}'s Company"
    finally:
        db.close()
