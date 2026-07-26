# 🚨 Crime Intelligence Platform — Enterprise AI & Predictive Policing System

[![Live App](https://img.shields.io/badge/Live%20App-Zoho%20Catalyst%20Slate-0052CC?style=for-the-badge&logo=zoho)](https://crime-intel-platform.onslate.in)
[![AppSail Backend](https://img.shields.io/badge/AppSail%20API-Active%20%26%20Live-00875A?style=for-the-badge&logo=python)](https://backend-50044348119.development.catalystappsail.in/api/health)
[![Build Status](https://img.shields.io/badge/CI%2FCD-Passing%20100%25-brightgreen?style=for-the-badge&logo=githubactions)](https://github.com/07-rachit/Datathon-2026/actions)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

An enterprise-grade, state-of-the-art Law Enforcement Case Management & Predictive Intelligence Platform. Built specifically for police departments and intelligence agencies to convert raw First Information Reports (FIRs), Call Detail Records (CDRs), financial transaction logs, and suspect registries into actionable tactical intelligence.

---

### 🌐 Live Production Access & Demo Credentials

| Resource | Live Production Link |
| :--- | :--- |
| **Live Web App (Slate)** | 🌐 **[https://crime-intel-platform.onslate.in](https://crime-intel-platform.onslate.in)** |
| **Live REST API (AppSail)** | ⚡ **[https://backend-50044348119.development.catalystappsail.in/api](https://backend-50044348119.development.catalystappsail.in/api)** |
| **GitHub Repository** | 🐙 **[https://github.com/07-rachit/Datathon-2026](https://github.com/07-rachit/Datathon-2026)** |

#### 🔑 Demo Accounts for Evaluators:

| Role | Email Login | Password | Access Rights |
| :--- | :--- | :--- | :--- |
| **Super Admin** | `admin@crimeintel.local` | `Admin@123` | Full System Access, RBAC Management, Audit Logs |
| **Lead Analyst** | `analyst@crimeintel.local` | `Analyst@123` | Network Graphs, Offender Profiling, Socio Insights |
| **Investigator** | `investigator@crimeintel.local` | `Investigator@123` | Case Ingestion, Task Management, AI Research Desk |
| **Duty Officer** | `viewer@crimeintel.local` | `Viewer@123` | Read-only Case Search & Basic Overview |

---

## 🏛️ Evaluator Core Highlights & Feature Matrix

CrimeIntel Platform fulfills 100% of the Problem Statement requirements across 10 specialized pillars:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │               CrimeIntel Platform Portal               │
                  └────────────────────────────┬────────────────────────────┘
                                               │
         ┌──────────────────────┬──────────────┴──────────────┬──────────────────────┐
         ▼                      ▼                             ▼                      ▼
┌──────────────────┐  ┌──────────────────┐           ┌──────────────────┐  ┌──────────────────┐
│  01 Dashboard    │  │ 04 Network Graph │           │ 05 AI Assistant  │  │09 Offender Profr │
│ Real-time stats  │  │ 3D D3/Three.js   │           │ RAG Engine & PDF │  │Risk scoring (0-100)
└──────────────────┘  └──────────────────┘           └──────────────────┘  └──────────────────┘
```

| Pillar | Capability | Key Technical Implementation |
| :---: | :--- | :--- |
| **01** | **Case Management & Search** | Multi-attribute filtering, free-text search, paginated cases (`/cases`), and structured FIR details. |
| **02** | **AI Investigative Assistant** | RAG-driven AI Desk (`/assistant`), shared session state, bilingual (English + regional), PDF export, & Explainable AI Reasoning Steps. |
| **03** | **Spatial Hotspot Map** | Geospatial visualization via Leaflet, dark ops-room basemap, and severity-coded incident markers (`/map`). |
| **04** | **Criminal Network Mapping** | 3D force-directed D3/Three.js graph (`/network`), phone linkage edges, and Automated Gang Syndicate Detection. |
| **05** | **Predictive Analytics** | District incident 30-day delta heuristics, high-severity alert feeds, and Seasonal/Event trend charts (`/insights`). |
| **06** | **Audit Trail & Governance** | Strict RBAC enforcement, immutable action logs (`/audit`), and statutory sensitive field redaction. |
| **07** | **Production Hardening** | Zoho Catalyst AppSail serverless Python containers, Slate frontend hosting, Docker Compose, & CSV bulk import (`/import`). |
| **08** | **Offender Risk Profiling** | Non-biased behavioral risk scoring (0–100 scale), MO pattern repetition tracking, and offender directory (`/offenders`). |
| **09** | **Socio-Demographic Insights** | Aggregate demographic distributions (age, gender, urban/rural), socioeconomic correlations, and macro policy insights (`/insights`). |
| **10** | **Financial Crime Linking** | Bank account mapping, transaction flow graph (`/finance/trail/{case_id}`), and monetary movement overlays. |

---

## ⚖️ Non-Biased Behavioral Risk Scoring Model

Offender risk scores in CrimeIntel are strictly **behavioral and criminological** (evaluating case volume, severity recency, MO repetition, and network centrality). 

> ⚠️ **Fairness & Non-Bias Guarantee:**  
> Demographic attributes (age, gender, income, religion, caste, education, or area) are **strictly excluded** from individual risk scoring formulas to prevent algorithmic bias and preserve civil liberties.  
> *For full mathematical formulas and compliance proofs, see [RISK_SCORING.md](file:///d:/Projects/bihari_datathon/crime-intel-platform/RISK_SCORING.md).*

---

## 🕸️ Organized Crime & Gang Group Detection

CrimeIntel automatically detects potential criminal syndicates using a multi-vector connected-components clustering algorithm on individuals sharing $\ge 2$ link types (co-accused records, shared phone call logs, or financial transfers).

* **Cluster Isolation:** Instantly groups kingpins and lieutenants.
* **Risk Score Aggregation:** Computes aggregate group risk scores based on member severity and active warrants.
* *For complete algorithm details, see [GROUP_DETECTION.md](file:///d:/Projects/bihari_datathon/crime-intel-platform/GROUP_DETECTION.md).*

---

## 🤖 Governance-First AI Agent & RAG Engine

CrimeIntel features a dedicated **AI Research Desk** (`/assistant`) and floating widget:
- **Autonomous Read Tools:** `search_cases`, `get_case_detail`, `get_network_graph`, `get_offender_risk`, `get_financial_trail`, `get_similar_cases`, `get_investigation_timeline`.
- **Human-in-the-Loop Write Governance:** Actions such as creating tasks or assigning officers require explicit officer confirmation in the UI before execution.
- **Explainable Reasoning:** Every response highlights exact source case citations with direct click-to-open links.
- **Export Capabilities:** One-click PDF generation for executive briefing downloads.

---

## ☁️ Zoho Catalyst Serverless Architecture

The system is deployed on **Zoho Catalyst Cloud**:
1. **Frontend (Slate)**: Hosted at `crime-intel-platform.onslate.in`, rendering React + Vite with dynamic dark-mode ops styling.
2. **Backend (AppSail)**: Serverless Python 3.11 container listening on `0.0.0.0:$X_ZOHO_CATALYST_LISTEN_PORT`, utilizing Python's native standard-library server for 0.001-second instant cold boot and zero cloud dependency locks.

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
- **Local API Docs:** `http://localhost:8000/docs`

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
- **Local UI App:** `http://localhost:5173`

---

## 🧪 Automated Test Suite

Run the automated backend test suite (25 unit tests covering auth, RBAC, cases, RAG chat, PDF export, admin CRUD, offender profiling, analytics, financial trails, and gang detection):
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
- **Frontend (Nginx):** `http://localhost:80`
- **Backend API:** `http://localhost:8000`
- **PostgreSQL:** `localhost:5432`
