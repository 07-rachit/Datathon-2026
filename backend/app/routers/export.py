"""
Security Case & Chat Export Router.

Provides reusable, multi-format report generation for Security Cases in PDF, HTML,
and CSV formats. Populates all captured project metadata, investigation labels,
investigator notes, statutory FIR details, evidence items, and activity audit timeline.
"""
import io
import csv
import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
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
from app import models, auth, risk_gates
from app.errors import ResourceNotFoundError, AuthorizationError, ValidationError

router = APIRouter(prefix="/api/export", tags=["export"])


# ── PDF Style Helpers ────────────────────────────────────────────────────────

def _build_pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportHeader", fontSize=22, leading=26, textColor=colors.HexColor("#0B0F17"),
        fontName="Helvetica-Bold", spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="ReportSubHeader", fontSize=9, leading=13, textColor=colors.HexColor("#64748B"),
        fontName="Helvetica", spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", fontSize=13, leading=16, textColor=colors.HexColor("#0F172A"),
        fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="BodyTextCustom", fontSize=10, leading=14, textColor=colors.HexColor("#1E293B"),
    ))
    styles.add(ParagraphStyle(
        name="NoteBoxText", fontSize=9.5, leading=13.5, textColor=colors.HexColor("#0F172A"),
        fontName="Helvetica-Oblique",
    ))
    return styles


def _generate_case_pdf(case: models.Case, current_user: models.User) -> io.BytesIO:
    """
    Generates a professionally formatted A4 PDF security case briefing document.
    Populates case metadata, investigation label callout, evidence log, and audit timeline.
    """
    styles = _build_pdf_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm, leftMargin=15 * mm, rightMargin=15 * mm,
    )
    story = []

    # Title & Subtitle
    story.append(Paragraph(f"Security Case Report &mdash; {case.case_id}", styles["ReportHeader"]))
    sub_info = (
        f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} &middot; "
        f"Requested by <b>{current_user.name}</b> ({current_user.role.value.upper()}) &middot; "
        f"Platform: CrimeIntel Security System"
    )
    story.append(Paragraph(sub_info, styles["ReportSubHeader"]))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#CBD5E1"), spaceAfter=10))

    # Case Metadata Table
    label_val = case.investigation_label.value if hasattr(case.investigation_label, "value") else str(case.investigation_label or "Unreviewed")
    rev_by = case.reviewer_name or "Not Reviewed"
    rev_at = case.review_timestamp.strftime("%Y-%m-%d %H:%M UTC") if case.review_timestamp else "N/A"

    meta_rows = [
        ["Case Title", case.title, "Investigation Label", label_val],
        ["Crime Category", case.crime_type, "Assigned Reviewer", rev_by],
        ["District", case.district, "Review Timestamp", rev_at],
        ["Station Name", case.station_name, "Incident Date", case.incident_date.strftime("%Y-%m-%d")],
        ["Case Status", case.status.value.replace("_", " ").title(), "Severity Level", case.severity.value.upper()],
    ]
    meta_table = Table(meta_rows, colWidths=[90, 170, 110, 160])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(meta_table)

    # Incident Summary
    story.append(Paragraph("Incident Summary & Context", styles["SectionHeading"]))
    story.append(Paragraph(case.summary or "No incident summary recorded for this security case.", styles["BodyTextCustom"]))

    # Investigator Rationale Note
    story.append(Paragraph("Investigator Rationale & Evidence Note", styles["SectionHeading"]))
    note_text = case.investigator_note or "No manual investigator note has been attached to this case yet."
    note_box_data = [[Paragraph(f"<b>Reviewer Note:</b> {note_text}", styles["NoteBoxText"])]]
    note_table = Table(note_box_data, colWidths=[530])
    note_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#F59E0B")),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(note_table)

    # Statutory & Legal Findings (if FIR details present)
    if case.fir_details:
        fir = case.fir_details
        story.append(Paragraph("Statutory FIR & Legal Findings", styles["SectionHeading"]))
        fir_rows = [
            ["FIR Crime No", fir.crime_no or "Not Available"],
            ["Registered Date", fir.crime_registered_date.strftime("%Y-%m-%d %H:%M") if fir.crime_registered_date else "N/A"],
            ["Act & Sections", ", ".join([a.section.section_number for a in case.act_sections]) if case.act_sections else "Pending Chargesheet"],
        ]
        fir_table = Table(fir_rows, colWidths=[120, 410])
        fir_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(fir_table)

    # Persons of Interest
    story.append(Paragraph(f"Persons of Interest & Suspect Roster ({len(case.persons)})", styles["SectionHeading"]))
    if case.persons:
        p_rows = [["Name", "Role in Incident", "Contact Phone"]] + [
            [p.name, p.role_in_case or "Subject", p.phone_number or "Not Available"] for p in case.persons
        ]
        p_table = Table(p_rows, colWidths=[200, 180, 150])
        p_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(p_table)
    else:
        story.append(Paragraph("No persons of interest associated with this case file.", styles["BodyTextCustom"]))

    # Evidence Items Log
    story.append(Paragraph(f"Evidence Inventory ({len(case.evidence)})", styles["SectionHeading"]))
    if case.evidence:
        e_rows = [["Description", "Cryptographic Hash / File Path"]] + [
            [e.description, (e.evidence_hash[:32] + "...") if e.evidence_hash else "Not Available"] for e in case.evidence
        ]
        e_table = Table(e_rows, colWidths=[300, 230])
        e_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(e_table)
    else:
        story.append(Paragraph("No evidence records attached to this case file.", styles["BodyTextCustom"]))

    # Investigation History Audit Log
    story.append(Paragraph("Investigation Audit History Log", styles["SectionHeading"]))
    if case.investigation_history:
        h_rows = [["Timestamp", "Previous Label", "New Label", "Reviewing Officer", "Note Excerpt"]]
        for h in case.investigation_history[:5]:
            note_sub = (h.investigator_note[:45] + "...") if len(h.investigator_note) > 45 else h.investigator_note
            h_rows.append([
                h.created_at.strftime("%Y-%m-%d %H:%M"),
                h.previous_label or "Unreviewed",
                h.new_label,
                h.reviewer_name,
                note_sub,
            ])
        h_table = Table(h_rows, colWidths=[90, 85, 85, 110, 160])
        h_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(h_table)
    else:
        story.append(Paragraph("No prior investigation history entries recorded.", styles["BodyTextCustom"]))

    doc.build(story)
    buffer.seek(0)
    return buffer


def _generate_case_html(case: models.Case, current_user: models.User) -> str:
    label_val = case.investigation_label.value if hasattr(case.investigation_label, "value") else str(case.investigation_label or "Unreviewed")
    rev_by = case.reviewer_name or "Not Reviewed"
    rev_at = case.review_timestamp.strftime("%Y-%m-%d %H:%M UTC") if case.review_timestamp else "Not Available"
    incident_dt = case.incident_date.strftime("%Y-%m-%d") if case.incident_date else "Not Available"

    badge_color = "#64748b"
    if label_val == "Suspected":
      badge_color = "#d97706"
    elif label_val == "Verified":
      badge_color = "#059669"
    elif label_val == "Needs Review":
      badge_color = "#4f46e5"

    persons_html = "".join([
        f"<tr><td>{p.name}</td><td>{p.role_in_case or 'Subject'}</td><td>{p.phone_number or 'Not Available'}</td></tr>"
        for p in case.persons
    ]) if case.persons else "<tr><td colSpan='3' style='color:#64748b;'>No persons of interest associated with this case.</td></tr>"

    evidence_html = "".join([
        f"<tr><td>{e.description}</td><td><code>{e.evidence_hash or 'Not Available'}</code></td></tr>"
        for e in case.evidence
    ]) if case.evidence else "<tr><td colSpan='2' style='color:#64748b;'>No evidence recorded.</td></tr>"

    history_html = "".join([
        f"<tr><td>{h.created_at.strftime('%Y-%m-%d %H:%M')}</td><td>{h.previous_label or 'Unreviewed'}</td><td><strong>{h.new_label}</strong></td><td>{h.reviewer_name}</td><td>{h.investigator_note}</td></tr>"
        for h in case.investigation_history
    ]) if case.investigation_history else "<tr><td colSpan='5' style='color:#64748b;'>No prior investigation audit history entries.</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Security Case Report - {case.case_id}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0b0f17; color: #f8fafc; margin: 0; padding: 40px; line-height: 1.6; }}
        .container {{ max-width: 960px; margin: 0 auto; background: #141b2d; border: 1px solid #1e293b; border-radius: 10px; padding: 36px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }}
        .header {{ border-bottom: 2px solid #334155; padding-bottom: 20px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; }}
        .title {{ font-size: 26px; font-weight: 700; color: #3fd6c1; margin: 0 0 6px 0; }}
        .meta-sub {{ font-size: 13px; color: #94a3b8; margin: 0; }}
        .badge {{ display: inline-block; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 700; color: #ffffff; background: {badge_color}; }}
        .section-title {{ font-size: 16px; font-weight: 700; color: #f8fafc; border-bottom: 1px solid #334155; padding-bottom: 6px; margin: 28px 0 14px 0; text-transform: uppercase; letter-spacing: 0.05em; }}
        .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 20px; }}
        .card {{ background: #0f172a; border: 1px solid #1e293b; border-radius: 6px; padding: 14px; }}
        .card-label {{ font-size: 11px; text-transform: uppercase; color: #64748b; font-weight: 600; margin-bottom: 4px; }}
        .card-val {{ font-size: 14px; color: #f1f5f9; font-weight: 600; }}
        .note-box {{ background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.4); color: #fbbf24; border-radius: 6px; padding: 16px; margin-top: 10px; font-size: 14px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }}
        th, td {{ border: 1px solid #334155; padding: 10px 12px; text-align: left; }}
        th {{ background: #0f172a; color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 11px; }}
        tr:nth-child(even) {{ background: rgba(255,255,255,0.02); }}
        @media print {{
            body {{ background: #ffffff; color: #000000; padding: 0; }}
            .container {{ border: none; box-shadow: none; padding: 0; background: #ffffff; color: #000000; }}
            .title {{ color: #000000; }}
            .card {{ background: #f8fafc; border-color: #cbd5e1; color: #000000; }}
            .card-val {{ color: #000000; }}
            th {{ background: #e2e8f0; color: #000000; }}
            td, th {{ border-color: #cbd5e1; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 class="title">Security Case Report &mdash; {case.case_id}</h1>
                <p class="meta-sub">
                    Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} &middot; 
                    User: {current_user.name} ({current_user.role.value.upper()}) &middot; 
                    Platform: CrimeIntel Security Management
                </p>
            </div>
            <div class="badge">{label_val}</div>
        </div>

        <div class="grid">
            <div class="card"><div class="card-label">Case Title</div><div class="card-val">{case.title}</div></div>
            <div class="card"><div class="card-label">Crime Category</div><div class="card-val">{case.crime_type}</div></div>
            <div class="card"><div class="card-label">District</div><div class="card-val">{case.district}</div></div>
            <div class="card"><div class="card-label">Station Name</div><div class="card-val">{case.station_name}</div></div>
            <div class="card"><div class="card-label">Case Status</div><div class="card-val">{case.status.value.replace("_", " ").title()}</div></div>
            <div class="card"><div class="card-label">Severity Level</div><div class="card-val">{case.severity.value.upper()}</div></div>
            <div class="card"><div class="card-label">Assigned Reviewer</div><div class="card-val">{rev_by}</div></div>
            <div class="card"><div class="card-label">Review Timestamp</div><div class="card-val">{rev_at}</div></div>
        </div>

        <div class="section-title">Incident Summary</div>
        <div class="card"><div class="card-val" style="font-weight:400;">{case.summary or "Not Available"}</div></div>

        <div class="section-title">Investigator Reasoning Note</div>
        <div class="note-box">
            <strong>Reviewer Note:</strong> {case.investigator_note or "No investigator reasoning notes recorded yet."}
        </div>

        <div class="section-title">Persons of Interest ({len(case.persons)})</div>
        <table>
            <thead><tr><th>Name</th><th>Role</th><th>Phone</th></tr></thead>
            <tbody>{persons_html}</tbody>
        </table>

        <div class="section-title">Evidence Inventory ({len(case.evidence)})</div>
        <table>
            <thead><tr><th>Description</th><th>Hash / File Identifier</th></tr></thead>
            <tbody>{evidence_html}</tbody>
        </table>

        <div class="section-title">Investigation Audit History</div>
        <table>
            <thead><tr><th>Timestamp</th><th>Previous Label</th><th>New Label</th><th>Reviewer</th><th>Note</th></tr></thead>
            <tbody>{history_html}</tbody>
        </table>
    </div>
</body>
</html>
"""
    return html


def _generate_case_csv(case: models.Case, current_user: models.User) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    label_val = case.investigation_label.value if hasattr(case.investigation_label, "value") else str(case.investigation_label or "Unreviewed")

    writer.writerow(["=== SECURITY CASE OVERVIEW METADATA ==="])
    writer.writerow(["Field Name", "Field Value"])
    writer.writerow(["Case ID", case.case_id])
    writer.writerow(["Title", case.title])
    writer.writerow(["Crime Type", case.crime_type])
    writer.writerow(["District", case.district])
    writer.writerow(["Station Name", case.station_name])
    writer.writerow(["Status", case.status.value])
    writer.writerow(["Severity", case.severity.value])
    writer.writerow(["Incident Date", case.incident_date.strftime("%Y-%m-%d") if case.incident_date else "Not Available"])
    writer.writerow(["Investigation Label", label_val])
    writer.writerow(["Reviewer Name", case.reviewer_name or "Not Available"])
    writer.writerow(["Reviewer ID", case.reviewer_id or "Not Available"])
    writer.writerow(["Review Timestamp", case.review_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if case.review_timestamp else "Not Available"])
    writer.writerow(["Investigator Note", case.investigator_note or "Not Available"])
    writer.writerow(["Summary", case.summary or "Not Available"])
    writer.writerow(["Exported By User", f"{current_user.name} ({current_user.email})"])
    writer.writerow(["Export Timestamp", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")])
    writer.writerow([])

    writer.writerow(["=== PERSONS OF INTEREST ROSTER ==="])
    writer.writerow(["Person ID", "Name", "Role in Case", "Phone Number"])
    if case.persons:
        for p in case.persons:
            writer.writerow([p.id, p.name, p.role_in_case or "Not Available", p.phone_number or "Not Available"])
    else:
        writer.writerow(["N/A", "No persons recorded", "N/A", "N/A"])
    writer.writerow([])

    writer.writerow(["=== EVIDENCE INVENTORY LOG ==="])
    writer.writerow(["Evidence ID", "Description", "Cryptographic Hash", "Date Created"])
    if case.evidence:
        for e in case.evidence:
            writer.writerow([e.id, e.description, e.evidence_hash or "Not Available", e.created_at.strftime("%Y-%m-%d") if e.created_at else "N/A"])
    else:
        writer.writerow(["N/A", "No evidence recorded", "N/A", "N/A"])
    writer.writerow([])

    writer.writerow(["=== INVESTIGATION HISTORY AUDIT LOG ==="])
    writer.writerow(["History ID", "Timestamp", "Previous Label", "New Label", "Reviewer Name", "Reviewer ID", "Investigator Note"])
    if case.investigation_history:
        for h in case.investigation_history:
            writer.writerow([
                h.id,
                h.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                h.previous_label or "Unreviewed",
                h.new_label,
                h.reviewer_name,
                h.reviewer_id,
                h.investigator_note,
            ])
    else:
        writer.writerow(["N/A", "No prior history", "N/A", "N/A", "N/A", "N/A", "N/A"])

    return output.getvalue()


# ── Report Export Endpoints ──────────────────────────────────────────────────

@router.get("/cases/{case_id}/report")
@router.get("/cases/{case_id}/report/{fmt_path}")
def export_security_case_report(
    case_id: str,
    fmt_path: Optional[str] = None,
    format: Optional[str] = Query(None, description="Export format: pdf, html, or csv"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    selected_format = (fmt_path or format or "pdf").lower().strip()
    case = risk_gates.check_report_export_gate(db, case_id, selected_format, current_user)

    now_str = datetime.utcnow().strftime("%Y%m%d_%H%M")
    filename = f"SecurityCase_{case.case_id}_{now_str}.{selected_format}"

    # Log to Audit Log
    audit_entry = models.AuditLog(
        user_id=current_user.id,
        action="export_security_case_report",
        detail=f"Exported case report for {case.case_id} in format '{selected_format}'",
    )
    db.add(audit_entry)
    db.commit()

    # Log to Activity History
    try:
        from app.activity_logger import record_activity
        record_activity(
            db=db,
            user_id=current_user.id,
            user_name=current_user.name,
            activity_type="case_report_exported",
            module="export",
            entity_type="Case",
            entity_id=case.id,
            title=f"Report Exported: {case.case_id}",
            description=f"Generated '{selected_format.upper()}' investigative report for {case.case_id}.",
            metadata={"format": selected_format, "case_id": case.case_id, "case_title": case.title},
            status="completed",
            tags=["export", selected_format, case.case_id],
        )
    except Exception as act_err:
        print(f"--> Activity logging export notice: {act_err}")

    if selected_format == "pdf":
        pdf_buffer = _generate_case_pdf(case, current_user)
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    elif selected_format == "html":
        html_content = _generate_case_html(case, current_user)
        return StreamingResponse(
            io.BytesIO(html_content.encode("utf-8")),
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    elif selected_format == "csv":
        csv_content = _generate_case_csv(case, current_user)
        return StreamingResponse(
            io.BytesIO(csv_content.encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    else:
        raise ValidationError(f"Unsupported export format '{selected_format}'")


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
        raise ResourceNotFoundError("Chat session not found")

    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session.id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )

    styles = _build_pdf_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=15 * mm, bottomMargin=15 * mm, leftMargin=15 * mm, rightMargin=15 * mm,
    )
    story = []

    story.append(Paragraph("Case Assistant &mdash; Conversation Transcript", styles["ReportHeader"]))
    story.append(Paragraph(
        f"Session: {session.title} &middot; Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} "
        f"&middot; User: {current_user.name} ({current_user.role.value})",
        styles["ReportSubHeader"],
    ))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#CBD5E1"), spaceAfter=10))

    speaker_style = ParagraphStyle(
        name="Speaker", parent=styles["BodyTextCustom"], fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=2,
        textColor=colors.HexColor("#0F172A"),
    )

    for msg in messages:
        speaker = "Investigator" if msg.role == "user" else "AI Case Assistant"
        story.append(Paragraph(speaker, speaker_style))
        story.append(Paragraph(msg.content.replace("\n", "<br/>"), styles["BodyTextCustom"]))

    if not messages:
        story.append(Paragraph("This conversation has no messages yet.", styles["BodyTextCustom"]))

    doc.build(story)
    buffer.seek(0)

    filename = f"chat_{session.id[:8]}_transcript.pdf"
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
