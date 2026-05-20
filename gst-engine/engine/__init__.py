"""
gst_engine — Indian GST law engine.
Import from submodules for specific functionality.
"""
from .core import (
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
from .rcm import classify_inward_invoice, RCMResult
from .risk import compute_risk_score, RiskReport
from .fuzzy import find_best_match, match_by_name, reconcile_pair, normalize, MatchResult
from .gstr_compute import (
    compute_gstr1,
    compute_gstr3b,
    compute_gstr4,
    compute_gstr9,
    compute_mismatch,
    fy_periods,
    OutwardInvoiceData,
    InwardInvoiceData,
    ReturnFilingData,
)
from .itc_monitor import scan_itc_expiry, check_itc_expiry_at_create, ITCExpiryAlert
from .rules_loader import load_rules, get_rules, RulesBundle

__all__ = [
    # core
    "validate_gstin", "get_state_from_gstin", "get_state_name",
    "determine_supply_type", "compute_tax_for_supply",
    "compute_itc_setoff", "is_itc_blocked", "check_itc_deadline",
    "check_itc_eligibility", "get_return_due_date", "get_compliance_calendar",
    "compute_late_fee", "compute_aggregate_turnover", "get_composition_info",
    "compute_credit_note_reversal",
    "ITCSetoff", "ITCEligibilityResult", "DueDateInfo", "LateFeeResult",
    "AggregateTurnoverResult", "CompositionInfo", "CreditNoteITCReversal", "SupplyType",
    # rcm
    "classify_inward_invoice", "RCMResult",
    # risk
    "compute_risk_score", "RiskReport",
    # fuzzy
    "find_best_match", "match_by_name", "reconcile_pair", "normalize", "MatchResult",
    # gstr compute
    "compute_gstr1", "compute_gstr3b", "compute_gstr4", "compute_gstr9",
    "compute_mismatch", "fy_periods",
    "OutwardInvoiceData", "InwardInvoiceData", "ReturnFilingData",
    # itc monitor
    "scan_itc_expiry", "check_itc_expiry_at_create", "ITCExpiryAlert",
    # rules
    "load_rules", "get_rules", "RulesBundle",
]
