# Explainable Behavioral Offender Risk Scoring Model

## Executive Summary
The CrimeIntel Offender Risk Scoring algorithm calculates a quantitative risk score (0 to 100) for individuals identified across crime cases. 

> [!IMPORTANT]
> **Fairness & Non-Bias Guarantee:**
> This risk scoring engine is strictly **criminological and behavioral**. It relies exclusively on objective case history, offense severity, recency of activity, modus operandi (MO) repetition, and network connectivity. 
> **Demographic traits (age, gender, occupation, education, income, ethnicity, caste, religion, or area of origin) are strictly excluded from risk calculation.**

---

## Risk Scoring Formula

The total risk score $S$ is calculated as the sum of 5 weighted behavioral components, capped at 100 points:

$$S = \min(100, S_{\text{volume}} + S_{\text{severity}} + S_{\text{recency}} + S_{\text{mo}} + S_{\text{network}})$$

### 1. Case Volume Component ($S_{\text{volume}}$)
Measures the number of distinct criminal cases linked to the individual as a suspect or accused.
- **Formula:** $S_{\text{volume}} = 10 \times (\text{linked case count})$
- **Max Weight:** 40 points

### 2. Offense Severity Component ($S_{\text{severity}}$)
Evaluates the highest severity among all linked cases.
- **Critical Severity:** +30 points
- **High Severity:** +20 points
- **Medium Severity:** +10 points
- **Low Severity:** +5 points
- **Max Weight:** 30 points

### 3. Recency Component ($S_{\text{recency}}$)
Applies a recency decay weight based on the date of the most recent linked incident.
- **Active within last 30 days:** +25 points
- **Active within last 90 days:** +15 points
- **Active within last 180 days:** +5 points
- **Inactive (>180 days):** +0 points
- **Max Weight:** 25 points

### 4. Modus Operandi (MO) Repetition Component ($S_{\text{mo}}$)
Rewards behavioral consistency patterns (e.g. repeated use of OTP fraud, night burglary techniques).
- **Formula:** $S_{\text{mo}} = 15 \times (\text{count of repeated MO tags across multiple cases})$
- **Max Weight:** 30 points

### 5. Network Centrality Component ($S_{\text{network}}$)
Measures multi-suspect connections and shared phone identifiers across distinct cases.
- **Formula:** $S_{\text{network}} = 10 \times (\text{distinct recurring phone links or co-suspect edges})$
- **Max Weight:** 20 points

---

## Risk Tier Classification

| Score Range | Category | Badge Styling | Actionable Guidance |
|---|---|---|---|
| **0 – 39** | **Low Risk** | `teal` / `border-teal` | Monitor routine court updates. |
| **40 – 69** | **Medium Risk** | `amber` / `border-amber` | Cross-verify MO tags against open district burglaries/frauds. |
| **70 – 100** | **High Risk** | `crit` / `border-crit` | Flag for priority intelligence review & multi-case connection mapping. |

---

## Auditability & Explainability
Every risk score calculation returns an explicit **Score Breakdown** dictionary:
```json
{
  "total_score": 75,
  "category": "high",
  "breakdown": {
    "volume_pts": 20,
    "severity_pts": 20,
    "recency_pts": 15,
    "mo_repetition_pts": 10,
    "network_centrality_pts": 10
  }
}
```
This guarantees that law enforcement officers can explain *why* an offender received a high risk classification during judicial proceedings.
