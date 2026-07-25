# CrimeIntel — Technical Architecture & System Blueprint

This document details the software architecture, data modeling, AI retrieval pipeline, security governance, and deployment topology of **CrimeIntel**.

---

## 🏗️ 1. System Overview Architecture

```mermaid
graph TD
    subgraph Client Layer
        UI["React 18 + Vite Frontend\n(Ops-Room Dark Theme / Tailwind CSS)"]
        Widget["ChatWidget.jsx / Assistant.jsx\n(Shared Session State)"]
    end

    subgraph Security & Gateway Layer
        Nginx["Nginx Reverse Proxy / Static Web Server"]
        Auth["FastAPI JWT Bearer Authentication"]
        RBAC["Role-Based Access Control (RBAC)\n(admin, analyst, investigator, viewer)"]
        RateLimit["Slowapi Rate Limiter"]
    end

    subgraph Core Application Layer (FastAPI)
        CasesAPI["/api/cases Router"]
        NetworkAPI["/api/network Router\n(D3 Force Graph & Gang Group Clustering)"]
        FinanceAPI["/api/finance Router\n(Wire Trail Mapping)"]
        AnalyticsAPI["/api/analytics Router\n(Seasonal Trends & Demographic Insights)"]
        ChatAPI["/api/chat Router\n(Deep Search RAG & Reasoning Pipeline)"]
        ExportAPI["/api/export Router\n(ReportLab PDF Generator)"]
    end

    subgraph AI Intelligence Engine
        Index["In-Memory TF-IDF Vector Index\n(ngram_range=(1,2), bi-grams)"]
        Retriever["Deep-Search Multi-Strategy Retriever\n(Case ID + Phone + TF-IDF + Keyword Fallback)"]
        LLM["Anthropic Claude API\n(Generation & Bilingual Synthesis)"]
    end

    subgraph Persistence Layer
        DB[("PostgreSQL 16 / SQLite Database")]
        Audit[("Audit Logs & Statutory Masking Ledger")]
    end

    UI --> Nginx
    Widget --> Nginx
    Nginx --> Auth
    Auth --> RBAC
    RBAC --> RateLimit
    RateLimit --> CasesAPI & NetworkAPI & FinanceAPI & AnalyticsAPI & ChatAPI & ExportAPI

    ChatAPI --> Retriever
    Retriever --> Index
    Retriever --> LLM
    CasesAPI & NetworkAPI & FinanceAPI & AnalyticsAPI --> DB
    RBAC --> Audit
```

---

## 🗄️ 2. Data Model & Schema Domain Groups

CrimeIntel's data model aligns with the **official Karnataka State Police (KSP) FIR ER Diagram Standard** while providing modular extensions for AI analytics:

| Domain Group | Primary Entities | Key Attributes & Capabilities |
|---|---|---|
| **Core KSP FIR Schema** | `Case`, `CaseFIRDetails`, `CaseCategoryMaster`, `GravityOffenceMaster`, `CrimeHead`, `CrimeSubHead`, `CaseStatusMaster`, `CourtMaster`, `UnitMaster`, `EmployeeMaster` | 18-digit structured crime numbers (`100120045202600018`), Heinous/Non-Heinous gravity classifications, registering officer IDs, district/station codes. |
| **Legal & Prosecution** | `Act`, `Section`, `ActSectionAssociation`, `ArrestSurrender`, `ChargesheetDetails` | IPC / BNS / IT Act associations, arrest events, chargesheet filing dates (CS-A / CS-B / CS-C status). |
| **Offender Profiling** | `Person`, `OffenderProfile` | Suspect/co-accused roles, MO tag tracking (`night-burglary`, `armed-robbery`), behavioral risk scores (0–100 scale). |
| **Financial Crime** | `FinancialAccount`, `FinancialTransaction` | Bank accounts (`HDFC`, `ICICI`, `Paytm Mule`), transaction wire trails, flagged OTP fraud transfers. |
| **Sociological Insights** | `ComplainantDetails`, `OccupationMaster`, `ReligionMaster`, `CasteMaster`, `DistrictIndicator` | Age/gender distributions, occupation analytics, district literacy/unemployment correlations. |
| **AI RAG & Chat** | `ChatSession`, `ChatMessage` | Session threads, message roles (`user`, `assistant`), cited source JSON, recorded execution reasoning steps. |
| **Governance & Audit** | `User`, `AuditLog` | JWT user accounts, role enums, action audit logs with IP tracking and sensitive field access records. |

---

## 🤖 3. AI Retrieval Pipeline & Explainable Governance

### Retrieval-Augmented Generation (RAG) Architecture
1. **Multi-Vector Context Retrieval:**
   - **Direct Case ID Detection:** Regex extraction (`CR-\d{4}-\d{4}`) for instant 1.0 confidence case file retrieval.
   - **Suspect Phone Matching:** Regex extraction (`+?\d[\d\- ]{6,}`) for 0.95 confidence suspect & co-accused case retrieval.
   - **TF-IDF Vector Similarity:** Bi-gram TF-IDF vectorization over all case titles, summaries, FIR details, acts/sections, and evidence text.
   - **Synonym-Expanded Keyword Fallback:** Automated fallback search mapping common typos (`karantka` $\rightarrow$ `karnataka`, `bengaluru`) and crime synonyms (`robbery` $\rightarrow$ `burglary`, `theft`).
2. **Generation Layer:**
   - Assembles top $K=8$ retrieved case chunks into a structured prompt context.
   - Dispatches context to the **Anthropic API** (or falls back to a clean direct RAG summary if unconfigured).
3. **Explainable Reasoning Pipeline:**
   - Instruments and logs step-by-step pipeline execution steps (e.g. `"Detected case ID CR-2026-0401"`, `"Retrieved 4 matching case chunks via TF-IDF vector similarity"`).
   - Displayed in real-time in the **Context Inspector** panel on `/assistant`.
4. **Statutory Non-Bias & Exclusion Rules:**
   - `religion_id` and `caste_id` are **strictly excluded** from TF-IDF chunk indexing, RAG prompts, risk scoring, and network graph algorithms.

### 3.5 Autonomous Unified AI Agent & Governance Architecture (Sprint 8)
1. **Tool-Calling Agent Loop (`agent_loop.py`):**
   - Implements multi-step tool execution loop (capped at max 6 iterations).
   - Reads LLM tool-use calls and dispatches to python functions in `agent_tools.py`.
2. **Autonomous Read Tools (7 Read Tools):**
   - `search_cases`, `get_case_detail`, `get_network_graph`, `get_offender_risk`, `get_financial_trail`, `get_similar_cases`, `get_investigation_timeline`.
3. **Human-in-the-Loop Write Governance (3 Write Tools):**
   - `create_task`, `assign_case`, `add_comment`.
   - When the agent attempts a write tool, execution halts immediately and creates a `PendingAgentAction` record with status `pending`.
   - Returns a `pending_action` payload to the frontend, which renders an explicit **Action Confirmation Card** with `"✓ Confirm & Execute Action"` and `"✕ Cancel Action"` buttons.
   - Execution occurs ONLY when an authorized user (`investigator`, `analyst`, `admin`) invokes `POST /api/chat/assistant/actions/{id}/confirm`.
4. **Demographic Attribute Exclusion Layer:**
   - `agent_tools.sanitize_tool_output()` recursively strips `religion_id`, `caste_id`, `religion`, and `caste` from all tool outputs before supplying context back to the LLM or UI.
5. **Proactive Background Case Analysis Worker (`proactive_agent.py`):**
   - Triggered asynchronously upon creation of `high`/`critical` severity cases.
   - Executes multi-tool investigative analysis, posts a structured 3-paragraph summary as a case comment marked `is_ai_authored=True`, and broadcasts an `ai_case_analysis` WebSocket notification.

---


## 🐳 4. Deployment Topology & Production Stack

### Containerized Stack (`docker-compose.yml`)
- **Frontend Container:** Static React SPA built with Vite, served by **Nginx** on port `80`.
- **Backend Container:** High-performance **FastAPI** application running `uvicorn` workers on port `8000`.
- **Database Container:** Production **PostgreSQL 16** database instance on port `5432` with persistent volume mounting.

### Production Environment Configuration
```env
DATABASE_URL=postgresql://crimeintel:securepassword@db:5432/crimeintel_db
SECRET_KEY=production-jwt-secret-key-32-bytes-min
ANTHROPIC_API_KEY=sk-ant-api-key-here
ENVIRONMENT=production
CORS_ORIGINS=http://localhost,https://crimeintel.karnataka.gov.in
```

---

## 🔒 5. Security & Governance Matrix

| Security Layer | Implementation Details |
|---|---|
| **Role-Based Access Control (RBAC)** | Role matrix: `admin` (full access & sensitive data view), `analyst` (full analytics & offender directory), `investigator` (case management & FIR creation), `viewer` (read-only with masked phone numbers). |
| **Statutory Sensitive Data Masking** | Complainant `religion_id` and `caste_id` return `null` for non-admin roles at the API serializer level. Admin reads automatically trigger an audit entry: `action="view_sensitive_complainant_data"`. |
| **Rate Limiting (`slowapi`)** | Endpoint-level rate limiting (`/api/auth/login` capped at 10 req/min, `/api/chat` capped at 30 req/min). |
| **Audit Trail Protocol** | Immutable `audit_logs` table tracking user ID, IP address, timestamp, action type, and detail string. |
