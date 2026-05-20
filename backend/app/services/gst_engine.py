"""
Thin shim — re-exports everything from the standalone gst-engine package.
All logic lives in gst-engine/engine/core.py.
"""
from engine.core import (  # noqa: F401
    validate_gstin,
    get_state_from_gstin,
    get_state_name,
    determine_supply_type,
    compute_tax_for_supply,
    compute_itc_setoff,
    is_itc_blocked,
    check_itc_deadline,
    check_itc_eligibility,
    get_return_due_date,
    get_compliance_calendar,
    compute_late_fee,
    compute_aggregate_turnover,
    get_composition_info,
    compute_credit_note_reversal,
    ITCSetoff,
    ITCEligibilityResult,
    DueDateInfo,
    LateFeeResult,
    AggregateTurnoverResult,
    CompositionInfo,
    CreditNoteITCReversal,
    SupplyType,
)
from engine.rules_loader import load_rules, get_rules, RulesBundle  # noqa: F401
