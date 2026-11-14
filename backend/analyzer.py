"""
backend/analyzer.py – Core NLP Analysis & Resume Evaluation Engine.

Provides:
- TF-IDF Vectorization and Cosine Similarity between Resume and Job Description
- Skill Coverage matching and gap detection
- Structural Resume Section Completeness Audit (Contact, Education, Experience, Projects, Skills, Certifications)
- Quantifiable Action Impact & Keyword Recommendation generation
- Transparent, non-random mathematical scoring formula
"""

import re
import math
from typing import Dict, List, Any, Tuple
from backend.skill_extractor import (
    extract_skills,
    compare_skills,
    extract_technical_skills_hybrid
)


# ─────────────────────────────────────────────────────────────
# SECTION AUDIT PATTERNS
# ─────────────────────────────────────────────────────────────
SECTION_PATTERNS = {
    "contact_info": [
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",  # email
        r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",  # phone
        r"linkedin\.com\/in\/[a-zA-Z0-9_-]+",
        r"github\.com\/[a-zA-Z0-9_-]+"
    ],
    "education": [
        r"\b(?:education|academic(?:s)?|university|college|bachelor(?:'s)?|master(?:'s)?|phd|b\.s\.|m\.s\.|b\.tech|m\.tech|degree)\b"
    ],
    "experience": [
        r"\b(?:work\s+experience|professional\s+experience|employment\s+history|experience|internship(?:s)?|work\s+history)\b"
    ],
    "projects": [
        r"\b(?:projects|technical\s+projects|personal\s+projects|academic\s+projects|portfolio|key\s+projects)\b"
    ],
    "skills": [
        r"\b(?:skills|technical\s+skills|core\s+competencies|technologies|proficiencies|tools\s+&\s+technologies)\b"
    ],
    "certifications": [
        r"\b(?:certifications|certificates|licenses|accreditations|credentials|certified)\b"
    ]
}

# Standard English stopwords to eliminate noise during TF-IDF calculation
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
    "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me",
    "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on", "once",
    "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same",
    "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd",
    "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where",
    "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
    "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves", "role", "job", "responsibilities", "requirements", "candidate", "years", "work",
    "working", "experience", "team", "company"
}


# ─────────────────────────────────────────────────────────────
# TF-IDF & COSINE SIMILARITY ENGINE
# ─────────────────────────────────────────────────────────────
def tokenize_and_clean(text: str) -> List[str]:
    """Tokenize text into lowercased alpha words filtering stopwords."""
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9+#.-]{1,30}\b", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def compute_tf_idf_cosine_similarity(doc1: str, doc2: str) -> float:
    """
    Computes TF-IDF Cosine Similarity between two texts (0.0 to 100.0).
    Tries scikit-learn first; seamlessly falls back to exact mathematical pure Python.
    """
    # Attempt 1: scikit-learn TfidfVectorizer if available
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=5000)
        tfidf_matrix = vectorizer.fit_transform([doc1, doc2])
        sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return max(0.0, min(100.0, float(sim) * 100.0))
    except Exception:
        pass

    # Attempt 2: Pure Python mathematical TF-IDF Cosine Similarity
    tokens1 = tokenize_and_clean(doc1)
    tokens2 = tokenize_and_clean(doc2)

    if not tokens1 or not tokens2:
        return 0.0

    # Build Vocabulary
    vocab = sorted(list(set(tokens1 + tokens2)))
    if not vocab:
        return 0.0

    # Calculate Term Frequency (TF)
    tf1: Dict[str, float] = {}
    tf2: Dict[str, float] = {}
    len1 = len(tokens1)
    len2 = len(tokens2)

    for w in tokens1:
        tf1[w] = tf1.get(w, 0.0) + (1.0 / len1)
    for w in tokens2:
        tf2[w] = tf2.get(w, 0.0) + (1.0 / len2)

    # Document Frequency (DF) across our 2 documents
    total_docs = 2.0
    vec1 = []
    vec2 = []

    for w in vocab:
        df = (1.0 if w in tf1 else 0.0) + (1.0 if w in tf2 else 0.0)
        # Smoothed inverse document frequency: log(N / df) + 1
        idf = math.log((total_docs + 1.0) / (df + 1.0)) + 1.0
        vec1.append(tf1.get(w, 0.0) * idf)
        vec2.append(tf2.get(w, 0.0) * idf)

    # Cosine Dot Product & Magnitude
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))

    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0

    sim_score = (dot_product / (mag1 * mag2)) * 100.0
    return max(0.0, min(100.0, sim_score))


# ─────────────────────────────────────────────────────────────
# RESUME SECTION AUDIT
# ─────────────────────────────────────────────────────────────
def audit_resume_sections(text: str) -> Dict[str, bool]:
    """
    Check if the 6 primary standard resume sections are detected in the document text.
    """
    results: Dict[str, bool] = {}
    for section_name, patterns in SECTION_PATTERNS.items():
        found = False
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                found = True
                break
        results[section_name] = found
    return results


# ─────────────────────────────────────────────────────────────
# ACTIONABLE RECOMMENDATIONS GENERATOR
# ─────────────────────────────────────────────────────────────
def generate_recommendations(
    resume_text: str,
    missing_skills: List[str],
    section_audit: Dict[str, bool],
    skill_coverage: float,
    semantic_sim: float
) -> List[Dict[str, str]]:
    """
    Generate contextual, tailored improvement suggestions based on actual content audit.
    """
    recs: List[Dict[str, str]] = []

    # 1. Missing Skills Recommendation
    if missing_skills:
        top_missing = missing_skills[:5]
        recs.append({
            "title": f"Integrate Missing Core Competencies ({', '.join(top_missing)})",
            "description": (
                f"The job description explicitly prioritizes {', '.join(top_missing)}. "
                "If you have relevant academic, personal, or commercial experience with these tools, "
                "incorporate them directly into your project descriptions and skills section."
            )
        })

    # 2. Section Completeness Recommendations
    if not section_audit.get("projects"):
        recs.append({
            "title": "Add a Dedicated Projects Section",
            "description": (
                "Technical recruiters and ATS screeners prioritize hands-on projects to verify applied skills. "
                "Include 2-3 significant projects with live URLs, technologies used, and measurable results."
            )
        })

    if not section_audit.get("certifications"):
        recs.append({
            "title": "Highlight Relevant Certifications or Coursework",
            "description": (
                "Adding industry credentials (e.g. AWS, Coursera, Meta, Google, or university specializations) "
                "proves continuous learning and boosts profile authority."
            )
        })

    if not section_audit.get("skills"):
        recs.append({
            "title": "Format a Clean 'Technical Skills' Category Block",
            "description": (
                "Organize your skills into distinct sub-categories (Languages, Frameworks, Developer Tools, Databases) "
                "near the top of your resume for rapid visual scanning."
            )
        })

    # 3. Quantifiable Impact Audit
    has_metrics = bool(re.search(r"\b(?:\d+%(?:\s+increase|\s+reduction)?|\$\d+k?|\d+\+?\s*(?:users|clients|requests|ms|seconds|hours))\b", resume_text, re.IGNORECASE))
    if not has_metrics:
        recs.append({
            "title": "Quantify Accomplishments with Specific Metrics",
            "description": (
                "Replace passive duty statements with active metrics (e.g., 'Optimized query latency by 35%' "
                "or 'Developed REST API serving 1,000+ daily active users'). Numbers establish credible impact."
            )
        })

    # 4. Action Verbs Audit
    action_verbs = ["built", "designed", "implemented", "engineered", "optimized", "architected", "automated", "spearheaded", "deployed"]
    verb_matches = [v for v in action_verbs if re.search(rf"\b{v}\b", resume_text, re.IGNORECASE)]
    if len(verb_matches) < 3:
        recs.append({
            "title": "Strengthen Bullet Points with Power Action Verbs",
            "description": (
                "Start experience bullet points with strong technical verbs such as 'Architected', 'Deployed', "
                "'Engineered', or 'Refactored' rather than 'Responsible for' or 'Worked on'."
            )
        })

    # 5. Semantic Match Suggestion if similarity is low
    if semantic_sim < 40.0:
        recs.append({
            "title": "Align Resume Phrasing with Job Posting Terminology",
            "description": (
                "Your resume vocabulary deviates from the job description's terminology. Mirror key phrasing "
                "used in the responsibilities section to enhance automated semantic relevance."
            )
        })

    # Fallback if resume is already nearly perfect
    if not recs:
        recs.append({
            "title": "Tailor Your Summary Statement for This Specific Employer",
            "description": (
                "Your skills and document structure exhibit high synergy with this posting. Ensure your top summary "
                "explicitly references the company's core mission and tech stack."
            )
        })

    return recs


# ─────────────────────────────────────────────────────────────
# MASTER ANALYSIS PIPELINE
# ─────────────────────────────────────────────────────────────
def analyze_resume_against_job(resume_text: str, job_description: str) -> Dict[str, Any]:
    """
    Execute full analysis pipeline:
    1. Extract skills from both texts
    2. Compute skill overlap, missing skills, and skill match percentage
    3. Compute TF-IDF Cosine Similarity
    4. Calculate documented weighted overall score:
       overall_score = (similarity_score * 0.4) + (skill_match_score * 0.6)
    5. Audit resume structural sections
    6. Generate actionable improvement recommendations
    """
    resume_text = resume_text or ""
    job_description = job_description or ""

    # 1. Skill Extraction
    resume_skills = extract_skills(resume_text)
    jd_skills = extract_skills(job_description)

    # 2. Skill Comparison
    skill_diff = compare_skills(resume_skills, jd_skills)
    matched_skills = skill_diff["matched"]
    missing_skills = skill_diff["missing"]

    if len(jd_skills) > 0:
        skill_match_score = (len(matched_skills) / len(jd_skills)) * 100.0
    else:
        # If the job description did not specify any recognized skills, default to 100 or semantic
        skill_match_score = 100.0

    # 3. TF-IDF Cosine Similarity
    similarity_score = compute_tf_idf_cosine_similarity(resume_text, job_description)

    # 4. Overall Weighted Score
    # Documented formula: 40% Semantic Similarity + 60% Required Skill Match
    if len(jd_skills) > 0:
        overall_score = (similarity_score * 0.4) + (skill_match_score * 0.6)
    else:
        overall_score = similarity_score

    overall_score = round(max(0.0, min(100.0, overall_score)), 1)
    similarity_score = round(similarity_score, 1)
    skill_match_score = round(skill_match_score, 1)

    # 5. Section Audit
    section_analysis = audit_resume_sections(resume_text)

    # 6. Recommendations
    recommendations = generate_recommendations(
        resume_text=resume_text,
        missing_skills=missing_skills,
        section_audit=section_analysis,
        skill_coverage=skill_match_score,
        semantic_sim=similarity_score
    )

    # 7. Structured Technical Skills Categorization (Hybrid Regex + ML)
    hybrid_extraction = extract_technical_skills_hybrid(resume_text)
    technical_skills = hybrid_extraction.get("technical_skills", {})
    extraction_method = hybrid_extraction.get("extraction_method", "regex_and_ml")
    evidence = hybrid_extraction.get("evidence", {})

    return {
        "similarity_score": similarity_score,
        "skill_match_score": skill_match_score,
        "overall_score": overall_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "resume_skills": resume_skills,
        "jd_skills": jd_skills,
        "section_analysis": section_analysis,
        "recommendations": recommendations,
        "technical_skills": technical_skills,
        "extraction_method": extraction_method,
        "evidence": evidence
    }
