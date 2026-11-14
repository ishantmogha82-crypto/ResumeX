"""
backend/ml/preprocessing.py – Text normalization, weak-label sanitization,
and category ontology mapping for ML skill extraction in ResumeX.
"""

import re
from typing import Dict, List, Set, Tuple, Optional


# ─────────────────────────────────────────────────────────────
# 5 TARGET TECHNICAL SKILL CATEGORIES
# ─────────────────────────────────────────────────────────────
CATEGORY_PROGRAMMING = "programming_languages"
CATEGORY_FRAMEWORKS = "frameworks"
CATEGORY_DATABASES = "databases"
CATEGORY_CLOUD_DEVOPS = "cloud_devops"
CATEGORY_DEV_TOOLS = "developer_tools"

VALID_CATEGORIES = {
    CATEGORY_PROGRAMMING,
    CATEGORY_FRAMEWORKS,
    CATEGORY_DATABASES,
    CATEGORY_CLOUD_DEVOPS,
    CATEGORY_DEV_TOOLS,
}

# Mapping raw vocabulary categories to our 5 canonical categories
VOCAB_CATEGORY_MAPPING = {
    "Programming languages": CATEGORY_PROGRAMMING,
    "Frameworks and libraries": CATEGORY_FRAMEWORKS,
    "Databases and data platforms": CATEGORY_DATABASES,
    "Cloud and DevOps": CATEGORY_CLOUD_DEVOPS,
    "Cybersecurity and networking": CATEGORY_CLOUD_DEVOPS,
    "Developer tools and IDEs": CATEGORY_DEV_TOOLS,
    "Data science and analytics": CATEGORY_DEV_TOOLS,
    "Web and content technologies": CATEGORY_DEV_TOOLS,
}

# Granular overrides for specific tools/skills
SKILL_CATEGORY_OVERRIDES = {
    # Web / Frameworks
    "HTML": CATEGORY_PROGRAMMING,
    "CSS": CATEGORY_PROGRAMMING,
    "XML": CATEGORY_PROGRAMMING,
    "JavaScript": CATEGORY_PROGRAMMING,
    "TypeScript": CATEGORY_PROGRAMMING,
    "SQL": CATEGORY_DATABASES,
    "PL/SQL": CATEGORY_DATABASES,
    "Oracle PL/SQL": CATEGORY_DATABASES,
    "T-SQL": CATEGORY_DATABASES,
    "MySQL": CATEGORY_DATABASES,
    "PostgreSQL": CATEGORY_DATABASES,
    "MongoDB": CATEGORY_DATABASES,
    "SQLite": CATEGORY_DATABASES,
    "Oracle Database": CATEGORY_DATABASES,
    "Microsoft SQL Server": CATEGORY_DATABASES,
    "SQL Server": CATEGORY_DATABASES,
    "Cassandra": CATEGORY_DATABASES,
    "Elasticsearch": CATEGORY_DATABASES,
    "Redis": CATEGORY_DATABASES,
    "NoSQL": CATEGORY_DATABASES,
    "Teradata Database": CATEGORY_DATABASES,
    "Amazon Redshift": CATEGORY_DATABASES,
    "Microsoft Access": CATEGORY_DATABASES,
    "Database software": CATEGORY_DATABASES,

    # Frameworks & Libraries
    "React": CATEGORY_FRAMEWORKS,
    "Angular": CATEGORY_FRAMEWORKS,
    "Vue": CATEGORY_FRAMEWORKS,
    "Node.js": CATEGORY_FRAMEWORKS,
    "Express": CATEGORY_FRAMEWORKS,
    "Flask": CATEGORY_FRAMEWORKS,
    "Django": CATEGORY_FRAMEWORKS,
    "FastAPI": CATEGORY_FRAMEWORKS,
    "Spring": CATEGORY_FRAMEWORKS,
    "Spring Boot": CATEGORY_FRAMEWORKS,
    "Hibernate": CATEGORY_FRAMEWORKS,
    ".NET": CATEGORY_FRAMEWORKS,
    "ASP.NET": CATEGORY_FRAMEWORKS,
    "jQuery": CATEGORY_FRAMEWORKS,
    "Bootstrap": CATEGORY_FRAMEWORKS,
    "Tailwind CSS": CATEGORY_FRAMEWORKS,
    "NumPy": CATEGORY_FRAMEWORKS,
    "Pandas": CATEGORY_FRAMEWORKS,
    "scikit-learn": CATEGORY_FRAMEWORKS,
    "Scikit-learn": CATEGORY_FRAMEWORKS,
    "TensorFlow": CATEGORY_FRAMEWORKS,
    "PyTorch": CATEGORY_FRAMEWORKS,
    "Keras": CATEGORY_FRAMEWORKS,
    "OpenCV": CATEGORY_FRAMEWORKS,
    "Matplotlib": CATEGORY_FRAMEWORKS,
    "Seaborn": CATEGORY_FRAMEWORKS,
    "NLTK": CATEGORY_FRAMEWORKS,
    "SciPy": CATEGORY_FRAMEWORKS,
    "Apache Spark": CATEGORY_FRAMEWORKS,
    "Hadoop": CATEGORY_FRAMEWORKS,
    "Ruby on Rails": CATEGORY_FRAMEWORKS,
    "LAMP Stack": CATEGORY_FRAMEWORKS,
    "JSP": CATEGORY_FRAMEWORKS,

    # Cloud & DevOps
    "AWS": CATEGORY_CLOUD_DEVOPS,
    "Amazon Web Services": CATEGORY_CLOUD_DEVOPS,
    "Azure": CATEGORY_CLOUD_DEVOPS,
    "Microsoft Azure": CATEGORY_CLOUD_DEVOPS,
    "GCP": CATEGORY_CLOUD_DEVOPS,
    "Google Cloud": CATEGORY_CLOUD_DEVOPS,
    "Docker": CATEGORY_CLOUD_DEVOPS,
    "Kubernetes": CATEGORY_CLOUD_DEVOPS,
    "Linux": CATEGORY_CLOUD_DEVOPS,
    "Unix": CATEGORY_CLOUD_DEVOPS,
    "Jenkins": CATEGORY_CLOUD_DEVOPS,
    "Git": CATEGORY_CLOUD_DEVOPS,
    "GitHub": CATEGORY_CLOUD_DEVOPS,
    "GitLab": CATEGORY_CLOUD_DEVOPS,
    "Bitbucket": CATEGORY_CLOUD_DEVOPS,
    "CI/CD": CATEGORY_CLOUD_DEVOPS,
    "Puppet": CATEGORY_CLOUD_DEVOPS,
    "Nagios": CATEGORY_CLOUD_DEVOPS,
    "Splunk": CATEGORY_CLOUD_DEVOPS,
    "Citrix": CATEGORY_CLOUD_DEVOPS,
    "Wireshark": CATEGORY_CLOUD_DEVOPS,
    "Red Hat Enterprise Linux": CATEGORY_CLOUD_DEVOPS,

    # Developer Tools & Platforms
    "Visual Studio": CATEGORY_DEV_TOOLS,
    "VS Code": CATEGORY_DEV_TOOLS,
    "Postman": CATEGORY_DEV_TOOLS,
    "Android Studio": CATEGORY_DEV_TOOLS,
    "Xcode": CATEGORY_DEV_TOOLS,
    "NetBeans": CATEGORY_DEV_TOOLS,
    "Atlassian JIRA": CATEGORY_DEV_TOOLS,
    "Jira": CATEGORY_DEV_TOOLS,
    "WordPress": CATEGORY_DEV_TOOLS,
    "Dreamweaver": CATEGORY_DEV_TOOLS,
    "Drupal": CATEGORY_DEV_TOOLS,
    "Microsoft SharePoint": CATEGORY_DEV_TOOLS,
    "Tableau": CATEGORY_DEV_TOOLS,
    "Power BI": CATEGORY_DEV_TOOLS,
    "SAS": CATEGORY_DEV_TOOLS,
    "MATLAB": CATEGORY_PROGRAMMING,
    "QlikView": CATEGORY_DEV_TOOLS,
}

# Canonical normalization map (synonyms / aliases -> canonical name)
SKILL_CANONICAL_NAME_MAP = {
    "amazon web services": "AWS",
    "aws": "AWS",
    "microsoft azure": "Azure",
    "azure": "Azure",
    "google cloud platform": "GCP",
    "google cloud": "GCP",
    "gcp": "GCP",
    "scikit-learn": "Scikit-learn",
    "sklearn": "Scikit-learn",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "py": "Python",
    "python": "Python",
    "python3": "Python",
    "golang": "Go",
    "go language": "Go",
    "c++": "C++",
    "cpp": "C++",
    "c#": "C#",
    "c sharp": "C#",
    "dot net": ".NET",
    ".net": ".NET",
    "react.js": "React",
    "reactjs": "React",
    "react": "React",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "node": "Node.js",
    "express.js": "Express",
    "expressjs": "Express",
    "express": "Express",
    "vue.js": "Vue",
    "vuejs": "Vue",
    "vue": "Vue",
    "angular.js": "Angular",
    "angularjs": "Angular",
    "angular": "Angular",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "ms sql": "SQL Server",
    "microsoft sql server": "SQL Server",
    "sql server": "SQL Server",
    "github": "GitHub",
    "gitlab": "GitLab",
    "docker": "Docker",
    "bash": "Bash",
    "powershell": "PowerShell",
    "microsoft windows powershell": "PowerShell",
    "visual basic": "Visual Basic",
    "microsoft visual basic": "Visual Basic",
    "vba": "VBA",
    "visual basic for applications": "VBA",
    "html5": "HTML",
    "html": "HTML",
    "css3": "CSS",
    "css": "CSS",
}


def normalize_skill_name(raw_name: str) -> str:
    """Normalize skill name to standard casing/canonical form."""
    if not raw_name:
        return ""
    cleaned = raw_name.strip()
    lower = cleaned.lower()
    return SKILL_CANONICAL_NAME_MAP.get(lower, cleaned)


def get_skill_category(skill_name: str, default_vocab_category: Optional[str] = None) -> str:
    """Resolve skill name to one of the 5 canonical technical categories."""
    canonical = normalize_skill_name(skill_name)
    if canonical in SKILL_CATEGORY_OVERRIDES:
        return SKILL_CATEGORY_OVERRIDES[canonical]
    if skill_name in SKILL_CATEGORY_OVERRIDES:
        return SKILL_CATEGORY_OVERRIDES[skill_name]

    if default_vocab_category and default_vocab_category in VOCAB_CATEGORY_MAPPING:
        return VOCAB_CATEGORY_MAPPING[default_vocab_category]

    return CATEGORY_DEV_TOOLS


# ─────────────────────────────────────────────────────────────
# WEAK LABEL SANITIZATION RULES
# ─────────────────────────────────────────────────────────────
# Ambiguous short terms that generate high false positives in non-technical resumes
AMBIGUOUS_SHORT_TERMS = {
    "C": [
        r"\bc\s*\+\+",
        r"\b(?:ansi\s+c|c\s+programming|c\s+language|embedded\s+c|c\s*,\s*c\+\+|objective-c)\b",
        r"\b(?:c\s+developer|c\s+software|c\s+code)\b",
    ],
    "R": [
        r"\br\s+(?:programming|language|script|studio|package|code)\b",
        r"\b(?:r\s*,\s*python|python\s*,\s*r|r\s+and\s+python)\b",
        r"\br\s*(?:for\s+data\s+science|for\s+statistics|shiny)\b",
    ],
    "Go": [
        r"\b(?:golang|go\s+language|go\s+developer|go\s+programming|go\s+backend)\b",
    ],
    "Swift": [
        r"\b(?:swift\s+developer|swift\s+programming|swift\s+language|swift\s+ios|swiftui)\b",
    ],
    "Git": [
        r"\b(?:git\s+version|git\s+branch|git\s+commit|git\s+repository|github|gitlab|git\s+cli)\b",
    ],
    "SAS": [
        r"\b(?:sas\s+programmer|sas\s+analytics|sas\s+software|sas\s+data|sas\s+macro|sas\s+base)\b",
    ],
}


def has_ambiguous_term_context(text: str, term: str) -> bool:
    """Check whether an ambiguous short token (C, R, Go, Swift) has real technical context."""
    patterns = AMBIGUOUS_SHORT_TERMS.get(term)
    if not patterns:
        return True
    lower_text = text.lower()
    for p in patterns:
        if re.search(p, lower_text):
            return True
    return False


NON_TECH_JOB_CATEGORIES = {
    "HR", "CHEF", "FITNESS", "AGRICULTURE", "APPAREL", "ARTS",
    "AUTOMOBILE", "AVIATION", "BANKING", "BPO", "CONSULTANT",
    "PUBLIC-RELATIONS", "TEACHER", "ADVOCATE", "ACCOUNTANT"
}


def sanitize_weak_labels(
    text: str,
    raw_skills: List[str],
    job_category: Optional[str] = None
) -> List[str]:
    """
    Remove spurious weak labels caused by vocabulary keyword matching
    without sufficient technical context.
    """
    if not raw_skills:
        return []

    is_non_tech = bool(job_category and job_category.upper() in NON_TECH_JOB_CATEGORIES)
    cleaned_skills = []

    for raw in raw_skills:
        skill = normalize_skill_name(raw)

        # Check ambiguous short words
        if skill in AMBIGUOUS_SHORT_TERMS:
            if not has_ambiguous_term_context(text, skill):
                # Dropped as weak-label noise
                continue

        # Check if the skill name actually appears in the text
        # (Escape punctuation in skill name)
        escaped = re.escape(skill)
        pattern = rf"(?i)\b{escaped}\b"
        if skill in ["C++", "C#", ".NET"]:
            escaped_special = re.escape(skill)
            pattern = rf"(?i)(?:^|[\s,;/]){escaped_special}(?:$|[\s,;/])"

        if not re.search(pattern, text):
            # Check canonical alias match
            found_alias = False
            for alias, target in SKILL_CANONICAL_NAME_MAP.items():
                if target == skill and re.search(rf"(?i)\b{re.escape(alias)}\b", text):
                    found_alias = True
                    break
            if not found_alias:
                continue

        # If non-tech resume has only 1 suspicious programming language and no other tech skills
        if is_non_tech and skill in ["Swift", "Go", "Perl", "Rust"] and not has_ambiguous_term_context(text, skill):
            continue

        cleaned_skills.append(skill)

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for s in cleaned_skills:
        if s.lower() not in seen:
            seen.add(s.lower())
            deduped.append(s)

    return deduped


def clean_resume_text(text: str) -> str:
    """Normalize text representation for ML vectorization."""
    if not text:
        return ""
    # Normalize unicode spaces & punctuation
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    # Preserve key technology symbols (+, #, ., -) while cleaning other punctuation
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def find_text_evidence(text: str, skill: str, window_chars: int = 40) -> Optional[str]:
    """
    Extract exact in-text evidence snippet where the skill is mentioned.
    Returns e.g. '...experience developing in Python 3.9 on AWS...'
    """
    if not text or not skill:
        return None

    canonical = normalize_skill_name(skill)
    search_terms = [re.escape(skill)]
    for alias, target in SKILL_CANONICAL_NAME_MAP.items():
        if target == canonical:
            search_terms.append(re.escape(alias))

    for term in search_terms:
        pattern = rf"(?i)(?:^|[\s,;/(])({term})(?:$|[\s,;/).])"
        match = re.search(pattern, text)
        if match:
            start = max(0, match.start() - window_chars)
            end = min(len(text), match.end() + window_chars)
            snippet = text[start:end].replace("\n", " ").strip()
            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(text) else ""
            return f"{prefix}{snippet}{suffix}"

    return None

