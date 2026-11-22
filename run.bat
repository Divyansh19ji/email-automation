@echo off
title Internship Cold Outreach Automation
cls
echo ===================================================================
echo     INTERNSHIP & STARTUP COLD EMAIL AUTOMATION
echo ===================================================================
echo.
echo Select an option:
echo   [1] Launch Interactive Web Dashboard (Recommended - Browser UI)
echo   [2] Launch Terminal CLI Menu
echo   [3] Test Import Sample Leads & Generate Drafts
echo   [4] Exit
echo.

set /p choice="Enter choice (1-4): "

if "%choice%"=="1" (
    echo.
    echo Starting Web Dashboard at http://127.0.0.1:8000 ...
    echo Opening browser...
    start http://127.0.0.1:8000
    python -m uvicorn server:app --host 127.0.0.1 --port 8000
) else if "%choice%"=="2" (
    python cli.py
) else if "%choice%"=="3" (
    python -c "from tracker import Tracker; from generator import EmailGenerator; t = Tracker(); res = t.import_from_csv('leads.example.csv'); print(f'Imported {res[\"imported\"]} leads'); g = EmailGenerator(); [t.update_draft(l['id'], *g.generate(l)) for l in t.get_all_leads() if l['status']=='PENDING']; print('Generated personalized drafts for all leads!');"
    pause
) else (
    exit
)
