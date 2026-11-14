"""
backend/ml package for ResumeX.
"""
from backend.ml.predict import get_predictor, predict_skills
from backend.ml.preprocessing import (
    clean_resume_text,
    find_text_evidence,
    normalize_skill_name,
    get_skill_category,
)

__all__ = [
    "get_predictor",
    "predict_skills",
    "clean_resume_text",
    "find_text_evidence",
    "normalize_skill_name",
    "get_skill_category",
]

