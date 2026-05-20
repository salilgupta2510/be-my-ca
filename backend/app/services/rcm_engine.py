"""
RCM auto-classification engine.
Implements Section 9(3) CGST Act — specified categories where recipient pays GST.
"""
from __future__ import annotations

from dataclasses import dataclass


# SAC codes subject to RCM under Notification 13/2017-CT(Rate) as amended
# Key: SAC prefix (str) or category name, Value: description
RCM_SAC_PREFIXES: dict[str, str] = {
    "9965": "Goods Transport Agency (GTA) — S.9(3)",
    "9967": "Goods Transport Agency supporting services — S.9(3)",
    "9982": "Legal services by advocate/law firm — S.9(3)",
    "9991": "Arbitral tribunal services — S.9(3)",
    "9983": "Sponsorship services — S.9(3)",
    "9971": "Insurance agent services — S.9(3)",
    "9985": "Recovery agent services — S.9(3)",
    "9996": "Director remuneration (non-employee) — S.9(3)",
    "9954": "Works contract — immovable property (S.17(5) blocked)",
}

# HSN codes for goods under RCM — Notification 4/2017-CT(Rate)
RCM_HSN_PREFIXES: dict[str, str] = {
    "0801": "Cashew nuts supplied by agriculturist — S.9(3)",
    "1404": "Bidi wrapper leaves (tendu) — S.9(3)",
    "2401": "Tobacco leaves — S.9(3)",
    "5004": "Silk yarn — S.9(3)",
    "5201": "Raw cotton — S.9(3)",
    "7101": "Used vehicles/waste — Govt supply S.9(3)",
}

# Supplier name keywords strongly indicating RCM category
RCM_SUPPLIER_KEYWORDS: dict[str, str] = {
    "transport": "Goods Transport Agency (GTA) — S.9(3)",
    "logistics": "Goods Transport Agency (GTA) — S.9(3)",
    "cargo": "Goods Transport Agency (GTA) — S.9(3)",
    "courier": "Goods Transport Agency (GTA) — S.9(3)",
    "advocates": "Legal services — S.9(3)",
    "advocate": "Legal services — S.9(3)",
    "solicitors": "Legal services — S.9(3)",
    "law firm": "Legal services — S.9(3)",
    "llp": "Legal services — S.9(3)",
    "arbitration": "Arbitral tribunal — S.9(3)",
}

# Section 17(5) blocked ITC categories mapped from HSN/SAC
BLOCKED_SAC_PREFIXES: dict[str, str] = {
    "9954": "works_contract",         # immovable property works contract
    "9963": "food_beverages",         # restaurant / catering
    "9972": "rent_a_cab",             # passenger transport
    "9973": "rent_a_cab",             # leasing motor vehicle
    "9993": "health_fitness",         # health / wellness
    "9994": "life_insurance",         # life insurance
    "9985119": "personal_use",        # beauty treatment
}

BLOCKED_HSN_PREFIXES: dict[str, str] = {
    "8703": "motor_vehicle",          # motor cars < 13 passengers
    "8702": "motor_vehicle",          # motor vehicles > 13 passengers (NOT blocked)
    "8704": "motor_vehicle",          # goods vehicles (NOT blocked unless mixed)
    "2101": "food_beverages",         # tea / coffee for office
}


@dataclass
class RCMResult:
    is_rcm: bool
    itc_blocked_reason: str | None    # None = eligible, else Section 17(5) category
    rcm_reason: str | None            # human-readable RCM basis
    is_import_of_service: bool


def classify_inward_invoice(
    supplier_gstin: str | None,
    hsn_code: str | None,
    supplier_name: str,
) -> RCMResult:
    """
    Auto-classify an inward invoice for:
    1. RCM applicability (is_rcm)
    2. ITC blocked reason (Section 17(5))
    3. Import of service flag (no GSTIN, foreign supplier)

    Priority: explicit HSN/SAC match > supplier name keyword > foreign supplier.
    """
    hsn = (hsn_code or "").strip().upper()
    name = supplier_name.lower()
    gstin = (supplier_gstin or "").strip().upper()

    # Import of service: no GSTIN and not a composition/URD Indian supplier
    # Heuristic: if name contains foreign indicators or no GSTIN at all
    is_import = not gstin and any(
        kw in name for kw in ("llp", "inc.", "ltd.", "corp.", "gmbh", "pvt")
    ) and not any(c.isdigit() for c in name[:5])

    # Check Section 17(5) blocked from HSN
    blocked_reason: str | None = None
    for prefix, reason in BLOCKED_HSN_PREFIXES.items():
        if hsn.startswith(prefix):
            # Motor vehicle: block only passenger vehicles (8703)
            if prefix == "8703":
                blocked_reason = reason
            elif prefix in ("8702", "8704"):
                pass  # not blocked
            else:
                blocked_reason = reason
            break

    for prefix, reason in BLOCKED_SAC_PREFIXES.items():
        if hsn.startswith(prefix):
            blocked_reason = reason
            break

    # Check RCM from SAC
    for prefix, rcm_desc in RCM_SAC_PREFIXES.items():
        if hsn.startswith(prefix):
            return RCMResult(
                is_rcm=True,
                itc_blocked_reason=blocked_reason,
                rcm_reason=rcm_desc,
                is_import_of_service=is_import,
            )

    # Check RCM from HSN (goods)
    for prefix, rcm_desc in RCM_HSN_PREFIXES.items():
        if hsn.startswith(prefix):
            return RCMResult(
                is_rcm=True,
                itc_blocked_reason=blocked_reason,
                rcm_reason=rcm_desc,
                is_import_of_service=is_import,
            )

    # Check RCM from supplier name keywords
    for keyword, rcm_desc in RCM_SUPPLIER_KEYWORDS.items():
        if keyword in name:
            return RCMResult(
                is_rcm=True,
                itc_blocked_reason=blocked_reason,
                rcm_reason=rcm_desc,
                is_import_of_service=is_import,
            )

    # Import of service is always RCM
    if is_import:
        return RCMResult(
            is_rcm=True,
            itc_blocked_reason=blocked_reason,
            rcm_reason="Import of service (no supplier GSTIN) — S.9(3)/(4)",
            is_import_of_service=True,
        )

    return RCMResult(
        is_rcm=False,
        itc_blocked_reason=blocked_reason,
        rcm_reason=None,
        is_import_of_service=False,
    )
