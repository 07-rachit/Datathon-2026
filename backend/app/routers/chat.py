import json
import re
from datetime import datetime
from typing import List, Tuple, Dict, Any


from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app import models, schemas, auth, rag, llm, agent_loop, agent_tools
from app.limiter import limiter, RATE_CHAT


router = APIRouter(prefix="/api/chat", tags=["chat"])

CASE_CODE_RE = re.compile(r"\bCR-\d{4}-\d{4}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"\+?\d[\d\- ]{6,}\d")
STOP_WORDS = {"in", "of", "the", "a", "an", "for", "and", "or", "to", "cases", "case", "show", "me", "tell", "about", "find", "all", "list", "what", "where", "how"}

SYNONYMS = {
    "karantka": ["karnataka", "bengaluru"],
    "karnatka": ["karnataka", "bengaluru"],
    "karnataka": ["karnataka", "bengaluru"],
    "bangalore": ["bengaluru"],
    "bengaluru": ["bengaluru", "karnataka"],
    "robbery": ["robbery", "burglary", "theft"],
    "robberies": ["robbery", "burglary", "theft"],
    "theft": ["theft", "burglary", "robbery"],
    "murder": ["murder", "assault"],
    "cyber": ["cyber", "fraud"],
}


def _deep_search(db: Session, query: str, top_k: int = 8) -> Tuple[List[Any], List[str]]:
    """
    Merge four retrieval strategies for a rich, investigator-grade search:
    1. Direct case-ID mentions
    2. Phone-number mentions
    3. TF-IDF vector similarity search
    4. Synonym-expanded keyword search & general recall fallback

    Instruments and records real intermediate execution steps for explainable AI.
    """
    # Always ensure in-memory index is fresh
    if not rag._chunks:
        rag.build_index(db)

    seen_chunk_ids = set()
    combined = []
    reasoning_steps = []

    # Step 1: Direct case-ID mentions
    case_codes = CASE_CODE_RE.findall(query)
    if case_codes:
        for code in case_codes:
            case = db.query(models.Case).filter(models.Case.case_id.ilike(code)).first()
            if case:
                reasoning_steps.append(f"Detected case ID '{code.upper()}' in query — direct case file lookup")
                for chunk in rag.get_case_chunks(case.id):
                    if chunk.chunk_id not in seen_chunk_ids:
                        seen_chunk_ids.add(chunk.chunk_id)
                        combined.append((chunk, 1.0, "direct_case_id"))
            else:
                reasoning_steps.append(f"Case ID '{code}' mentioned but not found in DB")
    else:
        reasoning_steps.append("No explicit case ID detected in query string")

    # Step 2: Phone-number mentions
    phone_matches = PHONE_RE.findall(query)
    found_phones = False
    for phone_match in phone_matches:
        digits = re.sub(r"\D", "", phone_match)
        if len(digits) < 7:
            continue
        persons = db.query(models.Person).filter(models.Person.phone_number.ilike(f"%{digits[-8:]}%")).all()
        if persons:
            found_phones = True
            reasoning_steps.append(f"Matched phone number '{phone_match.strip()}' to {len(persons)} suspect/person records")
            for person in persons:
                for chunk in rag.get_case_chunks(person.case_id):
                    if chunk.chunk_id not in seen_chunk_ids:
                        seen_chunk_ids.add(chunk.chunk_id)
                        combined.append((chunk, 0.95, "phone_match"))
    if not found_phones and not phone_matches:
        reasoning_steps.append("No phone numbers identified in query string")

    # Step 3: Broad TF-IDF similarity search
    # rag.retrieve() returns List[Chunk] (plain objects, not tuples)
    tfidf_hits = rag.retrieve(query, top_k=top_k)
    if tfidf_hits:
        reasoning_steps.append(f"Retrieved {len(tfidf_hits)} related case chunks via TF-IDF vector similarity")
        for chunk in tfidf_hits:
            if chunk.chunk_id not in seen_chunk_ids:
                seen_chunk_ids.add(chunk.chunk_id)
                combined.append((chunk, 0.9, "similarity"))
    else:
        reasoning_steps.append("TF-IDF similarity search yielded 0 matching chunks")

    # Step 4: Synonym-Expanded Keyword Fallback Search
    if len(combined) < 2:
        words = [w.lower() for w in re.findall(r"\w+", query) if w.lower() not in STOP_WORDS and len(w) > 2]
        expanded_words = set(words)
        for w in words:
            if w in SYNONYMS:
                expanded_words.update(SYNONYMS[w])

        if expanded_words:
            reasoning_steps.append(f"Initiated synonym-expanded search for keywords: {', '.join(list(expanded_words)[:5])}")
            for term in expanded_words:
                like_pattern = f"%{term}%"
                matched_cases = db.query(models.Case).filter(
                    or_(
                        models.Case.crime_type.ilike(like_pattern),
                        models.Case.district.ilike(like_pattern),
                        models.Case.title.ilike(like_pattern),
                        models.Case.summary.ilike(like_pattern),
                        models.Case.station_name.ilike(like_pattern),
                    )
                ).limit(5).all()

                for case in matched_cases:
                    for chunk in rag.get_case_chunks(case.id):
                        if chunk.chunk_id not in seen_chunk_ids:
                            seen_chunk_ids.add(chunk.chunk_id)
                            combined.append((chunk, 0.85, "keyword_match"))

    # Step 5: General Recall Fallback if still empty
    if len(combined) == 0:
        reasoning_steps.append("Executing general recall fallback: pulling top active cases for overview context")
        recent_cases = db.query(models.Case).order_by(models.Case.incident_date.desc()).limit(4).all()
        for case in recent_cases:
            for chunk in rag.get_case_chunks(case.id):
                if chunk.chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk.chunk_id)
                    combined.append((chunk, 0.5, "general_recall"))

    combined.sort(key=lambda x: x[1], reverse=True)
    results = combined[:top_k]
    reasoning_steps.append(f"Compiled final RAG context from {len(results)} distinct evidence/case chunks")
    return results, reasoning_steps


@router.post("/reindex")
def reindex(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst")),
):
    """Rebuild the RAG search index from current case data."""
    count = rag.build_index(db)
    return {"indexed_chunks": count}


@router.post("/sessions", response_model=schemas.ChatSessionOut)
def create_session(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    session = models.ChatSession(user_id=current_user.id, title="New conversation")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=list[schemas.ChatSessionOut])
def list_sessions(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == current_user.id)
        .order_by(models.ChatSession.created_at.desc())
        .all()
    )


@router.get("/sessions/{session_id}/messages", response_model=list[schemas.ChatMessageOut])
def get_messages(
    session_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)
):
    session = _get_owned_session(db, session_id, current_user)
    return (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )


@router.post("/sessions/{session_id}/messages", response_model=schemas.ChatAnswer)
@limiter.limit(RATE_CHAT)
def send_message(
    request: Request,
    session_id: str,
    payload: schemas.ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    session = _get_owned_session(db, session_id, current_user)

    user_msg = models.ChatMessage(session_id=session.id, role="user", content=payload.content)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Auto-title the session from the first question
    if session.title == "New conversation":
        session.title = payload.content[:60]
        db.commit()

    # Rebuild/lazily ensure RAG index is populated

    rag.build_index(db)
    hits, steps = _deep_search(db, payload.content, top_k=8)

    sources = [
        {
            "case_id": chunk.case_id,
            "case_code": chunk.case_code,
            "section": chunk.section,
            "snippet": chunk.text[:400],
            "score": round(score, 3),
            "match_type": match_type,
        }
        for chunk, score, match_type in hits
    ]

    context_snippets = [s["snippet"] for s in sources]

    # Sprint 8: Unified AI Agent Tool Loop
    answer_text, pending_action, agent_steps = agent_loop.run_agent_loop(
        db=db,
        current_user=current_user,
        question=payload.content,
        context_blocks=context_snippets,
        session_id=session.id,
    )

    combined_steps = steps + agent_steps

    assistant_msg = models.ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer_text,
        sources=json.dumps(sources),
    )
    db.add(assistant_msg)

    log = models.AuditLog(user_id=current_user.id, action="chat_query", detail=payload.content[:200])
    db.add(log)
    db.commit()
    db.refresh(assistant_msg)

    user_out = schemas.ChatMessageOut.model_validate(user_msg)
    asst_out = schemas.ChatMessageOut.model_validate(assistant_msg)
    asst_out.reasoning_steps = combined_steps

    pending_out = None
    if pending_action:
        pending_out = schemas.PendingActionOut(
            id=pending_action.id,
            session_id=pending_action.session_id,
            tool_name=pending_action.tool_name,
            arguments=json.loads(pending_action.arguments),
            description=pending_action.description,
            status=pending_action.status,
            created_at=pending_action.created_at,
        )

    return schemas.ChatAnswer(
        session_id=session.id,
        user_message=user_out,
        assistant_message=asst_out,
        pending_action=pending_out,
    )


# ─── SPRINT 8: PENDING ACTION CONFIRM / CANCEL ENDPOINTS ──────────────────────

@router.post("/assistant/actions/{action_id}/confirm", response_model=schemas.ActionConfirmResponse)
@router.post("/actions/{action_id}/confirm", response_model=schemas.ActionConfirmResponse)
def confirm_agent_action(
    action_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("admin", "analyst", "investigator")),
):
    """
    User confirms a pending write action. Re-enforces RBAC using confirming user's role and checks 24h expiry.
    """
    action = db.query(models.PendingAgentAction).filter(models.PendingAgentAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Pending action not found")

    # Check 24-hour expiry
    if action.status == "pending" and action.created_at:
        age_seconds = (datetime.utcnow() - action.created_at).total_seconds()
        if age_seconds > 24 * 3600:
            action.status = "expired"
            db.commit()
            raise HTTPException(status_code=400, detail="Action has expired (older than 24 hours) and can no longer be executed.")

    if action.status != "pending":
        raise HTTPException(status_code=400, detail=f"Action is already {action.status}")

    try:
        args = json.loads(action.arguments)
        result = agent_tools.execute_write_tool(db, current_user, action.tool_name, args)

        action.status = "executed"
        action.executed_at = datetime.utcnow()
        db.commit()

        return schemas.ActionConfirmResponse(
            action_id=action.id,
            status="executed",
            message=result.get("message", "Action executed successfully"),
            result=result,
        )
    except HTTPException:
        action.status = "failed"
        db.commit()
        raise
    except Exception as e:
        action.status = "failed"
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/assistant/actions/{action_id}/cancel", response_model=schemas.ActionConfirmResponse)
@router.post("/actions/{action_id}/cancel", response_model=schemas.ActionConfirmResponse)
def cancel_agent_action(
    action_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    User cancels a pending write action.
    """
    action = db.query(models.PendingAgentAction).filter(models.PendingAgentAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Pending action not found")

    # Check 24-hour expiry
    if action.status == "pending" and action.created_at:
        age_seconds = (datetime.utcnow() - action.created_at).total_seconds()
        if age_seconds > 24 * 3600:
            action.status = "expired"
            db.commit()
            raise HTTPException(status_code=400, detail="Action has expired (older than 24 hours).")

    if action.status != "pending":
        raise HTTPException(status_code=400, detail=f"Action is already {action.status}")

    action.status = "cancelled"
    db.commit()

    return schemas.ActionConfirmResponse(
        action_id=action.id,
        status="cancelled",
        message="Action cancelled by user.",
    )



def _get_owned_session(db: Session, session_id: str, user: models.User) -> models.ChatSession:
    session = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session

