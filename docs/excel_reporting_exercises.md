# Excel Reporting Exercises

Use only `fixtures/synthetic_inventory_events.csv` and `fixtures/synthetic_cases.json`. These exercises are intended to be completed in desktop Excel with synthetic records; a dashboard or CSV export by itself is not Excel proof. Save the finished workbook and screenshots from your own Excel session in `docs/excel-proof/` before presenting the exercise as completed. Do not place real operational screenshots in the repository.

## 1. Prepare source tables

1. Import the events CSV using **Data → From Text/CSV**. Set `occurred_at` to a timezone-aware timestamp or retain the ISO 8601 text alongside a normalized UTC datetime column. Name the table `Events`.
2. Load the case JSON with **Data → Get Data → From File → From JSON**, expand the list, and name the table `Cases`.
3. Keep source fields unchanged. Add cleaning columns rather than overwriting source values.

## 2. Data cleaning and reconciliation

- Duplicate check: `=COUNTIFS(Events[event_id],[@event_id])>1`. Investigate duplicate IDs; do not silently keep an arbitrary row.
- Normalize timestamps to UTC before grouping. Preserve the source timestamp and document rows with a missing timezone; do not guess a timezone.
- Join a correction record to its reconciliation with `=XLOOKUP([@reconciliation_id],Events[reconciliation_id],Events[source_ref],"No matching reconciliation")`. Filter to the desired event type before interpreting the result; XLOOKUP returns the first matching row, not all events.
- Expected units by reconciliation: `=SUMIFS(Events[quantity],Events[reconciliation_id],[@reconciliation_id],Events[event_type],"shipment")`.
- Recorded receipt units: `=SUMIFS(Events[quantity],Events[reconciliation_id],[@reconciliation_id],Events[event_type],"receipt")`.
- Raw mismatch: `=ABS([@expected_units]-[@recorded_units])`.
- Treat missing values as **unknown**, not zero. Keep the discrepancy rate blank (`=IF([@expected_units]=0,"",[@unexplained_units]/[@expected_units])`) when the denominator is zero or absent.

For `REC-SYN-001`, the first-pass comparison is 100 expected versus 92 recorded: an eight-unit recorded mismatch. Then separately display five units tied to the delayed correction and three to documented damage; unexplained units after review are zero. `REC-SYN-002` remains a two-unit unresolved discrepancy. Do not describe either as theft.

## 3. PivotTables

Create PivotTables from the Events and Cases tables. Use fictional site, process, and normalized week as row fields; count cases or reconciliation IDs and sum expected, recorded, correction, and adjustment units as values. Do not aggregate unrelated sites, process steps, or periods into one rate denominator. Add a slicer for event type and check that changing it does not accidentally remove the expected/recorded basis.

## 4. Aging and action completion

- Open case age in days: `=IF([@status]="closed","",TODAY()-DATEVALUE(LEFT([@opened_at],10)))`.
- Closed duration in days: `=IF([@status]<>"closed","",DATEVALUE(LEFT([@closed_at],10))-DATEVALUE(LEFT([@opened_at],10)))`.
- Report open and closed cases separately. Show the closed-case sample size beside the median closure duration.
- For a reporting-period action rate, use `COUNTIFS` for due actions and verified completed actions within the same due-date range. Leave the rate blank when no actions were due; do not present future actions as overdue.

## 5. One-page leadership communication

Include the reporting period, denominator definition, raw mismatch and unexplained units separately, case aging, closure sample size/median, recurring process issues, overdue actions, accountable owners, verification evidence, limitations, and next actions. State explicitly that a discrepancy is not proof of misconduct.

## Screenshot checklist

Capture screenshots from the completed workbook showing (1) source tables and duplicate/timestamp checks, (2) at least one PivotTable by site/process/week, and (3) the one-page operational summary. Store only screenshots containing these synthetic examples. The repository intentionally does not claim that these desktop Excel steps have been completed for you.

## Workbook scaffold

Install the backend requirements, then run `python backend/scripts/create_excel_practice_workbook.py` from the repository root. This creates `docs/excel-proof/losslens_synthetic_practice.xlsx` with synthetic source tables and starter formulas. It does not create PivotTables or screenshots; complete those steps in desktop Excel.