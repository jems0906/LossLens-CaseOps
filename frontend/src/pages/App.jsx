import { useEffect, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowLeft,
  Check,
  ChevronRight,
  CircleAlert,
  ClipboardList,
  FileClock,
  FilePlus2,
  FileUp,
  Fingerprint,
  LockKeyhole,
  Plus,
  Search,
  ShieldCheck,
  Upload,
  X,
} from "lucide-react";
import { request } from "../api/client.js";

const STATUS_LABELS = {
  draft: "Draft",
  review: "In review",
  approved_report: "Approved report",
  closed: "Closed",
};

function Metric({ label, value, note, tone = "ink" }) {
  return (
    <article className={`metric metric-${tone}`}>
      <span className="metric-label">{label}</span>
      <strong>{value}</strong>
      <span className="metric-note">{note}</span>
    </article>
  );
}

function Login({ onLogin, message }) {
  const [value, setValue] = useState("");
  return (
    <main className="login-screen">
      <section className="login-panel">
        <div className="brand-mark"><Activity size={21} strokeWidth={2.2} /></div>
        <p className="eyebrow">LOSSLENS / CASEOPS</p>
        <h1>Reconcile the record.<br /><em>Keep the conclusion open.</em></h1>
        <p className="login-copy">A restricted workspace for synthetic inventory discrepancies, evidence notes, and process review.</p>
        <form onSubmit={(event) => { event.preventDefault(); onLogin(value); }}>
          <label htmlFor="access-token">Workspace access token</label>
          <div className="token-input">
            <LockKeyhole size={17} />
            <input id="access-token" autoComplete="off" type="password" value={value} onChange={(event) => setValue(event.target.value)} placeholder="Enter analyst or reviewer token" required />
          </div>
          {message && <p className="form-error" role="alert">{message}</p>}
          <button className="button button-primary login-submit" type="submit">Open workspace <ChevronRight size={17} /></button>
        </form>
        <div className="login-foot"><ShieldCheck size={16} /><span>Synthetic records only. No employee surveillance or guilt scoring.</span></div>
      </section>
      <aside className="login-side">
        <div className="orbit orbit-one" /><div className="orbit orbit-two" />
        <div className="login-side-copy">
          <span className="side-index">01 — 02</span>
          <p>CASE STUDY</p>
          <h2>100 expected.<br />92 recorded.</h2>
          <div className="side-rule" />
          <p className="side-caption">A first-pass mismatch is a question to investigate, not an accusation to make.</p>
          <div className="side-equation"><span>8</span><i>raw variance</i><b>→</b><span>0</span><i>unexplained</i></div>
        </div>
      </aside>
    </main>
  );
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("losslens-token") || "");
  const [cases, setCases] = useState([]);
  const [summary, setSummary] = useState(null);
  const [selected, setSelected] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [actions, setActions] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [interviewNotes, setInterviewNotes] = useState([]);
  const [reconciliation, setReconciliation] = useState(null);
  const [role, setRole] = useState("");
  const [detailVersion, setDetailVersion] = useState(0);
  const [page, setPage] = useState("overview");
  const [modal, setModal] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loginError, setLoginError] = useState("");

  async function loadWorkspace(activeToken = token) {
    const [caseRows, report, session] = await Promise.all([
      request(activeToken, "/cases"),
      request(activeToken, "/reports/leadership"),
      request(activeToken, "/session"),
    ]);
    setCases(caseRows);
    setSummary(report);
    setRole(session.role);
  }

  useEffect(() => {
    if (!token) return;
    loadWorkspace().catch((issue) => {
      setError(issue.message);
      if (issue.message.includes("token")) {
        localStorage.removeItem("losslens-token");
        setToken("");
      }
    });
  }, [token]);

  useEffect(() => {
    if (!selected || !token) return;
    Promise.all([
      request(token, `/cases/${selected.case_id}/timeline`),
      request(token, `/cases/${selected.case_id}/actions`),
      request(token, `/cases/${selected.case_id}/evidence`),
      request(token, `/cases/${selected.case_id}/interview-notes`),
      selected.reconciliation_id
        ? request(token, `/reports/reconciliation/${selected.reconciliation_id}`)
        : Promise.resolve(null),
    ]).then(([entries, actionRows, evidenceRows, notes, result]) => {
      setTimeline(entries);
      setActions(actionRows);
      setEvidence(evidenceRows);
      setInterviewNotes(notes);
      setReconciliation(result);
    }).catch((issue) => setError(issue.message));
  }, [selected?.case_id, token, detailVersion]);

  async function login(value) {
    setBusy(true);
    setLoginError("");
    try {
      await request(value, "/session");
      localStorage.setItem("losslens-token", value);
      setToken(value);
    } catch (issue) {
      setLoginError(issue.message || "Access could not be verified.");
    } finally {
      setBusy(false);
    }
  }

  async function run(action, successMessage) {
    setBusy(true);
    setError("");
    try {
      await action();
      await loadWorkspace();
      if (selected) {
        const fresh = await request(token, `/cases/${selected.case_id}`);
        setSelected(fresh);
        setDetailVersion((version) => version + 1);
      }
      setNotice(successMessage);
      setModal("");
    } catch (issue) {
      setError(issue.message);
    } finally {
      setBusy(false);
    }
  }

  async function exportCsv(path, filename) {
    try {
      const blob = await request(token, path);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
      setNotice("Sanitized synthetic CSV exported.");
    } catch (issue) {
      setError(issue.message);
    }
  }

  async function importCsv(event) {
    event.preventDefault();
    const file = event.currentTarget.elements.csv.files[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    await run(() => request(token, "/imports/events", { method: "POST", body: form }), "Synthetic events imported.");
  }

  if (!token) return <Login onLogin={login} message={loginError || (busy ? "Checking access…" : "")} />;

  const trends = summary?.discrepancy_trends || [];
  const featured = cases.find((item) => item.case_id === "CASE-SYN-001") || cases[0];
  const featuredTrend = trends.find((item) => item.site_id === featured?.site_id && item.process_step === featured?.process_step);
  const largestUnresolved = [...trends].sort((left, right) => right.unexplained_units - left.unexplained_units)[0];
  const reviewer = role === "reviewer";

  function openCase(item) {
    setSelected(item);
    setPage("case");
    setError("");
  }

  function renderHeader() {
    return (
      <header className="topbar">
        <div className="mobile-brand"><Activity size={18} /> LossLens</div>
        <div className="breadcrumb"><span>Workspace</span><ChevronRight size={14} /><strong>{page === "case" ? selected?.case_id : page === "cases" ? "Case register" : "Overview"}</strong></div>
        <div className="topbar-right"><span className="access-pill"><i /> Restricted access</span><span className="role-label">{reviewer ? "REVIEWER" : "ANALYST"}</span><button className="avatar-button" title="Sign out" onClick={() => { localStorage.removeItem("losslens-token"); setToken(""); setSelected(null); }}>↗</button></div>
      </header>
    );
  }

  function renderSidebar() {
    return (
      <aside className="sidebar">
        <div className="brand-lockup"><div className="brand-mark"><Activity size={19} /></div><div><strong>LossLens</strong><span>CASEOPS / 01</span></div></div>
        <div className="nav-group-label">WORKSPACE</div>
        <button className={`nav-item ${page === "overview" ? "active" : ""}`} onClick={() => { setSelected(null); setPage("overview"); }}><Activity size={17} /> Overview <span className="nav-dot" /></button>
        <button className={`nav-item ${page === "cases" ? "active" : ""}`} onClick={() => { setSelected(null); setPage("cases"); }}><ClipboardList size={17} /> Case register <span className="nav-count">{cases.length}</span></button>
        <button className="nav-item" onClick={() => setModal("import")}><FileUp size={17} /> Import events</button>
        <div className="sidebar-spacer" />
        <div className="sidebar-note"><Fingerprint size={17} /><div><strong>Evidence note</strong><p>A file hash detects change, not authenticity or admissibility.</p></div></div>
        <div className="sidebar-foot"><span>SIMULATED DATASET</span><span>v1.0.0 <i className="online-dot" /></span></div>
      </aside>
    );
  }

  function renderOverview() {
    const north = trends.find((item) => item.site_id === "SITE-NORTH");
    return (
      <>
        <div className="page-heading">
          <div><p className="eyebrow">THURSDAY / 29 OCTOBER 2026</p><h1>Operational overview</h1><p className="subhead">A measured view of records, open questions, and process follow-through.</p></div>
          <div className="heading-actions"><button className="button button-quiet" onClick={() => exportCsv("/reports/cases.csv", "losslens_cases_synthetic.csv")}><ArrowDownToLine size={16} /> Export cases</button><button className="button button-primary" onClick={() => setModal("new-case")}><Plus size={16} /> New case</button></div>
        </div>
        <section className="featured-case">
          <div className="featured-kicker"><span className="case-index">FEATURED CASE / 01</span><span className="status-chip status-closed">RESOLVED</span></div>
          <div className="featured-main">
            <div className="featured-copy"><h2>100 expected.<br /><em>92 recorded.</em></h2><p>Receiving handoff · SITE-NORTH · 19 Oct 2026</p></div>
            <div className="featured-math"><span className="math-number">8</span><div><b>unit recorded mismatch</b><small>5 delayed correction · 3 documented damage</small></div><ChevronRight size={19} /></div>
          </div>
          <div className="featured-foot"><span><i className="check-mark"><Check size={12} /></i> Resolved reconciliation issue</span><button onClick={() => featured && openCase(featured)}>Open case file <ChevronRight size={15} /></button></div>
        </section>
        <div className="metric-grid">
          <Metric label="Featured case raw variance" value={`${featuredTrend?.raw_discrepancy_units ?? 0} units`} note="CASE-SYN-001 · 100 expected / 92 recorded" tone="signal" />
          <Metric label="Largest unresolved group" value={`${largestUnresolved?.unexplained_units ?? 0} units`} note={largestUnresolved ? `${largestUnresolved.site_id} · ${largestUnresolved.process_step.replaceAll("_", " ")} · ${largestUnresolved.expected_units} expected` : "No unexplained group"} tone="alert" />
          <Metric label="Cases in progress" value={summary?.case_aging?.open_case_count ?? 0} note={`${summary?.case_aging?.open_age_median_days ?? "—"} day median age`} tone="ink" />
          <Metric label="Median time to closure" value={summary?.time_to_closure?.median_days == null ? "—" : `${summary.time_to_closure.median_days}d`} note={`${summary?.time_to_closure?.sample_size ?? 0} closed case sample`} tone="mint" />
        </div>
        <div className="overview-grid">
          <section className="panel trend-panel">
            <div className="panel-heading"><div><p className="eyebrow">PROCESS / WEEK</p><h2>Reconciliation signals</h2></div><button className="icon-button" title="Export synthetic event rows" onClick={() => exportCsv("/reports/events.csv", "losslens_events_synthetic.csv")}><ArrowDownToLine size={17} /></button></div>
            <div className="trend-legend"><span><i className="legend-raw" />Recorded mismatch</span><span><i className="legend-open" />Unexplained</span></div>
            {trends.length === 0 ? <p className="empty-state">No event records yet. Import a synthetic CSV to begin.</p> : trends.map((item) => (
              <button className="trend-row" key={`${item.site_id}-${item.process_step}-${item.week_start}`} onClick={() => setPage("cases")}>
                <div className="trend-meta"><strong>{item.process_step.replaceAll("_", " ")}</strong><span>{item.site_id} · wk of {item.week_start}</span></div>
                <div className="trend-track"><i style={{ width: `${Math.min(100, Math.max(item.expected_units ? (item.raw_discrepancy_units / item.expected_units) * 1000 : 0, 3))}%` }} /><b style={{ width: `${Math.min(100, Math.max(item.expected_units ? (item.unexplained_units / item.expected_units) * 1000 : 0, 0))}%` }} /></div>
                <div className="trend-value"><strong>{item.raw_discrepancy_units}</strong><span>raw</span><small>{item.unexplained_units}/{item.expected_units} open · {item.discrepancy_rate == null ? "n/a" : `${(item.discrepancy_rate * 100).toFixed(2)}%`}</small></div>
              </button>
            ))}
            <div className="recurring-summary"><span>Recurring process issues</span>{summary?.recurring_process_issues?.length ? summary.recurring_process_issues.map((item) => <b key={item.process_step}>{item.process_step.replaceAll("_", " ")} · {item.case_count} cases</b>) : <b>No repeated process in current sample</b>}</div>
            <div className="panel-footnote">Unexplained units ÷ expected units, grouped by the same site, process, and ISO week.</div>
          </section>
          <section className="panel workflow-panel">
            <div className="panel-heading"><div><p className="eyebrow">FOLLOW-THROUGH</p><h2>Open cases & actions</h2></div><button className="text-button" onClick={() => setPage("cases")}>All cases <ChevronRight size={14} /></button></div>
            <div className="case-mini-list">{cases.filter((item) => item.status !== "closed").map((item) => (
              <button className="case-mini" key={item.case_id} onClick={() => openCase(item)}><span className={`priority-mark priority-${item.priority}`} /><div><strong>{item.case_id}</strong><span>{item.site_id} · {item.process_step.replaceAll("_", " ")}</span></div><b className={`status-text status-${item.status}`}>{STATUS_LABELS[item.status]}</b><ChevronRight size={15} /></button>
            ))}{cases.filter((item) => item.status !== "closed").length === 0 && <p className="empty-state">No open cases.</p>}</div>
            <div className="action-summary"><div className="action-icon"><FileClock size={17} /></div><div><strong>{summary?.overdue_actions ?? 0} overdue actions</strong><span>Verified completion required</span></div><button className="arrow-link" onClick={() => featured && openCase(featured)} aria-label="Open action details"><ChevronRight size={16} /></button></div>
            <div className="workflow-rate"><div><span>Month-to-date action completion</span><strong>{summary?.action_completion?.rate == null ? "No actions due" : `${Math.round(summary.action_completion.rate * 100)}%`}</strong></div><div className="rate-track"><i style={{ width: `${Math.round((summary?.action_completion?.rate || 0) * 100)}%` }} /></div></div>
          </section>
        </div>
        <section className="limitations-strip"><CircleAlert size={16} /><p><strong>Interpretation guardrail</strong> Missing scans, correlation, shift differences, and job assignments are not proof of misconduct. Current records are synthetic.</p><span>AS OF {summary?.as_of ? new Date(summary.as_of).toLocaleDateString() : "—"}</span></section>
      </>
    );
  }

  function renderCases() {
    return (
      <>
        <div className="page-heading"><div><p className="eyebrow">REGISTER / {cases.length.toString().padStart(2, "0")} RECORDS</p><h1>Case register</h1><p className="subhead">Structured case intake, neutral review, and process actions.</p></div><button className="button button-primary" onClick={() => setModal("new-case")}><Plus size={16} /> New case</button></div>
        <div className="panel case-table-panel"><div className="table-toolbar"><div className="search-box"><Search size={16} /><input placeholder="Search case, site, or process" onChange={(event) => document.querySelectorAll("[data-case-row]").forEach((row) => { row.hidden = !row.textContent.toLowerCase().includes(event.target.value.toLowerCase()); })} /></div><span>{cases.length} synthetic records</span></div>
          <div className="table-scroll"><table><thead><tr><th>CASE</th><th>CONCERN</th><th>SITE / PROCESS</th><th>OWNER</th><th>PRIORITY</th><th>STATUS</th><th /></tr></thead><tbody>
            {cases.map((item) => <tr data-case-row key={item.case_id} onClick={() => openCase(item)}><td><strong className="case-id">{item.case_id}</strong><span className="table-sub">Opened {new Date(item.opened_at).toLocaleDateString()}</span></td><td><span className="concern-cell">{item.concern}</span></td><td>{item.site_id}<span className="table-sub">{item.process_step.replaceAll("_", " ")}</span></td><td>{item.owner}</td><td><span className={`priority-label priority-${item.priority}`}>{item.priority}</span></td><td><span className={`status-chip status-${item.status}`}>{STATUS_LABELS[item.status]}</span></td><td><ChevronRight size={16} /></td></tr>)}
          </tbody></table></div>
        </div>
        <div className="register-note"><ShieldCheck size={17} /><p>Cases document discrepancies and verified explanations. They do not automatically attribute intent or assign individual risk.</p></div>
      </>
    );
  }

  function renderCase() {
    if (!selected) return renderCases();
    const result = reconciliation;
    return (
      <>
        <button className="back-link" onClick={() => setPage("cases")}><ArrowLeft size={16} /> Case register</button>
        <div className="case-detail-heading"><div><p className="eyebrow">SIMULATED / {selected.site_id} / {selected.process_step.replaceAll("_", " ")}</p><h1>{selected.case_id}</h1><p className="subhead">{selected.case_type.replaceAll("_", " ")} <span className="separator">/</span> {selected.report_source}</p></div><span className={`status-chip status-${selected.status}`}>{STATUS_LABELS[selected.status]}</span></div>
        <section className="case-summary-panel">
          <div className="case-summary-copy"><p className="eyebrow">NEUTRAL CONCERN</p><p>{selected.concern}</p><div className="case-meta-line"><span>Owner <b>{selected.owner}</b></span><span>Priority <b>{selected.priority}</b></span><span>Opened <b>{new Date(selected.opened_at).toLocaleDateString()}</b></span></div></div>
          {result && <div className="recon-card"><div className="recon-head"><span>RECONCILIATION</span><span>{result.classification.replaceAll("_", " ")}</span></div><div className="recon-total"><div><strong>{result.expected_units}</strong><span>expected</span></div><b>−</b><div><strong>{result.recorded_units}</strong><span>recorded</span></div><b>=</b><div className="recon-highlight"><strong>{result.raw_discrepancy_units}</strong><span>raw mismatch</span></div></div><div className="recon-explained"><span><i className="recon-dot correct" />Recording correction <b>{result.confirmed_recording_error_units}</b></span><span><i className="recon-dot adjust" />Documented adjustment <b>{result.documented_adjustment_units}</b></span><span><i className="recon-dot unknown" />Unexplained <b>{result.unexplained_units}</b></span></div></div>}
        </section>
        <section className="panel report-panel"><div className="panel-heading"><div><p className="eyebrow">REVIEW DOCUMENT</p><h2>Case report summary</h2></div>{selected.status !== "closed" && <button className="button button-small" onClick={() => setModal("report")}><ClipboardList size={14} /> {selected.report_summary ? "Edit summary" : "Add summary"}</button>}</div>{selected.report_summary ? <p>{selected.report_summary}</p> : <p className="empty-state">No report summary yet. Reviewer approval is blocked until the facts, limitations, and outcome are documented.</p>}</section>
        <div className="case-detail-grid">
          <section className="panel timeline-panel"><div className="panel-heading"><div><p className="eyebrow">SOURCE-ORDERED RECORD</p><h2>Investigation timeline</h2></div><button className="button button-small" onClick={() => setModal("timeline")}><Plus size={15} /> Add entry</button></div>
            <div className="timeline">{timeline.map((entry) => <article className="timeline-item" key={entry.entry_id}><span className={`timeline-marker marker-${entry.category}`} /><div><div className="timeline-top"><span className={`timeline-type type-${entry.category}`}>{entry.category.replaceAll("_", " ")}</span><time>{new Date(entry.created_at).toLocaleString()}</time></div><h3>{entry.summary}</h3><p>{entry.details}</p><small>Recorded by {entry.recorded_by}</small></div></article>)}</div>
          </section>
          <div className="case-side-stack">
            <section className="panel workflow-card"><div className="panel-heading"><div><p className="eyebrow">CONTROLLED STATES</p><h2>Review path</h2></div><ShieldCheck size={18} /></div><div className="stage-list">{["draft", "review", "approved_report", "closed"].map((stage, index) => <div key={stage} className={`stage ${["draft", "review", "approved_report", "closed"].indexOf(selected.status) >= index ? "stage-done" : ""}`}><span>{["draft", "review", "approved_report", "closed"].indexOf(selected.status) >= index ? <Check size={12} /> : index + 1}</span><b>{STATUS_LABELS[stage]}</b>{index < 3 && <i />}</div>)}</div>
              <div className="workflow-actions">{selected.status === "draft" && <button className="button button-primary button-wide" disabled={busy} onClick={() => run(() => request(token, `/cases/${selected.case_id}/reviews/submit`, { method: "POST" }), "Case submitted for review.")}>Submit for review <ChevronRight size={15} /></button>}{selected.status === "review" && reviewer && <button className="button button-primary button-wide" disabled={busy} onClick={() => run(() => request(token, `/cases/${selected.case_id}/reviews/approve`, { method: "POST" }), "Report approved.")}>Approve report <Check size={15} /></button>}{selected.status === "approved_report" && reviewer && <button className="button button-primary button-wide" disabled={busy} onClick={() => setModal("close-case")}>Close case <Check size={15} /></button>}{selected.status === "review" && !reviewer && <p className="reviewer-note"><LockKeyhole size={14} /> Reviewer permission is required for approval.</p>}{selected.status === "closed" && <p className="resolved-note"><Check size={15} />{selected.resolution}</p>}</div>
            </section>
            <section className="panel evidence-card"><div className="panel-heading"><div><p className="eyebrow">REGISTER / {evidence.length.toString().padStart(2, "0")}</p><h2>Evidence references</h2></div><button className="icon-button" title="Add evidence reference" onClick={() => setModal("evidence")}><Plus size={17} /></button></div>{evidence.length ? evidence.map((item) => <div className="evidence-row" key={item.evidence_id}><div className="evidence-icon"><Fingerprint size={16} /></div><div><strong>{item.source_ref}</strong><span>Collected by {item.collector} · {new Date(item.collection_time).toLocaleDateString()}</span>{item.file_hash && <code>{item.file_hash.slice(0, 18)}…</code>}</div></div>) : <p className="empty-state">No references recorded.</p>}<p className="hash-caveat">A hash may help detect a file change. It does not prove authenticity or admissibility.</p></section>
          </div>
        </div>
        <section className="panel actions-panel"><div className="panel-heading"><div><p className="eyebrow">PROCESS IMPROVEMENT</p><h2>Mitigation actions</h2></div><button className="button button-small" onClick={() => setModal("action")}><Plus size={15} /> Add action</button></div>{actions.length === 0 ? <p className="empty-state">No process changes linked yet.</p> : <div className="action-list">{actions.map((action) => <div className="action-row" key={action.action_id}><div className={`action-state state-${action.status}`}>{action.status === "completed" ? <Check size={15} /> : <FileClock size={15} />}</div><div className="action-description"><strong>{action.process_change}</strong><span>Owner: {action.owner} · Due {action.due_date}</span>{action.verification_evidence && <small>Verified: {action.verification_evidence}</small>}</div><span className={`status-chip status-${action.status}`}>{action.status.replaceAll("_", " ")}</span>{action.status !== "completed" && <button className="button button-small" onClick={() => setModal(`action-complete:${action.action_id}`)}>Update</button>}</div>)}</div>}</section>
        <section className="interview-strip"><div><p className="eyebrow">INTERVIEW PREPARATION</p><strong>Open-ended, non-coercive prompts</strong><span>No deception, guilt scoring, or automated credibility analysis.</span></div><div className="question-chips"><span>Walk me through the handoff.</span><span>What records did you use?</span><span>What context should we include?</span></div><button className="button button-quiet" onClick={async () => { try { const guide = await request(token, `/cases/${selected.case_id}/interview-guide`); setNotice(guide.questions.join("\n")); } catch (issue) { setError(issue.message); } }}>View guide <ChevronRight size={15} /></button><button className="button button-small" onClick={() => setModal("interview-notes")}><Plus size={14} /> Record notes</button></section>
        {interviewNotes.length > 0 && <section className="panel notes-panel"><div className="panel-heading"><div><p className="eyebrow">STRUCTURED INTERVIEW RECORD</p><h2>Notes</h2></div></div>{interviewNotes.map((note) => <article className="saved-note" key={note.note_id}><strong>{note.interviewee_role} <span>{note.interview_date || "Date not recorded"}</span></strong><p>{note.topics}</p><p>{note.notes}</p></article>)}</section>}
      </>
    );
  }

  function renderModal() {
    if (!modal) return null;
    const isComplete = modal.startsWith("action-complete:");
    const mode = isComplete ? "action-complete" : modal;
    const title = { import: "Import synthetic events", "new-case": "Open a case", timeline: "Add timeline entry", evidence: "Register evidence reference", action: "Add process action", "action-complete": "Verify action completion", "close-case": "Close approved case", report: "Document case report", "interview-notes": "Record interview notes" }[mode];
    return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setModal(""); }}><section className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"><div className="modal-heading"><div><p className="eyebrow">CASEOPS / DOCUMENTATION</p><h2 id="modal-title">{title}</h2></div><button className="icon-button" onClick={() => setModal("")} aria-label="Close dialog"><X size={18} /></button></div>
      {mode === "import" && <form className="modal-form" onSubmit={importCsv}><label className="file-drop"><Upload size={19} /><strong>Choose a synthetic event CSV</strong><span>Required columns are validated before import · 5 MB max</span><input type="file" name="csv" accept=".csv,text/csv" required /></label><p className="form-hint">Duplicate IDs, missing fields, invalid timestamps, and non-positive quantities stop the complete import.</p><button className="button button-primary button-wide" disabled={busy}><FileUp size={16} /> Import rows</button></form>}
      {mode === "new-case" && <form className="modal-form" onSubmit={(event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); run(() => request(token, "/cases", { method: "POST", body: JSON.stringify({ ...data, simulated: true }) }), "Synthetic case opened."); }}><label>Case type<input name="case_type" placeholder="receipt_mismatch" required /></label><div className="form-row"><label>Report source<input name="report_source" placeholder="scheduled reconciliation" required /></label><label>Priority<select name="priority"><option>normal</option><option>low</option><option>high</option><option>urgent</option></select></label></div><div className="form-row"><label>Owner<input name="owner" placeholder="Synthetic inventory analyst" required /></label><label>Site ID<input name="site_id" placeholder="SITE-NORTH" required /></label></div><label>Process step<input name="process_step" placeholder="receiving_handoff" required /></label><label>Reconciliation ID<input name="reconciliation_id" placeholder="REC-SYN-001 (optional)" /></label><label>Neutral concern<textarea name="concern" minLength="8" placeholder="Describe the records discrepancy. Do not infer intent." required /></label><p className="form-hint">Use synthetic records and role labels only. Theft or fraud scenarios must be explicitly labeled simulated.</p><button className="button button-primary button-wide" disabled={busy}><FilePlus2 size={16} /> Create draft case</button></form>}
      {mode === "timeline" && <form className="modal-form" onSubmit={(event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); run(() => request(token, `/cases/${selected.case_id}/timeline`, { method: "POST", body: JSON.stringify(data) }), "Timeline entry recorded."); }}><label>Entry category<select name="category"><option value="observation">Observation</option><option value="reported_statement">Reported statement</option><option value="hypothesis">Hypothesis</option><option value="reviewer_conclusion">Reviewer conclusion</option></select></label><label>Summary<input name="summary" maxLength="180" required /></label><label>Details<textarea name="details" required /></label><label>Event time<input name="event_time" type="datetime-local" /></label><button className="button button-primary button-wide" disabled={busy}><Plus size={16} /> Add to timeline</button></form>}
      {mode === "evidence" && <form className="modal-form" onSubmit={(event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); data.collection_time = new Date(data.collection_time).toISOString(); if (data.event_time) data.event_time = new Date(data.event_time).toISOString(); else delete data.event_time; if (!data.file_hash) delete data.file_hash; run(() => request(token, `/cases/${selected.case_id}/evidence`, { method: "POST", body: JSON.stringify(data) }), "Evidence reference added."); }}><label>Source reference<input name="source_ref" placeholder="DOC-SYN-003" required /></label><label>Collector role<input name="collector" placeholder="Synthetic inventory analyst" required /></label><div className="form-row"><label>Collection time<input name="collection_time" type="datetime-local" required /></label><label>Event time<input name="event_time" type="datetime-local" /></label></div><label>SHA-256 file hash, if applicable<input name="file_hash" placeholder="64 hexadecimal characters" maxLength="64" /></label><label>Notes<textarea name="notes" /></label><p className="form-hint">Hashes can help detect a file change; they do not prove that evidence is authentic, admissible, or tamper-proof.</p><button className="button button-primary button-wide" disabled={busy}><Fingerprint size={16} /> Register reference</button></form>}
      {mode === "action" && <form className="modal-form" onSubmit={(event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); run(() => request(token, `/cases/${selected.case_id}/actions`, { method: "POST", body: JSON.stringify(data) }), "Process action linked."); }}><label>Process change<textarea name="process_change" placeholder="Define the control to change and when it applies." required /></label><label>Accountable owner<input name="owner" required /></label><label>Due date<input name="due_date" type="date" required /></label><button className="button button-primary button-wide" disabled={busy}><Plus size={16} /> Link action</button></form>}
      {mode === "action-complete" && <form className="modal-form" onSubmit={(event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); data.status = "completed"; const actionId = modal.split(":")[1]; run(() => request(token, `/actions/${actionId}`, { method: "PATCH", body: JSON.stringify(data) }), "Verification evidence recorded."); }}><label>Verification evidence<textarea name="verification_evidence" minLength="2" placeholder="Synthetic reference to confirm the process change is operating." required /></label><p className="form-hint">Completion cannot be recorded without verification evidence.</p><button className="button button-primary button-wide" disabled={busy}><Check size={16} /> Mark verified</button></form>}
      {mode === "close-case" && <form className="modal-form" onSubmit={(event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); run(() => request(token, `/cases/${selected.case_id}/reviews/close`, { method: "POST", body: JSON.stringify(data) }), "Case closed."); }}><label>Resolution<textarea name="resolution" minLength="8" placeholder="Summarize verified facts, limits, and outcome. Avoid an unsupported intent finding." required /></label><button className="button button-primary button-wide" disabled={busy}><Check size={16} /> Close case</button></form>}
      {mode === "report" && <form className="modal-form" onSubmit={(event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); run(() => request(token, `/cases/${selected.case_id}`, { method: "PATCH", body: JSON.stringify(data) }), "Case report summary saved."); }}><label>Findings, alternative explanations, limits, and outcome<textarea name="report_summary" minLength="20" defaultValue={selected.report_summary || ""} placeholder="Separate verified records from hypotheses. State the unresolved amount and what the records cannot establish." required /></label><p className="form-hint">Reviewer approval requires a report summary. Do not enter real personal identifiers or infer intent from a records mismatch.</p><button className="button button-primary button-wide" disabled={busy}><ClipboardList size={16} /> Save report</button></form>}
      {mode === "interview-notes" && <form className="modal-form" onSubmit={(event) => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); if (!data.interview_date) delete data.interview_date; run(() => request(token, `/cases/${selected.case_id}/interview-notes`, { method: "POST", body: JSON.stringify(data) }), "Interview notes recorded."); }}><label>Interviewee role<input name="interviewee_role" placeholder="Synthetic receiving role" required /></label><label>Interview date<input name="interview_date" type="date" /></label><label>Topics covered<input name="topics" placeholder="Receiving handoff, correction timing" required /></label><label>Notes<textarea name="notes" placeholder="Distinguish reported statements from verified records." required /></label><p className="form-hint">Use synthetic role labels. No credibility score or guilt assessment is recorded.</p><button className="button button-primary button-wide" disabled={busy}><Plus size={16} /> Save notes</button></form>}
      </section></div>;
  }

  return <div className="app-shell">{renderSidebar()}<main className="main-area">{renderHeader()}<div className="content-area">{error && <div className="alert-bar" role="alert"><CircleAlert size={16} />{error}<button onClick={() => setError("")}><X size={15} /></button></div>}{notice && <div className="notice-bar"><Check size={16} /><span>{notice}</span><button onClick={() => setNotice("")}><X size={15} /></button></div>}{page === "overview" ? renderOverview() : page === "cases" ? renderCases() : renderCase()}</div><footer className="page-footer"><span>LOSSLENS CASEOPS</span><span>SIMULATED CASEWORK · RESTRICTED ACCESS · NOT A FINDING OF MISCONDUCT</span></footer></main>{renderModal()}</div>;
}

export default App;