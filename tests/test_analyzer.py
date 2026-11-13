"""
tests/test_analyzer.py – Unit Tests for Skill Extraction, NLP Analysis, and Scoring.
"""

from backend.skill_extractor import extract_skills, compare_skills
from backend.analyzer import (
    compute_tf_idf_cosine_similarity,
    audit_resume_sections,
    analyze_resume_against_job
)


def test_skill_extraction_accuracy():
    text = (
        "Experienced Full Stack Developer with 4 years building web apps using Python, "
        "React, and PostgreSQL (SQL). Proficient with Docker, Git, and REST APIs. "
        "Strong teamwork and communication skills."
    )
    skills = extract_skills(text)
    assert "Python" in skills
    assert "React" in skills
    assert "SQL" in skills
    assert "Docker" in skills
    assert "Git" in skills
    assert "Communication" in skills
    assert "Teamwork" in skills


def test_no_false_positive_skill_matches():
    # 'company' should not trigger 'C'
    # 'ongoing' should not trigger 'Go'
    # 'javascript' should not trigger 'Java'
    text = "Our company has ongoing projects developing javascript solutions."
    skills = extract_skills(text)
    assert "C" not in skills
    assert "Go" not in skills
    assert "Java" not in skills
    assert "JavaScript" in skills


def test_skill_comparison():
    resume_skills = ["Python", "Docker", "SQL", "Git"]
    jd_skills = ["Python", "Kubernetes", "AWS", "Docker"]

    diff = compare_skills(resume_skills, jd_skills)
    assert diff["matched"] == ["Docker", "Python"]
    assert diff["missing"] == ["AWS", "Kubernetes"]
    assert diff["bonus"] == ["Git", "SQL"]


def test_cosine_similarity_identical_and_divergent():
    doc1 = "Python developer building machine learning models with pandas and scikit-learn."
    doc2 = "Python developer building machine learning models with pandas and scikit-learn."
    sim_identical = compute_tf_idf_cosine_similarity(doc1, doc2)
    assert sim_identical >= 99.0

    doc3 = "Chef preparing gourmet French pastries and baking sourdough bread in bakery."
    sim_divergent = compute_tf_idf_cosine_similarity(doc1, doc3)
    assert sim_divergent < 10.0


def test_resume_section_detection():
    sample_resume = """
    Alex Morgan - alex.morgan@example.com - (555) 123-4567 - linkedin.com/in/alexmorgan
    
    EDUCATION
    B.S. in Computer Science, Stanford University, 2022
    
    WORK EXPERIENCE
    Software Engineer, Tech Solutions (2022 - Present)
    Built backend microservices in Python.
    
    TECHNICAL PROJECTS
    E-Commerce API: Built REST API in Flask.
    
    TECHNICAL SKILLS
    Python, JavaScript, Docker, SQL
    
    CERTIFICATIONS
    AWS Certified Solutions Architect
    """
    sections = audit_resume_sections(sample_resume)
    assert sections["contact_info"] is True
    assert sections["education"] is True
    assert sections["experience"] is True
    assert sections["projects"] is True
    assert sections["skills"] is True
    assert sections["certifications"] is True


def test_scoring_formula_consistency():
    resume = "Python engineer with Docker and SQL database experience building REST APIs."
    jd = "Seeking a Python backend engineer with Docker, Kubernetes, and AWS skills."

    result = analyze_resume_against_job(resume, jd)

    # Documented formula: overall = (similarity * 0.4) + (skill_match * 0.6)
    expected_overall = round((result["similarity_score"] * 0.4) + (result["skill_match_score"] * 0.6), 1)
    assert result["overall_score"] == expected_overall
    assert result["matched_skills"] == ["Docker", "Python"]
    assert "Kubernetes" in result["missing_skills"]
    assert "AWS" in result["missing_skills"]
    assert len(result["recommendations"]) > 0
