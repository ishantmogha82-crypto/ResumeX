"""
backend/routes.py – REST API Blueprint for ResumeX.

Implements all required REST endpoints:
- Authentication: register, login, logout, me
- Resumes: upload, list, get, delete
- Analyses: analyze, list, get, delete
- Reports: download PDF
"""

import os
import json
import uuid
from pathlib import Path
from flask import Blueprint, jsonify, request, session, current_app, send_file
from werkzeug.utils import secure_filename

from models.database import db, User, Resume, Analysis
from backend.auth import (
    register_user,
    authenticate_user,
    login_user_session,
    logout_user_session,
    get_current_user,
    login_required
)
from backend.resume_parser import parse_resume_document
from backend.analyzer import analyze_resume_against_job
from backend.report_generator import generate_pdf_report

api_bp = Blueprint("api", __name__)


# ─────────────────────────────────────────────────────────────
# HEALTH & STATUS
# ─────────────────────────────────────────────────────────────
@api_bp.route("/status")
def status():
    return jsonify({
        "status": "ok",
        "app": "ResumeX",
        "version": "1.0.0"
    })


# ─────────────────────────────────────────────────────────────
# AUTHENTICATION ENDPOINTS
# ─────────────────────────────────────────────────────────────
@api_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    user, error = register_user(name, email, password)
    if error:
        return jsonify({"error": error}), 400

    login_user_session(user)
    return jsonify({
        "message": "Account registered successfully.",
        "user": user.to_dict()
    }), 201


@api_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    user, error = authenticate_user(email, password)
    if error:
        return jsonify({"error": error}), 401

    login_user_session(user)
    return jsonify({
        "message": "Signed in successfully.",
        "user": user.to_dict()
    }), 200


@api_bp.route("/auth/logout", methods=["POST"])
def logout():
    logout_user_session()
    return jsonify({"message": "Signed out successfully."}), 200


@api_bp.route("/auth/me", methods=["GET"])
def me():
    user = get_current_user()
    if not user:
        return jsonify({"user": None}), 200
    return jsonify({"user": user.to_dict()}), 200


# ─────────────────────────────────────────────────────────────
# RESUME MANAGEMENT ENDPOINTS
# ─────────────────────────────────────────────────────────────
@api_bp.route("/resumes/upload", methods=["POST"])
@login_required
def upload_resume():
    user = get_current_user()

    if "resume" not in request.files:
        return jsonify({"error": "No resume file provided in the request."}), 400

    file = request.files["resume"]
    if not file or not file.filename:
        return jsonify({"error": "Selected file has an empty filename."}), 400

    original_filename = secure_filename(file.filename)
    ext = os.path.splitext(original_filename)[1].lower()

    allowed_exts = {".pdf", ".docx"}
    if ext not in allowed_exts:
        return jsonify({"error": f"Invalid file format '{ext}'. Only PDF and DOCX files are supported."}), 400

    # Ensure uploads folder exists
    upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
    upload_folder.mkdir(parents=True, exist_ok=True)

    # Save with unique identifier to prevent collisions
    unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
    saved_path = upload_folder / unique_filename

    try:
        file.save(str(saved_path))
    except Exception as e:
        return jsonify({"error": f"Failed to save uploaded file: {str(e)}"}), 500

    # Parse and extract document text
    try:
        extracted_text = parse_resume_document(saved_path, original_filename)
    except Exception as e:
        # Clean up corrupted or unparseable file
        if saved_path.exists():
            saved_path.unlink()
        return jsonify({"error": f"Document parsing failed: {str(e)}"}), 422

    # Save record to database
    resume = Resume(
        user_id=user.id,
        filename=unique_filename,
        original_name=original_filename,
        file_path=str(saved_path),
        extracted_text=extracted_text
    )

    try:
        db.session.add(resume)
        db.session.commit()
        return jsonify({
            "message": "Resume uploaded and parsed successfully.",
            "resume": resume.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500


@api_bp.route("/resumes", methods=["GET"])
@login_required
def list_resumes():
    user = get_current_user()
    resumes = Resume.query.filter_by(user_id=user.id).order_by(Resume.uploaded_at.desc()).all()
    return jsonify({
        "resumes": [r.to_dict() for r in resumes]
    }), 200


@api_bp.route("/resumes/<int:resume_id>", methods=["GET"])
@login_required
def get_resume(resume_id):
    user = get_current_user()
    resume = Resume.query.filter_by(id=resume_id, user_id=user.id).first()
    if not resume:
        return jsonify({"error": "Resume not found or access denied."}), 404
    return jsonify({"resume": resume.to_dict()}), 200


@api_bp.route("/resumes/<int:resume_id>", methods=["DELETE"])
@login_required
def delete_resume(resume_id):
    user = get_current_user()
    resume = Resume.query.filter_by(id=resume_id, user_id=user.id).first()
    if not resume:
        return jsonify({"error": "Resume not found or access denied."}), 404

    # Remove physical file from disk if it exists
    if resume.file_path and os.path.exists(resume.file_path):
        try:
            os.remove(resume.file_path)
        except OSError:
            pass

    try:
        db.session.delete(resume)
        db.session.commit()
        return jsonify({"message": "Resume deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete resume: {str(e)}"}), 500


# ─────────────────────────────────────────────────────────────
# ANALYSIS PIPELINE ENDPOINTS
# ─────────────────────────────────────────────────────────────
@api_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    resume_id = data.get("resume_id")
    job_title = (data.get("job_title") or "").strip()
    company_name = (data.get("company_name") or "").strip()
    job_description = (data.get("job_description") or "").strip()

    if not resume_id:
        return jsonify({"error": "A valid resume_id is required."}), 400
    if not job_title:
        return jsonify({"error": "Target job_title is required."}), 400
    if not job_description or len(job_description) < 20:
        return jsonify({"error": "Job description must be at least 20 characters."}), 400

    # Ensure resume exists and belongs to current user
    resume = Resume.query.filter_by(id=resume_id, user_id=user.id).first()
    if not resume:
        return jsonify({"error": "Resume not found or access unauthorized."}), 404

    if not resume.extracted_text:
        return jsonify({"error": "The selected resume contains no readable text."}), 400

    # Run Analysis Engine
    try:
        result = analyze_resume_against_job(
            resume_text=resume.extracted_text,
            job_description=job_description
        )
    except Exception as e:
        return jsonify({"error": f"Analysis calculation error: {str(e)}"}), 500

    # Store Analysis Record
    analysis = Analysis(
        user_id=user.id,
        resume_id=resume.id,
        job_title=job_title,
        company_name=company_name,
        job_description=job_description,
        similarity_score=result["similarity_score"],
        skill_match_score=result["skill_match_score"],
        overall_score=result["overall_score"],
        matched_skills=json.dumps(result["matched_skills"]),
        missing_skills=json.dumps(result["missing_skills"]),
        resume_skills=json.dumps(result["resume_skills"]),
        jd_skills=json.dumps(result["jd_skills"]),
        section_analysis=json.dumps(result["section_analysis"]),
        recommendations=json.dumps(result["recommendations"])
    )

    try:
        db.session.add(analysis)
        db.session.commit()
        return jsonify({
            "message": "Analysis evaluated successfully.",
            "analysis": analysis.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error saving analysis: {str(e)}"}), 500


@api_bp.route("/analyses", methods=["GET"])
@login_required
def list_analyses():
    user = get_current_user()
    records = Analysis.query.filter_by(user_id=user.id).order_by(Analysis.created_at.desc()).all()
    return jsonify({
        "analyses": [a.to_dict() for a in records]
    }), 200


@api_bp.route("/analyses/<int:analysis_id>", methods=["GET"])
@login_required
def get_analysis(analysis_id):
    user = get_current_user()
    analysis = Analysis.query.filter_by(id=analysis_id, user_id=user.id).first()
    if not analysis:
        return jsonify({"error": "Analysis record not found or access denied."}), 404
    return jsonify({"analysis": analysis.to_dict()}), 200


@api_bp.route("/analyses/<int:analysis_id>", methods=["DELETE"])
@login_required
def delete_analysis(analysis_id):
    user = get_current_user()
    analysis = Analysis.query.filter_by(id=analysis_id, user_id=user.id).first()
    if not analysis:
        return jsonify({"error": "Analysis record not found or access denied."}), 404

    try:
        db.session.delete(analysis)
        db.session.commit()
        return jsonify({"message": "Analysis record deleted successfully."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete analysis: {str(e)}"}), 500


# ─────────────────────────────────────────────────────────────
# AUDIT PDF REPORT DOWNLOAD
# ─────────────────────────────────────────────────────────────
@api_bp.route("/reports/<int:analysis_id>/pdf", methods=["GET"])
@login_required
def download_pdf_report(analysis_id):
    user = get_current_user()
    analysis = Analysis.query.filter_by(id=analysis_id, user_id=user.id).first()
    if not analysis:
        return jsonify({"error": "Analysis report not found or access unauthorized."}), 404

    reports_dir = Path(current_app.config["REPORTS_FOLDER"])
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_filename = f"ResumeX_Report_{analysis.id}.pdf"
    pdf_path = reports_dir / report_filename

    try:
        generate_pdf_report(analysis.to_dict(), pdf_path)
    except Exception as e:
        return jsonify({"error": f"PDF report generation failed: {str(e)}"}), 500

    return send_file(
        str(pdf_path),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=report_filename
    )
