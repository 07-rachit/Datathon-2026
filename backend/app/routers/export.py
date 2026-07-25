import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.database import get_db
from app import models, auth

router = APIRouter(prefix="/api/export", tags=["export"])


def _build_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", fontSize=20, leading=24, textColor=colors.HexColor("#0B0F17"),
        fontName="Helvetica-Bold", spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="ReportSub", fontSize=9, textColor=colors.HexColor("#7C8AA3"),
        fontName="Helvetica", spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        name="SectionHead", fontSize=12, textColor=colors.HexColor("#0B0F17"),
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Body", fontSize=10, leading=14, textColor=colors.HexColor("#232323"),
    ))
    return styles


@router.get("/cases/{case_id}/report")
def export_case_report(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    styles = _build_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
    )
    story = []

    story.append(Paragraph(f"Case Report &mdash; {case.case_id}", styles["ReportTitle"]))
    story.append(Paragraph(
        f"Generated {datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')} &middot; "
        f"Requested by {current_user.name} ({current_user.role.value})",
        styles["ReportSub"],
    ))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#D9D9D9")))

    meta_rows = [
        ["Title", case.title],
        ["Crime Type", case.crime_type],
        ["District", case.district],
        ["Station", case.station_name],
        ["Status", case.status.value.replace("_", " ").title()],
        ["Severity", case.severity.value.title()],
        ["Incident Date", case.incident_date.strftime("%d %b %Y")],
    ]
    meta_table = Table(meta_rows, colWidths=[100, 350])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#EEEEEE")),
    ]))
    story.append(Spacer(1, 10))
    story.append(meta_table)

    story.append(Paragraph("Summary", styles["SectionHead"]))
    story.append(Paragraph(case.summary or "No summary recorded for this case.", styles["Body"]))

    if case.persons:
        story.append(Paragraph("Persons of Interest", styles["SectionHead"]))
        rows = [["Name", "Role", "Phone"]] + [
            [p.name, p.role_in_case or "-", p.phone_number or "-"] for p in case.persons
        ]
        t = Table(rows, colWidths=[180, 130, 140])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B0F17")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

    if case.evidence:
        story.append(Paragraph("Evidence Log", styles["SectionHead"]))
        rows = [["Description", "Integrity Hash"]] + [
            [e.description, e.evidence_hash[:24] + "..."] for e in case.evidence
        ]
        t = Table(rows, colWidths=[280, 170])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B0F17")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

    doc.build(story)
    buffer.seek(0)

    log = models.AuditLog(
        user_id=current_user.id, action="export_case_report", detail=f"Exported PDF for {case.case_id}"
    )
    db.add(log)
    db.commit()

    filename = f"{case.case_id}_report.pdf"
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/chat/{session_id}/report")
def export_chat_report(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    session = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.id == session_id, models.ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )

    styles = _build_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=18 * mm, rightMargin=18 * mm,
    )
    story = []

    story.append(Paragraph("Case Assistant &mdash; Conversation Transcript", styles["ReportTitle"]))
    story.append(Paragraph(
        f"Session: {session.title} &middot; Generated {datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')} "
        f"&middot; User: {current_user.name} ({current_user.role.value})",
        styles["ReportSub"],
    ))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#D9D9D9")))
    story.append(Spacer(1, 10))

    speaker_style = ParagraphStyle(
        name="Speaker", parent=styles["Body"], fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=2,
        textColor=colors.HexColor("#0B0F17"),
    )
    source_style = ParagraphStyle(
        name="SourceNote", parent=styles["Body"], fontSize=8, textColor=colors.HexColor("#888888"),
        leftIndent=10, spaceAfter=8,
    )

    for msg in messages:
        speaker = "Investigator" if msg.role == "user" else "AI Case Assistant"
        story.append(Paragraph(speaker, speaker_style))
        story.append(Paragraph(msg.content.replace("\n", "<br/>"), styles["Body"]))

        if msg.sources:
            try:
                sources = json.loads(msg.sources)
                if sources:
                    ref_line = "Sources: " + ", ".join(
                        f"{s['case_code']} ({s.get('match_type', 'similarity')}, "
                        f"{round(s['score'] * 100)}% match)"
                        for s in sources
                    )
                    story.append(Paragraph(ref_line, source_style))
            except (json.JSONDecodeError, KeyError):
                pass

    if not messages:
        story.append(Paragraph("This conversation has no messages yet.", styles["Body"]))

    doc.build(story)
    buffer.seek(0)

    log = models.AuditLog(
        user_id=current_user.id, action="export_chat_report", detail=f"Exported chat transcript {session.id}"
    )
    db.add(log)
    db.commit()

    filename = f"chat_{session.id[:8]}_transcript.pdf"
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
