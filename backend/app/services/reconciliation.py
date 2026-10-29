from collections.abc import Iterable
from typing import Any


def calculate_reconciliation(events: Iterable[dict[str, Any]]) -> dict[str, int | str]:
    totals = {
        "expected_units": 0,
        "recorded_units": 0,
        "confirmed_recording_error_units": 0,
        "documented_adjustment_units": 0,
    }
    for event in events:
        quantity = int(event["quantity"])
        event_type = event["event_type"]
        if event_type in {"shipment", "transfer_in"}:
            totals["expected_units"] += quantity
        elif event_type in {"receipt", "transfer_out", "return"}:
            totals["recorded_units"] += quantity
        elif event_type == "receipt_correction":
            totals["confirmed_recording_error_units"] += quantity
        elif event_type in {"damage_adjustment", "inventory_adjustment"}:
            totals["documented_adjustment_units"] += quantity

    signed_difference = int(totals["expected_units"]) - int(totals["recorded_units"])
    raw_discrepancy = abs(signed_difference)
    available_explanations = (
        int(totals["confirmed_recording_error_units"])
        + int(totals["documented_adjustment_units"])
        if signed_difference > 0
        else 0
    )
    explained_units = min(raw_discrepancy, available_explanations)
    unexplained_units = max(raw_discrepancy - explained_units, 0)
    if raw_discrepancy == 0:
        classification = "no_discrepancy"
    elif unexplained_units == 0:
        classification = "resolved_reconciliation_issue"
    elif explained_units:
        classification = "partially_explained_discrepancy"
    else:
        classification = "unexplained_discrepancy"

    return {
        **totals,
        "raw_discrepancy_units": raw_discrepancy,
        "explained_units": explained_units,
        "unexplained_units": unexplained_units,
        "classification": classification,
    }