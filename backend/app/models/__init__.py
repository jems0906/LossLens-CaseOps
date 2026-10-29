from typing import Literal, TypedDict


EventType = Literal[
    "shipment",
    "receipt",
    "receipt_correction",
    "transfer_in",
    "transfer_out",
    "return",
    "damage_adjustment",
    "inventory_adjustment",
]
ReconciliationClassification = Literal[
    "no_discrepancy",
    "resolved_reconciliation_issue",
    "partially_explained_discrepancy",
    "unexplained_discrepancy",
]


class ReconciliationEvent(TypedDict, total=False):
    event_id: str
    event_type: EventType
    process_step: str
    site_id: str
    occurred_at: str
    quantity: int
    source_ref: str
    reconciliation_id: str


class ReconciliationResult(TypedDict):
    expected_units: int
    recorded_units: int
    confirmed_recording_error_units: int
    documented_adjustment_units: int
    raw_discrepancy_units: int
    explained_units: int
    unexplained_units: int
    classification: ReconciliationClassification