# Data Dictionary

All included records are synthetic. IDs use `SYN` markers or fictional `SITE-*` labels. Quantities are positive whole units; event types determine whether a row contributes to expected, recorded, correction, or adjustment totals.

## Inventory events

| Field | Meaning | Validation / notes |
|---|---|---|
| `event_id` | Unique source event identifier | Required; duplicates within the upload or existing store reject the full file |
| `event_type` | Shipment, receipt, correction, transfer, return, damage, or inventory adjustment | Must be one of the supported lower-case values |
| `process_step` | Defined handoff/process being reconciled | Required; use one consistent label per process |
| `site_id` | Fictional site code | Required; no address or real operational site name |
| `occurred_at` | Event time | ISO 8601 with timezone; normalized to UTC on import |
| `quantity` | Positive whole-unit count | Required; decimals, zero, negatives, and nonnumeric values rejected |
| `source_ref` | Synthetic source record reference | Required; does not establish source authenticity |
| `reconciliation_id` | Links related shipment/receipt/correction/adjustment records | Required; use a unique group for each reconciliation |

Shipment and transfer-in quantities contribute to expected units. Receipt, transfer-out, and return quantities contribute to recorded units. Receipt corrections contribute to confirmed recording errors. Damage and inventory adjustments contribute to documented operational adjustments. Reconciliation returns the absolute expected-versus-recorded variance; explanations are shown separately.

## Cases

| Field | Meaning | Notes |
|---|---|---|
| `case_id` | Unique case reference | Generated if omitted; demo IDs are fictional |
| `case_type` | Structured issue category | Do not use as an unsupported misconduct conclusion |
| `report_source` | How the case entered review | For example, scheduled reconciliation |
| `priority` | Low, normal, high, or urgent | Operational handling only |
| `owner` | Accountable synthetic role | Do not enter a real associate name |
| `status` | Draft, review, approved report, or closed | Approval and closure require reviewer role |
| `concern` | Neutral allegation/concern | Describe records, not intent |
| `report_summary` | Findings, alternative explanations, limits, and outcome | Required before approval |
| `simulated` | Scenario is fictional | API accepts only `true` |
| `site_id`, `process_step`, `reconciliation_id` | Connects case to the data basis | Supports grouping and reproducibility |
| `opened_at`, `closed_at` | Case lifecycle timestamps | Aging uses opened time; closure duration is reported only for closed cases |

## Evidence, timeline, and actions

- Evidence stores synthetic source reference, collector role, collection time, optional event time, optional 64-hex SHA-256, notes, and creation time. Register reads and metadata changes create application audit rows.
- Timeline category is one of `observation`, `reported_statement`, `hypothesis`, or `reviewer_conclusion`. Categories preserve epistemic status rather than blending reports and conclusions.
- Mitigation actions store process change, owner, due date, status, verification evidence, creation time, and verified completion time. Completed status requires verification evidence.
- Audit entries store actor role, action, entity, entity ID, JSON metadata, and timestamp. This SQLite table is not immutable or tamper-proof.

## Reporting definitions

- Discrepancy rate = unexplained units / expected units for the same site, process, and ISO week. The report retains separate reconciliation groups before summing within that bucket.
- Open case aging = current UTC time minus opened time; closed-case aging and time-to-closure are reported separately.
- Time-to-closure includes sample size and median.
- Action completion = verified completed actions / actions due in the month-to-date reporting period. A zero denominator is reported as blank/null, not zero percent.
- No financial estimate is calculated. No employee ranking, surveillance, or credibility score exists.