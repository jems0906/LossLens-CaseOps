# LossLens CaseOps

LossLens CaseOps is a restricted-access practice workspace that turns synthetic shipment, receipt, transfer, return, and adjustment records into documented reconciliation cases. It supports fact verification, alternative explanations, reviewer approval, mitigation tracking, and sanitized leadership reporting. It does not automatically accuse anyone or produce individual theft-risk scores.

## Safety and scope

- Included records are fictional and labeled synthetic. Use role labels only. Never enter real associate names, badge IDs, package IDs, customer addresses, incident details, or internal screenshots.
- A discrepancy is a records question, not proof of theft. Missing scans, correlation, shift differences, and job assignments are not treated as proof of misconduct.
- A SHA-256 hash may help detect a file change. It does not prove authenticity, admissibility, or tamper-proof storage. The SQLite audit table is not immutable.
- The bearer tokens are local demo credentials, not an enterprise identity system. Before any real deployment, replace them and add organization-approved identity, encryption, key management, authorization, retention, backup, monitoring, and privacy controls.

## Quick start

Requirements: Python 3.11+ and Node.js 20+.

1. Copy `.env.example` to `.env` and set two distinct, long random tokens. Enter those configured values at login. If no `.env` file is present, the local demo defaults (`local-demo-analyst` and `local-demo-reviewer`) are available for development only.
2. Install backend packages and seed the synthetic examples:

   ```powershell
   cd backend
   python -m pip install -r requirements.txt
   python scripts/seed_demo.py
   uvicorn app.main:app --reload
   ```

3. In another terminal, install and start the frontend:

   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

4. Open `http://localhost:5173`. Use the analyst token to document and submit a case; use reviewer access to approve or close it.

The seed script resets the configured SQLite database and reloads only the two synthetic cases. Do not run it against a database containing records you need to preserve.

## Included demonstration

- `CASE-SYN-001`: 100 expected and 92 recorded at `SITE-NORTH`, an eight-unit raw mismatch. A delayed correction explains five; documented damage explains three. It is closed as a resolved reconciliation issue, with a receiving handoff control recommendation and no theft finding.
- `CASE-SYN-002`: 12 expected and 10 recorded at `SITE-WEST`. Two units remain unexplained; the case is escalated to reviewer status with a neutral report summary requesting source records and preserving uncertainty.
- The leadership rate is unexplained units / expected units grouped by fictional site, process, and ISO week. The dashboard shows raw mismatch separately from unexplained units. Closure time includes its sample size and median.

## Features

- CSV upload validates required fields, supported event types, positive integer quantities, timezone-qualified ISO 8601 timestamps, duplicate IDs, file size, and previously imported IDs. A rejected file imports no rows.
- Reconciliation separates expected units, recorded units, confirmed recording errors, documented adjustments, and unexplained units.
- Case intake records type, source, priority, owner, status, neutral concern, fictional site/process, reconciliation ID, and a required simulated flag.
- Evidence references retain source, collector role, collection/event times, optional SHA-256, and notes. Register access and metadata changes create application audit events.
- Timeline entries are categorized as observation, reported statement, hypothesis, or reviewer conclusion. Interview prompts are neutral and open-ended; no coercion, deception, guilt scoring, or automated credibility analysis is provided.
- Workflow is draft → review → approved report → closed. Reviewer permission is required for approval and closure.
- Mitigation actions link a process change, owner, due date, and required verification evidence for completion.
- Leadership reports show trends, case aging, closure sample/median, recurring process issues, action completion, overdue actions, and sanitized synthetic CSV exports.

## Excel practice

Follow [`docs/excel_reporting_exercises.md`](docs/excel_reporting_exercises.md) using the fixtures. It covers PivotTables by fictional site/process/week, `COUNTIFS`, `SUMIFS`, `XLOOKUP`, timestamp normalization, duplicate checks, reconciliation, and a one-page leadership summary. Store screenshots from your completed Excel session in `docs/excel-proof/`; this repository does not claim that a desktop Excel exercise has been completed.

## API

The interactive API reference is available at `http://localhost:8000/docs`. Main routes include `/api/imports/events`, `/api/cases`, `/api/cases/{case_id}/evidence`, `/api/cases/{case_id}/timeline`, `/api/cases/{case_id}/interview-guide`, `/api/cases/{case_id}/reviews/submit`, `/api/cases/{case_id}/reviews/approve`, `/api/cases/{case_id}/reviews/close`, `/api/reports/leadership`, and `/api/reports/{cases,events}.csv`.

## Checks

```powershell
cd backend
python -m pytest -q
cd ../frontend
npm ci
npm run build
```