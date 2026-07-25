from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, field_validator


from app.models import RoleEnum, CaseStatus, Severity


# ---------- Auth ----------
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: RoleEnum = RoleEnum.viewer

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        if len(v) > 120:
            raise ValueError("name must be ≤ 120 characters")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: RoleEnum
    is_active: bool

    class Config:
        from_attributes = True


# Admin-facing user view (includes created_at)
class UserAdminOut(BaseModel):
    id: str
    name: str
    email: str
    role: RoleEnum
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None
    name: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("name must not be blank")
            if len(v) > 120:
                raise ValueError("name must be ≤ 120 characters")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------- Case ----------
class CaseCreate(BaseModel):
    case_id: str
    title: str
    crime_type: str
    district: str
    station_name: str
    status: CaseStatus = CaseStatus.open
    severity: Severity = Severity.medium
    incident_date: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    summary: Optional[str] = None

    @field_validator("case_id")
    @classmethod
    def case_id_valid(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 50:
            raise ValueError("case_id must be 1–50 characters")
        return v

    @field_validator("title")
    @classmethod
    def title_valid(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 300:
            raise ValueError("title must be 1–300 characters")
        return v

    @field_validator("crime_type", "district", "station_name")
    @classmethod
    def short_fields(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 120:
            raise ValueError("field must be 1–120 characters")
        return v

    @field_validator("summary")
    @classmethod
    def summary_length(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > 5000:
            raise ValueError("summary must be ≤ 5000 characters")
        return v


class CaseOut(BaseModel):
    id: str
    case_id: str
    title: str
    crime_type: str
    district: str
    station_name: str
    status: CaseStatus
    severity: Severity
    incident_date: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    summary: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CaseListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[CaseOut]


# ---------- Person / Evidence (for case detail) ----------
class PersonOut(BaseModel):
    id: str
    name: str
    role_in_case: Optional[str]
    phone_number: Optional[str]
    notes: Optional[str]

    class Config:
        from_attributes = True


class PersonOutMasked(BaseModel):
    """Phone number is redacted for viewer-role users."""
    id: str
    name: str
    role_in_case: Optional[str]
    phone_number: Optional[str]  # will be masked at serialization time
    notes: Optional[str]

    class Config:
        from_attributes = True

    @classmethod
    def mask(cls, person) -> "PersonOutMasked":
        """Return a PersonOutMasked with the last 6 digits hidden."""
        raw = person.phone_number
        if raw and len(raw) > 4:
            masked = raw[:-6] + "******" if len(raw) > 6 else "******"
        else:
            masked = raw
        return cls(
            id=person.id,
            name=person.name,
            role_in_case=person.role_in_case,
            phone_number=masked,
            notes=person.notes,
        )


class EvidenceOut(BaseModel):
    id: str
    description: str
    evidence_hash: str
    created_at: datetime

    class Config:
        from_attributes = True


class CaseDetailOut(CaseOut):
    persons: List[PersonOut] = []
    evidence: List[EvidenceOut] = []


class CaseDetailMaskedOut(CaseOut):
    """Returned to viewer-role users — phone numbers are masked."""
    persons: List[PersonOutMasked] = []
    evidence: List[EvidenceOut] = []


class MapCase(BaseModel):
    id: str
    case_id: str
    title: str
    crime_type: str
    district: str
    status: CaseStatus
    severity: Severity
    latitude: Optional[float]
    longitude: Optional[float]

    class Config:
        from_attributes = True


# ---------- Chat / RAG ----------
class ChatSessionOut(BaseModel):
    id: str
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: Optional[str] = None  # JSON-encoded list of {case_id, case_code, snippet, score}
    reasoning_steps: Optional[List[str]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    content: str
    language: str = "en"  # "en" or "kn" (Kannada)

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message content must not be blank")
        if len(v) > 2000:
            raise ValueError("message must be ≤ 2000 characters")
        return v


class ChatAnswer(BaseModel):
    session_id: str
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
    pending_action: Optional["PendingActionOut"] = None



# ---------- Dashboard ----------
class CrimeTypeCount(BaseModel):
    crime_type: str
    count: int


class DistrictCount(BaseModel):
    district: str
    count: int


class DashboardStats(BaseModel):
    total_cases: int
    open_cases: int
    closed_cases: int
    under_review_cases: int
    crime_type_distribution: List[CrimeTypeCount]
    district_summary: List[DistrictCount]
    recent_alerts: List[CaseOut]


# ---------- CSV Import ----------
class ImportSkippedRow(BaseModel):
    row: int
    reason: str


class ImportResult(BaseModel):
    imported: int
export_result_placeholder = None

# ---------- Sprint 2: Offender Profiling ----------
class OffenderRiskBreakdown(BaseModel):
    volume_pts: int
    severity_pts: int
    recency_pts: int
    mo_repetition_pts: int
    network_centrality_pts: int


class OffenderSummaryOut(BaseModel):
    person_id: str
    name: str
    phone_number: Optional[str] = None
    case_count: int
    mo_tags: List[str] = []
    last_recorded_date: Optional[datetime] = None
    risk_score: int
    risk_category: str  # "low" | "medium" | "high"
    risk_breakdown: OffenderRiskBreakdown


class OffenderDetailOut(OffenderSummaryOut):
    is_flagged_offender: bool
    first_recorded_date: Optional[datetime] = None
    linked_cases: List[CaseOut] = []
    network_connections_count: int = 0


# ---------- Sprint 2: Socio-demographic Analytics ----------
class GroupCount(BaseModel):
    label: str
    count: int


class DemographicsSummaryOut(BaseModel):
    by_age_group: List[GroupCount]
    by_gender: List[GroupCount]
    by_area_type: List[GroupCount]
    by_education: List[GroupCount]


class DistrictCorrelationItem(BaseModel):
    district: str
    crime_count: int
    unemployment_rate: float
    literacy_rate: float
    urbanization_pct: float
    population: int


class SocioeconomicCorrelationOut(BaseModel):
    disclaimer: str = "Aggregate statistical insights for policy and resourcing decisions — not to be used for individual profiling or targeting."
    district_correlations: List[DistrictCorrelationItem]


# ---------- Sprint 2: Financial Crime ----------
class FinancialAccountCreate(BaseModel):
    person_id: Optional[str] = None
    bank_name: str
    account_number_masked: str
    account_type: str = "savings"


class FinancialAccountOut(BaseModel):
    id: str
    person_id: Optional[str] = None
    bank_name: str
    account_number_masked: str
    account_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class FinancialTransactionCreate(BaseModel):
    from_account_id: str
    to_account_id: str
    amount: float
    case_id: Optional[str] = None
    flagged_reason: Optional[str] = None


class FinancialTransactionOut(BaseModel):
    id: str
    from_account_id: str
    to_account_id: str
    amount: float
    transaction_date: datetime
    case_id: Optional[str] = None
    flagged_reason: Optional[str] = None
    from_account_masked: Optional[str] = None
    to_account_masked: Optional[str] = None

    class Config:
        from_attributes = True


class FinancialTrailNode(BaseModel):
    id: str
    bank_name: str
    account_number_masked: str
    account_type: str
    person_name: Optional[str] = None


class FinancialTrailEdge(BaseModel):
    id: str
    source: str
    target: str
    amount: float
    date: datetime
    flagged_reason: Optional[str] = None


class FinancialTrailOut(BaseModel):
    case_id: str
    total_amount: float
    flagged_count: int
    nodes: List[FinancialTrailNode]
    edges: List[FinancialTrailEdge]


# ---------- Sprint 3: Official KSP FIR Schema Schemas ----------

def generate_crime_no(category_code: str = "1", district_code: str = "0012", station_code: str = "0045", year: str = "2026", serial: int = 1) -> str:
    """
    Structured 18-digit KSP Crime Number generator.
    Format: [1-digit Category][4-digit District Code][4-digit Station Code][4-digit Year][5-digit Serial]
    Example: 100120045202600001
    """
    cat = (category_code.strip() or "1")[:1]
    dist = f"{int(district_code):04d}" if district_code.isdigit() else "0001"
    stn = f"{int(station_code):04d}" if station_code.isdigit() else "0001"
    yr = f"{int(year):04d}" if year.isdigit() else "2026"
    ser = f"{int(serial):05d}"
    return f"{cat}{dist}{stn}{yr}{ser}"


class MasterLookupOut(BaseModel):
    id: str
    name: str
    is_active: bool

    class Config:
        from_attributes = True


class CrimeSubHeadOut(BaseModel):
    id: str
    crime_head_id: str
    name: str
    is_active: bool

    class Config:
        from_attributes = True


class SectionOut(BaseModel):
    id: str
    act_id: str
    section_number: str
    description: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class UnitMasterOut(BaseModel):
    id: str
    district_id: str
    unit_type_id: str
    unit_name: str
    code: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class CourtMasterOut(BaseModel):
    id: str
    district_id: str
    court_name: str
    court_type: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class EmployeeMasterOut(BaseModel):
    id: str
    kgid: Optional[str] = None
    name: str
    gender: Optional[str] = None
    rank_name: Optional[str] = None
    designation_name: Optional[str] = None
    unit_name: Optional[str] = None

    class Config:
        from_attributes = True


class CaseFIRDetailsCreate(BaseModel):
    crime_no: Optional[str] = None
    case_no: Optional[str] = None
    crime_registered_date: Optional[datetime] = None
    incident_from_date: Optional[datetime] = None
    incident_to_date: Optional[datetime] = None
    info_received_ps_date: Optional[datetime] = None
    case_category_id: Optional[str] = None
    gravity_offence_id: Optional[str] = None
    crime_head_id: Optional[str] = None
    crime_sub_head_id: Optional[str] = None
    case_status_id: Optional[str] = None
    court_id: Optional[str] = None
    police_station_id: Optional[str] = None
    registering_officer_id: Optional[str] = None


class CaseFIRDetailsOut(BaseModel):
    id: str
    case_id: str
    crime_no: str
    case_no: Optional[str] = None
    crime_registered_date: datetime
    incident_from_date: Optional[datetime] = None
    incident_to_date: Optional[datetime] = None
    info_received_ps_date: Optional[datetime] = None
    category_name: Optional[str] = None
    gravity_name: Optional[str] = None
    crime_head_name: Optional[str] = None
    crime_sub_head_name: Optional[str] = None
    case_status_name: Optional[str] = None
    court_name: Optional[str] = None
    police_station_name: Optional[str] = None
    registering_officer_name: Optional[str] = None

    class Config:
        from_attributes = True


class ComplainantDetailsCreate(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    occupation_id: Optional[str] = None
    religion_id: Optional[str] = None  # Sensitive compliance field
    caste_id: Optional[str] = None     # Sensitive compliance field


class ComplainantDetailsOut(BaseModel):
    id: str
    case_id: str
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    occupation_name: Optional[str] = None
    religion_name: Optional[str] = None  # Null for non-admin roles
    caste_name: Optional[str] = None     # Null for non-admin roles

    class Config:
        from_attributes = True


class ArrestSurrenderCreate(BaseModel):
    accused_person_id: str
    event_type: str  # "arrest" or "surrender"
    event_date: Optional[datetime] = None
    unit_id: Optional[str] = None
    investigating_officer_id: Optional[str] = None
    court_id: Optional[str] = None
    is_accused: bool = True
    is_complainant_accused: bool = False


class ArrestSurrenderOut(BaseModel):
    id: str
    case_id: str
    accused_person_id: str
    accused_name: Optional[str] = None
    event_type: str
    event_date: datetime
    unit_name: Optional[str] = None
    officer_name: Optional[str] = None
    court_name: Optional[str] = None
    is_accused: bool
    is_complainant_accused: bool

    class Config:
        from_attributes = True


class ActSectionAssociationCreate(BaseModel):
    act_id: str
    section_id: str
    display_order: int = 1


class ActSectionAssociationOut(BaseModel):
    id: str
    case_id: str
    act_id: str
    section_id: str
    act_name: Optional[str] = None
    section_number: Optional[str] = None
    section_description: Optional[str] = None
    display_order: int

    class Config:
        from_attributes = True


class ChargesheetDetailsCreate(BaseModel):
    chargesheet_date: Optional[datetime] = None
    cs_type: str = "A"  # A = Chargesheet, B = False Case, C = Undetected
    filing_officer_id: Optional[str] = None
    remarks: Optional[str] = None


class ChargesheetDetailsOut(BaseModel):
    id: str
    case_id: str
    chargesheet_date: datetime
    cs_type: str
    filing_officer_name: Optional[str] = None
    remarks: Optional[str] = None

    class Config:
        from_attributes = True


# ─── SPRINT 6: CASE COLLABORATION SCHEMAS ─────────────────────────────────────

class CommentCreate(BaseModel):
    content: str


class CommentUpdate(BaseModel):
    content: str


class CommentOut(BaseModel):
    id: str
    case_id: str
    author_user_id: Optional[str] = None
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    content: str
    is_ai_authored: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True



class AssignmentCreate(BaseModel):
    assigned_to_user_id: str
    role_on_case: str = "Supporting Officer"


class AssignmentUpdate(BaseModel):
    role_on_case: Optional[str] = None
    status: Optional[str] = None  # active / removed


class AssignmentOut(BaseModel):
    id: str
    case_id: str
    assigned_to_user_id: str
    assigned_to_name: Optional[str] = None
    assigned_to_email: Optional[str] = None
    assigned_by_user_id: str
    assigned_by_name: Optional[str] = None
    role_on_case: str
    assigned_at: datetime
    status: str

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to_user_id: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to_user_id: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None  # todo / in_progress / done


class TaskOut(BaseModel):
    id: str
    case_id: str
    case_code: Optional[str] = None
    case_title: Optional[str] = None
    case_severity: Optional[str] = None
    title: str
    description: Optional[str] = None
    assigned_to_user_id: Optional[str] = None
    assigned_to_name: Optional[str] = None
    created_by_user_id: str
    created_by_name: Optional[str] = None
    due_date: Optional[datetime] = None
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Sprint 7: Notification Schemas ──────────────────────────────────────────

class NotificationOut(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    related_case_id: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationUnreadCountOut(BaseModel):
    unread_count: int


# ── Sprint 8: Unified Agent Schemas ──────────────────────────────────────────

class PendingActionOut(BaseModel):
    id: str
    session_id: Optional[str] = None
    tool_name: str
    arguments: Dict[str, Any]
    description: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ActionConfirmResponse(BaseModel):
    action_id: str
    status: str
    message: str
    result: Optional[Dict[str, Any]] = None



