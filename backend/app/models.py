import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Enum, Text, Boolean
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id():
    return str(uuid.uuid4())


class RoleEnum(str, enum.Enum):
    investigator = "investigator"
    analyst = "analyst"
    admin = "admin"
    viewer = "viewer"


class CaseStatus(str, enum.Enum):
    open = "open"
    closed = "closed"
    under_review = "under_review"


class Severity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class InvestigationLabelEnum(str, enum.Enum):
    suspected = "Suspected"
    verified = "Verified"
    needs_review = "Needs Review"
    unreviewed = "Unreviewed"


class DifficultyLevelEnum(str, enum.Enum):
    beginner = "Beginner"
    intermediate = "Intermediate"
    advanced = "Advanced"
    expert = "Expert"


# ─── Reference / Lookup Master Tables (Sprint 3 KSP FIR Alignment) ──────────

class CaseCategoryMaster(Base):
    __tablename__ = "case_category_master"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, unique=True)  # FIR, UDR, Zero FIR, PAR
    is_active = Column(Boolean, default=True)


class GravityOffenceMaster(Base):
    __tablename__ = "gravity_offence_master"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, unique=True)  # Heinous, Non-Heinous
    is_active = Column(Boolean, default=True)


class CrimeHead(Base):
    __tablename__ = "crime_head"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, unique=True)  # e.g. "Crimes Against Body"
    is_active = Column(Boolean, default=True)


class CrimeSubHead(Base):
    __tablename__ = "crime_sub_head"
    id = Column(String, primary_key=True, default=gen_id)
    crime_head_id = Column(String, ForeignKey("crime_head.id"), nullable=False)
    name = Column(String, nullable=False)  # e.g. "Murder", "Robbery"
    is_active = Column(Boolean, default=True)

    crime_head = relationship("CrimeHead")


class CaseStatusMaster(Base):
    __tablename__ = "case_status_master"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, unique=True)  # Under Investigation, Charge Sheeted, Closed
    is_active = Column(Boolean, default=True)


class Act(Base):
    __tablename__ = "act"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, unique=True)  # e.g. "Indian Penal Code", "Bharatiya Nyaya Sanhita"
    is_active = Column(Boolean, default=True)


class Section(Base):
    __tablename__ = "section"
    id = Column(String, primary_key=True, default=gen_id)
    act_id = Column(String, ForeignKey("act.id"), nullable=False)
    section_number = Column(String, nullable=False)  # e.g. "302", "379"
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    act = relationship("Act")


class OccupationMaster(Base):
    __tablename__ = "occupation_master"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)


class ReligionMaster(Base):
    __tablename__ = "religion_master"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)


class CasteMaster(Base):
    __tablename__ = "caste_master"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)


class StateMaster(Base):
    __tablename__ = "state_master"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, unique=True)
    code = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)


class DistrictMaster(Base):
    __tablename__ = "district_master"
    id = Column(String, primary_key=True, default=gen_id)
    state_id = Column(String, ForeignKey("state_master.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    state = relationship("StateMaster")


class UnitTypeMaster(Base):
    __tablename__ = "unit_type_master"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, unique=True)  # Police Station, Circle, Sub-Division
    is_active = Column(Boolean, default=True)


class UnitMaster(Base):
    __tablename__ = "unit_master"
    id = Column(String, primary_key=True, default=gen_id)
    district_id = Column(String, ForeignKey("district_master.id"), nullable=False)
    unit_type_id = Column(String, ForeignKey("unit_type_master.id"), nullable=False)
    unit_name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    district = relationship("DistrictMaster")
    unit_type = relationship("UnitTypeMaster")


class CourtMaster(Base):
    __tablename__ = "court_master"
    id = Column(String, primary_key=True, default=gen_id)
    district_id = Column(String, ForeignKey("district_master.id"), nullable=False)
    court_name = Column(String, nullable=False)
    court_type = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    district = relationship("DistrictMaster")


class RankMaster(Base):
    __tablename__ = "rank_master"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, unique=True)
    code = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)


class DesignationMaster(Base):
    __tablename__ = "designation_master"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True)


class EmployeeMaster(Base):
    __tablename__ = "employee_master"
    id = Column(String, primary_key=True, default=gen_id)
    kgid = Column(String, unique=True, index=True, nullable=True)  # Karnataka Govt ID
    name = Column(String, nullable=False)
    gender = Column(String, nullable=True)
    dob = Column(DateTime, nullable=True)
    appointment_date = Column(DateTime, nullable=True)
    rank_id = Column(String, ForeignKey("rank_master.id"), nullable=True)
    designation_id = Column(String, ForeignKey("designation_master.id"), nullable=True)
    unit_id = Column(String, ForeignKey("unit_master.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    rank = relationship("RankMaster")
    designation = relationship("DesignationMaster")
    unit = relationship("UnitMaster")


# ─── Core Models ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.viewer, nullable=False)
    is_active = Column(Boolean, default=True)
    employee_id = Column(String, ForeignKey("employee_master.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    employee = relationship("EmployeeMaster")
    chat_sessions = relationship("ChatSession", back_populates="user")
    notifications = relationship("Notification", back_populates="user")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # high_severity_case, case_assigned, task_assigned, district_trend_alert, group_detected
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    related_case_id = Column(String, ForeignKey("cases.id"), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="notifications")
    related_case = relationship("Case")



class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, unique=True, index=True, nullable=False)  # human-readable e.g. CR-2026-0001
    title = Column(String, nullable=False)
    crime_type = Column(String, index=True, nullable=False)
    district = Column(String, index=True, nullable=False)
    station_name = Column(String, nullable=False)
    status = Column(Enum(CaseStatus), default=CaseStatus.open, index=True)
    severity = Column(Enum(Severity), default=Severity.medium, index=True)
    incident_date = Column(DateTime, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Security Case Manual Investigation Review & Labels
    investigation_label = Column(String, default="Unreviewed", index=True)
    investigator_note = Column(Text, nullable=True)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=True)
    reviewer_name = Column(String, nullable=True)
    review_timestamp = Column(DateTime, nullable=True)
    previous_investigation_label = Column(String, nullable=True)

    persons = relationship("Person", back_populates="case")
    evidence = relationship("Evidence", back_populates="case")
    transactions = relationship("FinancialTransaction", back_populates="case")

    # Sprint 3 additive KSP FIR extensions
    fir_details = relationship("CaseFIRDetails", uselist=False, back_populates="case")
    complainant = relationship("ComplainantDetails", uselist=False, back_populates="case")
    arrest_events = relationship("ArrestSurrender", back_populates="case")
    act_sections = relationship("ActSectionAssociation", back_populates="case")
    chargesheet = relationship("ChargesheetDetails", uselist=False, back_populates="case")

    # Sprint 6 Case Collaboration extensions
    comments = relationship("CaseComment", back_populates="case", cascade="all, delete-orphan")
    assignments = relationship("CaseAssignment", back_populates="case", cascade="all, delete-orphan")
    tasks = relationship("CaseTask", back_populates="case", cascade="all, delete-orphan")
    investigation_history = relationship("CaseInvestigationHistory", back_populates="case", cascade="all, delete-orphan", order_by="desc(CaseInvestigationHistory.created_at)")


class CaseInvestigationHistory(Base):
    __tablename__ = "case_investigation_history"

    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False, index=True)
    previous_label = Column(String, nullable=True)
    new_label = Column(String, nullable=False)
    investigator_note = Column(Text, nullable=False)
    reviewer_id = Column(String, ForeignKey("users.id"), nullable=False)
    reviewer_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    case = relationship("Case", back_populates="investigation_history")
    reviewer = relationship("User")


class CaseFIRDetails(Base):
    __tablename__ = "case_fir_details"

    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), unique=True, nullable=False)
    crime_no = Column(String, unique=True, index=True, nullable=False)  # Structured 18-digit KSP identifier
    case_no = Column(String, nullable=True)
    crime_registered_date = Column(DateTime, default=datetime.utcnow)
    incident_from_date = Column(DateTime, nullable=True)
    incident_to_date = Column(DateTime, nullable=True)
    info_received_ps_date = Column(DateTime, nullable=True)

    case_category_id = Column(String, ForeignKey("case_category_master.id"), nullable=True)
    gravity_offence_id = Column(String, ForeignKey("gravity_offence_master.id"), nullable=True)
    crime_head_id = Column(String, ForeignKey("crime_head.id"), nullable=True)
    crime_sub_head_id = Column(String, ForeignKey("crime_sub_head.id"), nullable=True)
    case_status_id = Column(String, ForeignKey("case_status_master.id"), nullable=True)
    court_id = Column(String, ForeignKey("court_master.id"), nullable=True)
    police_station_id = Column(String, ForeignKey("unit_master.id"), nullable=True)
    registering_officer_id = Column(String, ForeignKey("employee_master.id"), nullable=True)

    case = relationship("Case", back_populates="fir_details")
    category = relationship("CaseCategoryMaster")
    gravity = relationship("GravityOffenceMaster")
    crime_head = relationship("CrimeHead")
    crime_sub_head = relationship("CrimeSubHead")
    status_master = relationship("CaseStatusMaster")
    court = relationship("CourtMaster")
    police_station = relationship("UnitMaster")
    registering_officer = relationship("EmployeeMaster")


# ─── STATUTORY COMPLIANCE & SENSITIVE DATA RESTRICTION WARNING ──────────────
# religion_id and caste_id in ComplainantDetails are mandated fields in the official
# KSP FIR ER diagram, but are strictly access-restricted in CrimeIntel for statutory
# anti-discrimination compliance.
#
# RESTRICTION RULES:
# 1. MUST NEVER be indexed in RAG/TF-IDF chat engine context.
# 2. MUST NEVER be exposed in analytics, offender profiling, or network graphs.
# 3. Serialized ONLY for Admin role (returns null for non-admin roles).
# 4. Every access is logged to audit_logs (action="view_sensitive_complainant_data").
# ─────────────────────────────────────────────────────────────────────────────

class ComplainantDetails(Base):
    __tablename__ = "complainant_details"

    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), unique=True, nullable=False)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    occupation_id = Column(String, ForeignKey("occupation_master.id"), nullable=True)

    # Sensitive compliance-restricted fields
    religion_id = Column(String, ForeignKey("religion_master.id"), nullable=True)
    caste_id = Column(String, ForeignKey("caste_master.id"), nullable=True)

    case = relationship("Case", back_populates="complainant")
    occupation = relationship("OccupationMaster")
    religion = relationship("ReligionMaster")
    caste = relationship("CasteMaster")


class Person(Base):
    __tablename__ = "persons"

    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    name = Column(String, nullable=False)
    role_in_case = Column(String, nullable=True)  # suspect / witness / victim / complainant
    phone_number = Column(String, nullable=True, index=True)
    identifier_hash = Column(String, nullable=True)  # for linking across cases without storing raw PII
    notes = Column(Text, nullable=True)

    # ── Offender Profiling Fields ──
    is_flagged_offender = Column(Boolean, default=False)
    mo_tags = Column(Text, nullable=True)  # comma-separated MO tags e.g. "burglary-night,phone-otp-fraud"
    first_recorded_date = Column(DateTime, nullable=True)
    last_recorded_date = Column(DateTime, nullable=True)

    # ── Socio-demographic Fields ──
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)  # male / female / other
    occupation = Column(String, nullable=True)
    education_level = Column(String, nullable=True)  # primary / secondary / higher / none
    income_bracket = Column(String, nullable=True)  # low / medium / high
    area_type = Column(String, nullable=True)  # urban / rural / semi-urban

    # ── KSP FIR Extensions ──
    is_police = Column(Boolean, default=False)  # For victim role
    person_sort_id = Column(String, nullable=True)  # A1, A2, A3... for accused sorting

    case = relationship("Case", back_populates="persons")
    financial_accounts = relationship("FinancialAccount", back_populates="person")


class ArrestSurrender(Base):
    __tablename__ = "arrest_surrender"

    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    accused_person_id = Column(String, ForeignKey("persons.id"), nullable=False)
    event_type = Column(String, nullable=False)  # "arrest" or "surrender"
    event_date = Column(DateTime, default=datetime.utcnow)
    unit_id = Column(String, ForeignKey("unit_master.id"), nullable=True)
    investigating_officer_id = Column(String, ForeignKey("employee_master.id"), nullable=True)
    court_id = Column(String, ForeignKey("court_master.id"), nullable=True)
    is_accused = Column(Boolean, default=True)
    is_complainant_accused = Column(Boolean, default=False)

    case = relationship("Case", back_populates="arrest_events")
    accused_person = relationship("Person")
    unit = relationship("UnitMaster")
    investigating_officer = relationship("EmployeeMaster")
    court = relationship("CourtMaster")


class ActSectionAssociation(Base):
    __tablename__ = "act_section_association"

    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    act_id = Column(String, ForeignKey("act.id"), nullable=False)
    section_id = Column(String, ForeignKey("section.id"), nullable=False)
    display_order = Column(Integer, default=1)

    case = relationship("Case", back_populates="act_sections")
    act = relationship("Act")
    section = relationship("Section")


class ChargesheetDetails(Base):
    __tablename__ = "chargesheet_details"

    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), unique=True, nullable=False)
    chargesheet_date = Column(DateTime, default=datetime.utcnow)
    cs_type = Column(String, default="A")  # A = Chargesheet, B = False Case, C = Undetected
    filing_officer_id = Column(String, ForeignKey("employee_master.id"), nullable=True)
    remarks = Column(Text, nullable=True)

    case = relationship("Case", back_populates="chargesheet")
    filing_officer = relationship("EmployeeMaster")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    description = Column(String, nullable=False)
    evidence_hash = Column(String, nullable=False)  # integrity hash
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="evidence")


class DistrictIndicator(Base):
    __tablename__ = "district_indicators"

    id = Column(String, primary_key=True, default=gen_id)
    district = Column(String, unique=True, index=True, nullable=False)
    population = Column(Integer, nullable=False, default=500000)
    literacy_rate = Column(Float, nullable=False, default=75.0)
    unemployment_rate = Column(Float, nullable=False, default=6.5)
    urbanization_pct = Column(Float, nullable=False, default=60.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class FinancialAccount(Base):
    __tablename__ = "financial_accounts"

    id = Column(String, primary_key=True, default=gen_id)
    person_id = Column(String, ForeignKey("persons.id"), nullable=True)
    bank_name = Column(String, nullable=False)
    account_number_masked = Column(String, nullable=False)
    account_type = Column(String, default="savings")
    created_at = Column(DateTime, default=datetime.utcnow)

    person = relationship("Person", back_populates="financial_accounts")
    outgoing_transactions = relationship("FinancialTransaction", foreign_keys="[FinancialTransaction.from_account_id]", back_populates="from_account")
    incoming_transactions = relationship("FinancialTransaction", foreign_keys="[FinancialTransaction.to_account_id]", back_populates="to_account")


class FinancialTransaction(Base):
    __tablename__ = "financial_transactions"

    id = Column(String, primary_key=True, default=gen_id)
    from_account_id = Column(String, ForeignKey("financial_accounts.id"), nullable=False)
    to_account_id = Column(String, ForeignKey("financial_accounts.id"), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_date = Column(DateTime, default=datetime.utcnow)
    case_id = Column(String, ForeignKey("cases.id"), nullable=True)
    flagged_reason = Column(Text, nullable=True)

    from_account = relationship("FinancialAccount", foreign_keys=[from_account_id], back_populates="outgoing_transactions")
    to_account = relationship("FinancialAccount", foreign_keys=[to_account_id], back_populates="incoming_transactions")
    case = relationship("Case", back_populates="transactions")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New conversation")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # user / assistant
    content = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)  # JSON-encoded citation list
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ActivityHistory(Base):
    """
    Centralized Persistent Activity History model.
    Stores comprehensive event logs for AI outputs, twin/case edits, agent runs,
    export activities, risk gate failures, intake validations, citizen report actions,
    tasks, and workflow decisions.
    """
    __tablename__ = "activity_history"

    id = Column(String, primary_key=True, default=gen_id)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    user_name = Column(String, nullable=True)
    user_role = Column(String, nullable=True)
    activity_type = Column(String, nullable=False, index=True)
    module = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=True, index=True)
    entity_id = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    status = Column(String, default="success", nullable=False, index=True)
    tags = Column(Text, nullable=True)
    related_resources = Column(Text, nullable=True)
    execution_duration_ms = Column(Float, nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class JobStatusEnum(str, enum.Enum):
    QUEUED = "QUEUED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RETRYING = "RETRYING"
    TIMEOUT = "TIMEOUT"


class BackgroundJob(Base):
    """
    Persistent Background Task Runner Model.
    Tracks asynchronous jobs, automatic retries, execution progress, logs, and outputs.
    """
    __tablename__ = "background_jobs"

    id = Column(String, primary_key=True, default=gen_id)
    job_type = Column(String, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    user_name = Column(String, nullable=True)
    entity_type = Column(String, nullable=True, index=True)
    entity_id = Column(String, nullable=True, index=True)
    
    input_payload_json = Column(Text, nullable=True)
    output_result_json = Column(Text, nullable=True)
    status = Column(String, default="QUEUED", nullable=False, index=True)
    progress_pct = Column(Integer, default=0, nullable=False)
    
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    retry_delay_seconds = Column(Integer, default=2, nullable=False)
    timeout_seconds = Column(Integer, default=120, nullable=False)
    worker_id = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    execution_duration_ms = Column(Float, nullable=True)
    
    logs_json = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class AgentRun(Base):
    """
    Centralized Observability Model for AI Agent Executions.
    Tracks run lifecycle, latency breakdown, decision outputs, prompts, and tokens.
    """
    __tablename__ = "agent_runs"

    id = Column(String, primary_key=True, default=gen_id)
    parent_run_id = Column(String, ForeignKey("agent_runs.id"), nullable=True, index=True)
    session_id = Column(String, nullable=True, index=True)
    conversation_id = Column(String, nullable=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    user_name = Column(String, nullable=True)
    user_role = Column(String, nullable=True)
    
    agent_name = Column(String, nullable=False, index=True)
    execution_type = Column(String, default="agent_run", nullable=False, index=True)
    trigger_source = Column(String, default="user_chat", nullable=False, index=True)
    
    input_prompt = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    status = Column(String, default="RUNNING", nullable=False, index=True)
    decision = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    total_latency_ms = Column(Float, nullable=True)
    queue_time_ms = Column(Float, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    model_inference_time_ms = Column(Float, nullable=True)
    tool_execution_time_ms = Column(Float, nullable=True)
    retry_count = Column(Integer, default=0)
    tokens_used = Column(Integer, nullable=True)
    model_name = Column(String, nullable=True)
    
    logs_json = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    tool_calls = relationship("ToolCall", back_populates="agent_run", cascade="all, delete-orphan")


class ToolCall(Base):
    """
    Detailed Observability Record for Individual Tool Invocations.
    Linked to parent AgentRun with latency metrics, parameters, and results.
    """
    __tablename__ = "tool_calls"

    id = Column(String, primary_key=True, default=gen_id)
    run_id = Column(String, ForeignKey("agent_runs.id"), nullable=False, index=True)
    tool_name = Column(String, nullable=False, index=True)
    
    input_params_json = Column(Text, nullable=True)
    output_result_json = Column(Text, nullable=True)
    status = Column(String, default="SUCCESS", nullable=False, index=True)
    duration_ms = Column(Float, nullable=True)
    
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    agent_run = relationship("AgentRun", back_populates="tool_calls")


# ─── MULTI-STEP WORKFLOW & APPROVAL MODELS ────────────────────────────────────

class Workflow(Base):
    """
    Multi-Step Orchestration Workflow Model.
    Tracks overall execution state, step progress, risk level, and human approval gates.
    """
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=gen_id)
    workflow_type = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    initiator_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    initiator_user_name = Column(String, nullable=True)
    
    status = Column(String, default="PLANNED", nullable=False, index=True)
    risk_level = Column(String, default="LOW", nullable=False, index=True)
    
    current_step_index = Column(Integer, default=0, nullable=False)
    total_steps = Column(Integer, default=0, nullable=False)
    progress_pct = Column(Integer, default=0, nullable=False)
    
    input_payload_json = Column(Text, nullable=True)
    intermediate_results_json = Column(Text, nullable=True)
    final_output_json = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    execution_duration_ms = Column(Float, nullable=True)
    metadata_json = Column(Text, nullable=True)

    initiator = relationship("User", foreign_keys=[initiator_user_id])
    steps = relationship("WorkflowStep", back_populates="workflow", order_by="WorkflowStep.step_number", cascade="all, delete-orphan")
    approvals = relationship("WorkflowApproval", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowStep(Base):
    """
    Individual step definition within a Multi-Step Workflow.
    """
    __tablename__ = "workflow_steps"

    id = Column(String, primary_key=True, default=gen_id)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    step_name = Column(String, nullable=False)
    step_type = Column(String, nullable=False)
    
    assigned_agent = Column(String, nullable=True)
    assigned_tool = Column(String, nullable=True)
    risk_level = Column(String, default="LOW", nullable=False, index=True)
    
    status = Column(String, default="PENDING", nullable=False, index=True)
    requires_approval = Column(Boolean, default=False, nullable=False)
    
    input_params_json = Column(Text, nullable=True)
    output_result_json = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    execution_duration_ms = Column(Float, nullable=True)

    workflow = relationship("Workflow", back_populates="steps")
    approval_request = relationship("WorkflowApproval", back_populates="step", uselist=False, cascade="all, delete-orphan")


class WorkflowApproval(Base):
    """
    Human Approval Request Record for High/Critical Risk Workflow Steps.
    """
    __tablename__ = "workflow_approvals"

    id = Column(String, primary_key=True, default=gen_id)
    workflow_id = Column(String, ForeignKey("workflows.id"), nullable=False, index=True)
    step_id = Column(String, ForeignKey("workflow_steps.id"), nullable=False, index=True)
    
    requester_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    approver_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    approver_user_name = Column(String, nullable=True)
    
    status = Column(String, default="PENDING", nullable=False, index=True)
    risk_level = Column(String, default="HIGH", nullable=False)
    
    risk_explanation = Column(Text, nullable=True)
    expected_impact = Column(Text, nullable=True)
    affected_resources = Column(Text, nullable=True)
    proposed_action = Column(Text, nullable=True)
    comments = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    decided_at = Column(DateTime, nullable=True)

    workflow = relationship("Workflow", back_populates="approvals")
    step = relationship("WorkflowStep", back_populates="approval_request")
    requester = relationship("User", foreign_keys=[requester_user_id])
    approver = relationship("User", foreign_keys=[approver_user_id])


# ─── SPRINT 6: CASE COLLABORATION MODELS ─────────────────────────────────────

class CaseComment(Base):
    __tablename__ = "case_comments"

    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    author_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    content = Column(Text, nullable=False)
    is_ai_authored = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    case = relationship("Case", back_populates="comments")
    author = relationship("User")


class CaseAssignment(Base):
    __tablename__ = "case_assignments"

    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    assigned_to_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    assigned_by_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    role_on_case = Column(String, nullable=False, default="Supporting Officer")
    assigned_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="active", nullable=False)  # active / removed

    case = relationship("Case", back_populates="assignments")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_user_id])


class CaseTask(Base):
    __tablename__ = "case_tasks"

    id = Column(String, primary_key=True, default=gen_id)
    case_id = Column(String, ForeignKey("cases.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    assigned_to_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_by_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    due_date = Column(DateTime, nullable=True)
    status = Column(String, default="todo", nullable=False)  # todo / in_progress / done
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    case = relationship("Case", back_populates="tasks")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])


# ─── SPRINT 8: UNIFIED AGENT MODELS ───────────────────────────────────────────

class PendingAgentAction(Base):
    __tablename__ = "pending_agent_actions"

    id = Column(String, primary_key=True, default=gen_id)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    tool_name = Column(String, nullable=False)
    arguments = Column(Text, nullable=False)  # JSON-encoded dictionary
    description = Column(Text, nullable=False)  # Human-readable action description
    status = Column(String, default="pending", nullable=False, index=True)  # pending / confirmed / cancelled / executed / failed
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)

    session = relationship("ChatSession")
    user = relationship("User")


# ─── TRACE: CITIZEN CRIME REPORTING MODELS ───────────────────────────────────

class CitizenReport(Base):
    __tablename__ = "citizen_reports"

    id = Column(String, primary_key=True, default=gen_id)
    tracking_id = Column(String, unique=True, index=True, nullable=False)  # e.g. TRK-2026-00145
    crime_type = Column(String, nullable=False, index=True)
    incident_date = Column(DateTime, nullable=False)
    location = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    description = Column(Text, nullable=False)
    reporter_name = Column(String, nullable=False)
    reporter_phone = Column(String, nullable=False)
    reporter_email = Column(String, nullable=True)
    status = Column(String, default="pending", nullable=False, index=True)  # pending / verified / rejected
    ai_classification = Column(String, nullable=True)
    ai_priority = Column(String, nullable=True)  # low / medium / high / critical
    ai_summary = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_case_id = Column(String, ForeignKey("cases.id"), nullable=True)
    reviewed_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    created_case = relationship("Case", foreign_keys=[created_case_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])
    evidence_items = relationship("ReportEvidence", back_populates="report", cascade="all, delete-orphan")


class ReportEvidence(Base):
    __tablename__ = "report_evidence"

    id = Column(String, primary_key=True, default=gen_id)
    report_id = Column(String, ForeignKey("citizen_reports.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # image / video / audio / document / cctv
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("CitizenReport", back_populates="evidence_items")


class CareerPlan(Base):
    __tablename__ = "career_plans"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    topic = Column(String, nullable=False, index=True)
    difficulty_level = Column(String, default="Intermediate", index=True)
    target_goal = Column(String, nullable=False, index=True)
    deadline = Column(DateTime, nullable=True, index=True)
    tags = Column(String, nullable=True, index=True)
    status = Column(String, default="active", index=True)
    milestones = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User")


