from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean, Date
from sqlalchemy.orm import relationship
from app.database.db import Base


class UAEComplianceRecord(Base):
    """UAE-specific compliance tracking for projects"""
    __tablename__ = "uae_compliance_records"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    
    # DEWA (Electricity) Compliance
    dewa_registration = Column(String(100), nullable=True)  # DEWA registration number
    dewa_approved = Column(Boolean, default=False)
    dewa_approval_date = Column(Date, nullable=True)
    dewa_certificate_no = Column(String(100), nullable=True)
    
    # DAMA (Water) Compliance
    dama_registration = Column(String(100), nullable=True)  # DAMA registration number
    dama_approved = Column(Boolean, default=False)
    dama_approval_date = Column(Date, nullable=True)
    dama_certificate_no = Column(String(100), nullable=True)
    
    # Emirate Municipality Requirements
    municipality_code = Column(String(50), nullable=True)
    municipality_approved = Column(Boolean, default=False)
    municipality_approval_date = Column(Date, nullable=True)
    
    # Site Safety Compliance
    site_safety_induction_completed = Column(Boolean, default=False)
    safety_plan_submitted = Column(Boolean, default=False)
    safety_plan_approved = Column(Boolean, default=False)
    
    # Environmental Compliance
    environmental_assessment_done = Column(Boolean, default=False)
    waste_management_plan = Column(Boolean, default=False)
    environmental_approved = Column(Boolean, default=False)
    
    # Labor Welfare
    labor_accommodation_verified = Column(Boolean, default=False)
    labor_transportation_verified = Column(Boolean, default=False)
    labor_medical_verified = Column(Boolean, default=False)
    
    # Material Certifications
    material_certs_complete = Column(Boolean, default=False)
    certificates_uploaded = Column(Boolean, default=False)
    
    # Contractor Registration
    contractor_lic_valid = Column(Boolean, default=False)
    contractor_lic_expiry = Column(Date, nullable=True)
    consultant_lic_valid = Column(Boolean, default=False)
    consultant_lic_expiry = Column(Date, nullable=True)
    
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", foreign_keys=[project_id])


class ContractorLicense(Base):
    """Track contractor and consultant licenses for UAE compliance"""
    __tablename__ = "contractor_licenses"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False, index=True)
    company_name = Column(String(200), nullable=False)
    license_type = Column(String(50), nullable=False)  # CONTRACTOR, CONSULTANT, SUPPLIER
    license_number = Column(String(100), unique=True, nullable=False, index=True)
    issuing_authority = Column(String(100), nullable=False)  # DEWA, DAMA, Municipality, etc.
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    is_valid = Column(Boolean, default=True)
    registration_authority = Column(String(100), nullable=True)  # Dubai Municipality, etc.
    certificate_file = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MaterialCertification(Base):
    """Track material certifications and test reports"""
    __tablename__ = "material_certifications"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    material_name = Column(String(200), nullable=False)
    material_type = Column(String(100), nullable=False)  # PIPE, CABLE, CONCRETE, STEEL, etc.
    batch_number = Column(String(100), nullable=False)
    supplier_name = Column(String(200), nullable=False)
    supplier_license = Column(String(100), nullable=True)
    
    # Certification Details
    cert_type = Column(String(100), nullable=False)  # COC, MILL CERT, TEST REPORT, etc.
    cert_number = Column(String(100), nullable=True)
    testing_lab = Column(String(200), nullable=True)
    test_date = Column(Date, nullable=True)
    
    # Specifications
    specification_ref = Column(String(100), nullable=True)  # ESM 901, DM, etc.
    test_results = Column(Text, nullable=True)
    passed = Column(Boolean, default=False)
    
    cert_file = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", foreign_keys=[project_id])


class SafetyRecord(Base):
    """Track safety records and incidents"""
    __tablename__ = "safety_records"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    record_date = Column(Date, nullable=False)
    record_type = Column(String(50), nullable=False)  # INCIDENT, NEAR_MISS, AUDIT, TRAINING
    
    description = Column(Text, nullable=False)
    severity = Column(String(50), nullable=True)  # LOW, MEDIUM, HIGH, CRITICAL
    personnel_involved = Column(String(200), nullable=True)
    incident_location = Column(String(255), nullable=True)
    
    # Response
    immediate_action = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)
    action_responsible = Column(String(150), nullable=True)
    action_due_date = Column(Date, nullable=True)
    action_completed = Column(Boolean, default=False)
    
    # Authorization
    reported_by = Column(String(150), nullable=False)
    approved_by = Column(String(150), nullable=True)
    approval_date = Column(Date, nullable=True)
    
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", foreign_keys=[project_id])
