"""
models/database.py – SQLAlchemy ORM models for ResumeX.

Learning note:
  ORM = Object Relational Mapper.  Instead of writing raw SQL, we define Python
  classes (called "models") that SQLAlchemy automatically maps to database
  tables.  Every attribute on the class becomes a column in the table.

Tables created here:
  users       – registered accounts
  resumes     – uploaded resume files + extracted text
  analyses    – stored results of resume ↔ job-description comparisons
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

# The db object is the bridge between Flask and SQLAlchemy.
# It is created here without an app, then bound to the app in app.py via init_db().
# This pattern is called "late binding" and prevents circular imports.
db = SQLAlchemy()


def init_db(app):
    """Bind the db object to the Flask app and create all tables."""
    db.init_app(app)
    with app.app_context():
        db.create_all()   # creates tables if they don't already exist


# ─────────────────────────────────────────────────────────────────────────────
# Helper: current UTC time (timezone-aware)
# ─────────────────────────────────────────────────────────────────────────────
def utcnow():
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Model: User
# ─────────────────────────────────────────────────────────────────────────────
class User(db.Model):
    """
    Stores registered user accounts.

    Columns
    -------
    id            : auto-incrementing primary key
    name          : display name entered at registration
    email         : unique login identifier
    password_hash : bcrypt/pbkdf2 hash – we NEVER store the plain password
    created_at    : UTC timestamp of account creation
    """

    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships: accessing user.resumes gives all Resume rows for this user.
    # cascade="all, delete-orphan" means deleting a user also deletes their resumes.
    resumes  = db.relationship("Resume",   back_populates="user", cascade="all, delete-orphan", lazy="select")
    analyses = db.relationship("Analysis", back_populates="user", cascade="all, delete-orphan", lazy="select")

    def to_dict(self) -> dict:
        """Return a safe dictionary (never include password_hash)."""
        return {
            "id":         self.id,
            "name":       self.name,
            "email":      self.email,
            "created_at": self.created_at.isoformat(),
        }

    def __repr__(self):
        return f"<User id={self.id} email={self.email!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# Model: Resume
# ─────────────────────────────────────────────────────────────────────────────
class Resume(db.Model):
    """
    Stores metadata and extracted text for each uploaded resume.

    We store the extracted text (not the binary file) in the database so the
    analysis engine can operate without touching the filesystem every time.
    The original file is kept in uploads/ for reference and download.

    Columns
    -------
    id             : primary key
    user_id        : foreign key → users.id
    filename       : sanitized filename as saved on disk
    original_name  : the filename the user originally uploaded
    file_path      : absolute path to the saved file on disk
    extracted_text : plain-text content pulled from the PDF / DOCX
    uploaded_at    : UTC timestamp
    """

    __tablename__ = "resumes"

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    filename       = db.Column(db.String(255), nullable=False)
    original_name  = db.Column(db.String(255), nullable=False)
    file_path      = db.Column(db.String(512), nullable=False)
    extracted_text = db.Column(db.Text, nullable=True)
    uploaded_at    = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user     = db.relationship("User",     back_populates="resumes")
    analyses = db.relationship("Analysis", back_populates="resume", cascade="all, delete-orphan", lazy="select")

    def to_dict(self) -> dict:
        return {
            "id":            self.id,
            "filename":      self.filename,
            "original_name": self.original_name,
            "uploaded_at":   self.uploaded_at.isoformat(),
            "has_text":      bool(self.extracted_text),
        }

    def __repr__(self):
        return f"<Resume id={self.id} filename={self.filename!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# Model: Analysis
# ─────────────────────────────────────────────────────────────────────────────
class Analysis(db.Model):
    """
    Stores the result of one resume ↔ job-description analysis run.

    Score fields
    ------------
    similarity_score   : TF-IDF cosine similarity × 100  (0–100)
    skill_match_score  : percentage of JD skills found in resume  (0–100)
    overall_score      : weighted blend of the two scores  (0–100)

    JSON text fields
    ----------------
    SQLite has no native JSON column, so we store JSON-encoded strings and
    decode them in Python.  When migrating to PostgreSQL, change these to
    db.JSON for native support.
    """

    __tablename__ = "analyses"

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey("users.id"),   nullable=False, index=True)
    resume_id        = db.Column(db.Integer, db.ForeignKey("resumes.id"), nullable=False, index=True)

    # Job description metadata
    job_title        = db.Column(db.String(255), nullable=True)
    company_name     = db.Column(db.String(255), nullable=True)
    job_description  = db.Column(db.Text,        nullable=False)

    # Scores (stored as floats, displayed as percentages in the UI)
    similarity_score  = db.Column(db.Float, nullable=False, default=0.0)
    skill_match_score = db.Column(db.Float, nullable=False, default=0.0)
    overall_score     = db.Column(db.Float, nullable=False, default=0.0)

    # JSON-encoded lists / dicts
    matched_skills   = db.Column(db.Text, nullable=True)   # JSON list of strings
    missing_skills   = db.Column(db.Text, nullable=True)   # JSON list of strings
    resume_skills    = db.Column(db.Text, nullable=True)   # JSON list of strings
    jd_skills        = db.Column(db.Text, nullable=True)   # JSON list of strings
    section_analysis = db.Column(db.Text, nullable=True)   # JSON dict
    recommendations  = db.Column(db.Text, nullable=True)   # JSON list of strings

    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user   = db.relationship("User",   back_populates="analyses")
    resume = db.relationship("Resume", back_populates="analyses")

    def to_dict(self) -> dict:
        import json

        def _loads(val):
            """Safely decode a JSON column value."""
            if val is None:
                return []
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return []

        return {
            "id":               self.id,
            "resume_id":        self.resume_id,
            "resume_filename":  self.resume.original_name if self.resume else None,
            "job_title":        self.job_title,
            "company_name":     self.company_name,
            "similarity_score": round(self.similarity_score, 1),
            "skill_match_score":round(self.skill_match_score, 1),
            "overall_score":    round(self.overall_score, 1),
            "matched_skills":   _loads(self.matched_skills),
            "missing_skills":   _loads(self.missing_skills),
            "resume_skills":    _loads(self.resume_skills),
            "jd_skills":        _loads(self.jd_skills),
            "section_analysis": _loads(self.section_analysis) or {},
            "recommendations":  _loads(self.recommendations),
            "created_at":       self.created_at.isoformat(),
        }

    def __repr__(self):
        return f"<Analysis id={self.id} score={self.overall_score}>"

