"""
RCM auto-classification engine.
Section 9(3) CGST Act — specified categories where recipient pays GST.
Rules-aware: SAC/HSN/keyword lists loaded from RulesBundle.
"""
from __future__ import annotations

from dataclasses import dataclass

from .rules_loader import RulesBundle, get_rules


@dataclass
class RCMResult:
    is_rcm: bool
    itc_blocked_reason: str | None
    rcm_reason: str | None
    is_import_of_service: bool


def classify_inward_invoice(
    supplier_gstin: str | None,
    hsn_code: str | None,
    supplier_name: str,
    rules: RulesBundle | None = None,
) -> RCMResult:
    """
    Auto-classify for RCM, Section 17(5) block, and import of service.
    Priority: HSN/SAC match > supplier keyword > foreign supplier.
    """
    rules = rules or get_rules()
    hsn = (hsn_code or "").strip().upper()
    name = supplier_name.lower()
    gstin = (supplier_gstin or "").strip().upper()

    is_import = not gstin and any(
        kw in name for kw in ("llp", "inc.", "ltd.", "corp.", "gmbh", "pvt")
    ) and not any(c.isdigit() for c in name[:5])

    # Section 17(5) blocked from HSN
    blocked_reason: str | None = None
    for prefix, reason in rules.blocked_hsn_prefixes.items():
        if hsn.startswith(prefix):
            if prefix == "8703":
                blocked_reason = reason
            break

    for prefix, reason in rules.blocked_sac_prefixes.items():
        if hsn.startswith(prefix):
            blocked_reason = reason
            break

    # RCM from SAC
    for prefix, rcm_desc in rules.rcm_sac_prefixes.items():
        if hsn.startswith(prefix):
            return RCMResult(
                is_rcm=True, itc_blocked_reason=blocked_reason,
                rcm_reason=rcm_desc, is_import_of_service=is_import,
            )

    # RCM from HSN (goods)
    for prefix, rcm_desc in rules.rcm_hsn_prefixes.items():
        if hsn.startswith(prefix):
            return RCMResult(
                is_rcm=True, itc_blocked_reason=blocked_reason,
                rcm_reason=rcm_desc, is_import_of_service=is_import,
            )

    # RCM from supplier keywords
    for keyword, rcm_desc in rules.rcm_supplier_keywords.items():
        if keyword in name:
            return RCMResult(
                is_rcm=True, itc_blocked_reason=blocked_reason,
                rcm_reason=rcm_desc, is_import_of_service=is_import,
            )

    if is_import:
        return RCMResult(
            is_rcm=True, itc_blocked_reason=blocked_reason,
            rcm_reason="Import of service (no supplier GSTIN) — S.9(3)/(4)",
            is_import_of_service=True,
        )

    return RCMResult(
        is_rcm=False, itc_blocked_reason=blocked_reason,
        rcm_reason=None, is_import_of_service=False,
    )
