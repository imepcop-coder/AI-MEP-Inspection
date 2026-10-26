from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.tenant import apply_tenant_filter
from app.models.ai_request import AIRequest
from app.models.inspection import Inspection
from app.models.ncr import NCR
from app.models.project import Project
from app.models.uae_compliance import ContractorLicense, SafetyRecord, UAEComplianceRecord
from app.models.user import User


class AnalyticsFilterError(ValueError):
    pass


DATE_RANGES = {"7d", "30d", "90d", "year", "custom", "all"}


def resolve_date_range(
    period: str,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    today: date | None = None,
) -> tuple[date | None, date | None]:
    today = today or date.today()
    if period not in DATE_RANGES:
        raise AnalyticsFilterError("Choose a valid date range.")
    if period == "all":
        return None, None
    if period == "custom":
        if not start_date or not end_date:
            raise AnalyticsFilterError("A custom range requires both start and end dates.")
        try:
            start = date.fromisoformat(start_date)
            end = date.fromisoformat(end_date)
        except ValueError as exc:
            raise AnalyticsFilterError("Enter custom dates in YYYY-MM-DD format.") from exc
        if start > end:
            raise AnalyticsFilterError("The start date must be on or before the end date.")
        return start, end
    if period == "year":
        return date(today.year, 1, 1), today
    days = {"7d": 7, "30d": 30, "90d": 90}[period]
    return today - timedelta(days=days - 1), today


def _apply_date_range(query, column, start: date | None, end: date | None):
    if start:
        query = query.filter(column >= start)
    if end:
        query = query.filter(column <= end)
    return query


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _next_month(value: date) -> date:
    return date(value.year + (value.month == 12), 1 if value.month == 12 else value.month + 1, 1)


def _build_buckets(start: date, end: date) -> tuple[str, list[date]]:
    span = (end - start).days
    if span <= 30:
        return "day", [start + timedelta(days=offset) for offset in range(span + 1)]
    if span <= 120:
        buckets = []
        current = start
        while current <= end:
            buckets.append(current)
            current += timedelta(days=7)
        return "week", buckets
    if span > 365 * 8:
        buckets = []
        current = date(start.year, 1, 1)
        while current <= end:
            buckets.append(current)
            current = date(current.year + 1, 1, 1)
        return "year", buckets
    buckets = []
    current = _month_start(start)
    while current <= end:
        buckets.append(current)
        current = _next_month(current)
    return "month", buckets


def _date_value(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _format_bucket(value: date, granularity: str) -> str:
    if granularity == "day":
        return value.strftime("%b %d").replace(" 0", " ")
    if granularity == "week":
        return f"Week of {value.strftime('%b %d')}"
    if granularity == "year":
        return str(value.year)
    return value.strftime("%b %Y")


def _normalize(value: str | None) -> str:
    return (value or "Unknown").strip()


class AnalyticsService:
    def __init__(self, db: Session, user: User):
        if not user.company_id:
            raise AnalyticsFilterError("An authenticated company workspace is required for analytics.")
        self.db = db
        self.user = user

    def _project_scope(self, project_id: int | None) -> tuple[list[int], dict[int, Project]]:
        query = apply_tenant_filter(self.db.query(Project), self.user)
        if project_id is not None:
            project = query.filter(Project.id == project_id).first()
            if project is None:
                raise AnalyticsFilterError("The selected project is unavailable.")
            query = query.filter(Project.id == project_id)
        projects = query.order_by(Project.project_name.asc()).all()
        return [project.id for project in projects], {project.id: project for project in projects}

    def filter_options(self) -> dict[str, list[dict[str, Any]]]:
        projects = apply_tenant_filter(self.db.query(Project), self.user).order_by(Project.project_name.asc()).all()
        inspections = apply_tenant_filter(self.db.query(Inspection), self.user)
        ncrs = apply_tenant_filter(self.db.query(NCR), self.user)
        return {
            "projects": [{"id": project.id, "name": project.project_name} for project in projects],
            "disciplines": sorted(value for (value,) in inspections.with_entities(Inspection.discipline).distinct().all() if value),
            "inspectors": sorted(value for (value,) in inspections.with_entities(Inspection.inspector).distinct().all() if value),
            "inspection_statuses": sorted(value for (value,) in inspections.with_entities(Inspection.status).distinct().all() if value),
            "ncr_statuses": sorted(value for (value,) in ncrs.with_entities(NCR.status).distinct().all() if value),
            "ncr_severities": sorted(value for (value,) in ncrs.with_entities(NCR.severity).distinct().all() if value),
        }

    def build(
        self,
        *,
        period: str = "90d",
        start_date: str | None = None,
        end_date: str | None = None,
        project_id: int | None = None,
        discipline: str | None = None,
        inspector: str | None = None,
        inspection_status: str | None = None,
        ncr_status: str | None = None,
        ncr_severity: str | None = None,
        include_export_rows: bool = False,
    ) -> dict[str, Any]:
        start, end = resolve_date_range(period, start_date, end_date)
        project_ids, projects_by_id = self._project_scope(project_id)

        inspection_query = apply_tenant_filter(self.db.query(Inspection), self.user)
        inspection_query = inspection_query.filter(Inspection.project_id.in_(project_ids))
        inspection_query = _apply_date_range(inspection_query, Inspection.inspection_date, start, end)
        if discipline:
            inspection_query = inspection_query.filter(func.lower(Inspection.discipline) == discipline.strip().lower())
        if inspector:
            inspection_query = inspection_query.filter(func.lower(Inspection.inspector) == inspector.strip().lower())
        if inspection_status:
            inspection_query = inspection_query.filter(func.lower(Inspection.status) == inspection_status.strip().lower())

        inspection_count = inspection_query.count()
        status_rows = (
            inspection_query.with_entities(Inspection.status, func.count(Inspection.id))
            .group_by(Inspection.status)
            .all()
        )
        status_counts = {_normalize(status): count for status, count in status_rows}
        completed_count = sum(count for status, count in status_counts.items() if status.lower() == "closed")
        pending_count = sum(
            count for status, count in status_counts.items()
            if status.lower() in {"open", "in progress", "pending"}
        )

        today = date.today()
        min_inspection_day, max_inspection_day = (
            inspection_query.with_entities(
                func.min(Inspection.inspection_date),
                func.max(Inspection.inspection_date),
            ).one()
        )
        chart_start = start or _date_value(min_inspection_day) or today - timedelta(days=364)
        chart_end = end or max(today, _date_value(max_inspection_day) or today)
        if chart_start > chart_end:
            chart_start = chart_end
        granularity, bucket_dates = _build_buckets(chart_start, chart_end)
        trend_query = _apply_date_range(inspection_query, Inspection.inspection_date, chart_start, chart_end)
        trend_rows = (
            trend_query.with_entities(Inspection.inspection_date, func.count(Inspection.id))
            .group_by(Inspection.inspection_date)
            .all()
        )
        trend_counts: dict[str, int] = {}
        for raw_day, count in trend_rows:
            day = _date_value(raw_day)
            if day is None:
                continue
            if granularity == "day":
                bucket = day
            elif granularity == "week":
                bucket = chart_start + timedelta(days=((day - chart_start).days // 7) * 7)
            else:
                bucket = _month_start(day)
            trend_counts[bucket.isoformat()] = trend_counts.get(bucket.isoformat(), 0) + count

        discipline_rows = (
            inspection_query.with_entities(
                Inspection.discipline,
                Inspection.status,
                func.count(Inspection.id),
            )
            .group_by(Inspection.discipline, Inspection.status)
            .all()
        )
        discipline_totals: dict[str, dict[str, int]] = {}
        for name, status, count in discipline_rows:
            label = _normalize(name)
            totals = discipline_totals.setdefault(label, {"total": 0, "completed": 0})
            totals["total"] += count
            if _normalize(status).lower() == "closed":
                totals["completed"] += count
        discipline_performance = [
            {
                "discipline": label,
                "total": values["total"],
                "completed": values["completed"],
                "completion_rate": round(values["completed"] * 100 / values["total"], 1) if values["total"] else 0,
            }
            for label, values in sorted(discipline_totals.items(), key=lambda item: item[1]["total"], reverse=True)
        ]

        project_rows = (
            self.db.query(Project.id, Project.project_name, Inspection.status, func.count(Inspection.id))
            .join(Inspection, Inspection.project_id == Project.id)
            .filter(Project.id.in_(project_ids))
            .filter(Inspection.id.in_(inspection_query.with_entities(Inspection.id).statement))
            .group_by(Project.id, Project.project_name, Inspection.status)
            .all()
        )
        project_totals: dict[int, dict[str, Any]] = {}
        for project_key, project_name, status, count in project_rows:
            item = project_totals.setdefault(project_key, {"name": project_name, "total": 0, "completed": 0})
            item["total"] += count
            if _normalize(status).lower() == "closed":
                item["completed"] += count
        project_progress = [
            {
                "id": project_key,
                "name": values["name"],
                "total": values["total"],
                "completed": values["completed"],
                "completion_rate": round(values["completed"] * 100 / values["total"], 1) if values["total"] else 0,
                "url": f"/projects/{project_key}",
            }
            for project_key, values in sorted(project_totals.items(), key=lambda item: item[1]["total"], reverse=True)
        ]

        ncr_query = apply_tenant_filter(self.db.query(NCR), self.user).filter(NCR.project_id.in_(project_ids))
        if start:
            ncr_query = ncr_query.filter(NCR.created_at >= datetime.combine(start, datetime.min.time()))
        if end:
            ncr_query = ncr_query.filter(NCR.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time()))
        if ncr_status:
            ncr_query = ncr_query.filter(func.lower(NCR.status) == ncr_status.strip().lower())
        if ncr_severity:
            ncr_query = ncr_query.filter(func.lower(NCR.severity) == ncr_severity.strip().lower())
        ncr_rows = (
            ncr_query.with_entities(NCR.severity, NCR.status, func.count(NCR.id))
            .group_by(NCR.severity, NCR.status)
            .all()
        )
        ncr_severity_counts: dict[str, int] = {}
        ncr_status_counts: dict[str, int] = {}
        for severity, status, count in ncr_rows:
            severity_label = _normalize(severity)
            status_label = _normalize(status)
            ncr_severity_counts[severity_label] = ncr_severity_counts.get(severity_label, 0) + count
            ncr_status_counts[status_label] = ncr_status_counts.get(status_label, 0) + count
        open_ncr_count = sum(count for status, count in ncr_status_counts.items() if status.lower() == "open")
        high_severity_count = sum(
            count for severity, count in ncr_severity_counts.items()
            if severity.lower() in {"high", "critical"}
        )

        overdue_actions_query = apply_tenant_filter(self.db.query(SafetyRecord), self.user)
        overdue_actions_query = overdue_actions_query.filter(
            SafetyRecord.project_id.in_(project_ids),
            SafetyRecord.action_completed.is_not(True),
            SafetyRecord.action_due_date.is_not(None),
            SafetyRecord.action_due_date < today,
        )
        overdue_actions_count = overdue_actions_query.count()

        compliance_records = (
            apply_tenant_filter(self.db.query(UAEComplianceRecord), self.user)
            .filter(UAEComplianceRecord.project_id.in_(project_ids))
            .all()
        )
        compliance_by_project = {record.project_id: record for record in compliance_records}
        compliance_flags = (
            ("DEWA approval", "dewa_approved"),
            ("DAMA approval", "dama_approved"),
            ("Municipality approval", "municipality_approved"),
        )
        compliance_gaps = []
        for scoped_project_id, project in projects_by_id.items():
            record = compliance_by_project.get(scoped_project_id)
            missing = ["Compliance record"] if record is None else [
                label for label, attribute in compliance_flags if not getattr(record, attribute)
            ]
            if missing:
                compliance_gaps.append(
                    {
                        "project_id": scoped_project_id,
                        "project_name": project.project_name,
                        "missing": missing,
                        "url": f"/projects/{scoped_project_id}/compliance",
                    }
                )

        license_query = apply_tenant_filter(self.db.query(ContractorLicense), self.user)
        expiry_cutoff = today + timedelta(days=30)
        expiring_license_query = license_query.filter(
            (ContractorLicense.expiry_date <= expiry_cutoff)
            | (ContractorLicense.is_valid.is_(False))
        )
        expiring_licenses = None if project_id is not None else expiring_license_query.count()

        ai_is_scoped = not any((project_id, discipline, inspector, inspection_status))
        ai_query = apply_tenant_filter(self.db.query(AIRequest), self.user)
        if start:
            ai_query = ai_query.filter(AIRequest.created_at >= datetime.combine(start, datetime.min.time()))
        if end:
            ai_query = ai_query.filter(AIRequest.created_at < datetime.combine(end + timedelta(days=1), datetime.min.time()))
        ai_count: int | None = ai_query.count() if ai_is_scoped else None
        ai_trend: dict[str, int] = {}
        ai_bucket_dates = bucket_dates
        ai_granularity = granularity
        if ai_is_scoped:
            ai_rows = (
                ai_query.with_entities(func.date(AIRequest.created_at), func.count(AIRequest.id))
                .group_by(func.date(AIRequest.created_at))
                .all()
            )
            ai_dates = [day for raw_day, _ in ai_rows if (day := _date_value(raw_day)) is not None]
            ai_chart_start = start or (min(ai_dates) if ai_dates else today - timedelta(days=364))
            ai_chart_end = end or max(today, max(ai_dates) if ai_dates else today)
            if ai_chart_start > ai_chart_end:
                ai_chart_start = ai_chart_end
            ai_granularity, ai_bucket_dates = _build_buckets(ai_chart_start, ai_chart_end)
            for raw_day, count in ai_rows:
                day = _date_value(raw_day)
                if day is None or day < ai_chart_start or day > ai_chart_end:
                    continue
                if ai_granularity == "day":
                    bucket = day
                elif ai_granularity == "week":
                    bucket = ai_chart_start + timedelta(days=((day - ai_chart_start).days // 7) * 7)
                elif ai_granularity == "year":
                    bucket = date(day.year, 1, 1)
                else:
                    bucket = _month_start(day)
                ai_trend[bucket.isoformat()] = ai_trend.get(bucket.isoformat(), 0) + count

        insights: list[dict[str, str]] = []
        high_ncrs = (
            ncr_query.filter(
                func.lower(NCR.status) == "open",
                func.lower(NCR.severity).in_(("high", "critical")),
            )
            .order_by(NCR.created_at.desc())
            .limit(5)
            .all()
        )
        for ncr in high_ncrs:
            project = projects_by_id.get(ncr.project_id)
            if project:
                insights.append(
                    {
                        "kind": "critical",
                        "text": f"{ncr.severity} open NCR: {ncr.title} ({project.project_name}).",
                        "url": f"/projects/{project.id}",
                    }
                )
        overdue_actions = overdue_actions_query.order_by(SafetyRecord.action_due_date.asc()).limit(5).all()
        for action in overdue_actions:
            project = projects_by_id.get(action.project_id)
            if project:
                insights.append(
                    {
                        "kind": "warning",
                        "text": f"Overdue corrective action for {project.project_name}; due {action.action_due_date.isoformat()}.",
                        "url": f"/projects/{project.id}/safety-records",
                    }
                )
        for gap in compliance_gaps[:5]:
            missing = ", ".join(gap["missing"])
            insights.append(
                {
                    "kind": "warning",
                    "text": f"{gap['project_name']} needs compliance attention: {missing}.",
                    "url": gap["url"],
                }
            )
        if not insights:
            insights.append(
                {
                    "kind": "neutral",
                    "text": "No attention items were found in the selected scope.",
                    "url": "/projects",
                }
            )

        inspection_record_query = inspection_query.order_by(Inspection.inspection_date.desc(), Inspection.id.desc())
        ncr_record_query = ncr_query.order_by(NCR.created_at.desc())
        result: dict[str, Any] = {
            "filters": {
                "period": period,
                "start_date": start.isoformat() if start else None,
                "end_date": end.isoformat() if end else None,
                "project_id": project_id,
                "project_name": projects_by_id[project_id].project_name if project_id in projects_by_id else None,
                "discipline": discipline,
                "inspector": inspector,
                "inspection_status": inspection_status,
                "ncr_status": ncr_status,
                "ncr_severity": ncr_severity,
            },
            "kpis": {
                "projects_with_inspections": len(project_totals),
                "total_inspections": inspection_count,
                "completed_inspections": completed_count,
                "pending_inspections": pending_count,
                "overdue_inspections": None,
                "inspection_pass_rate": None,
                "open_ncrs": open_ncr_count,
                "high_severity_ncrs": high_severity_count,
                "overdue_corrective_actions": overdue_actions_count,
                "ai_requests": ai_count,
                "compliance_gaps": len(compliance_gaps),
                "expiring_licenses": expiring_licenses,
            },
            "unavailable": {
                "overdue_inspections": "Inspection records do not have a separate due-date field.",
                "inspection_pass_rate": "Inspection records store workflow status, not pass/fail outcomes.",
                "ai_requests": None if ai_is_scoped else "AI requests are not linked to projects, disciplines, or inspectors.",
                "expiring_licenses": "License records are company-wide and are not linked to individual projects." if project_id is not None else None,
            },
            "charts": {
                "inspection_trend": {
                    "labels": [_format_bucket(value, granularity) for value in bucket_dates],
                    "data": [trend_counts.get(value.isoformat(), 0) for value in bucket_dates],
                },
                "inspection_status": {
                    "labels": list(status_counts.keys()),
                    "data": list(status_counts.values()),
                },
                "ncr_severity": {
                    "labels": list(ncr_severity_counts.keys()),
                    "data": list(ncr_severity_counts.values()),
                },
                "ncr_status": {
                    "labels": list(ncr_status_counts.keys()),
                    "data": list(ncr_status_counts.values()),
                },
                "discipline_performance": {
                    "labels": [item["discipline"] for item in discipline_performance],
                    "total": [item["total"] for item in discipline_performance],
                    "completed": [item["completed"] for item in discipline_performance],
                },
                "project_progress": {
                    "labels": [item["name"] for item in project_progress[:12]],
                    "data": [item["completion_rate"] for item in project_progress[:12]],
                },
                "ai_usage": {
                    "labels": [_format_bucket(value, ai_granularity) for value in ai_bucket_dates],
                    "data": [ai_trend.get(value.isoformat(), 0) for value in ai_bucket_dates],
                    "available": ai_is_scoped,
                },
                "compliance_status": {
                    "labels": ["Needs attention", "Approvals recorded"],
                    "data": [len(compliance_gaps), max(0, len(project_ids) - len(compliance_gaps))],
                },
            },
            "project_progress": project_progress,
            "insights": insights,
            "recent_inspections": [
                {
                    "inspection_no": item.inspection_no,
                    "project": projects_by_id[item.project_id].project_name if item.project_id in projects_by_id else "—",
                    "inspector": item.inspector or "Unassigned",
                    "discipline": item.discipline,
                    "status": item.status or "Unknown",
                    "date": item.inspection_date.isoformat() if item.inspection_date else "—",
                    "url": f"/inspections/{item.id}",
                }
                for item in inspection_record_query.limit(10).all()
            ],
            "generated_at": datetime.now().astimezone().isoformat(),
        }
        if include_export_rows:
            result["export_inspections"] = [
                {
                    "inspection_no": item.inspection_no,
                    "project": projects_by_id[item.project_id].project_name if item.project_id in projects_by_id else "—",
                    "inspector": item.inspector or "",
                    "discipline": item.discipline,
                    "status": item.status or "Unknown",
                    "date": item.inspection_date.isoformat() if item.inspection_date else "",
                    "location": item.location or "",
                }
                for item in inspection_record_query.all()
            ]
            result["export_ncrs"] = [
                {
                    "project": projects_by_id[item.project_id].project_name if item.project_id in projects_by_id else "—",
                    "title": item.title,
                    "severity": item.severity or "Unknown",
                    "status": item.status or "Unknown",
                    "created_at": item.created_at.isoformat() if item.created_at else "",
                }
                for item in ncr_record_query.all()
            ]
            result["export_corrective_actions"] = [
                {
                    "project": projects_by_id[item.project_id].project_name if item.project_id in projects_by_id else "—",
                    "record_type": item.record_type,
                    "description": item.description,
                    "due_date": item.action_due_date.isoformat() if item.action_due_date else "",
                    "severity": item.severity or "",
                }
                for item in overdue_actions_query.order_by(SafetyRecord.action_due_date.asc()).all()
            ]
            result["export_compliance_gaps"] = [
                {
                    "project": item["project_name"],
                    "missing_approvals": ", ".join(item["missing"]),
                }
                for item in compliance_gaps
            ]
            result["export_expiring_licenses"] = [
                {
                    "company": item.company_name,
                    "license_type": item.license_type,
                    "authority": item.issuing_authority,
                    "expiry_date": item.expiry_date.isoformat(),
                }
                for item in (
                    expiring_license_query.order_by(ContractorLicense.expiry_date.asc()).all()
                    if project_id is None else []
                )
            ]
        return result
