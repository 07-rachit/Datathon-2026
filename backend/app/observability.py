"""
Centralized Observability Instrumentation Module.

Records agent executions, tool invocations, latency breakdowns, decisions,
prompts, outputs, and structured logs with sensitive data scrubbing.
"""
import json
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app import models
from app.logger import sanitize_data, get_logger

logger = get_logger("observability")


def _sanitize_prompt_text(text: Optional[str]) -> Optional[str]:
    if not text or not isinstance(text, str):
        return text
    import re
    cleaned = text
    cleaned = re.sub(r'(password|secret|api_key|token|auth)\s*[:=]\s*\S+', r'\1=[REDACTED]', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'(password|secret|api_key|token|auth)\s+\S+', r'\1 [REDACTED]', cleaned, flags=re.IGNORECASE)
    return cleaned


def start_agent_run(
    db: Session,
    agent_name: str,
    user_id: Optional[str] = None,
    user_name: Optional[str] = None,
    user_role: Optional[str] = None,
    input_prompt: Optional[str] = None,
    parent_run_id: Optional[str] = None,
    session_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    execution_type: str = "agent_run",
    trigger_source: str = "user_chat",
    model_name: Optional[str] = "gemini-1.5-pro",
    metadata: Optional[Dict[str, Any]] = None,
) -> models.AgentRun:
    """Create and start a new AgentRun record in DB."""
    sanitized_prompt = _sanitize_prompt_text(input_prompt)
    sanitized_meta = sanitize_data(metadata or {})

    run = models.AgentRun(
        id=str(uuid.uuid4()),
        parent_run_id=parent_run_id,
        session_id=session_id,
        conversation_id=conversation_id,
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        agent_name=agent_name,
        execution_type=execution_type,
        trigger_source=trigger_source,
        input_prompt=str(sanitized_prompt) if sanitized_prompt else None,
        status="RUNNING",
        created_at=datetime.utcnow(),
        started_at=datetime.utcnow(),
        model_name=model_name,
        logs_json=json.dumps([f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] AgentRun '{agent_name}' initiated."]),
        metadata_json=json.dumps(sanitized_meta) if sanitized_meta else None,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def log_tool_call(
    db: Session,
    run_id: str,
    tool_name: str,
    input_params: Optional[Any] = None,
    output_result: Optional[Any] = None,
    duration_ms: Optional[float] = None,
    status: str = "SUCCESS",
    error_message: Optional[str] = None,
) -> models.ToolCall:
    """Record an individual tool invocation linked to an AgentRun."""
    sanitized_in = sanitize_data(input_params or {})
    sanitized_out = sanitize_data(output_result or {})

    tool_call = models.ToolCall(
        id=str(uuid.uuid4()),
        run_id=run_id,
        tool_name=tool_name,
        input_params_json=json.dumps(sanitized_in) if sanitized_in else None,
        output_result_json=json.dumps(sanitized_out) if sanitized_out else None,
        status=status,
        duration_ms=duration_ms,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
        error_message=error_message,
    )
    db.add(tool_call)
    
    # Append to agent run logs
    run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    if run:
        logs = []
        if run.logs_json:
            try:
                logs = json.loads(run.logs_json)
            except Exception:
                logs = [run.logs_json]
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        logs.append(f"[{ts}] Tool '{tool_name}' executed in {duration_ms or 0}ms with status {status}")
        run.logs_json = json.dumps(logs)
        
        # Accumulate tool execution time
        run.tool_execution_time_ms = (run.tool_execution_time_ms or 0.0) + (duration_ms or 0.0)

    db.commit()
    db.refresh(tool_call)
    return tool_call


def finish_agent_run(
    db: Session,
    run_id: str,
    output_summary: Optional[str] = None,
    decision: Optional[str] = None,
    confidence_score: Optional[float] = None,
    status: str = "COMPLETED",
    total_latency_ms: Optional[float] = None,
    queue_time_ms: Optional[float] = None,
    processing_time_ms: Optional[float] = None,
    model_inference_time_ms: Optional[float] = None,
    tokens_used: Optional[int] = None,
    error_details: Optional[Any] = None,
) -> Optional[models.AgentRun]:
    """Finalize an AgentRun record with summary outputs and status."""
    run = db.query(models.AgentRun).filter(models.AgentRun.id == run_id).first()
    if not run:
        return None

    sanitized_out = sanitize_data(output_summary) if output_summary else None
    if isinstance(sanitized_out, (dict, list)):
        sanitized_out = json.dumps(sanitized_out)

    run.status = status
    run.completed_at = datetime.utcnow()
    run.output_summary = str(sanitized_out) if sanitized_out else None
    run.decision = decision
    run.confidence_score = confidence_score
    run.total_latency_ms = total_latency_ms
    run.queue_time_ms = queue_time_ms
    run.processing_time_ms = processing_time_ms
    run.model_inference_time_ms = model_inference_time_ms
    run.tokens_used = tokens_used

    if error_details:
        run.error_details = json.dumps(sanitize_data(error_details))

    logs = []
    if run.logs_json:
        try:
            logs = json.loads(run.logs_json)
        except Exception:
            logs = [run.logs_json]
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    logs.append(f"[{ts}] AgentRun finished with status {status} (Latency: {total_latency_ms or 0}ms)")
    run.logs_json = json.dumps(logs)

    db.commit()
    db.refresh(run)
    return run
