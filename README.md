# ✉️ Automated Internship Cold Emailing System

A personalized, spam-safe cold outreach engine engineered specifically for students seeking internships at high-growth startups and tech companies.

---

## 🌟 Key Features

1. **Hyper-Personalized Email Generator**:
   - Matches the company's product & tech stack with your relevant projects and skills.
   - Supports **Gemini AI** (`GEMINI_API_KEY`) or **Intelligent Built-in Contextual Templates** (zero setup required).
   - 80–120 word high-conversion emails designed for busy founders & engineering leads.

2. **Deliverability & Anti-Spam Engine**:
   - **Smart Jitter Delays**: Random 35–75 second wait between sends to mimic natural human typing and bypass spam detection.
   - **Daily Sending Caps**: Configurable safe limit (20–30 emails/day) to keep your domain and email reputation spotless.
   - **Deduplication Safeguard**: Automatically prevents emailing the same contact or company twice.

3. **Dry-Run & Preview First**:
   - Inspect, edit, and fine-tune every draft before sending.
   - Built-in **Dry-Run mode** to simulate campaigns without contacting SMTP.
   - **Self-Test Email**: Send 1 test email directly to yourself to verify inbox formatting and PDF resume attachment.

4. **Two Easy Ways to Run**:
   - **Modern Web Dashboard**: Visual UI at `http://localhost:8000` with lead management, draft editor, live logs, and settings.
   - **Interactive Terminal CLI**: Lightweight terminal runner for quick executions.

---

## 🚀 Quick Start (in 3 Minutes)

### Step 1: Set Up Your Email Credentials (Gmail App Password)
> [!IMPORTANT]
> Google does **not** allow logging in with your normal account password via SMTP. You must create a free **App Password**:
> 1. Go to your **[Google Account Security](https://myaccount.google.com/security)**.
> 2. Ensure **2-Step Verification** is turned ON.
> 3. Search for or click **"App passwords"** (or visit: `https://myaccount.google.com/apppasswords`).
> 4. Enter an app name (e.g. `Internship Mailer`) and click **Create**.
> 5. Copy the 16-character password (e.g. `abcd efgh ijkl mnop`).

### Step 2: Configure Your Profile
Either:
- Launch the Web Dashboard and configure everything in the **⚙️ Profile & Settings** tab, **OR**
- Edit the `.env` file in this folder:
  ```env
  SENDER_NAME="Your Full Name"
  SENDER_EMAIL="your_email@gmail.com"
  SENDER_PASSWORD="your 16 char app password"
  YOUR_UNIVERSITY="Your University Name"
  YOUR_DEGREE="B.Tech Computer Science"
  YOUR_GRADUATION_YEAR="2026"
  YOUR_SKILLS="Python, React, TypeScript, FastAPI, PostgreSQL"
  YOUR_PORTFOLIO_URL="https://github.com/yourusername"
  YOUR_LINKEDIN_URL="https://linkedin.com/in/yourusername"
  ```

### Step 3: Add Your Resume
Drop your PDF resume into the `resume/` folder and name it:
```
resume/resume.pdf
```
*(If no PDF is present, the system will seamlessly direct recruiters to your GitHub and LinkedIn links instead!)*

### Step 4: Run the System

Double-click `run.bat` or run in terminal:

#### Option A: Web Dashboard (Recommended)
```powershell
python -m uvicorn server:app --reload
```
Open your browser at **`http://localhost:8000`**.

#### Option B: Terminal CLI
```powershell
python cli.py
```

---

## 📊 How to Add Leads (`leads.csv`)

You can upload a CSV directly in the Web Dashboard or edit a CSV file with these column headers:

| company | contact_name | email | role | website | notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Acme AI** | Alex Rivera | founder@acme.ai | AI Engineer Intern | https://acme.ai | Building autonomous customer agents; PyTorch & Python |
| **StripeFlow** | Sarah Chen | careers@stripeflow.com | Full Stack Intern | https://stripeflow.com | SaaS payments platform; Next.js and Postgres |

> **Pro-Tip**: In the `notes` column, write 1 short sentence on what the startup builds or what tech they use. The generator automatically uses this to write a customized hook!

---

## 🎯 The Cold Email Formula That Gets 40%+ Open Rates

Cold emails fail when they look like mass-blast templates. This system enforces the winning 4-part structure:

1. **Specific Hook**: *"I've been following Acme AI's work on autonomous customer support agents..."*
2. **Value / Proof of Work**: *"As a CS student at [University], I built [Project] using FastAPI and PyTorch which handled 10k real-time queries..."*
3. **Alignment**: *"I'd love to contribute to shipping features for your engineering team this summer."*
4. **Low-Friction Call to Action (CTA)**: *"Would you or someone on your team be open to a 10-minute chat or reviewing my resume for upcoming intern openings?"*

---

## 🛡️ Deliverability Best Practices

- **Warm up your email**: Do not send 100 emails on Day 1. Start with 10–15/day, then 25–30/day.
- **Always Run a Dry-Run first**: Use the Dry-Run toggle to inspect your emails before sending live.
- **Send a Test Email to yourself**: Make sure your resume attachment opens correctly and the links work.
