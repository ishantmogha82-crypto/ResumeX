ResumeX programming technical-skill extraction
================================================
Input: resume_dataset.csv (2484 resumes) and Software Skills.xlsx (31821 rows).
All 2484 resumes are retained. The existing resume label is preserved as job_category, not used as a skill label.

Coverage
- Resumes with at least one detected skill: 971
- Resumes with no detected vocabulary match: 1513
- Total resume-skill matches: 2591
- Vocabulary size: 199

Counts by category (resume-skill occurrences)
- Cloud and DevOps: 230
- Cybersecurity and networking: 74
- Data science and analytics: 69
- Databases and data platforms: 192
- Developer tools and IDEs: 138
- Frameworks and libraries: 194
- Programming languages: 1576
- Web and content technologies: 118

Method and limitations
- Case-insensitive phrase matching against programming/developer-focused terms, including relevant terms drawn from the supplied Software Skills workbook.
- These are weak-label candidate annotations, not verified ground truth.
- A mention does not establish proficiency, recency, or hands-on experience.
- Short terms such as C, R, Go, and Git may cause false positives even with word boundaries.
- Skills absent from the vocabulary will be missed. Human review and correction are recommended before supervised model training.
