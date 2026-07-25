# Organized Crime & Gang Group Detection Algorithm

This document defines the explainable graph clustering methodology used by CrimeIntel to identify potential organized crime syndicates and gang networks.

---

## 🎯 Clustering Principles & Rules

Group detection runs on the unified criminal network graph comprising **Persons**, **Cases**, and **Financial Accounts**.

### Minimum Qualification Threshold:
A graph cluster is flagged as a **"Potential Organized Crime Syndicate / Gang"** if and only if it satisfies both:
1. **Member Capacity:** Contains **$\ge 3$ distinct suspects/persons**.
2. **Multi-Vector Link Density:** Possesses **$\ge 2$ distinct shared relationship vectors** among:
   - **Vector A (Co-Accused):** Linked as suspects in the same criminal case.
   - **Vector B (Communication):** Share a common phone number across separate cases.
   - **Vector C (Financial Linkage):** Share a bank account or direct monetary transaction flow.

---

## ⚖️ Group Risk Score Formula

Each detected group is assigned an aggregate **Group Risk Score** ($0 - 100$):

$$\text{Group Risk Score} = \min\left(100, \, \overline{\text{Member Risk Scores}} + (N_{\text{cases}} \times 4) + (N_{\text{flagged\_tx}} \times 5)\right)$$

Where:
- $\overline{\text{Member Risk Scores}}$ is the arithmetic mean of individual behavioral risk scores (calculated per [RISK_SCORING.md](file:///d:/Projects/bihari_datathon/crime-intel-platform/RISK_SCORING.md)).
- $N_{\text{cases}}$ is the total number of distinct cases associated with cluster members.
- $N_{\text{flagged\_tx}}$ is the number of flagged suspicious financial transactions between cluster members.

---

## 🔒 Access Control & Audit Logging

- **RBAC:** Access to `GET /api/network/groups` is restricted to `investigator`, `analyst`, and `admin` roles.
- **Audit Logging:** Every call to the group detection endpoint writes a `view_network_groups` entry to `audit_logs`.
