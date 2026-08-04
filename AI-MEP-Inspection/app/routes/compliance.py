from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.uae_compliance import (
    UAEComplianceRecord,
    ContractorLicense,
    MaterialCertification,
    SafetyRecord,
)
from app.models.project import Project
from app.models.user import User

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


# UAE Compliance Records
@router.post("/projects/{project_id}/compliance")
async def create_compliance_record(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create or update UAE compliance record for a project"""
    user_id = request.session.get("user", {}).get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    compliance = db.query(UAEComplianceRecord).filter(UAEComplianceRecord.project_id == project_id).first()
    if not compliance:
        compliance = UAEComplianceRecord(project_id=project_id)
        db.add(compliance)

    db.commit()
    db.refresh(compliance)
    return {
        "id": compliance.id,
        "project_id": compliance.project_id,
        "dewa_approved": compliance.dewa_approved,
        "dama_approved": compliance.dama_approved,
        "municipality_approved": compliance.municipality_approved,
        "created_at": compliance.created_at,
    }


@router.get("/projects/{project_id}/compliance")
async def get_compliance_record(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """Get UAE compliance status for a project"""
    user_id = request.session.get("user", {}).get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    compliance = db.query(UAEComplianceRecord).filter(UAEComplianceRecord.project_id == project_id).first()
    if not compliance:
        return {
            "id": None,
            "status": "Not started",
            "compliance_items": [],
        }

    compliance_items = {
        "DEWA": {
            "status": "Approved" if compliance.dewa_approved else "Pending",
            "registration": compliance.dewa_registration,
            "date": compliance.dewa_approval_date,
        },
        "DAMA": {
            "status": "Approved" if compliance.dama_approved else "Pending",
            "registration": compliance.dama_registration,
            "date": compliance.dama_approval_date,
        },
        "Municipality": {
            "status": "Approved" if compliance.municipality_approved else "Pending",
            "code": compliance.municipality_code,
            "date": compliance.municipality_approval_date,
        },
        "Site Safety": {
            "induction": compliance.site_safety_induction_completed,
            "plan_approved": compliance.safety_plan_approved,
        },
        "Environmental": {
            "assessment": compliance.environmental_assessment_done,
            "waste_plan": compliance.waste_management_plan,
            "approved": compliance.environmental_approved,
        },
        "Labor Welfare": {
            "accommodation": compliance.labor_accommodation_verified,
            "transportation": compliance.labor_transportation_verified,
            "medical": compliance.labor_medical_verified,
        },
        "Material Certifications": {
            "complete": compliance.material_certs_complete,
            "uploaded": compliance.certificates_uploaded,
        },
        "Contractor Licenses": {
            "contractor_valid": compliance.contractor_lic_valid,
            "contractor_expiry": compliance.contractor_lic_expiry,
            "consultant_valid": compliance.consultant_lic_valid,
            "consultant_expiry": compliance.consultant_lic_expiry,
        },
    }

    return {
        "id": compliance.id,
        "project_id": compliance.project_id,
        "compliance_items": compliance_items,
        "updated_at": compliance.updated_at,
    }


# Contractor License Management
@router.post("/licenses")
async def register_contractor_license(
    data: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    """Register a new contractor or consultant license"""
    user_id = request.session.get("user", {}).get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    license_record = ContractorLicense(
        company_name=data.get("company_name"),
        license_type=data.get("license_type"),
        license_number=data.get("license_number"),
        issuing_authority=data.get("issuing_authority"),
        issue_date=data.get("issue_date"),
        expiry_date=data.get("expiry_date"),
        is_valid=True,
        registration_authority=data.get("registration_authority"),
        certificate_file=data.get("certificate_file"),
        notes=data.get("notes"),
    )
    db.add(license_record)
    db.commit()
    db.refresh(license_record)

    return {
        "id": license_record.id,
        "company_name": license_record.company_name,
        "license_number": license_record.license_number,
        "expiry_date": license_record.expiry_date,
        "is_valid": license_record.is_valid,
    }


@router.get("/licenses")
async def list_contractor_licenses(
    request: Request,
    db: Session = Depends(get_db),
):
    """List all registered contractor licenses"""
    user_id = request.session.get("user", {}).get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    licenses = db.query(ContractorLicense).all()
    return [
        {
            "id": lic.id,
            "company_name": lic.company_name,
            "license_type": lic.license_type,
            "license_number": lic.license_number,
            "expiry_date": lic.expiry_date,
            "is_valid": lic.is_valid,
            "days_to_expiry": (lic.expiry_date - date.today()).days if lic.expiry_date else None,
        }
        for lic in licenses
    ]


# Material Certification Management
@router.post("/projects/{project_id}/materials")
async def register_material_certification(
    project_id: int,
    data: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    """Register material certification for a project"""
    user_id = request.session.get("user", {}).get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    material = MaterialCertification(
        project_id=project_id,
        material_name=data.get("material_name"),
        material_type=data.get("material_type"),
        batch_number=data.get("batch_number"),
        supplier_name=data.get("supplier_name"),
        supplier_license=data.get("supplier_license"),
        cert_type=data.get("cert_type"),
        cert_number=data.get("cert_number"),
        testing_lab=data.get("testing_lab"),
        test_date=data.get("test_date"),
        specification_ref=data.get("specification_ref"),
        test_results=data.get("test_results"),
        passed=data.get("passed", False),
        cert_file=data.get("cert_file"),
        notes=data.get("notes"),
    )
    db.add(material)
    db.commit()
    db.refresh(material)

    return {
        "id": material.id,
        "material_name": material.material_name,
        "batch_number": material.batch_number,
        "passed": material.passed,
        "created_at": material.created_at,
    }


@router.get("/projects/{project_id}/materials")
async def list_material_certifications(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """List all material certifications for a project"""
    user_id = request.session.get("user", {}).get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    materials = db.query(MaterialCertification).filter(MaterialCertification.project_id == project_id).all()
    return [
        {
            "id": m.id,
            "material_name": m.material_name,
            "material_type": m.material_type,
            "batch_number": m.batch_number,
            "supplier_name": m.supplier_name,
            "passed": m.passed,
            "test_date": m.test_date,
            "specification_ref": m.specification_ref,
        }
        for m in materials
    ]


# Safety Records
@router.post("/projects/{project_id}/safety-records")
async def create_safety_record(
    project_id: int,
    data: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    """Create a new safety record for a project"""
    user_id = request.session.get("user", {}).get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    safety_record = SafetyRecord(
        project_id=project_id,
        record_date=data.get("record_date", date.today()),
        record_type=data.get("record_type"),
        description=data.get("description"),
        severity=data.get("severity"),
        personnel_involved=data.get("personnel_involved"),
        incident_location=data.get("incident_location"),
        immediate_action=data.get("immediate_action"),
        corrective_action=data.get("corrective_action"),
        action_responsible=data.get("action_responsible"),
        action_due_date=data.get("action_due_date"),
        reported_by=data.get("reported_by"),
        notes=data.get("notes"),
    )
    db.add(safety_record)
    db.commit()
    db.refresh(safety_record)

    return {
        "id": safety_record.id,
        "record_type": safety_record.record_type,
        "severity": safety_record.severity,
        "created_at": safety_record.created_at,
    }


@router.get("/projects/{project_id}/safety-records")
async def list_safety_records(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """List all safety records for a project"""
    user_id = request.session.get("user", {}).get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    records = db.query(SafetyRecord).filter(SafetyRecord.project_id == project_id).order_by(SafetyRecord.record_date.desc()).all()
    return [
        {
            "id": r.id,
            "record_type": r.record_type,
            "record_date": r.record_date,
            "severity": r.severity,
            "description": r.description,
            "action_completed": r.action_completed,
            "reported_by": r.reported_by,
        }
        for r in records
    ]


@router.get("/compliance-summary")
async def get_compliance_summary(
    request: Request,
    db: Session = Depends(get_db),
):
    """Get overall compliance summary for user's projects"""
    user_id = request.session.get("user", {}).get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    projects = db.query(Project).filter(Project.user_id == user_id).all()
    
    summary = {
        "total_projects": len(projects),
        "compliance_status": {},
        "license_expiry_alerts": [],
        "pending_inspections": 0,
    }

    for project in projects:
        compliance = db.query(UAEComplianceRecord).filter(UAEComplianceRecord.project_id == project.id).first()
        if compliance:
            summary["compliance_status"][project.project_name] = {
                "dewa": compliance.dewa_approved,
                "dama": compliance.dama_approved,
                "municipality": compliance.municipality_approved,
            }

    licenses = db.query(ContractorLicense).all()
    for lic in licenses:
        if lic.expiry_date:
            days_to_expiry = (lic.expiry_date - date.today()).days
            if days_to_expiry < 30:
                summary["license_expiry_alerts"].append({
                    "company": lic.company_name,
                    "license_number": lic.license_number,
                    "days_remaining": days_to_expiry,
                })

    return summary
