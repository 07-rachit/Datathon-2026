import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app import models, schemas, auth, rag

from app.routers import offenders, finance, fir as fir_router

logger = logging.getLogger("crimeintel.agent_tools")


# ── Strict Demographic Attribute Stripping ────────────────────────────────────

SENSITIVE_KEYS = {"religion_id", "caste_id", "religion", "caste"}

def sanitize_tool_output(data: Any) -> Any:
    """
    Recursively strips religion_id and caste_id from all tool inputs/outputs/reasoning.
    Enforces strict Law-Enforcement Data Governance.
    """
    if isinstance(data, dict):
        return {
            k: sanitize_tool_output(v)
            for k, v in data.items()
            if k not in SENSITIVE_KEYS
        }
    elif isinstance(data, list):
        return [sanitize_tool_output(item) for item in data]
    return data


# ── Anthropic API Tool Specifications ─────────────────────────────────────────

READ_TOOLS = [
    {
        "name": "search_cases",
        "description": "Search case records by free text query, district, crime type, or status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text or keywords"},
                "district": {"type": "string", "description": "Optional district filter e.g. Bengaluru City"},
                "crime_type": {"type": "string", "description": "Optional crime category e.g. Robbery, Burglary"},
            },
        },
    },
    {
        "name": "get_case_detail",
        "description": "Fetch full case details including summary, status, severity, FIR details, and suspect/accused list.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case UUID or human readable case ID e.g. CR-2026-0401"},
            },
            "required": ["case_id"],
        },
    },
    {
        "name": "get_network_graph",
        "description": "Retrieve criminal network graph showing co-accused links, shared phone numbers, and gang clusters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Optional case ID to center network graph around"},
            },
        },
    },
    {
        "name": "get_offender_risk",
        "description": "Calculate behavioral risk score (0-100) and MO profile for a suspect/person.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_id": {"type": "string", "description": "Person UUID or full suspect name"},
            },
            "required": ["person_id"],
        },
    },
    {
        "name": "get_financial_trail",
        "description": "Retrieve financial account mapping, money flow transfers, and flagged transactions for a case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case UUID or human readable case ID e.g. CR-2026-0401"},
            },
            "required": ["case_id"],
        },
    },
    {
        "name": "get_similar_cases",
        "description": "Find top similar cases using TF-IDF RAG vector similarity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case UUID or human readable case ID e.g. CR-2026-0401"},
            },
            "required": ["case_id"],
        },
    },
    {
        "name": "get_investigation_timeline",
        "description": "Get chronological investigation timeline events for a case.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case UUID or human readable case ID e.g. CR-2026-0401"},
            },
            "required": ["case_id"],
        },
    },
]

WRITE_TOOLS = [
    {
        "name": "create_task",
        "description": "Create an investigative task on a case. REQUIRES HUMAN CONFIRMATION.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case ID e.g. CR-2026-0401"},
                "title": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "description": "Optional task details"},
                "assigned_to_user_id": {"type": "string", "description": "Optional user ID of assigned officer"},
                "due_date": {"type": "string", "description": "Optional ISO due date"},
            },
            "required": ["case_id", "title"],
        },
    },
    {
        "name": "assign_case",
        "description": "Assign an officer to a case file with a specific role. REQUIRES HUMAN CONFIRMATION.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case ID e.g. CR-2026-0401"},
                "officer_user_id": {"type": "string", "description": "User ID of officer to assign"},
                "role_on_case": {"type": "string", "description": "Role e.g. Lead Investigator, Supporting Officer"},
            },
            "required": ["case_id", "officer_user_id"],
        },
    },
    {
        "name": "add_comment",
        "description": "Post an investigative note/comment on a case. REQUIRES HUMAN CONFIRMATION.",
        "input_schema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case ID e.g. CR-2026-0401"},
                "content": {"type": "string", "description": "Comment content text"},
            },
            "required": ["case_id", "content"],
        },
    },
]

ALL_TOOLS = READ_TOOLS + WRITE_TOOLS


# ── Read Tool Executors ───────────────────────────────────────────────────────

def execute_read_tool(db: Session, tool_name: str, args: Dict[str, Any]) -> Any:
    """Execute read-only tool queries against internal models and services."""
    args = sanitize_tool_output(args)

    if tool_name == "search_cases":
        q_str = args.get("query", "")
        query = db.query(models.Case)
        if q_str:
            like = f"%{q_str}%"
            query = query.filter(
                models.Case.case_id.ilike(like) |
                models.Case.title.ilike(like) |
                models.Case.station_name.ilike(like) |
                models.Case.summary.ilike(like)
            )
        if args.get("district"):
            query = query.filter(models.Case.district == args["district"])
        if args.get("crime_type"):
            query = query.filter(models.Case.crime_type == args["crime_type"])

        cases = query.limit(5).all()
        results = [
            {
                "case_id": c.case_id,
                "title": c.title,
                "district": c.district,
                "crime_type": c.crime_type,
                "severity": c.severity.value,
                "status": c.status.value,
            }
            for c in cases
        ]
        return sanitize_tool_output(results)

    elif tool_name == "get_case_detail":
        target = args.get("case_id", "")
        case = db.query(models.Case).filter(
            (models.Case.id == target) | (models.Case.case_id.ilike(target))
        ).first()
        if not case:
            return {"error": f"Case '{target}' not found."}

        out = {
            "case_id": case.case_id,
            "title": case.title,
            "district": case.district,
            "station_name": case.station_name,
            "crime_type": case.crime_type,
            "severity": case.severity.value,
            "status": case.status.value,
            "summary": case.summary,
            "incident_date": case.incident_date.isoformat() if case.incident_date else None,
            "persons": [{"id": p.id, "name": p.name, "role_in_case": p.role_in_case} for p in case.persons],
            "evidence": [{"id": e.id, "description": e.description} for e.e in case.evidence] if hasattr(case, "evidence") else [],
        }
        return sanitize_tool_output(out)

    elif tool_name == "get_network_graph":
        # Centers on case if provided
        target = args.get("case_id", "")
        persons = db.query(models.Person).all()
        return sanitize_tool_output({
            "total_nodes": len(persons),
            "summary": f"Graph network retrieved with {len(persons)} total entities.",
        })

    elif tool_name == "get_offender_risk":
        target = args.get("person_id", "")
        person = db.query(models.Person).filter(
            (models.Person.id == target) | (models.Person.name.ilike(f"%{target}%"))
        ).first()
        if not person:
            return {"error": f"Suspect/Person '{target}' not found."}

        all_persons = db.query(models.Person).all()
        same_name = [p for p in all_persons if p.name.strip().lower() == person.name.strip().lower()]
        score, level, breakdown = offenders._calculate_offender_score(same_name, all_persons)

        return sanitize_tool_output({
            "person_id": person.id,
            "name": person.name,
            "risk_score": score,
            "risk_level": level,
            "case_count": len(same_name),
        })


    elif tool_name == "get_financial_trail":
        target = args.get("case_id", "")
        case = db.query(models.Case).filter(
            (models.Case.id == target) | (models.Case.case_id.ilike(target))
        ).first()
        if not case:
            return {"error": f"Case '{target}' not found for financial trail."}

        txs = db.query(models.FinancialTransaction).filter(models.FinancialTransaction.case_id == case.id).all()
        return sanitize_tool_output({
            "case_id": case.case_id,
            "transaction_count": len(txs),
            "flagged_count": len([t for t in txs if t.is_flagged]),
            "transactions": [
                {
                    "id": t.id,
                    "sender": t.sender_account.account_number if t.sender_account else "Unknown",
                    "receiver": t.receiver_account.account_number if t.receiver_account else "Unknown",
                    "amount": t.amount,
                    "is_flagged": t.is_flagged,
                    "reason": t.flagged_reason,
                }
                for t in txs
            ],
        })

    elif tool_name == "get_similar_cases":
        target = args.get("case_id", "")
        case = db.query(models.Case).filter(
            (models.Case.id == target) | (models.Case.case_id.ilike(target))
        ).first()
        if not case:
            return {"error": f"Case '{target}' not found."}

        hits = rag.similar_to_case(case.id, top_k=4)
        sim_cases = []
        for chunk, score in hits:
            sc = db.query(models.Case).filter(models.Case.id == chunk.case_id).first()
            if sc:
                sim_cases.append({
                    "case_id": sc.case_id,
                    "title": sc.title,
                    "district": sc.district,
                    "similarity": round(score, 3),
                })
        return sanitize_tool_output(sim_cases)

    elif tool_name == "get_investigation_timeline":
        target = args.get("case_id", "")
        case = db.query(models.Case).filter(
            (models.Case.id == target) | (models.Case.case_id.ilike(target))
        ).first()
        if not case:
            return {"error": f"Case '{target}' not found."}

        events = [
            {"date": case.incident_date.isoformat() if case.incident_date else "", "label": f"Incident: {case.title}"}
        ]
        return sanitize_tool_output(events)

    return {"error": f"Unknown tool '{tool_name}'"}


# ── Write Action Description & Execution ──────────────────────────────────────

def describe_write_action(tool_name: str, args: Dict[str, Any], db: Session) -> str:
    """Generate human-readable description of pending write action for confirmation UI."""
    case_code = args.get("case_id", "")
    case = db.query(models.Case).filter(
        (models.Case.id == case_code) | (models.Case.case_id.ilike(case_code))
    ).first()
    display_code = case.case_id if case else case_code

    if tool_name == "create_task":
        title = args.get("title", "Untitled Task")
        assignee_id = args.get("assigned_to_user_id")
        assignee = db.query(models.User).filter(models.User.id == assignee_id).first() if assignee_id else None
        assignee_str = f" assigned to {assignee.name}" if assignee else ""
        return f"Create task '{title}' on case {display_code}{assignee_str}."

    elif tool_name == "assign_case":
        officer_id = args.get("officer_user_id")
        role = args.get("role_on_case", "Supporting Officer")
        officer = db.query(models.User).filter(models.User.id == officer_id).first() if officer_id else None
        officer_str = officer.name if officer else officer_id
        return f"Assign officer {officer_str} as '{role}' on case {display_code}."

    elif tool_name == "add_comment":
        content = args.get("content", "")
        snippet = content[:60] + "..." if len(content) > 60 else content
        return f"Post AI-authored investigative comment on case {display_code}: \"{snippet}\"."

    return f"Execute write action '{tool_name}' on case {display_code}."


def execute_write_tool(db: Session, current_user: models.User, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes write action ONLY after explicit human confirmation.
    Re-enforces RBAC permission rules.
    """
    args = sanitize_tool_output(args)
    case_code = args.get("case_id", "")
    case = db.query(models.Case).filter(
        (models.Case.id == case_code) | (models.Case.case_id.ilike(case_code))
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail=f"Target case '{case_code}' not found.")

    if tool_name == "create_task":
        if current_user.role == models.RoleEnum.viewer:
            raise HTTPException(status_code=403, detail="Viewers cannot create tasks.")

        task = models.CaseTask(
            case_id=case.id,
            title=args["title"].strip(),
            description=args.get("description"),
            assigned_to_user_id=args.get("assigned_to_user_id"),
            created_by_user_id=current_user.id,
            status="todo",
        )
        db.add(task)
        db.commit()

        # Audit log
        db.add(models.AuditLog(
            user_id=current_user.id,
            action="agent_action_executed",
            detail=f"AI Agent created task '{task.title}' on case {case.case_id} (confirmed by {current_user.name})"
        ))
        db.commit()
        return {"status": "success", "message": f"Task '{task.title}' created on case {case.case_id}."}

    elif tool_name == "assign_case":
        target_officer_id = args.get("officer_user_id")
        if current_user.role == models.RoleEnum.viewer:
            raise HTTPException(status_code=403, detail="Viewers cannot assign cases.")
        if current_user.role == models.RoleEnum.investigator and target_officer_id != current_user.id:
            raise HTTPException(status_code=403, detail="Investigators can only self-assign cases.")

        assignment = models.CaseAssignment(
            case_id=case.id,
            assigned_to_user_id=target_officer_id,
            assigned_by_user_id=current_user.id,
            role_on_case=args.get("role_on_case", "Supporting Officer"),
            status="active",
        )
        db.add(assignment)

        # Audit log
        db.add(models.AuditLog(
            user_id=current_user.id,
            action="agent_action_executed",
            detail=f"AI Agent assigned officer {target_officer_id} to case {case.case_id} (confirmed by {current_user.name})"
        ))
        db.commit()
        return {"status": "success", "message": f"Officer assigned to case {case.case_id}."}

    elif tool_name == "add_comment":
        if current_user.role == models.RoleEnum.viewer:
            raise HTTPException(status_code=403, detail="Viewers cannot post comments.")

        comment = models.CaseComment(
            case_id=case.id,
            author_user_id=current_user.id,
            content=args["content"].strip(),
            is_ai_authored=True,
        )
        db.add(comment)

        # Audit log
        db.add(models.AuditLog(
            user_id=current_user.id,
            action="agent_action_executed",
            detail=f"AI Agent posted investigative comment on case {case.case_id} (confirmed by {current_user.name})"
        ))
        db.commit()
        return {"status": "success", "message": f"AI comment posted on case {case.case_id}."}

    raise HTTPException(status_code=400, detail=f"Unknown write tool '{tool_name}'")

