"""
tests/test_integration.py – Full End-to-End Pipeline Integration Test.
"""

import io
from app import create_app
from models.database import db
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_sample_pdf_bytes():
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(100, 750, "Jordan Rivera - jordan.rivera@example.com - (555) 987-6543")
    c.drawString(100, 730, "github.com/jordanrivera - linkedin.com/in/jordanrivera")
    c.drawString(100, 700, "EDUCATION")
    c.drawString(100, 685, "B.S. Computer Science, University of California, 2023")
    c.drawString(100, 655, "WORK EXPERIENCE")
    c.drawString(100, 640, "Software Engineer Intern at Tech Corp (2023 - 2024)")
    c.drawString(100, 625, "Engineered REST APIs using Python, Flask, and PostgreSQL (SQL).")
    c.drawString(100, 610, "Deployed containerized services using Docker and Git. Increased throughput by 25%.")
    c.drawString(100, 580, "TECHNICAL PROJECTS")
    c.drawString(100, 565, "AI Dashboard: Built React and Node.js web application.")
    c.drawString(100, 535, "TECHNICAL SKILLS")
    c.drawString(100, 520, "Python, Flask, React, Node.js, SQL, Docker, Git, REST API, Problem Solving")
    c.drawString(100, 490, "CERTIFICATIONS")
    c.drawString(100, 475, "AWS Certified Cloud Practitioner")
    c.save()
    buf.seek(0)
    return buf.getvalue()


def test_full_pipeline_workflow():
    app = create_app("testing")
    with app.test_client() as client:
        with app.app_context():
            db.create_all()

            # 1. Register User
            reg_res = client.post("/api/auth/register", json={
                "name": "Jordan Rivera",
                "email": "jordan@example.com",
                "password": "strongpassword123"
            })
            assert reg_res.status_code == 201

            # 2. Upload Resume Document (PDF)
            pdf_bytes = create_sample_pdf_bytes()
            upload_data = {
                "resume": (io.BytesIO(pdf_bytes), "Jordan_Rivera_Resume.pdf")
            }
            upload_res = client.post(
                "/api/resumes/upload",
                data=upload_data,
                content_type="multipart/form-data"
            )
            assert upload_res.status_code == 201
            resume_info = upload_res.get_json()["resume"]
            resume_id = resume_info["id"]
            assert resume_info["has_text"] is True

            # 3. Analyze against Job Description
            target_jd = (
                "We are seeking a Senior Python & React Engineer to join our team. "
                "Required skills: Python, React, Docker, Kubernetes, AWS, SQL, and GraphQL. "
                "Experience with CI/CD and leadership is a plus."
            )
            analyze_res = client.post("/api/analyze", json={
                "resume_id": resume_id,
                "job_title": "Full Stack Engineer",
                "company_name": "CloudScale Inc",
                "job_description": target_jd
            })
            assert analyze_res.status_code == 201
            analysis_info = analyze_res.get_json()["analysis"]
            analysis_id = analysis_info["id"]

            # Verify analytical outputs
            assert analysis_info["overall_score"] > 0
            assert "Python" in analysis_info["matched_skills"]
            assert "React" in analysis_info["matched_skills"]
            assert "Docker" in analysis_info["matched_skills"]
            assert "Kubernetes" in analysis_info["missing_skills"]
            assert "GraphQL" in analysis_info["missing_skills"]
            assert analysis_info["section_analysis"]["contact_info"] is True
            assert len(analysis_info["recommendations"]) > 0

            # 4. Fetch Analysis by ID
            get_res = client.get(f"/api/analyses/{analysis_id}")
            assert get_res.status_code == 200
            assert get_res.get_json()["analysis"]["job_title"] == "Full Stack Engineer"

            # 5. Download Generated PDF Report
            report_res = client.get(f"/api/reports/{analysis_id}/pdf")
            assert report_res.status_code == 200
            assert report_res.content_type == "application/pdf"
            assert len(report_res.data) > 500  # valid PDF payload

            # 6. List Analyses
            list_res = client.get("/api/analyses")
            assert list_res.status_code == 200
            assert len(list_res.get_json()["analyses"]) == 1

            # 7. Delete Analysis
            del_res = client.delete(f"/api/analyses/{analysis_id}")
            assert del_res.status_code == 200

            # Verify deletion
            list_after_res = client.get("/api/analyses")
            assert len(list_after_res.get_json()["analyses"]) == 0

            db.session.remove()
            db.drop_all()

