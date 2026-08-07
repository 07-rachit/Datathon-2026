import json
import logging
import os
import re
import requests
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from app import models, llm
from app.agent_tools import ALL_TOOLS, READ_TOOLS, WRITE_TOOLS, execute_read_tool, describe_write_action, sanitize_tool_output

logger = logging.getLogger("crimeintel.agent_loop")

MAX_AGENT_STEPS = 6


def run_agent_loop(
    db: Session,
    current_user: models.User,
    question: str,
    context_blocks: List[str],
    session_id: Optional[str] = None,
) -> Tuple[str, Optional[models.PendingAgentAction], List[str]]:
    """
    Executes a multi-step tool-use agent loop:
    1. Automatically executes read tools up to MAX_AGENT_STEPS.
    2. Intercepts write tool requests, generates a PendingAgentAction, and pauses for human confirmation.
    3. Records every tool call into reasoning_steps and audit_logs.
    """
    reasoning_steps: List[str] = []

    # Check if Anthropic API key is configured
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if api_key:
        return _run_anthropic_tool_loop(db, current_user, question, context_blocks, session_id, api_key, reasoning_steps)
    else:
        return _run_local_fallback_agent_loop(db, current_user, question, context_blocks, session_id, reasoning_steps)


# ── Anthropic API Tool-Use Agent Loop ─────────────────────────────────────────

def _run_anthropic_tool_loop(
    db: Session,
    current_user: models.User,
    question: str,
    context_blocks: List[str],
    session_id: Optional[str],
    api_key: str,
    reasoning_steps: List[str],
) -> Tuple[str, Optional[models.PendingAgentAction], List[str]]:
    
    messages = [{"role": "user", "content": question}]
    context_text = "\n\n".join(f"[Source {i+1}] {b}" for i, b in enumerate(context_blocks))
    
    system_prompt = (
        "You are a law-enforcement senior intelligence agent with tool-use capabilities.\n"
        "You can execute read tools to investigate cases, suspects, risk scores, network graphs, and financial trails.\n"
        "You can also request write actions (create_task, assign_case, add_comment), which will be held for explicit human officer confirmation.\n"
        f"INITIAL CONTEXT:\n{context_text}"
    )

    for step in range(MAX_AGENT_STEPS):
        try:
            response = requests.post(
                llm.ANTHROPIC_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": llm.ANTHROPIC_MODEL,
                    "max_tokens": 1200,
                    "system": system_prompt,
                    "tools": ALL_TOOLS,
                    "messages": messages,
                },
                timeout=45,
            )
            response.raise_for_status()
            data = response.json()

            stop_reason = data.get("stop_reason")
            content_blocks = data.get("content", [])

            # Check if model called a tool
            tool_calls = [b for b in content_blocks if b.get("type") == "tool_use"]
            if not tool_calls:
                # Model finished with final text response
                final_text = "\n".join([b["text"] for b in content_blocks if b.get("type") == "text"]).strip()
                return final_text or "Analysis completed.", None, reasoning_steps

            for tool_block in tool_calls:
                tool_name = tool_block["name"]
                tool_args = sanitize_tool_output(tool_block.get("input", {}))

                # Check if it's a WRITE TOOL (requires human confirmation)
                if tool_name in ["create_task", "assign_case", "add_comment"]:
                    desc = describe_write_action(tool_name, tool_args, db)
                    pending_action = models.PendingAgentAction(
                        session_id=session_id,
                        user_id=current_user.id,
                        tool_name=tool_name,
                        arguments=json.dumps(tool_args),
                        description=desc,
                        status="pending",
                    )
                    db.add(pending_action)
                    db.commit()
                    db.refresh(pending_action)

                    step_msg = f"⚠️ Requested write action '{tool_name}' — Paused for human officer confirmation."
                    reasoning_steps.append(step_msg)

                    text_content = "\n".join([b["text"] for b in content_blocks if b.get("type") == "text"]).strip()
                    final_reply = text_content or f"I have prepared the action: {desc}. Please confirm below to execute."
                    return final_reply, pending_action, reasoning_steps

                # READ TOOL (auto-execute)
                step_msg = f"🔧 Executing tool '{tool_name}' with args {json.dumps(tool_args)}"
                reasoning_steps.append(step_msg)
                
                # Log audit entry
                db.add(models.AuditLog(
                    user_id=current_user.id,
                    action="agent_read_tool_executed",
                    detail=f"AI Agent executed tool '{tool_name}'"
                ))
                db.commit()

                tool_result = execute_read_tool(db, tool_name, tool_args)
                messages.append({"role": "assistant", "content": content_blocks})
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_block["id"],
                            "content": json.dumps(tool_result),
                        }
                    ],
                })

        except Exception as e:
            logger.error(f"Error in Anthropic agent loop: {e}")
            break

    # Fallback if max steps reached
    reasoning_steps.append(f"Reached maximum agent reasoning depth ({MAX_AGENT_STEPS} steps).")
    return "The query was too complex to finish within the maximum step limit (6 steps). Partial findings have been recorded in the reasoning log — please break your request into smaller, specific investigative questions.", None, reasoning_steps



def _synthesize_local_rag_answer(question: str, context_blocks: List[str]) -> str:
    """Synthesize a structured intelligence answer directly from RAG context blocks when LLM is unconfigured."""
    if not context_blocks:
        return f"No matching case files, suspect records, or evidence logs were found matching **\"{question.strip()}\"**. Please verify the case ID, phone number, or search terms."

    lines = [
        f"Based on intelligence records retrieved for **\"{question.strip()}\"**:\n",
        "### Key Findings & Matched Evidence:"
    ]

    seen_cases = set()
    for idx, block in enumerate(context_blocks[:6], 1):
        clean_text = block.strip().replace("\n", " ")
        case_match = re.search(r"CR-\d{4}-[\w\d]+", clean_text, re.IGNORECASE)
        case_tag = f" (**{case_match.group(0).upper()}**)" if case_match else ""
        lines.append(f"{idx}.{case_tag} {clean_text}")
        if case_match:
            seen_cases.add(case_match.group(0).upper())

    lines.append("\n### Summary of Findings:")
    if seen_cases:
        lines.append(f"- Relevant intelligence matched across **{len(seen_cases)} case file(s)**: {', '.join(sorted(seen_cases))}.")
    else:
        lines.append("- Intelligence records matched your query terms.")
    lines.append("- Please inspect the **Source Case Citations** panel on the right for full evidence excerpts and direct file navigation.")

    return "\n".join(lines)


# ── Local Heuristic Fallback Agent Loop (When API Key is Absent) ──────────────

def _run_local_fallback_agent_loop(
    db: Session,
    current_user: models.User,
    question: str,
    context_blocks: List[str],
    session_id: Optional[str],
    reasoning_steps: List[str],
) -> Tuple[str, Optional[models.PendingAgentAction], List[str]]:
    """Heuristic intent detection fallback agent loop for offline/demo operation."""
    q_lower = question.lower()
    case_code_match = re.search(r"CR-\d{4}-[\w\d]+", question, re.IGNORECASE)
    case_code = case_code_match.group(0).upper() if case_code_match else "CR-2026-0401"


    # Intent 1: Check for Task Creation intent
    if "create task" in q_lower or "add task" in q_lower:
        title = "Investigate case leads"
        if "cctv" in q_lower:
            title = "Verify CCTV footage from incident scene"
        elif "bank" in q_lower or "receipt" in q_lower:
            title = "Request bank statement and transfer records"

        tool_args = {"case_id": case_code, "title": title}
        desc = describe_write_action("create_task", tool_args, db)

        pending_action = models.PendingAgentAction(
            session_id=session_id,
            user_id=current_user.id,
            tool_name="create_task",
            arguments=json.dumps(tool_args),
            description=desc,
            status="pending",
        )
        db.add(pending_action)
        db.commit()
        db.refresh(pending_action)

        reasoning_steps.append(f"Detected intent to create task on case {case_code}.")
        reasoning_steps.append("⚠️ Generated pending task creation action — waiting for human confirmation.")
        return f"I have prepared a new task for case **{case_code}**: *\"{title}\"*. Please review and confirm the action below.", pending_action, reasoning_steps

    # Intent 2: Check for Case Assignment intent
    if "assign" in q_lower or "claim" in q_lower:
        tool_args = {"case_id": case_code, "officer_user_id": current_user.id, "role_on_case": "Lead Investigator"}
        desc = describe_write_action("assign_case", tool_args, db)

        pending_action = models.PendingAgentAction(
            session_id=session_id,
            user_id=current_user.id,
            tool_name="assign_case",
            arguments=json.dumps(tool_args),
            description=desc,
            status="pending",
        )
        db.add(pending_action)
        db.commit()
        db.refresh(pending_action)

        reasoning_steps.append(f"Detected intent to assign officer to case {case_code}.")
        reasoning_steps.append("⚠️ Generated pending case assignment action — waiting for human confirmation.")
        return f"I have prepared the case assignment for **{case_code}**. Please review and confirm the action below.", pending_action, reasoning_steps

    # Intent 2b: Check for Add Comment intent
    if "add comment" in q_lower or "comment" in q_lower and ("case" in q_lower or case_code_match):
        # Extract comment text heuristically using regex patterns
        comment_text = None
        # Pattern 1: "... saying <TEXT> on case ..."
        m = re.search(r'saying\s+(.+?)\s+on\s+case\s+CR-', question, re.IGNORECASE)
        if m:
            comment_text = m.group(1).strip()
        if not comment_text:
            # Pattern 2: "add comment <TEXT> on case ..."
            m = re.search(r'(?:add\s+)?comment\s+(.+?)\s+on\s+case\s+CR-', question, re.IGNORECASE)
            if m:
                comment_text = m.group(1).strip()
                # Remove leading "saying" if present
                comment_text = re.sub(r'^saying\s+', '', comment_text, flags=re.IGNORECASE).strip()
        if not comment_text:
            # Fallback: strip known prefixes and trailing case code
            comment_text = question
            comment_text = re.sub(r'^.*?(?:add\s+comment|comment)\s*', '', comment_text, flags=re.IGNORECASE).strip()
            comment_text = re.sub(r'^saying\s+', '', comment_text, flags=re.IGNORECASE).strip()
            comment_text = re.sub(r'\s*on\s+case\s+CR-\d{4}-[\w\d]+\s*$', '', comment_text, flags=re.IGNORECASE).strip()
        if not comment_text:
            comment_text = "Follow up required."

        tool_args = {"case_id": case_code, "content": comment_text}
        desc = describe_write_action("add_comment", tool_args, db)

        pending_action = models.PendingAgentAction(
            session_id=session_id,
            user_id=current_user.id,
            tool_name="add_comment",
            arguments=json.dumps(tool_args),
            description=desc,
            status="pending",
        )
        db.add(pending_action)
        db.commit()
        db.refresh(pending_action)

        reasoning_steps.append(f"Detected intent to add comment on case {case_code}.")
        reasoning_steps.append("⚠️ Generated pending add_comment action — waiting for human confirmation.")
        return f"I have prepared a comment for case **{case_code}**: *\"{comment_text}\"*. Please review and confirm the action below.", pending_action, reasoning_steps

    # Intent 3: Read Tool Execution (Risk / Finance / Similar Cases / Timeline)
    if any(k in q_lower for k in ["risk", "offender", "suspect", "accused", "ramesh", "black hat", "who is", "tell me"]):
        reasoning_steps.append("🔧 Executed tool 'get_offender_risk' → Calculated behavioral risk profiles.")
        person = db.query(models.Person).filter(models.Person.name.ilike("%ramesh%")).first()
        person_id = person.id if person else "Black Hat"
        result = execute_read_tool(db, "get_offender_risk", {"person_id": person_id})
        if isinstance(result, dict) and "risk_score" in result:
            reasoning_steps.append(f"Risk Score Result for {result.get('name', 'Suspect')}: {result.get('risk_level', 'HIGH')} (Score: {result.get('risk_score', 82)})")

    if "finance" in q_lower or "money" in q_lower or "trail" in q_lower:
        reasoning_steps.append(f"🔧 Executed tool 'get_financial_trail' for case {case_code}.")
        fin_res = execute_read_tool(db, "get_financial_trail", {"case_id": case_code})
        flagged = fin_res.get("flagged_count", 0) if isinstance(fin_res, dict) else 0
        reasoning_steps.append(f"Financial Trail Result: Found {flagged} flagged transaction(s).")

    if "similar" in q_lower:
        reasoning_steps.append(f"🔧 Executed tool 'get_similar_cases' for case {case_code}.")
        sim_res = execute_read_tool(db, "get_similar_cases", {"case_id": case_code})
        reasoning_steps.append(f"TF-IDF Similarity Search Result: Found {len(sim_res) if isinstance(sim_res, list) else 0} matching cases.")

    # Call standard RAG answer generator for Q&A
    try:
        answer = llm.generate_answer(question, context_blocks, language="en")
    except (llm.LLMNotConfigured, Exception) as e:
        if not isinstance(e, llm.LLMNotConfigured):
            logger.error(f"LLM call failed in fallback agent: {e}")
        answer = _synthesize_local_rag_answer(question, context_blocks)

    return answer, None, reasoning_steps
