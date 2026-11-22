from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import asyncio

from config import Config, ENV_FILE, BASE_DIR
from tracker import Tracker
from generator import EmailGenerator
from sender import EmailSender

app = FastAPI(title="Internship Cold Outreach Automation API")
tracker = Tracker()
generator = EmailGenerator()
sender = EmailSender(tracker=tracker)

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

# In-memory sending status for live monitoring
dispatch_status = {
    "is_running": False,
    "current_lead": None,
    "progress": 0,
    "total": 0,
    "logs": []
}

class LeadCreate(BaseModel):
    company: str
    email: str
    contact_name: Optional[str] = ""
    role: Optional[str] = "Software Engineer Intern"
    website: Optional[str] = ""
    notes: Optional[str] = ""

class DraftUpdate(BaseModel):
    lead_id: int
    subject: str
    body: str

class SendBatchRequest(BaseModel):
    lead_ids: Optional[List[int]] = None
    dry_run: bool = False

class TestEmailRequest(BaseModel):
    email: Optional[str] = None

class ConfigUpdate(BaseModel):
    sender_name: str
    sender_email: str
    sender_password: Optional[str] = None
    gemini_api_key: Optional[str] = None
    your_university: str
    your_degree: str
    your_graduation_year: str
    your_skills: str
    your_portfolio_url: str
    your_linkedin_url: str
    min_delay_seconds: int = 35
    max_delay_seconds: int = 75

@app.get("/api/stats")
def get_stats():
    stats = tracker.get_stats()
    stats["dispatch"] = dispatch_status
    return stats

@app.get("/api/leads")
def get_leads(status: Optional[str] = None):
    return tracker.get_all_leads(status=status)

@app.post("/api/leads")
def add_lead(lead: LeadCreate):
    try:
        created = tracker.add_lead(
            company=lead.company,
            email=lead.email,
            contact_name=lead.contact_name or "",
            role=lead.role or "Software Engineer Intern",
            website=lead.website or "",
            notes=lead.notes or ""
        )
        return {"success": True, "lead": created}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/leads/{lead_id}")
def delete_lead(lead_id: int):
    ok = tracker.delete_lead(lead_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True}

class CSVUploadRequest(BaseModel):
    csv_text: str

@app.post("/api/leads/upload-csv")
def upload_csv(req: CSVUploadRequest):
    try:
        res = tracker.import_from_csv_text(req.csv_text)
        return {"success": True, "imported": res["imported"], "skipped": res["skipped"]}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/generate-drafts")
def generate_drafts(lead_ids: Optional[List[int]] = None):
    leads = tracker.get_all_leads()
    if lead_ids:
        targets = [l for l in leads if l["id"] in lead_ids]
    else:
        # Default to all pending leads
        targets = [l for l in leads if l["status"] in ("PENDING", "FAILED")]

    generated_count = 0
    for lead in targets:
        subject, body = generator.generate(lead)
        tracker.update_draft(lead["id"], subject, body)
        generated_count += 1

    return {"success": True, "generated_count": generated_count}

@app.post("/api/update-draft")
def update_draft(req: DraftUpdate):
    ok = tracker.update_draft(req.lead_id, req.subject, req.body)
    if not ok:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"success": True}

@app.post("/api/send-test")
def send_test(req: TestEmailRequest):
    res = sender.send_test_email(req.email)
    return res

def run_dispatch_task(lead_ids: List[int], dry_run: bool):
    global dispatch_status
    dispatch_status["is_running"] = True
    dispatch_status["total"] = len(lead_ids)
    dispatch_status["progress"] = 0
    dispatch_status["logs"] = []

    def callback(evt):
        msg = evt.get("message", "")
        if msg:
            dispatch_status["logs"].append(msg)
            if len(dispatch_status["logs"]) > 100:
                dispatch_status["logs"].pop(0)
        if "index" in evt:
            dispatch_status["progress"] = evt["index"]
            dispatch_status["current_lead"] = evt.get("lead")

    try:
        sender.dispatch_batch(lead_ids, dry_run=dry_run, progress_callback=callback)
    finally:
        dispatch_status["is_running"] = False
        dispatch_status["current_lead"] = None

@app.post("/api/send-batch")
def send_batch(req: SendBatchRequest, background_tasks: BackgroundTasks):
    global dispatch_status
    if dispatch_status["is_running"]:
        raise HTTPException(status_code=400, detail="A dispatch campaign is already running!")

    leads = tracker.get_all_leads()
    if req.lead_ids:
        target_ids = req.lead_ids
    else:
        # Default to all leads in DRAFTED status
        target_ids = [l["id"] for l in leads if l["status"] == "DRAFTED"]

    if not target_ids:
        raise HTTPException(status_code=400, detail="No drafted emails available to send. Generate drafts first.")

    background_tasks.add_task(run_dispatch_task, target_ids, req.dry_run)
    return {"success": True, "queued": len(target_ids), "dry_run": req.dry_run}

@app.get("/api/config")
def get_config():
    return Config.to_dict()

@app.post("/api/config")
def update_config(update: ConfigUpdate):
    # Read existing env lines
    env_data = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_data[k.strip()] = v.strip().strip('"').strip("'")

    env_data["SENDER_NAME"] = update.sender_name
    env_data["SENDER_EMAIL"] = update.sender_email
    if update.sender_password:
        env_data["SENDER_PASSWORD"] = update.sender_password
    if update.gemini_api_key is not None:
        env_data["GEMINI_API_KEY"] = update.gemini_api_key
    env_data["YOUR_UNIVERSITY"] = update.your_university
    env_data["YOUR_DEGREE"] = update.your_degree
    env_data["YOUR_GRADUATION_YEAR"] = update.your_graduation_year
    env_data["YOUR_SKILLS"] = update.your_skills
    env_data["YOUR_PORTFOLIO_URL"] = update.your_portfolio_url
    env_data["YOUR_LINKEDIN_URL"] = update.your_linkedin_url
    env_data["MIN_DELAY_SECONDS"] = str(update.min_delay_seconds)
    env_data["MAX_DELAY_SECONDS"] = str(update.max_delay_seconds)

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        for k, v in env_data.items():
            f.write(f'{k}="{v}"\n')

    # Update in-memory config
    Config.SENDER_NAME = update.sender_name
    Config.SENDER_EMAIL = update.sender_email
    if update.sender_password:
        Config.SENDER_PASSWORD = update.sender_password
    if update.gemini_api_key is not None:
        Config.GEMINI_API_KEY = update.gemini_api_key
    Config.YOUR_UNIVERSITY = update.your_university
    Config.YOUR_DEGREE = update.your_degree
    Config.YOUR_GRADUATION_YEAR = update.your_graduation_year
    Config.YOUR_SKILLS = update.your_skills
    Config.YOUR_PORTFOLIO_URL = update.your_portfolio_url
    Config.YOUR_LINKEDIN_URL = update.your_linkedin_url
    Config.MIN_DELAY_SECONDS = update.min_delay_seconds
    Config.MAX_DELAY_SECONDS = update.max_delay_seconds

    return {"success": True, "config": Config.to_dict()}

# Mount Static Files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_index():
    return FileResponse(str(STATIC_DIR / "index.html"))
