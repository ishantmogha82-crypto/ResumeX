"""
backend/skill_extractor.py – Domain-Specific Skill Extraction Engine.

Features:
- Comprehensive skill ontology across Programming, Libraries, Web, Tools, and Soft Skills
- Precise token matching using word boundaries and punctuation-aware regex
- Prevents false-positive substrings (e.g. 'c' in 'concept', 'go' in 'good', 'java' in 'javascript')
- Grouped skill taxonomies for structured display in reports
- Seamless integration with Machine Learning model (TF-IDF + Multi-label classification)
- Enforces exact in-text evidence verification
- Hybrid extraction method combining Regex and ML with zero duplicate skills
"""

import re
import logging
from typing import Dict, List, Set, Any, Optional

logger = logging.getLogger("ResumeX-SkillExtractor")

# ─────────────────────────────────────────────────────────────
# 5 CANONICAL TECHNICAL CATEGORY KEYS
# ─────────────────────────────────────────────────────────────
CAT_PROGRAMMING = "programming_languages"
CAT_FRAMEWORKS = "frameworks"
CAT_DATABASES = "databases"
CAT_CLOUD_DEVOPS = "cloud_devops"
CAT_DEV_TOOLS = "developer_tools"

# ─────────────────────────────────────────────────────────────
# SKILL TAXONOMY (Regex Base Patterns)
# ─────────────────────────────────────────────────────────────
SKILL_TAXONOMY: Dict[str, Dict[str, List[str]]] = {
    "programming_languages": {
        "Python": [r"\bpython(?:3)?\b"],
        "JavaScript": [r"\bjavascript\b", r"\bjs\b"],
        "TypeScript": [r"\btypescript\b", r"\bts\b"],
        "Java": [r"\bjava\b(?!\s*script)"],
        "C++": [r"\bc\+\+\b", r"\bcpp\b"],
        "C": [r"\bc\b(?![#+a-zA-Z0-9])"],
        "C#": [r"\bc#\b", r"\bc\s*sharp\b"],
        "SQL": [r"\bsql\b", r"\bstructured query language\b", r"\bpostgresql\b", r"\bmysql\b", r"\bsqlite\b"],
        "Go": [r"\bgolang\b", r"\bgo\s+language\b", r"\bgo\b(?=\s*(?:developer|backend|programming|engineer))"],
        "Rust": [r"\brust\b(?=\s*(?:developer|backend|programming|engineer|lang))"],
        "PHP": [r"\bphp\b"],
        "Ruby": [r"\bruby\b"],
        "Swift": [r"\bswift\b(?=\s*(?:developer|programming|ios|app|language|code))"],
        "Kotlin": [r"\bkotlin\b"],
        "Bash": [r"\bbash\b", r"\bshell\s+scripting\b", r"\bpowershell\b"]
    },
    "libraries_frameworks": {
        "NumPy": [r"\bnumpy\b"],
        "Pandas": [r"\bpandas\b"],
        "Scikit-learn": [r"\bscikit[-_]learn\b", r"\bsklearn\b"],
        "TensorFlow": [r"\btensorflow\b", r"\btf\b"],
        "PyTorch": [r"\bpytorch\b"],
        "Matplotlib": [r"\bmatplotlib\b"],
        "Seaborn": [r"\bseaborn\b"],
        "Keras": [r"\bkeras\b"],
        "OpenCV": [r"\bopencv\b"],
        "NLTK": [r"\bnltk\b"],
        "SciPy": [r"\bscipy\b"]
    },
    "web_development": {
        "HTML": [r"\bhtml(?:5)?\b"],
        "CSS": [r"\bcss(?:3)?\b"],
        "React": [r"\breact(?:\.js|js)?\b(?!\s*(?:ion|ive|or))"],
        "Node.js": [r"\bnode(?:\.js|js)?\b"],
        "Express": [r"\bexpress(?:\.js|js)?\b"],
        "Flask": [r"\bflask\b"],
        "Django": [r"\bdjango\b"],
        "FastAPI": [r"\bfastapi\b"],
        "Vue": [r"\bvue(?:\.js|js)?\b"],
        "Angular": [r"\bangular(?:\.js|js)?\b"],
        "Next.js": [r"\bnext(?:\.js|js)?\b"],
        "Tailwind CSS": [r"\btailwind(?:\s*css)?\b"],
        "Bootstrap": [r"\bbootstrap\b"],
        "REST API": [r"\brest(?:ful)?\s*api(?:s)?\b", r"\brest\s*api\b"],
        "GraphQL": [r"\bgraphql\b"]
    },
    "tools_infrastructure": {
        "Git": [r"\bgit\b(?!\s*hub|\s*lab)"],
        "GitHub": [r"\bgithub\b"],
        "GitLab": [r"\bgitlab\b"],
        "Docker": [r"\bdocker\b"],
        "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
        "VS Code": [r"\bvs\s*code\b", r"\bvisual\s*studio\s*code\b"],
        "Linux": [r"\blinux\b", r"\bubuntu\b"],
        "AWS": [r"\baws\b", r"\bamazon\s+web\s+services\b"],
        "Azure": [r"\bazure\b"],
        "GCP": [r"\bgcp\b", r"\bgoogle\s+cloud(?:\s+platform)?\b"],
        "CI/CD": [r"\bci\/cd\b", r"\bcontinuous\s+integration\b"],
        "Jenkins": [r"\bjenkins\b"],
        "Jira": [r"\bjira\b"],
        "Postman": [r"\bpostman\b"]
    },
    "soft_skills": {
        "Communication": [r"\bcommunication\b", r"\bwritten\s+communication\b", r"\bverbal\s+communication\b"],
        "Leadership": [r"\bleadership\b", r"\bmentoring\b", r"\bteam\s+lead\b"],
        "Teamwork": [r"\bteamwork\b", r"\bteam\s+player\b", r"\bcross[- ]functional\b"],
        "Problem Solving": [r"\bproblem[- ]solving\b", r"\banalytical\s+skills\b"],
        "Critical Thinking": [r"\bcritical\s+thinking\b"],
        "Time Management": [r"\btime\s+management\b", r"\bprioritization\b"],
        "Adaptability": [r"\badaptability\b", r"\bagile\b"],
        "Collaboration": [r"\bcollaboration\b", r"\bcollaborative\b"],
        "Project Management": [r"\bproject\s+management\b", r"\bscrum\b", r"\bkanban\b"]
    }
}


# Precompile all regex patterns for high-throughput matching
COMPILED_PATTERNS: Dict[str, List[re.Pattern]] = {}
SKILL_CATEGORY_MAP: Dict[str, str] = {}

for category, skills in SKILL_TAXONOMY.items():
    for skill_name, patterns in skills.items():
        SKILL_CATEGORY_MAP[skill_name] = category
        COMPILED_PATTERNS[skill_name] = [
            re.compile(p, re.IGNORECASE) for p in patterns
        ]

# Map regex taxonomy categories into the 5 target technical categories
REGEX_TO_TECHNICAL_CATEGORY = {
    "programming_languages": CAT_PROGRAMMING,
    "libraries_frameworks": CAT_FRAMEWORKS,
    "web_development": CAT_FRAMEWORKS,
    "tools_infrastructure": CAT_DEV_TOOLS,
}

# Granular regex overrides for technical classification
REGEX_TECHNICAL_OVERRIDES = {
    "Docker": CAT_CLOUD_DEVOPS,
    "Kubernetes": CAT_CLOUD_DEVOPS,
    "AWS": CAT_CLOUD_DEVOPS,
    "Azure": CAT_CLOUD_DEVOPS,
    "GCP": CAT_CLOUD_DEVOPS,
    "Linux": CAT_CLOUD_DEVOPS,
    "CI/CD": CAT_CLOUD_DEVOPS,
    "Jenkins": CAT_CLOUD_DEVOPS,
    "SQL": CAT_DATABASES,
    "PostgreSQL": CAT_DATABASES,
    "MySQL": CAT_DATABASES,
    "SQLite": CAT_DATABASES,
    "HTML": CAT_PROGRAMMING,
    "CSS": CAT_PROGRAMMING,
    "Git": CAT_DEV_TOOLS,
    "GitHub": CAT_DEV_TOOLS,
    "GitLab": CAT_DEV_TOOLS,
    "VS Code": CAT_DEV_TOOLS,
    "Postman": CAT_DEV_TOOLS,
    "Jira": CAT_DEV_TOOLS,
}


def _classify_skill_to_technical_category(skill_name: str, regex_category: Optional[str] = None) -> str:
    """Classify a skill into one of the 5 canonical technical categories."""
    if skill_name in REGEX_TECHNICAL_OVERRIDES:
        return REGEX_TECHNICAL_OVERRIDES[skill_name]
    if regex_category and regex_category in REGEX_TO_TECHNICAL_CATEGORY:
        return REGEX_TO_TECHNICAL_CATEGORY[regex_category]
    return CAT_DEV_TOOLS


def extract_regex_skills(text: str) -> List[str]:
    """
    Extract a unique, ordered list of normalized skill names found in the text using regex.
    """
    if not text:
        return []

    detected_skills = set()
    for skill_name, regex_list in COMPILED_PATTERNS.items():
        for regex in regex_list:
            if regex.search(text):
                detected_skills.add(skill_name)
                break

    return sorted(list(detected_skills))


def extract_technical_skills_hybrid(text: str) -> Dict[str, Any]:
    """
    Master Hybrid Technical Skill Extractor (Regex + Machine Learning).
    Returns structured technical skill categories and extraction metadata.

    Output Schema:
    {
      "technical_skills": {
        "programming_languages": [...],
        "frameworks": [...],
        "databases": [...],
        "cloud_devops": [...],
        "developer_tools": [...]
      },
      "extraction_method": "regex_and_ml",
      "evidence": {
        "Python": "...",
        ...
      }
    }
    """
    categorized: Dict[str, List[str]] = {
        CAT_PROGRAMMING: [],
        CAT_FRAMEWORKS: [],
        CAT_DATABASES: [],
        CAT_CLOUD_DEVOPS: [],
        CAT_DEV_TOOLS: [],
    }
    evidence_map: Dict[str, str] = {}
    seen_skills_lower: Set[str] = set()

    if not text:
        return {
            "technical_skills": categorized,
            "extraction_method": "regex_and_ml",
            "evidence": {}
        }

    # 1. Regex Extraction
    regex_skills = extract_regex_skills(text)
    for skill in regex_skills:
        orig_cat = SKILL_CATEGORY_MAP.get(skill)
        # Exclude soft skills from pure technical categories
        if orig_cat == "soft_skills":
            continue

        target_cat = _classify_skill_to_technical_category(skill, orig_cat)
        if skill.lower() not in seen_skills_lower:
            seen_skills_lower.add(skill.lower())
            categorized[target_cat].append(skill)

    # 2. ML Model Extraction (loads once, singleton)
    method_used = "regex"
    try:
        from backend.ml.predict import get_predictor
        from backend.ml.preprocessing import find_text_evidence, normalize_skill_name

        predictor = get_predictor()
        if predictor.is_loaded:
            method_used = "regex_and_ml"
            ml_result = predictor.predict(text, require_evidence=True)

            for pred in ml_result.get("predictions", []):
                skill_name = pred["skill"]
                canonical = normalize_skill_name(skill_name)
                cat = pred.get("category", CAT_DEV_TOOLS)

                if cat not in categorized:
                    cat = CAT_DEV_TOOLS

                if canonical.lower() not in seen_skills_lower:
                    seen_skills_lower.add(canonical.lower())
                    categorized[cat].append(canonical)

                if pred.get("evidence"):
                    evidence_map[canonical] = pred["evidence"]

        # Ensure evidence exists for regex detected skills as well
        for cat_skills in categorized.values():
            for s in cat_skills:
                if s not in evidence_map:
                    ev = find_text_evidence(text, s)
                    if ev:
                        evidence_map[s] = ev

    except Exception as e:
        logger.warning(f"ML extraction skipped or encountered an error: {e}")

    # Sort skills within each category
    for cat in categorized:
        categorized[cat] = sorted(categorized[cat])

    return {
        "technical_skills": categorized,
        "extraction_method": method_used,
        "evidence": evidence_map
    }


def extract_skills(text: str) -> List[str]:
    """
    Extract a unique, ordered list of all normalized skill names found in the text.
    Combines high-precision regex extraction with ML-extracted technical skills.
    Preserves backward compatibility with existing tests and API callers.
    """
    if not text:
        return []

    # 1. Extract base regex skills (including soft skills)
    all_skills_set = set(extract_regex_skills(text))

    # 2. Augment with ML technical skills if available
    try:
        hybrid = extract_technical_skills_hybrid(text)
        for cat_list in hybrid["technical_skills"].values():
            for skill in cat_list:
                all_skills_set.add(skill)
    except Exception as e:
        logger.warning(f"ML augmentation in extract_skills skipped: {e}")

    return sorted(list(all_skills_set))


def extract_categorized_skills(text: str) -> Dict[str, List[str]]:
    """
    Extract skills and group them into their taxonomy categories:
    (programming_languages, libraries_frameworks, web_development, tools_infrastructure, soft_skills)
    Maintains backward compatibility with legacy reporting and UI components.
    """
    all_skills = extract_skills(text)
    categorized: Dict[str, List[str]] = {cat: [] for cat in SKILL_TAXONOMY.keys()}

    for skill in all_skills:
        cat = SKILL_CATEGORY_MAP.get(skill)
        if cat in categorized:
            categorized[cat].append(skill)
        else:
            # Categorize ML-added skills into existing taxonomy buckets
            if skill in ["PostgreSQL", "MySQL", "MongoDB", "SQLite", "Oracle Database", "Cassandra"]:
                categorized["tools_infrastructure"].append(skill)
            elif skill in ["Spring", "Spring Boot", "Hibernate", ".NET", "ASP.NET"]:
                categorized["libraries_frameworks"].append(skill)
            else:
                categorized["tools_infrastructure"].append(skill)

    return categorized


def compare_skills(resume_skills: List[str], jd_skills: List[str]) -> Dict[str, List[str]]:
    """
    Compare resume skills against job description skills.
    Returns:
      matched_skills: present in BOTH resume and JD
      missing_skills: present in JD but NOT in resume
      bonus_skills: present in resume but NOT specifically required in JD
    """
    resume_set: Set[str] = set(resume_skills)
    jd_set: Set[str] = set(jd_skills)

    matched = sorted(list(resume_set.intersection(jd_set)))
    missing = sorted(list(jd_set.difference(resume_set)))
    bonus = sorted(list(resume_set.difference(jd_set)))

    return {
        "matched": matched,
        "missing": missing,
        "bonus": bonus
    }
