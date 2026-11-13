"""
backend/skill_extractor.py – Domain-Specific Skill Extraction Engine.

Features:
- Comprehensive skill ontology across Programming, Libraries, Web, Tools, and Soft Skills
- Precise token matching using word boundaries and punctuation-aware regex
- Prevents false-positive substrings (e.g. 'c' in 'concept', 'go' in 'good', 'java' in 'javascript')
- Grouped skill taxonomies for structured display in reports
"""

import re
from typing import Dict, List, Set


# ─────────────────────────────────────────────────────────────
# SKILL TAXONOMY
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
        "Swift": [r"\bswift\b"],
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


def extract_skills(text: str) -> List[str]:
    """
    Extract a unique, ordered list of normalized skill names found in the text.
    Uses regex word boundary rules to prevent false positives.
    """
    if not text:
        return []

    detected_skills = set()

    for skill_name, regex_list in COMPILED_PATTERNS.items():
        for regex in regex_list:
            if regex.search(text):
                detected_skills.add(skill_name)
                break

    # Return as sorted list for consistency
    return sorted(list(detected_skills))


def extract_categorized_skills(text: str) -> Dict[str, List[str]]:
    """
    Extract skills and group them into their taxonomy categories:
    (programming_languages, libraries_frameworks, web_development, tools_infrastructure, soft_skills)
    """
    all_skills = extract_skills(text)
    categorized: Dict[str, List[str]] = {cat: [] for cat in SKILL_TAXONOMY.keys()}

    for skill in all_skills:
        cat = SKILL_CATEGORY_MAP.get(skill)
        if cat in categorized:
            categorized[cat].append(skill)

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
