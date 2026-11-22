import json
import re
from typing import Dict, Any, Tuple
import httpx
from config import Config

class EmailGenerator:
    def __init__(self, config=Config):
        self.config = config

    def generate(self, lead: Dict[str, Any]) -> Tuple[str, str]:
        """
        Generates a personalized subject and email body for a target lead.
        Uses Gemini API if key is available; otherwise falls back to smart templating.
        """
        if self.config.GEMINI_API_KEY:
            try:
                subject, body = self._generate_with_gemini(lead)
                if subject and body:
                    return subject, body
            except Exception as e:
                print(f"[Warning] Gemini generation failed: {e}. Falling back to smart template.")

        return self._generate_with_template(lead)

    def _generate_with_gemini(self, lead: Dict[str, Any]) -> Tuple[str, str]:
        """Call Gemini API via httpx for contextual, hyper-personalized drafting."""
        prompt = f"""
You are an expert cold email coach helping a talented student land an internship at a startup.
Write an authentic, highly targeted, respectful, and concise cold email (under 120 words).

Candidate Profile:
- Name: {self.config.SENDER_NAME}
- University: {self.config.YOUR_UNIVERSITY} ({self.config.YOUR_DEGREE}, Class of {self.config.YOUR_GRADUATION_YEAR})
- Skills: {self.config.YOUR_SKILLS}
- Portfolio/GitHub: {self.config.YOUR_PORTFOLIO_URL}
- LinkedIn: {self.config.YOUR_LINKEDIN_URL}

Target Company & Lead:
- Company: {lead.get('company')}
- Contact Name: {lead.get('contact_name') or 'Hiring Team'}
- Desired Role: {lead.get('role') or 'Software Engineer Intern'}
- Company Website: {lead.get('website', '')}
- Company Context / Notes: {lead.get('notes', '')}

Rules:
1. The tone must be genuine, professional, and enthusiastic without being sycophantic or robotic.
2. Subject line should be short and curiosity-sparking (e.g. "Quick note regarding [Company] & [Specific area] | [Candidate Name]").
3. Body must be 3-4 punchy paragraphs:
   - Greeting: "Hi [First Name]," (or "Hi [Company] team,")
   - The Hook: 1 sentence showing genuine interest in what their product or team does.
   - Proof of Work: 1-2 sentences highlighting how the candidate's skills / projects align with what the company is building.
   - Soft CTA: Ask if they are open to a brief 10-minute chat or considering interns for upcoming cycles.
   - Sign-off with Name and links (Portfolio, LinkedIn, mention attached resume).
4. Output EXACTLY valid JSON with keys: "subject" and "body". Do NOT wrap in markdown quotes if possible.
"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.config.GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600}
        }
        
        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            # Clean markdown code block if present
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
            cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE).strip()
            
            parsed = json.loads(cleaned)
            return parsed.get("subject", "").strip(), parsed.get("body", "").strip()

    def _generate_with_template(self, lead: Dict[str, Any]) -> Tuple[str, str]:
        """Smart contextual template generation with dynamic personalization logic."""
        company = lead.get("company", "your team")
        contact_name = lead.get("contact_name", "").strip()
        
        # Smart greeting handling (deals with titles like Dr., Prof., etc.)
        if contact_name:
            parts = contact_name.split()
            honorifics = ("dr.", "dr", "prof.", "prof", "mr.", "mr", "ms.", "ms", "mrs.", "mrs")
            if parts[0].lower() in honorifics and len(parts) > 1:
                greeting = f"Hi {parts[0].capitalize()} {parts[-1]},"
            else:
                greeting = f"Hi {parts[0]},"
        else:
            greeting = f"Hi {company} team,"
        
        role = lead.get("role", "Software Engineering Intern")
        notes = (lead.get("notes") or "").strip()
        
        # Analyze company focus from notes & role
        notes_lower = notes.lower()
        if any(w in notes_lower for w in ["ai", "agent", "llm", "machine learning", "pytorch", "model"]):
            subject = f"Question re: {company}'s AI stack & {role} inquiry"
            focus_hook = f"I've been following what you're building at {company}" + (f" ({notes})" if notes else "") + ", especially how you're applying AI."
            skill_highlight = f"As a student at {self.config.YOUR_UNIVERSITY} focused on machine learning and backend systems, I've spent considerable time working with {self.config.YOUR_SKILLS}."
        elif any(w in notes_lower for w in ["frontend", "fullstack", "full stack", "react", "next", "web", "design"]):
            subject = f"Connecting re: {company}'s product & {role} opening"
            focus_hook = f"I recently came across {company}" + (f" and loved the focus on {notes}" if notes else " and was really impressed by your product") + "."
            skill_highlight = f"I'm a {self.config.YOUR_DEGREE} student at {self.config.YOUR_UNIVERSITY} with hands-on experience in full-stack development, specifically using {self.config.YOUR_SKILLS}."
        elif any(w in notes_lower for w in ["cloud", "devops", "kubernetes", "infra", "backend", "scale", "database"]):
            subject = f"Inquiry regarding {company}'s backend engineering & {role}"
            focus_hook = f"I came across {company}'s engineering work" + (f" regarding {notes}" if notes else "") + " and wanted to reach out."
            skill_highlight = f"I'm currently studying at {self.config.YOUR_UNIVERSITY} with a focus on scalable systems, working regularly with {self.config.YOUR_SKILLS}."
        else:
            subject = f"{self.config.SENDER_NAME} - {role} interest at {company}"
            focus_hook = f"I've been following {company}'s journey" + (f" ({notes})" if notes else "") + " and really admire the mission."
            skill_highlight = f"I am a {self.config.YOUR_DEGREE} student at {self.config.YOUR_UNIVERSITY} with strong fundamentals in {self.config.YOUR_SKILLS}."

        body = f"""{greeting}

{focus_hook}

{skill_highlight} I'm actively looking for a {role} opportunity where I can contribute to shipping features from day one while learning from your engineering team.

You can check out some of the projects I've built here:
- Portfolio / GitHub: {self.config.YOUR_PORTFOLIO_URL}
- LinkedIn: {self.config.YOUR_LINKEDIN_URL}

I've attached my resume for reference. Would you or someone on the team be open to a 10-minute conversation to see if my background might be a fit for upcoming openings?

Thank you for your time,
{self.config.SENDER_NAME}
{self.config.YOUR_UNIVERSITY} | Class of {self.config.YOUR_GRADUATION_YEAR}"""

        return subject, body
