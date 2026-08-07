# Crime Intelligence Platform — Production & Complete 10-Pillar Build

A complete, enterprise-grade law enforcement case management and AI intelligence platform aligned with the **official Karnataka State Police (KSP) FIR ER Diagram**, built with **FastAPI**, **SQLite/PostgreSQL**, **React**, **Tailwind CSS**, **D3.js**, and **Recharts**.

### 📚 Presentation & Evaluation Documents
- 🎥 **Presenter Demo Script:** [DEMO_WALKTHROUGH.md](file:///d:/Projects/bihari_datathon/crime-intel-platform/DEMO_WALKTHROUGH.md) (12–15 minute presenter script mapping Storylines A–F to all 10 problem statement pillars)
- 🏗️ **Technical Architecture:** [ARCHITECTURE.md](file:///d:/Projects/bihari_datathon/crime-intel-platform/ARCHITECTURE.md) (System overview Mermaid diagrams, data models, RAG retrieval pipeline, and deployment topology)
- ⚖️ **Fairness & Risk Scoring:** [RISK_SCORING.md](file:///d:/Projects/bihari_datathon/crime-intel-platform/RISK_SCORING.md)
- 🕸️ **Gang Detection Rules:** [GROUP_DETECTION.md](file:///d:/Projects/bihari_datathon/crime-intel-platform/GROUP_DETECTION.md)

---

## 🚀 Problem Statement 10-Pillar Feature Mapping (100% Coverage)

| Pillar # | Problem Statement Requirement | CrimeIntel Implemented Feature & Route |
|---|---|---|
| **Pillar 1** | Case Management & Search | Multi-attribute filtering, free-text search, paginated cases (`/cases`), and structured KSP FIR details. |
| **Pillar 2** | AI Case Assistant | **Full-Page AI Research Desk** (`/assistant`) + Floating Widget (`ChatWidget.jsx`), shared session state, deep-search RAG, bilingual (English + Kannada), Web Speech API voice I/O, PDF export, and **Explainable AI Reasoning Steps**. |
| **Pillar 3** | Hotspot Map | Spatial visualization with Leaflet, dark ops-room basemap, and severity-coded incident markers (`/map`). |
| **Pillar 4** | Criminal Network Visualization | Force-directed D3 graph (`/network`), recurring phone link edges, and **Organized Crime / Gang Group Detection** (`/api/network/groups`). |
| **Pillar 5** | Predictive Analytics & Trend Alerts | District incident trend comparison (30-day delta heuristics), high-severity alert feeds on `/dashboard`, and **Seasonal/Event-based trend analysis** on `/insights`. |
| **Pillar 6** | Audit Trail & RBAC | Role-based access control (`investigator`, `analyst`, `admin`, `viewer`), full action logs (`/audit`), and statutory sensitive field redaction. |
| **Pillar 7** | Production Hardening | Docker Compose orchestration (Postgres 16 + FastAPI + Nginx), rate limiting via `slowapi`, Admin User Management UI (`/admin`), and CSV bulk case import (`/import`). |
| **Pillar 8** | Offender Profiling & Risk Scoring | Non-biased behavioral risk scoring (0–100 scale), MO pattern repetition tracking, and offender profile directory (`/offenders`). |
| **Pillar 9** | Socio-Demographic Crime Insights | Aggregate demographic distributions (age, gender, urban/rural), district socioeconomic correlations, and **Seasonal/Event-based trend charts** (`/insights`). |
| **Pillar 10** | Financial Crime Linking | Bank account mapping, transaction flow graph (`/finance/trail/{case_id}`), and flagged monetary movement overlays on the network graph. |

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

## 📜 Persistent Activity History System (Bounty 2)

CrimeIntel integrates a centralized **Persistent Activity History Framework** (`activity_history` table):
- **Automatic Interceptor Middleware (`ActivityLoggingMiddleware`):** Intercepts all mutating requests, AI generation queries, CSV imports, PDF exports, and user operations, capturing execution duration, user metadata, module names, entity IDs, and scrubbed payload parameters.
- **REST APIs (`/api/activity-history`):** Multi-attribute search (`q`), filtering by `module`, `activity_type`, `status`, `user_id`, and `date_range`, with paginated responses and aggregate statistics.
- **Immutability & Access Control:** Read access for all authorized personnel; deletion is strictly restricted to Super Admin users (`admin` role).
- **Frontend Timeline & Inspector Module (`/activity`):** Interactive Ops-Room Activity History page with real-time stats cards, module filter toggles, dual Timeline/Table layout modes, and expandable JSON metadata inspector drawers.

---

## ⚙️ Background Task Runner with Retries (Bounty 3)

CrimeIntel includes an asynchronous **Background Task Runner** (`background_jobs` table) for non-blocking operations:
- **Asynchronous Execution Pipeline (`app/job_runner.py`):** Offloads heavy AI content generation, CSV case ingestion, PDF dossier exports, citizen report AI analysis, and business trend calculations to background worker threads.
- **Automatic Retry Engine with Exponential Backoff:** Detects transient failures and automatically retries jobs (`QUEUED` $\rightarrow$ `RUNNING` $\rightarrow$ `RETRYING` $\rightarrow$ `COMPLETED`). Immediately halts unrecoverable validation/auth errors (`FAILED`) without wasting retry cycles.
- **REST APIs (`/api/jobs`):** Submit jobs (`POST`), poll real-time status and progress percentage (`GET /{id}`), fetch step-by-step logs (`GET /{id}/logs`), manually re-queue failed jobs (`POST /{id}/retry`), and cancel active tasks (`POST /{id}/cancel`).
- **Frontend Job Center (`/jobs`):** Dedicated Job Center UI (`JobCenter.jsx`) featuring 2s auto-polling progress bars, execution duration counters, status badges, log drawers, output downloads, and 1-click retry buttons.

---

## ⚡ Real-Time In-App Alerts via WebSocket (Sprint 7)

CrimeIntel delivers instant, multi-device live notifications over WebSockets (`/ws/notifications?token=<JWT>`):
- **Event Sources:** Automatically triggers persistent alert rows and WebSocket pushes on high-severity case creation (`high`/`critical`), officer case assignment, task assignment, district trend alerts, and gang group detections.
- **RBAC Scoping & Deduplication:** `viewer` users are restricted from receiving investigation/high-severity alerts. Duplicate alerts are suppressed.
- **Persistent Storage:** Notifications survive page refreshes and offline periods (`notifications` database table).
- **Top Navigation Bell Icon & Toast Popups:** App-wide `Header.jsx` with an interactive **Notification Bell**, unread badge pill, dropdown panel with click-to-navigate links, and non-intrusive toast popups.

---

## 🤝 Case Collaboration & Task Tracking (Sprint 6)


CrimeIntel enables multi-investigator coordination across case files:
- **Officer Assignments & Role Gating:** Supervisory roles (`admin`/`analyst`) can assign any officer to a case with specific role titles (e.g. *Lead Investigator*, *Reviewing Analyst*). Investigators can self-claim cases (`assigned_to_user_id == current_user.id`).
- **Investigative Tasks:** Create and track case to-dos with due dates, assignees, and status transitions (`todo` $\rightarrow$ `in_progress` $\rightarrow$ `done`). Status changes write entries to `audit_logs`.
- **Threaded Case Comments:** Chronological investigator discussion feed on `CaseDetail.jsx`.
- **"My Work" Officer Workspace (`/my-work`):** Dedicated page listing active case assignments and open tasks assigned to the logged-in officer across all cases, accompanied by a live task count badge pill in the navigation sidebar (`"06 · My Work"`).

---

## 🤖 Full-Page AI Assistant (`/assistant`)


In addition to the floating bottom-right `ChatWidget.jsx`, CrimeIntel features a dedicated 3-column **AI Assistant Desk** at `/assistant`:
- **Left Column:** Saved Investigative Threads session list & "+ New Conversation" button.
- **Center Column:** Full-height thread, bilingual language toggle (EN/Kannada), speech-to-text mic, read-aloud toggle, and **"⬇ Export PDF Report"** transcript generator.
- **Right Column:** Real-time **Execution Reasoning Steps** and **Source Case Citations** with similarity scores and direct links (`[Open Case File ➔]`).
- **Shared Session State:** Conversations seamlessly synchronize between the floating widget and full page using shared `localStorage` session keying.

---

## 🧠 Autonomous Governance-First AI Agent (Sprint 8)

CrimeIntel upgrades the Case Assistant from single-shot RAG into an autonomous, tool-calling agent with strict write-action governance:
- **7 Read Tools (Autonomous Execution):** `search_cases`, `get_case_detail`, `get_network_graph`, `get_offender_risk`, `get_financial_trail`, `get_similar_cases`, `get_investigation_timeline`.
- **3 Write Tools (Human-in-the-Loop Governance):** `create_task`, `assign_case`, `add_comment`. Every write action requires explicit officer confirmation in the UI via `PendingAgentAction` cards (`"✓ Confirm & Execute Action"` / `"✕ Cancel Action"`) before execution.
- **Demographic Exclusion Guarantee:** Automatically strips `religion_id` and `caste_id` from all tool inputs, outputs, and reasoning steps.
- **Proactive Background Case Worker:** Async background task automatically runs multi-step investigative analysis on new `high`/`critical` severity cases, posts an AI-authored comment (`is_ai_authored=True`, `"🤖 AI Agent"`), and dispatches a WebSocket notification.

---

## 🔒 Statutory Compliance & Sensitive Data Protocol


> **Notice:** `religion_id` and `caste_id` on Complainant records are mandated by the official KSP FIR schema, but are strictly access-restricted in CrimeIntel for anti-discrimination compliance. These fields are:
> - **Excluded** from AI RAG index, analytics, risk scoring, and network graph computations.
> - **Masked** as `null` for non-admin roles at the API layer.
> - **Logged** to `audit_logs` (`action="view_sensitive_complainant_data"`) whenever read by an Admin user.

---

## 📢 Synthetic Demo Data Disclosure

> **Notice:** All socio-demographic statistics, district indicators, bank accounts, financial transactions, and FIR records seeded in this demo environment are **synthetic data** generated exclusively for technical evaluation and policy insight demonstration.

---

## 🛠️ Quick Start (Local Development)

### 1. Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate            # source venv/bin/activate on Linux/Mac
pip install -r requirements.txt
python seed.py                   # Populates connected demo storylines A-F & lookup masters
uvicorn app.main:app --reload --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Default Credentials:
  - Admin: `admin@crimeintel.local` / `Admin@123`
  - Analyst: `analyst@crimeintel.local` / `Analyst@123`
  - Investigator: `investigator@crimeintel.local` / `Investigator@123`
  - Viewer: `viewer@crimeintel.local` / `Viewer@123`

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
- Frontend UI: `http://localhost:5173`

---

## 🧪 Automated Testing

### ⚙️ Bounty 5: Multi-Step Orchestration with Human Approval Gates
- **Intelligent Workflow Engine:** Decomposes complex user requests into ordered multi-step execution plans (`workflows`, `workflow_steps`, `workflow_approvals` tables) with step risk classification (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Human Approval Gate System:** Low and medium risk steps execute automatically. High and critical risk operations (financial account freezes, judicial arrest warrants, production data modification) automatically pause the workflow and generate a human approval request.
- **Resumable Execution & Fault Tolerance:** Workflows persist state across server restarts and resume execution from the exact paused step upon human approval (`APPROVED`) without repeating completed steps. Rejection (`REJECTED`) terminates the workflow gracefully while preserving audit logs.
- **Approval Center UI (`/workflows`):** Dashboard featuring workflow progress bars, step timeline inspection modal, and dedicated Human Approval Center with risk badges, expected impact details, proposed actions, and approval/rejection action buttons.
- **REST APIs (`/api/workflows`):** Endpoints to create (`POST /api/workflows`), list (`GET /api/workflows`), inspect (`GET /api/workflows/{id}`), execute step (`POST /api/workflows/{id}/execute`), cancel (`POST /api/workflows/{id}/cancel`), list pending approvals (`GET /api/workflows/approvals/pending`), and submit decisions (`POST /api/workflows/approvals/{id}/decision`).

---

Run the automated backend test suite (79 unit & integration tests):
```bash
cd backend
python -m pytest tests/ -v
```

---

## 🐳 Docker Deployment (Production Stack)

Deploy the entire production stack (PostgreSQL 16, FastAPI, Nginx) with Docker Compose:
```bash
docker-compose up --build
```
- Frontend (Nginx): `http://localhost:80`
- Backend API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`
