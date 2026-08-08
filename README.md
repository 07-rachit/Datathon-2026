# Crime Intelligence Platform — Production & Complete 10-Pillar Build

A complete, enterprise-grade law enforcement case management and AI intelligence platform aligned with the **official Karnataka State Police (KSP) FIR ER Diagram**, built with **FastAPI**, **SQLite/PostgreSQL**, **React**, **Tailwind CSS**, **D3.js**, and **Recharts**. Deployed serverlessly via **Vercel** (`vercel.json`).

### 📚 Presentation & Evaluation Documents
- 🎥 **Presenter Demo Script:** [DEMO_WALKTHROUGH.md](file:///d:/Projects/bihari_datathon/crime-intel-platform/DEMO_WALKTHROUGH.md) (12–15 minute presenter script mapping Storylines A–F to all 10 problem statement pillars)
- 🏗️ **Technical Architecture:** [ARCHITECTURE.md](file:///d:/Projects/bihari_datathon/crime-intel-platform/ARCHITECTURE.md) (System overview Mermaid diagrams, data models, RAG retrieval pipeline, and Vercel serverless deployment topology)
- ⚖️ **Fairness & Risk Scoring:** [RISK_SCORING.md](file:///d:/Projects/bihari_datathon/crime-intel-platform/RISK_SCORING.md)
- 🕸️ **Gang Detection Rules:** [GROUP_DETECTION.md](file:///d:/Projects/bihari_datathon/crime-intel-platform/GROUP_DETECTION.md)

---

## 🚀 Problem Statement 10-Pillar Feature Mapping (100% Coverage)

| Pillar # | Problem Statement Requirement | CrimeIntel Implemented Feature & Route |
|---|---|---|
| **Pillar 1** | Case Management & Search | Multi-attribute filtering, free-text search, role-aware list scoping (`/cases`), and structured KSP FIR details. |
| **Pillar 2** | AI Case Assistant | **Full-Page AI Research Desk** (`/assistant`) + Floating Widget (`ChatWidget.jsx`), shared session state, deep-search RAG, bilingual (English + Kannada), Web Speech API voice I/O, PDF export, and **Explainable AI Reasoning Steps**. |
| **Pillar 3** | Hotspot Map | Spatial visualization with Leaflet, dark ops-room basemap, and severity-coded incident markers (`/map`). |
| **Pillar 4** | Criminal Network Visualization | Force-directed D3 graph (`/network`), recurring phone link edges, and **Organized Crime / Gang Group Detection** (`/api/network/groups`). |
| **Pillar 5** | Predictive Analytics & Trend Alerts | District incident trend comparison (30-day delta heuristics), high-severity alert feeds on `/dashboard`, and **Seasonal/Event-based trend analysis** on `/insights`. |
| **Pillar 6** | Audit Trail & RBAC | Role-based access control (`investigator`, `analyst`, `admin`, `viewer`), full action logs (`/audit`), and statutory sensitive field redaction. |
| **Pillar 7** | Production Hardening & Vercel | Vercel serverless deployment (`vercel.json`), rate limiting via `slowapi`, Admin User Management UI (`/admin`), and CSV bulk case import (`/import`). |
| **Pillar 8** | Offender Profiling & Risk Scoring | Non-biased behavioral risk scoring (0–100 scale), MO pattern repetition tracking, and offender profile directory (`/offenders`). |
| **Pillar 9** | Socio-Demographic Crime Insights | Aggregate demographic distributions (age, gender, urban/rural), district socioeconomic correlations, and **Seasonal/Event-based trend charts** (`/insights`). |
| **Pillar 10** | Financial Crime Linking | Bank account mapping, transaction flow graph (`/finance/trail/{case_id}`), and flagged monetary movement overlays on the network graph. |

---

## 🏆 Latest 3 Bounties (100% Implemented & Verified)

### 1. 🏷️ **Investigation Labels for Security Cases**
- **Official Label Categorization**: Authorized reviewers can mark every security case record with one of three official investigation labels: **Suspected**, **Verified**, or **Needs Review**.
- **Mandatory Investigator Notes & Validation**: Enforces a required investigator reasoning note (3–1000 characters) explaining the evidence and rationale behind each label update. Invalid or missing notes are blocked by Pydantic validation and risk gates.
- **Immutable Audit Timeline History**: Creates persistent audit entries in the `CaseInvestigationHistory` database table, storing reviewer ID, reviewer name, review timestamp, previous label, new label, and reasoning notes permanently.
- **REST APIs & RBAC Access Control**: Developed `GET /api/cases/{case_id}/investigation` and `PUT /api/cases/{case_id}/investigation` endpoints with strict role gating (`investigator`, `analyst`, `admin` permitted; `viewer` blocked with 403 `AuthorizationError`).
- **UI & Dashboard Integration**: Displays color-coded badges (*Amber ⚠️ Suspected, Emerald ✓ Verified, Indigo 🔍 Needs Review*) across the Dashboard, Case Search, and Case Details pages, accompanied by a dedicated **Investigation Review Modal**.
- **Pre-Reviewed Sample Demonstration Case**: Includes pre-seeded reviewed sample security case **`CR-2026-9999`** (*"High-Risk Cyber-Financial Extortion Incident"*).
- **Backend Test Suite**: Verified with dedicated unit and integration tests in `tests/test_investigation_labels.py`.

### 2. 🎯 **Role-Aware Security Case Filters**
- **Role-Scoped API Query Engine**: Extended `GET /api/cases?role_scope=...` to support role-based list query scoping:
  - **`admin`**: Full platform overview (all security case records).
  - **`investigator`**: Cases active for investigation (`open`, `under_review`, `Suspected`, `Verified`, `Needs Review`, or user assigned).
  - **`reviewer`**: Cases requiring review decision (`Needs Review`, `Suspected`, or reviewer assigned).
  - **`authority`**: High-level security incidents (`high`/`critical` severity or statutory FIR registered cases).
  - **`hospital`**: Medico-legal & violent security incidents (*Assault, Violent Offense, Emergency Cyber Threat*).
  - **`user`**: Citizen-reported security cases and user-assigned records.
- **Role Scope Bar & Tabs**: Added a prominent Role Scope Selector Bar on the Cases page with role icons, descriptions, and a quick role switcher for live judging demonstrations.
- **Visible Scoped Count Indicator**: Prominent badge displaying `📊 Visible Count: X Security Cases Scoped` updating dynamically as filters or role scopes change.
- **Multi-Status & Keyword Combination**: Combines role-aware scope filters with status, severity, investigation label, and keyword search filters.
- **Backend Test Suite**: Verified with dedicated tests in `tests/test_role_filters.py`.

### 3. 📄 **Project-Specific Security Case Report Export**
- **Multi-Format Export Engine**: Built reusable report generation services in `backend/app/routers/export.py` for **PDF** (ReportLab document with tables and badges), **HTML** (printable web report with CSS badges), and **CSV** (multi-section spreadsheet tables).
- **Comprehensive Data Reuse**: Automatically populates all captured project fields (case ID, title, crime type, station, district, status, severity, incident date, investigation label, reviewer info, investigator notes, FIR statutory details, evidence log, suspect roster, financial trail, and audit history) without manual data re-entry or duplication.
- **REST APIs & Risk Gate**: `GET /api/export/cases/{case_id}/report?format=pdf|html|csv` with risk gate authorization (`check_report_export_gate`), 404/422 validation error handling, and immutable audit/activity logging (`export_security_case_report`).
- **Frontend Export Modal**: Prominent **Export Case Report (PDF / HTML / CSV)** button on Case Details page with interactive format selection modal and automated file downloads (`SecurityCase_<CaseID>_<Date>.<ext>`).
- **Sample Export Artifacts**: Pre-generated sample export files for judging demonstration:
  - `SecurityCase_CR-2026-9999_Sample.pdf`
  - `SecurityCase_CR-2026-9999_Sample.html`
  - `SecurityCase_CR-2026-9999_Sample.csv`
- **Backend Test Suite**: Verified with dedicated tests in `tests/test_report_export.py`.

---

## 🌟 5 Previous Bounties (100% Implemented & Detailed)

### 📊 **Previous Bounty 1: Agent Execution Observability & Run Tracking** (`/observability`)
- **Real-Time Execution Trees**: Captures multi-step AI agent runs (`agent_runs`, `agent_tool_calls` tables), visualizing tool call chains, step execution order, latency breakdowns, and token consumption metrics.
- **Tool Performance & Usage Ranking**: Ranks tool execution frequency and latency across investigative tools (`search_cases`, `get_offender_risk`, `get_financial_trail`, etc.).
- **Sensitive Data Sanitization**: Automatically scrubs passwords, tokens, secrets, and statutory sensitive attributes (`caste_id`, `religion_id`) from prompt logs and tool call inputs/outputs.
- **Observability Desk UI**: Dedicated Ops-Room Observability page (`Observability.jsx`) featuring interactive execution tree inspection modals, latency distribution charts, and search filters.
- **Backend Test Suite**: Verified with `tests/test_observability.py`.

### 📜 **Previous Bounty 2: Centralized Persistent Activity History Framework** (`/activity`)
- **Centralized Event Interceptor Middleware**: `ActivityLoggingMiddleware` automatically intercepts all mutating HTTP requests, AI queries, CSV imports, report exports, and user actions into persistent database history (`activity_history` table).
- **REST APIs & Inspector Drawer**: Search (`q`), filter by `module`, `activity_type`, `status`, `user_id`, and `date_range`, with expandable JSON metadata inspector drawers on `/activity`.
- **Immutability & Access Control**: Audit logs are read-only for investigators and analysts; deletion is strictly restricted to Super Admin users (`admin` role).
- **Backend Test Suite**: Verified with `tests/test_activity_history.py`.

### ⚙️ **Previous Bounty 3: Background Tasks Engine with Exponential Retries** (`/jobs`)
- **Non-Blocking Async Worker Pipeline**: Offloads heavy tasks (AI research queries, bulk CSV case imports, report exports, trend calculations) to background worker threads (`background_jobs` table).
- **Automatic Retry Engine**: Detects transient errors and retries jobs with exponential backoff (`QUEUED` $\rightarrow$ `RUNNING` $\rightarrow$ `RETRYING` $\rightarrow$ `COMPLETED`). Halts immediately on non-recoverable validation/auth failures without wasting cycles.
- **Job Center UI**: Features auto-polling progress bars, log drawers, output download links, job cancellation, and 1-click manual retry buttons on `/jobs`.
- **Backend Test Suite**: Verified with `tests/test_background_jobs.py`.

### ⚙️ **Previous Bounty 4: Automated AI Workflows & Human Approval Gates** (`/workflows`)
- **Risk-Aware Multi-Step Execution Engine**: Decomposes complex user instructions into ordered execution plans (`workflows`, `workflow_steps`, `workflow_approvals` tables) classified by step risk levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Human Approval Gates**: Low and medium risk steps execute automatically. High and critical risk operations (financial account freezes, judicial arrest warrants) automatically pause the workflow and generate a human approval request.
- **Resumable Execution & Approval Center**: Workflows persist state across restarts and resume execution from the exact paused step upon human approval (`APPROVED`). Features Approval Center UI on `/workflows`.
- **Backend Test Suite**: Verified with `tests/test_workflows.py`.

### 🌐 **Previous Bounty 5: Public Citizen Crime Reporting Portal & Verification** (`/report-crime` & `/citizen-reports`)
- **Public Citizen Reporting Portal**: Enables public citizens to submit crime reports anonymously (`/report-crime`) with incident photos/documents, generating unique tracking codes (`REP-YYYY-XXXX`).
- **Officer Verification Workflow**: Officers inspect incoming reports on `/citizen-reports`, verify evidence integrity, and promote valid reports directly into formal KSP FIR security cases.
- **Backend Test Suite**: Verified with `tests/test_citizen_reports.py`.

### 📚 **Bonus Bounty: Learning Search & Topic Filters for Career Plans** (`/career-plans`)
- **Career Plans Database**: Stores career plan records containing searchable metadata including title, description, topic, difficulty level (`Beginner`, `Intermediate`, `Advanced`, `Expert`), target goal, deadline, tags, milestones, and notes.
- **Search & Multi-Criteria Filtering**: Keyword search (`q`) across titles, descriptions, goals, milestones, notes, or tags, combined with filters for Topic, Difficulty, Target Goal, and Deadline Horizon.
- **Interactive Active Chips Bar**: Removable filter chips with individual `(x)` buttons and a single-click **Reset Filters** button (`🔄 Reset Filters`).
- **Backend Test Suite**: Verified with `tests/test_career_plans.py`.

---

## ⚖️ Non-Biased Risk Scoring Model

Offender risk scores are strictly **behavioral and criminological** (case volume, max severity, recency, MO repetition, and network centrality). 
**Demographic attributes (age, gender, income, education, area) are strictly excluded from individual risk scoring.**
For full mathematical formulas and fairness guarantees, see [RISK_SCORING.md](file:///d:/Projects/bihari_datathon/crime-intel-platform/RISK_SCORING.md).

---

## 🕸️ Organized Crime & Gang Group Detection

CrimeIntel automatically detects potential criminal syndicates using a multi-vector connected-components clustering algorithm on persons with $\ge 2$ link types (co-accused, shared phone number, or shared financial transfers).
For full clustering thresholds and group risk formulas, see [GROUP_DETECTION.md](file:///d:/Projects/bihari_datathon/crime-intel-platform/GROUP_DETECTION.md).

---

## 🛡️ Evidence Intake Validation & Risk Gates Protocol

CrimeIntel enforces a centralized **Validation Layer** and **Risk Gates Protocol** before any business logic executes:
- **Typed Exception Hierarchy (`app/errors.py`):** Standardized JSON error response format across `ValidationError` (422), `AuthenticationError` (401), `AuthorizationError` (403), `ResourceNotFoundError` (404), `ConflictError` (409), `BusinessRuleError` (400), `RateLimitError` (429), `DatabaseError` (500), and `InternalServerError` (500).
- **Request Tracking & Logging (`app/middleware.py`, `app/logger.py`):** Automatic UUID `x-request-id` injection per request, structured log outputs, and automatic redaction of passwords, tokens, secrets, and statutory sensitive attributes (`caste_id`, `religion_id`).
- **Pre-Execution Risk Gates (`app/risk_gates.py`):**
  - *Auth & Role Authorization Gate:* Verifies session validity, active account status, and role permissions.
  - *Entity Existence & Ownership Gate:* Verifies case, report, task, and account existence before updates.
  - *Idempotency & Duplicate Action Gate:* Rejects duplicate case IDs, registered FIR crime numbers, duplicate report verifications, and existing case assignments.
  - *State Transition Gate:* Validates task status progressions (`todo` $\rightarrow$ `in_progress` $\rightarrow$ `done`) and prevents re-reviewing already processed citizen reports.
  - *Business Constraint & Safety Gate:* Rejects future `incident_date` timestamps, out-of-range lat/long coordinates, negative transaction amounts, self-transfers, and Super Admin self-deactivation.

---

## ⚡ Real-Time In-App Alerts via WebSocket

CrimeIntel delivers instant, multi-device live notifications over WebSockets (`/ws/notifications?token=<JWT>`):
- **Event Sources:** Automatically triggers persistent alert rows and WebSocket pushes on high-severity case creation (`high`/`critical`), officer case assignment, task assignment, district trend alerts, and gang group detections.
- **RBAC Scoping & Deduplication:** `viewer` users are restricted from receiving investigation/high-severity alerts. Duplicate alerts are suppressed.
- **Persistent Storage:** Notifications survive page refreshes and offline periods (`notifications` database table).

---

## 🤝 Case Collaboration & Task Tracking

CrimeIntel enables multi-investigator coordination across case files:
- **Officer Assignments & Role Gating:** Supervisory roles (`admin`/`analyst`) can assign any officer to a case with specific role titles (e.g. *Lead Investigator*, *Reviewing Analyst*).
- **Investigative Tasks:** Create and track case to-dos with due dates, assignees, and status transitions (`todo` $\rightarrow$ `in_progress` $\rightarrow$ `done`).
- **Threaded Case Comments:** Chronological investigator discussion feed on `CaseDetail.jsx`.
- **"My Work" Officer Workspace (`/my-work`):** Dedicated page listing active case assignments and open tasks assigned to the logged-in officer across all cases.

---

## 🔒 Statutory Compliance & Sensitive Data Protocol

> **Notice:** `religion_id` and `caste_id` on Complainant records are mandated by the official KSP FIR schema, but are strictly access-restricted in CrimeIntel for anti-discrimination compliance. These fields are:
> - **Excluded** from AI RAG index, analytics, risk scoring, and network graph computations.
> - **Masked** as `null` for non-admin roles at the API layer.
> - **Logged** to `audit_logs` (`action="view_sensitive_complainant_data"`) whenever read by an Admin user.

---

## 🚀 Deployment & Vercel Serverless Configuration

The platform is deployed serverlessly on **Vercel** (`vercel.json`):
- 🌐 **Vercel Production Application UI**: `https://datathon-2026.vercel.app`
- 📚 **Vercel Production API Documentation**: `https://datathon-2026.vercel.app/api/docs`
- ⚡ **Vercel Serverless API Base**: `/api` (Production Serverless Python Backend)

### 1. Vercel Serverless Production Links
- **Live Application URL**: `https://datathon-2026.vercel.app`
- **Live OpenAPI Documentation**: `https://datathon-2026.vercel.app/api/docs`
- **Default RBAC Credentials**:
  - Admin: `admin@crimeintel.local` / `Admin@123`
  - Analyst: `analyst@crimeintel.local` / `Analyst@123`
  - Investigator: `investigator@crimeintel.local` / `Investigator@123`
  - Viewer: `viewer@crimeintel.local` / `Viewer@123`

```bash
# Deploy to Vercel via CLI
vercel --prod
```

### 2. Local Development Setup
```bash
# Backend Setup
cd backend
python -m venv venv
venv\Scripts\activate            # source venv/bin/activate on Linux/Mac
pip install -r requirements.txt
python seed.py                   # Populates connected demo storylines A-F & sample case CR-2026-9999
uvicorn app.main:app --reload --port 8000
```

```bash
# Frontend Setup
cd frontend
npm install
npm run dev
```

---

## 🧪 Automated Testing

Run the automated backend test suite (**104 unit & integration tests, 100% pass rate**):
```bash
cd backend
python -m pytest tests/ -v
```
