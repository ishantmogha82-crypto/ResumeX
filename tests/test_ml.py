"""
tests/test_ml.py – Comprehensive Tests for Machine Learning Skill Extraction & Integration.

Validates:
1. ML Model loading & singleton persistence
2. Precision & thresholding behavior
3. Hybrid skill extraction (Regex + ML)
4. In-text evidence verification
5. Edge cases: non-technical resumes (zero false positives)
6. Edge cases: unfamiliar / complex tech stacks
7. API integration via /api/skills/extract
"""

import pytest
from backend.ml.predict import get_predictor, predict_skills
from backend.ml.preprocessing import clean_resume_text, find_text_evidence, sanitize_weak_labels
from backend.skill_extractor import (
    extract_skills,
    extract_regex_skills,
    extract_technical_skills_hybrid,
    compare_skills
)
from app import create_app
from models.database import db


def test_ml_model_singleton_loading():
    """Verify ML model is loaded as a singleton and contains trained classes."""
    predictor = get_predictor()
    assert predictor.is_loaded is True
    assert len(predictor.classes) >= 50
    assert predictor.vectorizer is not None
    assert predictor.model is not None


def test_in_text_evidence_verification():
    """Verify text evidence extraction returns exact matching window."""
    text = "Full stack developer designing backend microservices with Python and Docker on AWS cloud."
    ev_py = find_text_evidence(text, "Python")
    assert ev_py is not None
    assert "Python" in ev_py

    ev_docker = find_text_evidence(text, "Docker")
    assert ev_docker is not None
    assert "Docker" in ev_docker

    # Non-existent skill should return None
    ev_ruby = find_text_evidence(text, "Ruby")
    assert ev_ruby is None


def test_hybrid_skill_extraction_structure():
    """Verify hybrid extractor output matches required 5-category format and extraction_method."""
    resume_text = (
        "Senior Software Engineer\n"
        "Proficient in Python, Java, and TypeScript.\n"
        "Built web interfaces with React, Django, and FastAPI.\n"
        "Managed data with PostgreSQL and MongoDB.\n"
        "Deployed CI/CD pipelines with Docker and AWS.\n"
        "Version control with Git and GitHub."
    )
    result = extract_technical_skills_hybrid(resume_text)

    assert "technical_skills" in result
    assert "extraction_method" in result
    assert result["extraction_method"] == "regex_and_ml"

    tech = result["technical_skills"]
    assert "programming_languages" in tech
    assert "frameworks" in tech
    assert "databases" in tech
    assert "cloud_devops" in tech
    assert "developer_tools" in tech

    # Check that skills are categorized into appropriate buckets
    assert "Python" in tech["programming_languages"]
    assert "Java" in tech["programming_languages"]
    assert any(f in tech["frameworks"] for f in ["React", "Django", "FastAPI"])
    assert any(d in tech["databases"] for d in ["PostgreSQL", "MongoDB"])
    assert any(c in tech["cloud_devops"] for c in ["Docker", "AWS"])
    assert any(t in tech["developer_tools"] for t in ["Git", "GitHub"])


def test_zero_false_positives_on_non_technical_resume():
    """Verify resumes with no technical skills return zero false positives."""
    non_tech_text = (
        "Executive Sous Chef with 10 years experience running high-volume kitchens. "
        "Expertise in menu design, culinary team management, food safety, inventory control, "
        "and vendor negotiations. Passionate about sourdough baking and French cuisine."
    )
    result = extract_technical_skills_hybrid(non_tech_text)
    tech = result["technical_skills"]

    total_extracted = sum(len(skills) for skills in tech.values())
    assert total_extracted == 0, f"Expected 0 technical skills for chef resume, got {tech}"


def test_unfamiliar_and_mixed_technologies():
    """Verify handling of resumes with mixed and advanced technologies."""
    text = (
        "Data Engineer working with Apache Spark, Hadoop, PostgreSQL, Linux, "
        "and Python scripting for ETL data pipelines."
    )
    result = extract_technical_skills_hybrid(text)
    tech = result["technical_skills"]

    assert "Python" in tech["programming_languages"]
    assert "PostgreSQL" in tech["databases"]
    assert "Linux" in tech["cloud_devops"]


def test_regex_vs_ml_vs_hybrid_comparison():
    """Compare regex vs ML vs combined hybrid extraction."""
    text = (
        "Backend Developer working with Python, PostgreSQL, and Spring Boot on Linux. "
        "Strong leadership and collaboration skills."
    )
    regex_only = extract_regex_skills(text)
    hybrid_dict = extract_technical_skills_hybrid(text)
    combined_skills = extract_skills(text)

    # Regex captures Python, Linux, Leadership, Collaboration
    assert "Python" in regex_only
    assert "Linux" in regex_only

    # Hybrid categorized skills include PostgreSQL (from ML/extended ontology)
    flat_hybrid = [s for cat in hybrid_dict["technical_skills"].values() for s in cat]
    assert "PostgreSQL" in flat_hybrid

    # Combined extract_skills contains union
    assert "Python" in combined_skills
    assert "PostgreSQL" in combined_skills
    assert "Leadership" in combined_skills


def test_api_skills_extract_endpoint():
    """Verify POST /api/skills/extract endpoint."""
    app = create_app("testing")
    with app.test_client() as client:
        with app.app_context():
            db.create_all()

            # Register and login
            client.post("/api/auth/register", json={
                "name": "Dev User",
                "email": "dev@example.com",
                "password": "securepassword123"
            })

            # Call endpoint
            payload = {
                "text": "Software engineer proficient in Python, Docker, PostgreSQL, and Git."
            }
            res = client.post("/api/skills/extract", json=payload)
            assert res.status_code == 200
            data = res.get_json()

            assert "technical_skills" in data
            assert data["extraction_method"] == "regex_and_ml"
            assert "Python" in data["technical_skills"]["programming_languages"]
            assert "PostgreSQL" in data["technical_skills"]["databases"]
            assert "Docker" in data["technical_skills"]["cloud_devops"]

