# Configuration file for Email Automation System
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
RESUME_DIR = BASE_DIR / "resume"

# Ensure essential directories exist
DATA_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
RESUME_DIR.mkdir(exist_ok=True)

def load_env():
    """Simple parser for .env file without external dependencies."""
    env_vars = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'").strip('"')
                env_vars[key] = val
                os.environ[key] = val
    return env_vars

load_env()

class Config:
    # SMTP Settings (defaults to Gmail)
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    
    # Credentials
    SENDER_NAME = os.getenv("SENDER_NAME", "Your Name")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
    SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")  # Gmail App Password (16 chars)
    
    # AI Personalization (Optional Gemini API Key)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    # User Profile / Pitch Details
    YOUR_UNIVERSITY = os.getenv("YOUR_UNIVERSITY", "Your University / College")
    YOUR_DEGREE = os.getenv("YOUR_DEGREE", "B.Tech Computer Science")
    YOUR_GRADUATION_YEAR = os.getenv("YOUR_GRADUATION_YEAR", "2026")
    YOUR_SKILLS = os.getenv("YOUR_SKILLS", "Python, React, TypeScript, FastAPI, PostgreSQL, Git")
    YOUR_PORTFOLIO_URL = os.getenv("YOUR_PORTFOLIO_URL", "https://github.com/yourusername")
    YOUR_LINKEDIN_URL = os.getenv("YOUR_LINKEDIN_URL", "https://linkedin.com/in/yourusername")
    
    # Attachment
    ATTACHMENT_PATH = os.getenv("ATTACHMENT_PATH", str(RESUME_DIR / "resume.pdf"))
    
    # Safety Throttles
    MIN_DELAY_SECONDS = int(os.getenv("MIN_DELAY_SECONDS", "35"))
    MAX_DELAY_SECONDS = int(os.getenv("MAX_DELAY_SECONDS", "75"))
    MAX_DAILY_EMAILS = int(os.getenv("MAX_DAILY_EMAILS", "30"))

    @classmethod
    def to_dict(cls):
        return {
            "smtp_server": cls.SMTP_SERVER,
            "smtp_port": cls.SMTP_PORT,
            "sender_name": cls.SENDER_NAME,
            "sender_email": cls.SENDER_EMAIL,
            "has_password": bool(cls.SENDER_PASSWORD),
            "has_gemini_key": bool(cls.GEMINI_API_KEY),
            "your_university": cls.YOUR_UNIVERSITY,
            "your_degree": cls.YOUR_DEGREE,
            "your_graduation_year": cls.YOUR_GRADUATION_YEAR,
            "your_skills": cls.YOUR_SKILLS,
            "your_portfolio_url": cls.YOUR_PORTFOLIO_URL,
            "your_linkedin_url": cls.YOUR_LINKEDIN_URL,
            "attachment_path": cls.ATTACHMENT_PATH,
            "has_resume": Path(cls.ATTACHMENT_PATH).exists() if cls.ATTACHMENT_PATH else False,
            "min_delay_seconds": cls.MIN_DELAY_SECONDS,
            "max_delay_seconds": cls.MAX_DELAY_SECONDS,
            "max_daily_emails": cls.MAX_DAILY_EMAILS
        }
