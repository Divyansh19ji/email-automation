let leads = [];
let selectedLeadId = null;
let pollInterval = null;

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  loadConfig();
  refreshStatsAndLeads();
  startStatusPolling();
});

// Tab Navigation
function setupNavigation() {
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const tabId = btn.getAttribute("data-tab");
      document.getElementById(tabId).classList.add("active");

      if (tabId === "drafts-tab") {
        renderDraftsList();
      }
    });
  });

  const dryRunCheckbox = document.getElementById("dry-run-checkbox");
  dryRunCheckbox.addEventListener("change", (e) => {
    const isDry = e.target.checked;
    document.getElementById("mode-label").innerText = isDry 
      ? "Dry-Run Mode (Simulation - Safe)" 
      : "LIVE SEND MODE (Real Emails Will Be Sent!)";
    document.getElementById("mode-desc").innerText = isDry
      ? "Emails will be simulated and logged without contacting your SMTP server."
      : "Emails will be dispatched directly to recipients via your SMTP server!";
    document.getElementById("mode-label").style.color = isDry ? "#fff" : "#ef4444";
  });
}

// Data Fetching
async function refreshStatsAndLeads() {
  try {
    const [statsRes, leadsRes] = await Promise.all([
      fetch("/api/stats").then(r => r.json()),
      fetch("/api/leads").then(r => r.json())
    ]);

    document.getElementById("stat-total").innerText = statsRes.total_leads || 0;
    document.getElementById("stat-drafted").innerText = statsRes.drafted || 0;
    document.getElementById("stat-today").innerText = statsRes.sent_today || 0;
    document.getElementById("stat-sent").innerText = statsRes.sent || 0;
    document.getElementById("campaign-draft-count").innerText = statsRes.drafted || 0;

    leads = leadsRes;
    renderLeadsTable();
  } catch (err) {
    console.error("Failed to load dashboard data:", err);
  }
}

// Leads Table Rendering
function renderLeadsTable() {
  const tbody = document.getElementById("leads-table-body");
  if (!leads || leads.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4" style="text-align: center; color: #94a3b8; padding: 2rem;">No leads found. Add a lead or import a CSV!</td></tr>`;
    return;
  }

  tbody.innerHTML = leads.map(l => {
    const statusClass = `badge-${(l.status || 'pending').toLowerCase()}`;
    return `
      <tr>
        <td><strong>${escapeHtml(l.company)}</strong></td>
        <td>${escapeHtml(l.contact_name || 'N/A')}</td>
        <td>${escapeHtml(l.role || 'Intern')}</td>
        <td><code>${escapeHtml(l.email)}</code></td>
        <td><span class="badge ${statusClass}">${l.status}</span></td>
        <td>
          <button class="btn btn-outline btn-sm" onclick="viewDraftForLead(${l.id})">Preview</button>
          <button class="btn btn-outline btn-sm" style="color:#ef4444;" onclick="deleteLead(${l.id})">✕</button>
        </td>
      </tr>
    `;
  }).join("");
}

// Modal Handlers
function openAddLeadModal() {
  document.getElementById("add-lead-modal").classList.add("show");
}

function closeAddLeadModal() {
  document.getElementById("add-lead-modal").classList.remove("show");
}

async function submitNewLead(e) {
  e.preventDefault();
  const payload = {
    company: document.getElementById("new-lead-company").value,
    contact_name: document.getElementById("new-lead-name").value,
    email: document.getElementById("new-lead-email").value,
    role: document.getElementById("new-lead-role").value,
    website: document.getElementById("new-lead-website").value,
    notes: document.getElementById("new-lead-notes").value
  };

  try {
    const res = await fetch("/api/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(r => r.json());

    if (res.success) {
      closeAddLeadModal();
      await refreshStatsAndLeads();
      alert("Lead added successfully!");
    }
  } catch (err) {
    alert("Error adding lead: " + err.message);
  }
}

async function deleteLead(id) {
  if (!confirm("Are you sure you want to delete this lead?")) return;
  try {
    await fetch(`/api/leads/${id}`, { method: "DELETE" });
    await refreshStatsAndLeads();
  } catch (err) {
    alert("Error deleting lead: " + err.message);
  }
}

async function handleCSVUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (event) => {
    const csvText = event.target.result;
    try {
      const res = await fetch("/api/leads/upload-csv", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ csv_text: csvText })
      }).then(r => r.json());

      if (res.success) {
        alert(`CSV Imported! ${res.imported} leads added (${res.skipped} skipped).`);
        await refreshStatsAndLeads();
      } else {
        alert("Upload error: " + (res.detail || "Failed to process CSV"));
      }
    } catch (err) {
      alert("Error uploading CSV: " + err.message);
    }
  };
  reader.readAsText(file);
}

async function loadSampleLeads() {
  const sampleLeads = [
    { company: "Acme AI", contact_name: "Alex Rivera", email: "alex@acmeai-example.com", role: "AI Engineer Intern", notes: "Autonomous AI support agents; Python & PyTorch" },
    { company: "StripeFlow", contact_name: "Sarah Chen", email: "sarah@stripeflow-example.com", role: "Full Stack Intern", notes: "SaaS payment engine; Next.js, Node.js, PostgreSQL" },
    { company: "DataPulse", contact_name: "David Miller", email: "david@datapulse-example.com", role: "Backend Developer Intern", notes: "Real-time streaming analytics; FastAPI and ClickHouse" }
  ];

  for (const item of sampleLeads) {
    await fetch("/api/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item)
    });
  }
  await refreshStatsAndLeads();
  alert("Sample leads loaded!");
}

// Drafts Generation & Editor
async function generateAllDrafts() {
  const btn = event.target;
  btn.innerText = "⏳ Generating...";
  btn.disabled = true;

  try {
    const res = await fetch("/api/generate-drafts", { method: "POST" }).then(r => r.json());
    alert(`Generated drafts for ${res.generated_count} leads!`);
    await refreshStatsAndLeads();
    renderDraftsList();
  } catch (err) {
    alert("Error generating drafts: " + err.message);
  } finally {
    btn.innerText = "✨ Generate AI Drafts";
    btn.disabled = false;
  }
}

function renderDraftsList() {
  const container = document.getElementById("draft-sidebar-list");
  const draftedLeads = leads.filter(l => l.subject && l.body);

  if (draftedLeads.length === 0) {
    container.innerHTML = `<div class="text-muted" style="padding:1rem;">No drafts created yet. Click 'Generate AI Drafts' on the Leads tab!</div>`;
    return;
  }

  container.innerHTML = draftedLeads.map(l => `
    <div class="draft-item ${l.id === selectedLeadId ? 'active' : ''}" onclick="selectDraft(${l.id})">
      <div class="draft-item-company">${escapeHtml(l.company)}</div>
      <div class="draft-item-role">${escapeHtml(l.role || 'Intern')}</div>
    </div>
  `).join("");

  if (!selectedLeadId && draftedLeads.length > 0) {
    selectDraft(draftedLeads[0].id);
  }
}

function selectDraft(id) {
  selectedLeadId = id;
  const lead = leads.find(l => l.id === id);
  if (!lead) return;

  document.querySelectorAll(".draft-item").forEach(el => el.classList.remove("active"));
  renderDraftsList();

  document.getElementById("draft-editor-empty").style.display = "none";
  document.getElementById("draft-editor-content").style.display = "block";

  document.getElementById("editor-company").innerText = lead.company;
  document.getElementById("editor-recipient").innerText = lead.email;
  document.getElementById("editor-subject").value = lead.subject || "";
  document.getElementById("editor-body").value = lead.body || "";
}

function viewDraftForLead(id) {
  document.querySelector(`[data-tab="drafts-tab"]`).click();
  selectDraft(id);
}

async function saveDraft() {
  if (!selectedLeadId) return;
  const subject = document.getElementById("editor-subject").value;
  const body = document.getElementById("editor-body").value;

  try {
    await fetch("/api/update-draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lead_id: selectedLeadId, subject, body })
    });
    alert("Draft saved!");
    await refreshStatsAndLeads();
  } catch (err) {
    alert("Failed to save draft: " + err.message);
  }
}

async function regenerateCurrentDraft() {
  if (!selectedLeadId) return;
  try {
    await fetch("/api/generate-drafts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lead_ids: [selectedLeadId] })
    });
    await refreshStatsAndLeads();
    selectDraft(selectedLeadId);
  } catch (err) {
    alert("Error: " + err.message);
  }
}

// Campaign Dispatch
async function startCampaign() {
  const isDry = document.getElementById("dry-run-checkbox").checked;
  const drafted = leads.filter(l => l.status === "DRAFTED");

  if (drafted.length === 0) {
    alert("No drafted emails ready to send. Please generate drafts first!");
    return;
  }

  const promptMsg = isDry 
    ? `Simulate sending (Dry-Run) to ${drafted.length} leads?`
    : `⚠️ LIVE SEND CONFIRMATION: You are about to send real emails to ${drafted.length} recipients. Proceed?`;

  if (!confirm(promptMsg)) return;

  try {
    await fetch("/api/send-batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dry_run: isDry })
    });
    addLog(`Campaign initiated in ${isDry ? 'DRY-RUN' : 'LIVE'} mode for ${drafted.length} emails.`);
  } catch (err) {
    alert("Error starting campaign: " + err.message);
  }
}

function addLog(msg) {
  const win = document.getElementById("activity-log-window");
  const line = document.createElement("div");
  line.className = "log-line";
  line.innerText = `[${new Date().toLocaleTimeString()}] ${msg}`;
  win.appendChild(line);
  win.scrollTop = win.scrollHeight;
}

function startStatusPolling() {
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(async () => {
    try {
      const stats = await fetch("/api/stats").then(r => r.json());
      const dispatch = stats.dispatch;
      if (dispatch && dispatch.is_running) {
        document.getElementById("btn-start-campaign").disabled = true;
        document.getElementById("btn-start-campaign").innerText = `Sending (${dispatch.progress}/${dispatch.total})...`;
        if (dispatch.logs && dispatch.logs.length > 0) {
          const lastLog = dispatch.logs[dispatch.logs.length - 1];
          addLog(lastLog);
        }
      } else {
        document.getElementById("btn-start-campaign").disabled = false;
        document.getElementById("btn-start-campaign").innerText = `🚀 Start Campaign (${stats.drafted} Drafts Ready)`;
      }
    } catch (e) {
      // silently ignore polling errors
    }
  }, 3000);
}

// Settings & Config
async function loadConfig() {
  try {
    const cfg = await fetch("/api/config").then(r => r.json());
    document.getElementById("badge-name").innerText = cfg.sender_name || "Your Name";
    document.getElementById("badge-email").innerText = cfg.sender_email || "Not set";

    document.getElementById("cfg-sender-name").value = cfg.sender_name || "";
    document.getElementById("cfg-sender-email").value = cfg.sender_email || "";
    document.getElementById("cfg-university").value = cfg.your_university || "";
    document.getElementById("cfg-degree").value = cfg.your_degree || "";
    document.getElementById("cfg-grad-year").value = cfg.your_graduation_year || "";
    document.getElementById("cfg-skills").value = cfg.your_skills || "";
    document.getElementById("cfg-portfolio").value = cfg.your_portfolio_url || "";
    document.getElementById("cfg-linkedin").value = cfg.your_linkedin_url || "";
    document.getElementById("cfg-min-delay").value = cfg.min_delay_seconds || 35;
    document.getElementById("cfg-max-delay").value = cfg.max_delay_seconds || 75;

    document.getElementById("campaign-resume-status").innerText = cfg.has_resume
      ? "Attached (resume/resume.pdf found)"
      : "No PDF in resume/ folder (links will be used)";
  } catch (err) {
    console.error("Failed to load config:", err);
  }
}

async function saveSettings(e) {
  e.preventDefault();
  const payload = {
    sender_name: document.getElementById("cfg-sender-name").value,
    sender_email: document.getElementById("cfg-sender-email").value,
    sender_password: document.getElementById("cfg-sender-password").value || null,
    gemini_api_key: document.getElementById("cfg-gemini-key").value || null,
    your_university: document.getElementById("cfg-university").value,
    your_degree: document.getElementById("cfg-degree").value,
    your_graduation_year: document.getElementById("cfg-grad-year").value,
    your_skills: document.getElementById("cfg-skills").value,
    your_portfolio_url: document.getElementById("cfg-portfolio").value,
    your_linkedin_url: document.getElementById("cfg-linkedin").value,
    min_delay_seconds: parseInt(document.getElementById("cfg-min-delay").value) || 35,
    max_delay_seconds: parseInt(document.getElementById("cfg-max-delay").value) || 75
  };

  try {
    await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    alert("Settings saved successfully!");
    await loadConfig();
  } catch (err) {
    alert("Failed to save settings: " + err.message);
  }
}

async function sendTestEmail() {
  const target = prompt("Enter email address to send test preview to:", document.getElementById("cfg-sender-email").value);
  if (!target) return;

  try {
    const res = await fetch("/api/send-test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: target })
    }).then(r => r.json());

    if (res.success) {
      alert("Test email sent! Check your inbox.");
    } else {
      alert("Failed to send test email: " + (res.error || "Unknown error"));
    }
  } catch (err) {
    alert("Error sending test email: " + err.message);
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
