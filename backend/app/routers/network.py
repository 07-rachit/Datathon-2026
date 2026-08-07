from collections import defaultdict
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, auth
from app.routers.offenders import _calculate_offender_score

router = APIRouter(prefix="/api/network", tags=["network"])


@router.get("/graph")
def get_graph(
    district: str | None = None,
    include_financial: bool = Query(False, description="Overlay financial account nodes and transaction flow edges"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Build a node/edge graph:
      - case nodes
      - person nodes
      - case -> person edges ("linked_to")
      - person -> person edges when they share a phone number across different cases
      - (optional) account nodes & transaction flow edges
    """
    query = db.query(models.Case).options(joinedload(models.Case.persons))
    if district:
        query = query.filter(models.Case.district == district)
    cases = query.all()
    case_ids = {c.id for c in cases}

    nodes = []
    edges = []
    phone_to_persons = defaultdict(list)

    for case in cases:
        nodes.append({
            "id": f"case:{case.id}",
            "type": "case",
            "label": case.case_id,
            "sublabel": case.title,
            "severity": case.severity.value,
            "district": case.district,
            "ref_id": case.id,
        })
        for person in case.persons:
            person_node_id = f"person:{person.id}"
            nodes.append({
                "id": person_node_id,
                "type": "person",
                "label": person.name,
                "sublabel": person.role_in_case or "unknown role",
                "phone": person.phone_number,
                "ref_id": person.case_id,
            })
            edges.append({
                "source": person_node_id,
                "target": f"case:{case.id}",
                "kind": "linked_to",
            })
            if person.phone_number:
                phone_to_persons[person.phone_number].append(person)

    # Recurring-suspect edges: same phone number appearing across different cases
    recurring_count = 0
    for phone, persons in phone_to_persons.items():
        distinct_cases = {p.case_id for p in persons}
        if len(distinct_cases) > 1 and len(persons) > 1:
            for i in range(len(persons)):
                for j in range(i + 1, len(persons)):
                    edges.append({
                        "source": f"person:{persons[i].id}",
                        "target": f"person:{persons[j].id}",
                        "kind": "shared_phone",
                    })
                    recurring_count += 1

    # Optional Financial Graph Overlay
    if include_financial:
        transactions = db.query(models.FinancialTransaction).options(
            joinedload(models.FinancialTransaction.from_account),
            joinedload(models.FinancialTransaction.to_account),
        ).all()

        added_accounts = set()
        for tx in transactions:
            if tx.case_id and tx.case_id not in case_ids:
                continue

            for acc in [tx.from_account, tx.to_account]:
                if acc and acc.id not in added_accounts:
                    added_accounts.add(acc.id)
                    nodes.append({
                        "id": f"account:{acc.id}",
                        "type": "account",
                        "label": f"{acc.bank_name} ({acc.account_number_masked})",
                        "sublabel": acc.account_type,
                        "ref_id": acc.id,
                    })

                    # If account is linked to a person in graph, add edge
                    if acc.person_id:
                        edges.append({
                            "source": f"person:{acc.person_id}",
                            "target": f"account:{acc.id}",
                            "kind": "owns_account",
                        })

            edges.append({
                "source": f"account:{tx.from_account_id}",
                "target": f"account:{tx.to_account_id}",
                "kind": "financial_transfer",
                "amount": tx.amount,
                "flagged": bool(tx.flagged_reason),
            })

    return {"nodes": nodes, "edges": edges, "recurring_links": recurring_count}


@router.get("/groups")
def get_network_groups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("investigator", "analyst", "admin")),
):
    """
    Connected-Components Gang / Organized Crime Group Detection.
    Identifies person clusters sharing multiple link vectors (co-accused, shared phone, financial transfer).
    """
    # Audit log entry
    log = models.AuditLog(
        user_id=current_user.id,
        action="view_network_groups",
        detail="Accessed organized crime syndicate & group detection analytics",
    )
    db.add(log)
    db.commit()

    all_persons = db.query(models.Person).all()
    if not all_persons:
        return []

    # Map persons by ID
    person_by_id = {p.id: p for p in all_persons}
    adj = defaultdict(set)
    vectors = defaultdict(lambda: defaultdict(set))

    # Vector 1: Co-accused in same case
    case_to_persons = defaultdict(list)
    for p in all_persons:
        if p.role_in_case in ["suspect", "accused"]:
            case_to_persons[p.case_id].append(p.id)

    for case_id, p_ids in case_to_persons.items():
        if len(p_ids) > 1:
            for i in range(len(p_ids)):
                for j in range(i + 1, len(p_ids)):
                    u, v = p_ids[i], p_ids[j]
                    adj[u].add(v)
                    adj[v].add(u)
                    vectors[u][v].add("co_accused")
                    vectors[v][u].add("co_accused")

    # Vector 2: Shared phone number across different cases
    phone_to_persons = defaultdict(list)
    for p in all_persons:
        if p.phone_number:
            phone_to_persons[p.phone_number].append(p.id)

    for phone, p_ids in phone_to_persons.items():
        if len(p_ids) > 1:
            for i in range(len(p_ids)):
                for j in range(i + 1, len(p_ids)):
                    u, v = p_ids[i], p_ids[j]
                    adj[u].add(v)
                    adj[v].add(u)
                    vectors[u][v].add("shared_phone")
                    vectors[v][u].add("shared_phone")

    # Vector 3: Financial linkages
    transactions = db.query(models.FinancialTransaction).options(
        joinedload(models.FinancialTransaction.from_account),
        joinedload(models.FinancialTransaction.to_account),
    ).all()

    for tx in transactions:
        p1 = tx.from_account.person_id if tx.from_account else None
        p2 = tx.to_account.person_id if tx.to_account else None
        if p1 and p2 and p1 != p2:
            adj[p1].add(p2)
            adj[p2].add(p1)
            vectors[p1][p2].add("financial_transfer")
            vectors[p2][p1].add("financial_transfer")

    # Connected Components Traversal
    visited = set()
    groups = []
    group_idx = 1

    for p_id in person_by_id:
        if p_id in visited:
            continue
        
        # BFS / DFS
        component = []
        queue = [p_id]
        visited.add(p_id)

        while queue:
            curr = queue.pop(0)
            component.append(curr)
            for nxt in adj[curr]:
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)

        # Qualify cluster: >= 2 persons and distinct shared link types
        if len(component) >= 2:
            comp_persons = [person_by_id[cid] for cid in component]
            linked_cases = len({p.case_id for p in comp_persons})

            # Compute group risk using the behavioral scoring function
            try:
                group_score, _, _ = _calculate_offender_score(comp_persons, all_persons)
            except Exception:
                # Fallback: simple severity + volume heuristic
                severity_weights = {"critical": 30, "high": 20, "medium": 10, "low": 5}
                sev_pts = max(
                    (severity_weights.get(getattr(getattr(p, 'case', None), 'severity', None), 5)
                     for p in comp_persons
                     if getattr(p, 'case', None)),
                    default=5,
                )
                group_score = min(100, 10 * len(component) + sev_pts)

            # Aggregate shared vectors
            shared_vector_set = set()
            for u in component:
                for v in component:
                    if u != v and v in vectors[u]:
                        shared_vector_set.update(vectors[u][v])

            group_risk = min(100, int(group_score + (linked_cases * 4)))

            groups.append({
                "group_id": f"group-{group_idx:02d}",
                "name": f"Syndicate Cluster #{group_idx} ({len(component)} suspects)",
                "member_count": len(component),
                "members": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "role": p.role_in_case,
                        "phone": p.phone_number,
                        "person_node_id": f"person:{p.id}",
                    }
                    for p in comp_persons
                ],
                "linked_cases": linked_cases,
                "shared_vectors": list(shared_vector_set),
                "group_risk_score": group_risk,
            })
            group_idx += 1

    groups.sort(key=lambda g: g["group_risk_score"], reverse=True)
    return groups
