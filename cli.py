import sys
import time
from pathlib import Path
from config import Config, ENV_FILE, RESUME_DIR
from tracker import Tracker
from generator import EmailGenerator
from sender import EmailSender

def print_banner():
    print("""
===================================================================
     COLD EMAIL AUTOMATION - INTERNSHIP & STARTUP OUTREACH
===================================================================
    """)

def check_setup():
    issues = []
    if not Config.SENDER_EMAIL or "your_email" in Config.SENDER_EMAIL:
        issues.append("SENDER_EMAIL is not set in .env")
    if not Config.SENDER_PASSWORD or "xxxx" in Config.SENDER_PASSWORD:
        issues.append("SENDER_PASSWORD (Gmail App Password) is not set in .env")
    
    resume_path = Path(Config.ATTACHMENT_PATH)
    if not resume_path.exists():
        issues.append(f"Resume PDF not found at: {Config.ATTACHMENT_PATH} (Drop your resume.pdf into resume/ folder)")

    if issues:
        print("\n[!] Setup notices:")
        for issue in issues:
            print(f"    - {issue}")
        print("\nEdit .env to update credentials and settings.")
    else:
        print("\n[OK] Configuration loaded. Sender: " + Config.SENDER_EMAIL)

def menu():
    tracker = Tracker()
    generator = EmailGenerator()
    sender = EmailSender(tracker=tracker)

    while True:
        stats = tracker.get_stats()
        print("\n-------------------------------------------------------------")
        print(f"Dashboard Stats: Total Leads: {stats['total_leads']} | "
              f"Pending: {stats['pending']} | Drafted: {stats['drafted']} | "
              f"Sent Today: {stats['sent_today']} | Total Sent: {stats['sent']}")
        print("-------------------------------------------------------------")
        print("1. Import leads from CSV (e.g. leads.example.csv)")
        print("2. Add a single lead manually")
        print("3. View all leads & status")
        print("4. Generate personalized email drafts (AI / Smart Engine)")
        print("5. Preview & review generated drafts")
        print("6. Send a TEST email to yourself (Verify SMTP & resume)")
        print("7. Launch Outreach Campaign (Dry-Run / Live Send)")
        print("8. Export leads and history to CSV")
        print("9. Launch Web Dashboard (Browser GUI)")
        print("0. Exit")
        print("-------------------------------------------------------------")

        choice = input("Enter choice (0-9): ").strip()

        if choice == "1":
            csv_path = input("Enter CSV path [default: leads.example.csv]: ").strip() or "leads.example.csv"
            try:
                res = tracker.import_from_csv(csv_path)
                print(f"[+] Imported {res['imported']} leads ({res['skipped']} skipped).")
            except Exception as e:
                print(f"[-] Error: {e}")

        elif choice == "2":
            company = input("Company name: ").strip()
            if not company:
                continue
            email = input("Contact Email: ").strip()
            contact_name = input("Contact/Founder Name: ").strip()
            role = input("Desired Role [default: Software Engineer Intern]: ").strip() or "Software Engineer Intern"
            website = input("Website (optional): ").strip()
            notes = input("Context/Notes (e.g., Tech stack, what they build): ").strip()
            
            lead = tracker.add_lead(company, email, contact_name, role, website, notes)
            print(f"[+] Lead added successfully (ID: {lead['id']})")

        elif choice == "3":
            leads = tracker.get_all_leads()
            if not leads:
                print("No leads in database yet.")
                continue
            print("\nID  | Company                | Contact             | Role                    | Status")
            print("----+------------------------+---------------------+-------------------------+---------")
            for l in leads:
                print(f"{l['id']:<3} | {l['company'][:22]:<22} | {(l['contact_name'] or 'N/A')[:19]:<19} | {l['role'][:23]:<23} | {l['status']}")

        elif choice == "4":
            leads = tracker.get_all_leads(status="PENDING")
            if not leads:
                print("No pending leads require draft generation. (All already drafted or sent)")
                continue
            print(f"[+] Generating personalized drafts for {len(leads)} leads...")
            for l in leads:
                print(f"  -> Drafting email for {l['company']} ({l['contact_name'] or 'Hiring Team'})...")
                subject, body = generator.generate(l)
                tracker.update_draft(l['id'], subject, body)
            print(f"[+] Successfully drafted emails for {len(leads)} leads!")

        elif choice == "5":
            leads = tracker.get_all_leads()
            drafted = [l for l in leads if l.get("subject") and l.get("body")]
            if not drafted:
                print("No drafts available. Run option 4 to generate drafts first.")
                continue
            for l in drafted:
                print(f"\n==========================================================")
                print(f"Lead #{l['id']} - {l['company']} ({l['email']}) [Status: {l['status']}]")
                print(f"Subject: {l['subject']}")
                print(f"----------------------------------------------------------")
                print(l['body'])
                print(f"==========================================================")
                action = input("Press [Enter] for next, 'e' to edit, 'q' to stop: ").strip().lower()
                if action == 'e':
                    new_subj = input(f"New Subject [{l['subject']}]: ").strip() or l['subject']
                    print("Enter new body (type 'END' on a new line to finish):")
                    lines = []
                    while True:
                        line = input()
                        if line == "END":
                            break
                        lines.append(line)
                    if lines:
                        tracker.update_draft(l['id'], new_subj, "\n".join(lines))
                        print("[+] Draft updated.")
                elif action == 'q':
                    break

        elif choice == "6":
            target = input(f"Send test email to [{Config.SENDER_EMAIL}]: ").strip() or Config.SENDER_EMAIL
            print(f"[+] Sending test email to {target}...")
            res = sender.send_test_email(target)
            if res.get("success"):
                print("[+] TEST EMAIL SENT SUCCESSFULLY! Check your inbox (and spam/promotions folder).")
            else:
                print(f"[-] Failed to send test email: {res.get('error')}")

        elif choice == "7":
            drafted = [l for l in tracker.get_all_leads() if l["status"] == "DRAFTED"]
            if not drafted:
                print("No leads in 'DRAFTED' status ready for sending. Generate drafts first (Option 4).")
                continue

            print(f"Found {len(drafted)} drafted emails ready to send.")
            mode = input("Select mode: [1] Dry-Run (simulate only) | [2] Live Send: ").strip()
            dry_run = (mode != "2")

            confirm = input(f"Proceed with {'DRY-RUN' if dry_run else 'LIVE SEND'} for {len(drafted)} leads? (y/N): ").strip().lower()
            if confirm != "y":
                print("Cancelled.")
                continue

            lead_ids = [l["id"] for l in drafted]
            
            def cli_callback(event):
                msg = event.get("message", "")
                if msg:
                    print(f"  {msg}")
            
            results = sender.dispatch_batch(lead_ids, dry_run=dry_run, progress_callback=cli_callback)
            print(f"\n[+] Campaign Finished! Sent: {results['sent']}, Failed: {results['failed']}, Skipped: {results['skipped']}")

        elif choice == "8":
            out_file = input("Export filename [default: exported_leads.csv]: ").strip() or "exported_leads.csv"
            tracker.export_csv(out_file)
            print(f"[+] Exported all leads to {out_file}")

        elif choice == "9":
            print("[+] Starting Web Dashboard...")
            print("Access via browser at: http://127.0.0.1:8000")
            import uvicorn
            uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)

        elif choice == "0":
            print("Goodbye and good luck with your internship applications!")
            sys.exit(0)

if __name__ == "__main__":
    print_banner()
    check_setup()
    menu()
