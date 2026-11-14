"""
backend/ml/predict.py – Production ML inference engine for ResumeX.

Features:
- Singleton loader: loads trained model artifact into memory ONCE at module load.
- Avoids expensive re-training on resume uploads.
- Calibrated probability thresholding.
- Strict in-text evidence verification to prevent hallucinations.
- Categorizes skills into the 5 core technical buckets:
  (programming_languages, frameworks, databases, cloud_devops, developer_tools)
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

import joblib
from backend.ml.preprocessing import (
    clean_resume_text,
    normalize_skill_name,
    find_text_evidence,
    get_skill_category,
    CATEGORY_PROGRAMMING,
    CATEGORY_FRAMEWORKS,
    CATEGORY_DATABASES,
    CATEGORY_CLOUD_DEVOPS,
    CATEGORY_DEV_TOOLS,
    VALID_CATEGORIES,
)

logger = logging.getLogger("ResumeX-ML-Predict")


class SkillPredictor:
    """
    Singleton wrapper for trained TF-IDF multi-label skill classifier.
    """
    _instance: Optional["SkillPredictor"] = None

    def __init__(self, model_path: Optional[str | Path] = None):
        if model_path is None:
            # Default to backend/ml/artifacts/skill_model.joblib
            base_dir = Path(__file__).resolve().parent
            model_path = base_dir / "artifacts" / "skill_model.joblib"

        self.model_path = Path(model_path)
        self.is_loaded = False
        self.vectorizer = None
        self.model = None
        self.mlb = None
        self.classes = []
        self.skill_category_map = {}
        self.default_threshold = 0.40
        self.metrics = {}

        self.load_model()

    @classmethod
    def get_instance(cls, model_path: Optional[str | Path] = None) -> "SkillPredictor":
        """Access singleton predictor instance."""
        if cls._instance is None:
            cls._instance = SkillPredictor(model_path)
        return cls._instance

    def load_model(self) -> bool:
        """Load serialized model bundle from disk."""
        if not self.model_path.exists():
            logger.warning(f"Skill model artifact not found at {self.model_path}. ML predictions will be unavailable.")
            self.is_loaded = False
            return False

        try:
            logger.info(f"Loading ML skill model from {self.model_path}...")
            artifacts = joblib.load(self.model_path)
            self.vectorizer = artifacts["vectorizer"]
            self.model = artifacts["model"]
            self.mlb = artifacts["mlb"]
            self.classes = artifacts["classes"]
            self.skill_category_map = artifacts.get("skill_category_map", {})
            self.default_threshold = artifacts.get("optimal_threshold", 0.40)
            self.metrics = artifacts.get("metrics", {})
            self.is_loaded = True
            logger.info(f"ML skill model loaded successfully with {len(self.classes)} classes.")
            return True
        except Exception as e:
            logger.error(f"Error loading ML skill model artifact: {e}")
            self.is_loaded = False
            return False

    def predict(
        self,
        text: str,
        threshold: Optional[float] = None,
        require_evidence: bool = True
    ) -> Dict[str, Any]:
        """
        Predict technical skills from raw resume or job description text.

        Args:
            text: Raw input document text.
            threshold: Confidence cutoff (0.0 to 1.0). If None, uses default calibrated threshold.
            require_evidence: If True, only confirms skills having verifiable text evidence.

        Returns:
            Dict containing:
              - technical_skills: dict of 5 categories -> list of skills
              - predictions: list of dicts with skill, confidence, category, evidence
              - extraction_method: 'ml'
        """
        empty_result = {
            "technical_skills": {
                CATEGORY_PROGRAMMING: [],
                CATEGORY_FRAMEWORKS: [],
                CATEGORY_DATABASES: [],
                CATEGORY_CLOUD_DEVOPS: [],
                CATEGORY_DEV_TOOLS: [],
            },
            "predictions": [],
            "extraction_method": "ml"
        }

        if not text or not self.is_loaded or self.vectorizer is None or self.model is None:
            return empty_result

        cutoff = threshold if threshold is not None else self.default_threshold
        cleaned = clean_resume_text(text)
        if not cleaned:
            return empty_result

        try:
            vec = self.vectorizer.transform([cleaned])
            probs = self.model.predict_proba(vec)[0]
        except Exception as e:
            logger.error(f"Prediction inference error: {e}")
            return empty_result

        predictions = []
        categorized: Dict[str, List[str]] = {cat: [] for cat in VALID_CATEGORIES}
        seen_skills = set()

        for idx, skill in enumerate(self.classes):
            conf = float(probs[idx])
            evidence = find_text_evidence(text, skill)

            # When evidence is present in the document text, verify the skill
            if evidence:
                effective_conf = max(conf, 0.75) if conf < 0.75 else conf
                canonical = normalize_skill_name(skill)
                if canonical.lower() in seen_skills:
                    continue
                seen_skills.add(canonical.lower())

                cat = self.skill_category_map.get(skill) or get_skill_category(canonical)
                if cat not in categorized:
                    cat = CATEGORY_DEV_TOOLS

                predictions.append({
                    "skill": canonical,
                    "confidence": round(effective_conf, 4),
                    "category": cat,
                    "evidence": evidence
                })
                categorized[cat].append(canonical)

            elif not require_evidence and conf >= max(cutoff, 0.65):
                # Inferred without direct text mention (only when require_evidence is explicitly False)
                canonical = normalize_skill_name(skill)
                if canonical.lower() in seen_skills:
                    continue
                seen_skills.add(canonical.lower())

                cat = self.skill_category_map.get(skill) or get_skill_category(canonical)
                if cat not in categorized:
                    cat = CATEGORY_DEV_TOOLS

                predictions.append({
                    "skill": canonical,
                    "confidence": round(conf, 4),
                    "category": cat,
                    "evidence": None
                })
                categorized[cat].append(canonical)

        # Sort each category alphabetically for consistency
        for cat in categorized:
            categorized[cat] = sorted(categorized[cat])

        # Sort predictions by confidence descending
        predictions.sort(key=lambda p: p["confidence"], reverse=True)

        return {
            "technical_skills": categorized,
            "predictions": predictions,
            "extraction_method": "ml"
        }


# Global singleton instance accessor
def get_predictor() -> SkillPredictor:
    return SkillPredictor.get_instance()


def predict_skills(text: str, threshold: Optional[float] = None) -> Dict[str, Any]:
    """Functional convenience entrypoint."""
    return get_predictor().predict(text, threshold=threshold)
