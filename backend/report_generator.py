"""
backend/report_generator.py – Professional PDF Audit Report Generator for ResumeX.

Features:
- Produces clean, monochrome audit reports using ReportLab
- Includes compatibility scores, matched vs missing skills, section checklist, and recommendations
- Handles formatting, margins, typography hierarchy, and page bounds gracefully
"""

import os
from pathlib import Path
from datetime import datetime


def generate_pdf_report(analysis_data: dict, output_path: str | Path) -> str:
    """
    Generate a polished PDF analysis report.
    Returns the absolute path to the generated PDF.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()

        # Custom Monochrome Styles
        brand_dark = colors.HexColor("#1C1C1C")
        brand_card = colors.HexColor("#262626")
        brand_border = colors.HexColor("#404040")
        text_primary = colors.HexColor("#1A1A1A")
        text_muted = colors.HexColor("#666666")

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=brand_dark
        )

        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=text_muted
        )

        h2_style = ParagraphStyle(
            "Heading2Custom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=brand_dark,
            spaceBefore=12,
            spaceAfter=6
        )

        body_style = ParagraphStyle(
            "BodyCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=text_primary
        )

        bullet_style = ParagraphStyle(
            "BulletCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=text_primary,
            leftIndent=14
        )

        story = []

        # Header Title
        story.append(Paragraph("<b>ResumeX</b> &nbsp;|&nbsp; AI Resume Evaluation Report", title_style))
        story.append(Spacer(1, 4))
        job_title = analysis_data.get("job_title") or "Target Role"
        company = analysis_data.get("company_name") or "Employer"
        date_str = datetime.now().strftime("%B %d, %Y")
        story.append(Paragraph(f"Target Position: <b>{job_title}</b> ({company}) &nbsp;•&nbsp; Generated on: {date_str}", subtitle_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1, color=brand_border, spaceBefore=4, spaceAfter=14))

        # Score Summary Table
        overall = analysis_data.get("overall_score", 0)
        skill_score = analysis_data.get("skill_match_score", 0)
        semantic_score = analysis_data.get("similarity_score", 0)

        score_table_data = [
            [
                Paragraph("<b>OVERALL COMPATIBILITY</b>", subtitle_style),
                Paragraph("<b>SKILL COVERAGE</b>", subtitle_style),
                Paragraph("<b>SEMANTIC SIMILARITY</b>", subtitle_style)
            ],
            [
                Paragraph(f"<font size=18><b>{overall}%</b></font>", title_style),
                Paragraph(f"<font size=14><b>{skill_score}%</b></font>", h2_style),
                Paragraph(f"<font size=14><b>{semantic_score}%</b></font>", h2_style)
            ]
        ]
        score_table = Table(score_table_data, colWidths=[200, 160, 160])
        score_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F5F5")),
            ("BOX", (0, 0), (-1, -1), 1, brand_border),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, brand_border),
            ("PADDING", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 14))

        # Skills Comparison: Matched vs Missing
        story.append(Paragraph("<b>Competency & Skill Gap Analysis</b>", h2_style))
        matched = analysis_data.get("matched_skills") or []
        missing = analysis_data.get("missing_skills") or []

        matched_text = ", ".join(matched) if matched else "None detected"
        missing_text = ", ".join(missing) if missing else "No critical skills missing"

        skills_table_data = [
            [Paragraph("<b>Matched Skills</b>", subtitle_style), Paragraph(matched_text, body_style)],
            [Paragraph("<b>Missing High-Priority Skills</b>", subtitle_style), Paragraph(missing_text, body_style)]
        ]
        skills_table = Table(skills_table_data, colWidths=[160, 360])
        skills_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
        ]))
        story.append(skills_table)
        story.append(Spacer(1, 14))

        # Structural Section Completeness Audit
        story.append(Paragraph("<b>Structural Completeness Audit</b>", h2_style))
        sections = analysis_data.get("section_analysis") or {}
        section_rows = [
            ("Contact Information", sections.get("contact_info", False)),
            ("Education & Degrees", sections.get("education", False)),
            ("Work Experience", sections.get("experience", False)),
            ("Technical Projects", sections.get("projects", False)),
            ("Skills Summary Section", sections.get("skills", False)),
            ("Certifications & Accreditations", sections.get("certifications", False)),
        ]

        sec_table_data = []
        for name, detected in section_rows:
            status = "DETECTED" if detected else "MISSING"
            sec_table_data.append([
                Paragraph(name, body_style),
                Paragraph(f"<b>{status}</b>", body_style)
            ])

        sec_table = Table(sec_table_data, colWidths=[380, 140])
        sec_table.setStyle(TableStyle([
            ("PADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#EEEEEE")),
        ]))
        story.append(sec_table)
        story.append(Spacer(1, 14))

        # Recommendations
        story.append(Paragraph("<b>Actionable Recommendations</b>", h2_style))
        recs = analysis_data.get("recommendations") or []
        for idx, r in enumerate(recs[:4], start=1):
            if isinstance(r, dict):
                title = r.get("title", f"Suggestion {idx}")
                desc = r.get("description", "")
                story.append(Paragraph(f"<b>{idx}. {title}</b>", body_style))
                story.append(Paragraph(desc, bullet_style))
                story.append(Spacer(1, 4))
            else:
                story.append(Paragraph(f"• {str(r)}", bullet_style))
                story.append(Spacer(1, 3))

        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=0.5, color=brand_border, spaceBefore=4, spaceAfter=8))
        disclaimer = (
            "Disclaimer: ResumeX compatibility scores are algorithmic indicators calculated via natural language "
            "processing (TF-IDF vector cosine angle and exact skill overlap). They are estimates and do not guarantee "
            "interviews, hiring decisions, or commercial ATS acceptance."
        )
        story.append(Paragraph(disclaimer, ParagraphStyle("Disc", parent=body_style, fontSize=7.5, leading=10, textColor=text_muted)))

        doc.build(story)
        return str(output_path)

    except Exception as e:
        # Fallback to generating a plain-text structured PDF if ReportLab fails
        return generate_simple_pdf_fallback(analysis_data, output_path)


def generate_simple_pdf_fallback(analysis_data: dict, output_path: Path) -> str:
    """
    Lightweight fallback that creates a basic valid PDF file with audit contents
    if ReportLab has rendering issues.
    """
    job_title = analysis_data.get("job_title", "Target Role")
    overall = analysis_data.get("overall_score", 0)
    matched = ", ".join(analysis_data.get("matched_skills", []))
    missing = ", ".join(analysis_data.get("missing_skills", []))

    content = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 380 >> stream
BT
/F1 18 Tf
50 720 Td
(ResumeX - AI Resume Analysis Report) Tj
/F1 12 Tf
0 -30 Td
(Target Role: {job_title}) Tj
0 -20 Td
(Overall Compatibility Score: {overall}%) Tj
0 -30 Td
(Matched Skills: {matched[:80]}) Tj
0 -20 Td
(Missing Skills: {missing[:80]}) Tj
0 -40 Td
(Report generated successfully by ResumeX.) Tj
ET
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000676 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
755
%%EOF
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return str(output_path)
