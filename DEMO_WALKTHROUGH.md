# CrimeIntel — Presenter Demo Walkthrough Script

**Platform Overview:** CrimeIntel is an enterprise-grade law enforcement case management and AI intelligence platform built for state police departments, investigators, and crime analysts. It integrates official Karnataka State Police (KSP) FIR ER diagram structures, TF-IDF vector RAG deep-search, D3 force-directed network graphs, non-biased criminological risk scoring, and role-based statutory governance.

---

## ⏱️ Live Presentation Flow (12–15 Minutes)

### Step 1: Login & Ops-Room Dashboard
- **Page to Open:** `http://localhost:5173/login` $\rightarrow$ Sign in as **Lead Analyst** (`analyst@crimeintel.local` / `Analyst@123`).
- **What to Click/Ask:** Navigate to **01 · Dashboard**.
- **What to Point Out:** Point out the dark ops-room aesthetic, real-time KPI metrics (Total Cases, Heinous Offence Ratio, Active Investigation Counts), 30-day district incident delta alerts, and high-severity incident feed.
- **Proves Pillar:** **Pillar 5 (Predictive Analytics & Trend Alerts)** & **Pillar 6 (Secure RBAC & Governance)**.

---

### Step 2: KSP FIR Case Search & Structured Standard (Storyline D)
- **Page to Open:** **02 · Case Search** (`/cases`) $\rightarrow$ Click on case **`CR-2026-0401`** (*Commercial Street Jewelry Heist*).
- **What to Click/Ask:** Scroll through the case detail header, crime metadata, and statutory FIR section.
- **What to Point Out:** Point out the 18-digit KSP structured crime number (`100120045202600001`), Heinous gravity classification, crime head (*Crimes Against Property*), crime sub-head (*Robbery*), and associated IPC Sections (*Section 392 - Punishment for Robbery*).
- **Proves Pillar:** **Pillar 1 (Case Management & Search)**.

---

### Step 3: Investigation Timeline (Storyline D)
- **Page to Open:** `CaseDetail.jsx` for **`CR-2026-0401`** $\rightarrow$ Scroll down to **"Investigation Timeline"**.
- **What to Point Out:** Highlight the full vertical chronological milestone timeline:
  1. *Incident Date & Incident Info Received* (May 1, 2026)
  2. *FIR Registered* by Inspector K. Sharma
  3. *Arrest Event Recorded* (Ramesh Rao apprehended on May 15, 2026)
  4. *Chargesheet Filed* in Principal District Court (June 1, 2026).
- **Proves Pillar:** **Pillar 6 (Investigator Decision Support)**.

---

### Step 4: Offender Profiling & Non-Biased Risk Scoring (Storyline A)
- **Page to Open:** **08 · Offender Profiles** (`/offenders`).
- **What to Click/Ask:** Click on profile card for **`Ramesh @ 'Black Hat' Rao`**.
- **What to Point Out:** Point out his **High Risk Score (88/100)** and explain the non-biased model: score is computed strictly from case frequency (4 linked cases across Bengaluru & Mysuru), max severity, recency, MO repetition (`night-burglary`, `armed-robbery`), and co-accused centrality. **Demographic fields (age, religion, income) are strictly excluded.**
- **Proves Pillar:** **Pillar 8 (Offender Profiling & Risk Scoring)**.

---

### Step 5: Criminal Network Graph & Gang Group Detection (Storyline B)
- **Page to Open:** **04 · Network Graph** (`/network`).
- **What to Click/Ask:** Observe the force-directed D3 network graph and look at the right sidebar panel titled **"Detected Gangs & Syndicates"**.
- **What to Point Out:** Point out **"The Electronic City Cyber Syndicate"** cluster. Click on the group card to highlight co-accused members (*Vikram 'Viper' Singh*, *Anand 'Techie' Rao*, *Suresh 'Broker' Kumar*, *Deepak 'Rider' Verma*) connected by shared co-accused links and phone edge `9876543210`.
- **Proves Pillar:** **Pillar 4 (Criminal Network Visualization & Syndicate Clustering)**.

---

### Step 6: Financial Crime Linking & Wire Trail (Storyline C)
- **Page to Open:** Navigate to case **`CR-2026-0301`** (*Phishing OTP Fraud*) $\rightarrow$ Click **"View Wire Transfer Trail"**.
- **What to Click/Ask:** Interact with the node-and-link financial graph on `/finance/trail/CR-2026-0301`.
- **What to Point Out:** Trace the ₹8,50,000 multi-hop money flow:
  1. *Victim HDFC Account* (`XXXX-9001`) $\rightarrow$
  2. *Transit ICICI Account* (`XXXX-9002` held by Anand Rao) $\rightarrow$
  3. *Paytm Digital Mule Wallet* (`XXXX-9003` held by Suresh Kumar) with flagged ATM cash withdrawal.
- **Proves Pillar:** **Pillar 10 (Financial Crime Linking)**.

---

### Step 7: Socio-Demographic Crime Insights & Seasonal Trends (Storyline E)
- **Page to Open:** **09 · Socio Insights** (`/insights`).
- **What to Click/Ask:** Scroll down to the **"Seasonal & Event-Based Trend Analysis"** section.
- **What to Point Out:** Point out the prominent **October/November festive season spike bar** in the Month-of-Year distribution chart, proving how Deepavali holiday periods correlate with residential burglaries in Bengaluru.
- **Proves Pillar:** **Pillar 9 (Socio-Demographic Crime Insights & Pattern Forecasting)**.

---

### Step 8: Hotspot Map Spatial Visualization
- **Page to Open:** **03 · Hotspot Map** (`/map`).
- **What to Click/Ask:** Zoom into Bengaluru City and click on a red critical severity marker.
- **What to Point Out:** Show dark ops-room basemap, severity color-coded markers (Red = Critical, Amber = High, Teal = Medium), and instant popup linking directly to the case file.
- **Proves Pillar:** **Pillar 3 (Hotspot Map Spatial Visualization)**.

---

### Step 9: Full-Page AI Assistant & Explainable AI (Deep Search)
- **Page to Open:** **05 · AI Assistant** (`/assistant`).
- **What to Click/Ask:** Type the following 3 live test queries into the AI Assistant:
  1. `What cases are linked to suspect Ramesh Rao?`
  2. `Show me phishing wire transfer cases in Bengaluru`
  3. `What is the status of case CR-2026-0401?`
- **What to Point Out:**
  - **Left Column:** Live conversation history & "+ New" thread creation.
  - **Center Column:** Bilingual EN/Kannada toggle, voice mic, and PDF report export.
  - **Right Inspector Panel:** Point out **⚡ Execution Reasoning Steps** showing real-time RAG steps, and **📄 Source Case Citations** with match percentages and direct links (`[Open Case File ➔]`).
- **Proves Pillar:** **Pillar 2 (Conversational AI Assistant)** & **Explainable AI Reasoning Steps**.

---

### Step 10: Statutory Sensitive Data Protection Live Demo (Storyline F)
- **Page to Open:** Sign out and log in as **Investigator** (`investigator@crimeintel.local`), open case **`CR-2026-0601`**.
- **What to Click/Ask:** Observe the **Complainant Details** section.
- **What to Point Out:** Show that `Religion` and `Caste` display **`[MASKED - STATUTORY RESTRICTION]`** for Non-Admin roles. Then sign out, log back in as **Admin** (`admin@crimeintel.local`), re-open `CR-2026-0601`, and show that Admin can view the statutory records, which writes an entry to **06 · Audit Trail**.
- **Proves Pillar:** **Pillar 6 (Secure RBAC & Statutory Governance)**.

---

## ❓ Evaluator / Judge FAQ

### Q1: Is this real Karnataka State Police (KSP) data?
> **Answer:** The schema strictly implements the **official Karnataka State Police (KSP) FIR ER Diagram standard** (18-digit structured crime numbers, master lookup tables, arrest events, act/sections, chargesheets). However, all case narratives, suspect names, phone numbers, and bank accounts seeded in this demo environment are **100% synthetic data** generated for evaluation safety.

### Q2: How is the offender risk score computed, and is it biased?
> **Answer:** Risk scores (0–100) are computed strictly using **criminological and behavioral metrics**: case frequency, max severity, recency, MO tag repetition, and network centrality. **Demographic attributes (religion, caste, age, gender, income) are strictly excluded from risk scoring** to prevent algorithmic bias.

### Q3: How is statutory sensitive complainant data protected?
> **Answer:** `religion_id` and `caste_id` are statutory KSP FIR fields, but CrimeIntel enforces strict access controls: they are **excluded from AI RAG indexes, analytics, and risk scoring**, **masked as null at the API layer for non-admin roles**, and **audited in `audit_logs` whenever accessed by an Admin**.
