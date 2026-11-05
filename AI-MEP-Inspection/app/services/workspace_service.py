from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.tenant import apply_tenant_filter
from app.models import AIRequest, AuditLog, Document, Notification, Observation, Project, Inspection, NCR, User
from app.models.company import Company
from app.models.workspace import Workspace


class WorkspaceService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_context(self, user: User) -> dict[str, Any]:
        projects = apply_tenant_filter(self.db.query(Project), user).order_by(Project.id.desc()).limit(5).all()
        inspections = apply_tenant_filter(self.db.query(Inspection), user).order_by(Inspection.id.desc()).limit(5).all()
        recent_documents = apply_tenant_filter(self.db.query(Document), user).order_by(Document.id.desc()).limit(5).all()
        notifications = apply_tenant_filter(self.db.query(Notification), user).order_by(Notification.id.desc()).limit(5).all()

        pending_inspections = apply_tenant_filter(self.db.query(Inspection), user).filter(Inspection.status == "Pending").count()
        approved_inspections = apply_tenant_filter(self.db.query(Inspection), user).filter(Inspection.status == "Approved").count()
        total_projects = apply_tenant_filter(self.db.query(Project), user).count()
        total_inspections = apply_tenant_filter(self.db.query(Inspection), user).count()
        inspection_completion_percent = (
            round(approved_inspections / total_inspections * 100)
            if total_inspections
            else 0
        )
        ai_requests = apply_tenant_filter(self.db.query(AIRequest), user).count()
        status_rows = (
            apply_tenant_filter(self.db.query(Inspection), user)
            .with_entities(Inspection.status, func.count(Inspection.id))
            .group_by(Inspection.status)
            .order_by(Inspection.status)
            .all()
        )
        inspection_status_breakdown = [
            {
                "status": status or "Unspecified",
                "count": count,
                "percent": round(count / total_inspections * 100) if total_inspections else 0,
            }
            for status, count in status_rows
        ]

        # Include available calculators for quick access on dashboard. Import locally to avoid import cycles.
        calculators = []
        try:
            from app.routes.mep_calculators import CALCULATOR_PAGES

            for slug, meta in CALCULATOR_PAGES.items():
                calculators.append(
                    {
                        "slug": slug,
                        "category": meta.get("category", "plumbing"),
                        "title": meta.get("title", slug.replace("-", " ").title()),
                        "description": meta.get("description", ""),
                        "icon": meta.get("icon", "bi-calculator"),
                    }
                )
        except Exception:
            # If calculators can't be loaded, return an empty list — dashboard remains functional.
            calculators = []

        return {
            "user": user,
            "projects": projects,
            "inspections": inspections,
            "recent_documents": recent_documents,
            "notifications": notifications,
            "pending_inspections": pending_inspections,
            "approved_inspections": approved_inspections,
            "inspection_completion_percent": inspection_completion_percent,
            "total_projects": total_projects,
            "total_inspections": total_inspections,
            "inspection_status_breakdown": inspection_status_breakdown,
            "ai_requests": ai_requests,
            "subscription_plan": user.subscription_plan,
            "ai_usage_count": user.ai_usage_count,
            "calculators": calculators,
        }

    def log_action(self, user: User | None, action: str, details: str | None = None) -> None:
        log_entry = AuditLog(user_id=user.id if user else None, action=action, details=details)
        self.db.add(log_entry)
        self.db.commit()

    def create_default_workspace(self, user: User) -> Workspace:
        company = self.db.query(Company).filter(Company.owner_id == user.id).first()
        if not company:
            company = Company(
                name=f"{user.full_name}'s Company",
                slug=f"{user.email.split('@')[0].lower()}-company",
                owner_id=user.id,
                is_active=True,
            )
            self.db.add(company)
            self.db.flush()

        workspace = self.db.query(Workspace).filter(Workspace.company_id == company.id).first()
        if not workspace:
            workspace = Workspace(
                name=f"{user.full_name}'s Workspace",
                slug=f"{user.email.split('@')[0].lower()}-workspace",
                company_id=company.id,
                description="Default private workspace",
                is_active=True,
            )
            self.db.add(workspace)
            self.db.commit()
            self.db.refresh(workspace)

        return workspace

    def create_notification(self, user: User, title: str, message: str) -> Notification:
        notification = Notification(user_id=user.id, title=title, message=message)
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def increment_ai_usage(self, user: User) -> None:
        user.ai_usage_count = (user.ai_usage_count or 0) + 1
        self.db.commit()
