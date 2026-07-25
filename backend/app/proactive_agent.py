import logging
import asyncio
from sqlalchemy.orm import Session
from app import models
from app.agent_tools import execute_read_tool, sanitize_tool_output
from app.websocket import broadcast_notification_to_roles

logger = logging.getLogger("crimeintel.proactive_agent")


def run_proactive_case_analysis_sync(db: Session, case_id: str):
    """
    Synchronous worker logic for proactive background analysis.
    Gather case context, similar cases, offender risk, network links, and financial trail,
    then post an AI-authored comment and dispatch WebSocket alerts.
    """
    case = db.query(models.Case).filter(
        (models.Case.id == case_id) | (models.Case.case_id == case_id)
    ).first()

    if not case:
        logger.warning(f"Proactive analysis skipped: Case '{case_id}' not found.")
        return

    logger.info(f"Starting proactive AI case analysis for {case.case_id} ({case.severity.value.upper()})...")

    # 1. Gather Similar Cases
    similar = execute_read_tool(db, "get_similar_cases", {"case_id": case.id})
    sim_summary = ""
    if isinstance(similar, list) and len(similar) > 0:
        sim_codes = [s["case_id"] for s in similar[:2]]
        sim_summary = f"Identified {len(similar)} pattern-matched incidents (e.g. {', '.join(sim_codes)})."

    # 2. Gather Linked Suspect Risk Scores
    linked_suspects = [p for p in case.persons if p.role_in_case in ["suspect", "accused", "co-accused"]]
    risk_findings = []
    for s in linked_suspects:
        rp = execute_read_tool(db, "get_offender_risk", {"person_id": s.id})
        if isinstance(rp, dict) and "risk_score" in rp:
            risk_findings.append(f"{s.name}: {rp.get('risk_level', 'HIGH')} ({rp.get('risk_score')} pts)")

    risk_text = f"Suspect Risk Evaluation: {'; '.join(risk_findings)}." if risk_findings else "No high-risk repeat offenders linked directly in initial FIR."

    # 3. Gather Financial Trail
    fin_trail = execute_read_tool(db, "get_financial_trail", {"case_id": case.id})
    flagged_tx = fin_trail.get("flagged_count", 0) if isinstance(fin_trail, dict) else 0
    fin_summary = f"Financial Audit: Found {flagged_tx} flagged transactions requiring section 91 CrPC freezing notices." if flagged_tx > 0 else "Financial Audit: No flagged monetary transfers detected."

    # 4. Synthesize 3-Paragraph AI Analysis Report
    ai_comment_text = (
        f"🤖 AI PROACTIVE INVESTIGATIVE ANALYSIS & RISK ASSESSMENT\n\n"
        f"Incident Overview: Case {case.case_id} registered at {case.station_name} ({case.district}) classified as {case.severity.value.upper()} severity. "
        f"Summary: {case.summary or 'Initial incident record lodged.'}\n\n"
        f"Pattern Match & Offender Intelligence: {sim_summary} {risk_text}\n\n"
        f"Suggested Investigative Leads:\n"
        f"1. {fin_summary}\n"
        f"2. Issue statutory evidence preservation notices for CCTV footage within 500m radius of {case.station_name}.\n"
        f"3. Cross-examine linked co-accused phone numbers against master call detail records (CDR)."
    )

    # 5. Post AI-Authored Comment
    ai_comment = models.CaseComment(
        case_id=case.id,
        author_user_id=None,
        content=ai_comment_text,
        is_ai_authored=True,
    )
    db.add(ai_comment)

    # 6. Audit Log
    db.add(models.AuditLog(
        user_id=None,
        action="proactive_ai_analysis",
        detail=f"Proactive AI agent completed automated investigation report for case {case.case_id}"
    ))

    db.commit()
    logger.info(f"Successfully posted proactive AI analysis comment on case {case.case_id}.")


async def trigger_proactive_case_analysis_task(case_id: str, db_session_factory):
    """Async wrapper task for background execution."""
    await asyncio.sleep(0.5)  # allow main transaction to settle
    db = db_session_factory()
    try:
        run_proactive_case_analysis_sync(db, case_id)
        # Dispatch WebSocket notification
        case = db.query(models.Case).filter(models.Case.id == case_id).first()
        if case:
            await broadcast_notification_to_roles(
                db=db,
                roles=[models.RoleEnum.investigator, models.RoleEnum.analyst, models.RoleEnum.admin],
                notification_type="ai_case_analysis",
                title=f"🤖 AI Analysis Complete: {case.case_id}",
                message=f"Proactive AI analysis and investigative leads generated for case {case.title}.",
                related_case_id=case.id,
            )
    except Exception as e:
        logger.error(f"Error running proactive case analysis for {case_id}: {e}")
    finally:
        db.close()
