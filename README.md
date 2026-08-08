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

## 🏆 Current Bounties (100% Implemented & Verified)

### 1. 🏷️ **Investigation Labels for Security Cases**
- **Label Categorization**: Every security case can be reviewed and marked with one of three official investigation labels: **Suspected**, **Verified**, or **Needs Review**.
- **Mandatory Investigator Notes**: Enforces a required investigator reasoning note (3–1000 characters) explaining the evidence behind each label update.
- **Audit Timeline History**: Creates immutable audit records (`CaseInvestigationHistory` table) storing reviewer ID, reviewer name, review timestamp, previous label, new label, and reasoning notes.
- **UI & Dashboard Integration**: Displays prominent color-coded badges (*Amber Suspected, Emerald Verified, Indigo Needs Review*) on the Dashboard, Case Search, and Case Details pages, accompanied by a dedicated **Investigation Review Modal**.
- **Pre-Reviewed Sample Case**: Includes pre-seeded reviewed sample security case `CR-2026-9999` (*"High-Risk Cyber-Financial Extortion Incident"*).

### 2. 🎯 **Role-Aware Security Case Filters**
- **Role-Scoped API**: Extended `GET /api/cases?role_scope=...` to support role-based list query scoping for **Admin** (`all`), **Investigator** (`investigator`), **Reviewer** (`reviewer`), **Authority HQ** (`authority`), **Hospital / Medico-Legal** (`hospital`), and **User / Citizen** (`user`).
- **Role Scope Bar & Tabs**: Added a prominent Role Scope Selector Bar on the Cases page with role icons, descriptions, and a quick role switcher for live judging demonstrations.
- **Visible Count Indicator**: Prominent badge displaying `📊 Visible Count: X Security Cases Scoped` updating dynamically as filters or role scopes change.
- **Multi-Status Filtering**: Combines role-aware scope filters with status, severity, and investigation label filters.

### 3. 📄 **Project-Specific Security Case Report Export**
- **Multi-Format Export Engine**: Built reusable report generation services in `backend/app/routers/export.py` for **PDF** (ReportLab document with tables and badges), **HTML** (printable web report with CSS badges), and **CSV** (multi-section spreadsheet tables).
- **Comprehensive Data Reuse**: Automatically populates all captured project fields (case ID, title, crime type, station, district, status, severity, incident date, investigation label, reviewer info, investigator notes, FIR statutory details, evidence log, suspect roster, financial trail, and audit history) without manual data re-entry.
- **REST APIs & Risk Gate**: `GET /api/export/cases/{case_id}/report?format=pdf|html|csv` with risk gate authorization (`check_report_export_gate`), 404/422 validation error handling, and immutable audit/activity logging (`export_security_case_report`).
- **Frontend Export Modal**: Prominent **Export Case Report (PDF / HTML / CSV)** button on Case Details page with interactive format selection modal and automated file downloads (`SecurityCase_<CaseID>_<Date>.<ext>`).
- **Sample Export Artifacts**: Pre-generated sample export files for judging demonstration:
  - `SecurityCase_CR-2026-9999_Sample.pdf`
  - `SecurityCase_CR-2026-9999_Sample.html`
  - `SecurityCase_CR-2026-9999_Sample.csv`

---

## 🌟 Previous Bounties & Feature Extensions (100% Implemented)

### 📊 **Bounty 1: Agent Execution Observability & Run Tracking** (`/observability`)
- **Real-Time Execution Trees**: Visualizes multi-step AI agent trajectories, tool call invocations, latency breakdowns, and token counts.
- **Tool Rankings & Performance**: Ranks tool usage metrics and execution duration across investigative tools.
- **Sensitive Data Sanitization**: Automatically scrubs passwords, tokens, secrets, and statutory sensitive attributes (`caste_id`, `religion_id`) from prompt logs and tool traces.

### 📜 **Bounty 2: Persistent Activity History System** (`/activity`)
- **Centralized Event Logging**: Intercepts all mutating requests, AI generation queries, CSV imports, PDF/HTML exports, and user operations into persistent database history (`activity_history` table).
- **REST APIs & Inspector Drawer**: Search (`q`), filter by module, status, user, and date range, with expandable JSON metadata inspector drawers on `/activity`.

### ⚙️ **Bounty 3: Background Tasks Engine with Exponential Retries** (`/jobs`)
- **Async Non-Blocking Execution**: Offloads heavy tasks (AI research, CSV case imports, report generation) to background worker threads.
- **Automatic Retry Engine**: Detects transient errors and retries jobs with exponential backoff (`QUEUED` $\rightarrow$ `RUNNING` $\rightarrow$ `RETRYING` $\rightarrow$ `COMPLETED`).
- **Job Center UI**: Auto-polling progress bars, log drawers, output download links, and 1-click manual retry buttons on `/jobs`.

### ⚙️ **Bounty 4: Automated AI Workflows & Human Approval Gates** (`/workflows`)
- **Risk-Aware Multi-Step Engine**: Decomposes requests into ordered execution plans (`workflows` table) classified by risk levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Human Approval Gates**: Automatically pauses high/critical actions (account freezes, judicial arrest warrants) for officer confirmation before execution.
- **Resumable State**: Resumes execution seamlessly upon approval without repeating completed steps.

### 🌐 **Bounty 5: Public Citizen Crime Reporting Portal & Verification** (`/report-crime` & `/citizen-reports`)
- **Public Reporting Portal**: Allows citizens to submit crime reports (`/report-crime`) with incident photos/documents, generating unique tracking codes (`REP-YYYY-XXXX`).
- **Officer Verification Workflow**: Officers inspect reports on `/citizen-reports`, verify evidence, and promote valid reports directly into formal KSP FIR security cases.

### 📚 **Bonus Bounty: Learning Search & Topic Filters for Career Plans** (`/career-plans`)
- **Search & Filtering System**: Enables learners to search career plans by keyword (`q`) and apply filters for **Topic**, **Difficulty Level**, **Target Goal**, and **Deadline Horizon**.
- **Interactive Active Chips Bar**: Removable filter chips with individual `(x)` buttons and a single-click **Reset Filters** button (`🔄 Reset Filters`).

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
