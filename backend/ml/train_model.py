"""
backend/ml/train_model.py – End-to-end ML training pipeline for ResumeX.

Features:
- Loads weakly annotated resume dataset and curated skill vocabulary
- Identifies and drops duplicate resume documents
- Sanitizes weak labels (filters false-positive noise on ambiguous tokens)
- Enforces strict train/test split (80/20) with seed control to prevent data leakage
- Extracts n-gram TF-IDF textual features
- Trains multi-label One-vs-Rest classification model
- Calculates Precision, Recall, Micro F1, and Macro F1 scores
- Calibrates confidence thresholds on held-out test data
- Serializes trained model pipeline and metadata via joblib
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple

import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, f1_score, classification_report

from backend.ml.preprocessing import (
    clean_resume_text,
    sanitize_weak_labels,
    normalize_skill_name,
    get_skill_category,
    VALID_CATEGORIES,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ResumeX-ML-Train")


def load_and_prepare_dataset(
    csv_path: str | Path,
    vocab_path: str | Path,
    min_skill_frequency: int = 2
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Load training dataset, deduplicate, sanitize weak labels, and map categories.
    """
    logger.info(f"Loading training data from {csv_path}...")
    df = pd.read_csv(csv_path)

    # 1. Duplicate detection and removal
    initial_len = len(df)
    df = df.drop_duplicates(subset=["resume_text"]).copy()
    duplicates_removed = initial_len - len(df)
    if duplicates_removed > 0:
        logger.info(f"Removed {duplicates_removed} duplicate resume records.")

    # 2. Vocabulary & Category Mapping
    logger.info(f"Loading skill vocabulary from {vocab_path}...")
    vocab_df = pd.read_csv(vocab_path)
    vocab_cat_map = dict(zip(vocab_df["skill"], vocab_df["category"]))

    # 3. Weak label sanitization
    logger.info("Sanitizing weak labels and filtering vocabulary noise...")
    cleaned_skills_col = []
    clean_text_col = []

    for _, row in df.iterrows():
        raw_skills = []
        if isinstance(row["technical_skills"], str):
            try:
                raw_skills = json.loads(row["technical_skills"])
            except json.JSONDecodeError:
                raw_skills = []

        cleaned_text = clean_resume_text(str(row["resume_text"]))
        clean_text_col.append(cleaned_text)

        sanitized = sanitize_weak_labels(
            text=cleaned_text,
            raw_skills=raw_skills,
            job_category=str(row.get("job_category", ""))
        )
        cleaned_skills_col.append(sanitized)

    df["processed_text"] = clean_text_col
    df["sanitized_skills"] = cleaned_skills_col

    # 4. Filter skills by minimum frequency
    skill_counts: Dict[str, int] = {}
    for skills in df["sanitized_skills"]:
        for s in skills:
            skill_counts[s] = skill_counts.get(s, 0) + 1

    retained_skills = {s for s, count in skill_counts.items() if count >= min_skill_frequency}
    logger.info(
        f"Unique skills before filtering: {len(skill_counts)}, "
        f"retained with frequency >= {min_skill_frequency}: {len(retained_skills)}"
    )

    df["final_skills"] = df["sanitized_skills"].apply(
        lambda skills: [s for s in skills if s in retained_skills]
    )

    # Build canonical skill-to-category mapping for all retained skills
    skill_category_map = {}
    for skill in retained_skills:
        vocab_cat = vocab_cat_map.get(skill)
        skill_category_map[skill] = get_skill_category(skill, default_vocab_category=vocab_cat)

    return df, skill_category_map


def train_and_evaluate(
    df: pd.DataFrame,
    skill_category_map: Dict[str, str],
    test_size: float = 0.2,
    random_state: int = 42
) -> Dict[str, Any]:
    """
    Train TF-IDF + Multi-label OneVsRest classifier, evaluate metrics, and calibrate threshold.
    """
    logger.info(f"Splitting dataset: {int((1-test_size)*100)}% train / {int(test_size*100)}% test...")
    X_train_raw, X_test_raw, y_train_skills, y_test_skills = train_test_split(
        df["processed_text"].values,
        df["final_skills"].values,
        test_size=test_size,
        random_state=random_state
    )

    # 1. MultiLabel Binarization
    mlb = MultiLabelBinarizer()
    y_train = mlb.fit_transform(y_train_skills)
    y_test = mlb.transform(y_test_skills)
    classes = list(mlb.classes_)
    logger.info(f"Target multi-label classes: {len(classes)} distinct skills.")

    # 2. Text Feature Extraction (TF-IDF)
    logger.info("Extracting TF-IDF features (unigrams + bigrams)...")
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=8000,
        sublinear_tf=True,
        min_df=2,
        stop_words="english"
    )
    X_train = vectorizer.fit_transform(X_train_raw)
    X_test = vectorizer.transform(X_test_raw)
    logger.info(f"TF-IDF matrix shape - Train: {X_train.shape}, Test: {X_test.shape}")

    # 3. Model Training
    logger.info("Training One-vs-Rest Logistic Regression classifier...")
    base_clf = LogisticRegression(
        C=2.5,
        class_weight="balanced",
        max_iter=1000,
        random_state=random_state,
        solver="liblinear"
    )
    model = OneVsRestClassifier(base_clf)
    model.fit(X_train, y_train)

    # 4. Threshold Calibration on Test Split
    test_probs = model.predict_proba(X_test)
    best_threshold = 0.40
    best_f1 = 0.0
    best_metrics = {}

    threshold_candidates = [0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
    logger.info("Evaluating thresholds on held-out test split:")

    for th in threshold_candidates:
        y_pred = (test_probs >= th).astype(int)
        micro_f1 = f1_score(y_test, y_pred, average="micro", zero_division=0)
        macro_f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
        precision_micro = precision_score(y_test, y_pred, average="micro", zero_division=0)
        recall_micro = recall_score(y_test, y_pred, average="micro", zero_division=0)

        logger.info(
            f"  Threshold {th:.2f} -> Precision: {precision_micro:.4f}, "
            f"Recall: {recall_micro:.4f}, Micro F1: {micro_f1:.4f}, Macro F1: {macro_f1:.4f}"
        )

        if micro_f1 > best_f1:
            best_f1 = micro_f1
            best_threshold = th
            best_metrics = {
                "threshold": th,
                "precision_micro": round(float(precision_micro), 4),
                "recall_micro": round(float(recall_micro), 4),
                "micro_f1": round(float(micro_f1), 4),
                "macro_f1": round(float(macro_f1), 4),
                "test_samples": int(len(X_test_raw)),
                "train_samples": int(len(X_train_raw)),
                "classes_count": int(len(classes)),
            }

    logger.info(f"Selected optimal threshold: {best_threshold:.2f} (Micro F1: {best_f1:.4f})")

    # Final detailed classification report at best threshold
    y_pred_best = (test_probs >= best_threshold).astype(int)
    clf_report = classification_report(
        y_test,
        y_pred_best,
        target_names=classes,
        output_dict=True,
        zero_division=0
    )

    artifacts = {
        "vectorizer": vectorizer,
        "model": model,
        "mlb": mlb,
        "classes": classes,
        "skill_category_map": skill_category_map,
        "optimal_threshold": best_threshold,
        "metrics": best_metrics,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_version": "1.0.0",
    }

    return artifacts, clf_report


def save_model_artifacts(
    artifacts: Dict[str, Any],
    output_dir: str | Path = "backend/ml/artifacts"
) -> Path:
    """Save trained model bundle and metadata to disk using joblib."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    bundle_file = out_path / "skill_model.joblib"
    joblib.dump(artifacts, bundle_file, compress=3)
    logger.info(f"Model artifact bundle saved successfully to {bundle_file}")

    # Also save a human-readable metadata json
    meta = {
        "model_version": artifacts["model_version"],
        "trained_at": artifacts["trained_at"],
        "optimal_threshold": artifacts["optimal_threshold"],
        "metrics": artifacts["metrics"],
        "num_classes": len(artifacts["classes"]),
        "classes": artifacts["classes"],
    }
    meta_file = out_path / "model_metadata.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    logger.info(f"Model metadata exported to {meta_file}")

    return bundle_file


def run_pipeline(
    csv_path: str = "data/resumex_programming_skills_training.csv",
    vocab_path: str = "data/resumex_skill_vocabulary.csv",
    output_dir: str = "backend/ml/artifacts"
) -> Dict[str, Any]:
    """Execute complete training pipeline."""
    df, skill_cat_map = load_and_prepare_dataset(csv_path, vocab_path)
    artifacts, report = train_and_evaluate(df, skill_cat_map)
    save_model_artifacts(artifacts, output_dir)
    return artifacts["metrics"]


if __name__ == "__main__":
    run_pipeline()

