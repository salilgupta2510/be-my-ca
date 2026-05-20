"""
GSTR computation functions — pure dataclass inputs, no DB/ORM dependency.
Extracted from backend/app/api/v1/returns.py for standalone use.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from .core import compute_itc_setoff, check_itc_eligibility
from .rules_loader import RulesBundle, get_rules


# ─── Input Dataclasses ────────────────────────────────────────────────────────

@dataclass
class OutwardInvoiceData:
    invoice_type: str       # "b2b" | "b2c_large" | "b2c_small" | "export" | "credit_note"
    period: str
    taxable_value: Decimal = Decimal("0")
    igst: Decimal = Decimal("0")
    cgst: Decimal = Decimal("0")
    sgst: Decimal = Decimal("0")
    cess: Decimal = Decimal("0")


@dataclass
class InwardInvoiceData:
    id: str
    supplier_name: str
    invoice_number: str
    invoice_date: date
    period: str
    igst: Decimal = Decimal("0")
    cgst: Decimal = Decimal("0")
    sgst: Decimal = Decimal("0")
    supplier_gstin: str | None = None
    itc_blocked_reason: str | None = None
    is_rcm: bool = False
    # "unverified" | "matched" | "missing_in_2b" | "accepted_with_risk"
    itc_2b_status: str = "unverified"


@dataclass
class ReturnFilingData:
    """Minimal summary of a previously computed+filed return."""
    period: str
    return_type: str   # "gstr1" | "gstr3b" | "gstr4" | "gstr9"
    status: str        # "draft" | "filed"
    total_tax_payable: Decimal = Decimal("0")
    itc_claimed: Decimal = Decimal("0")
    computed_payload: dict = field(default_factory=dict)


# ─── GSTR-1 Compute ───────────────────────────────────────────────────────────

def compute_gstr1(
    invoices: list[OutwardInvoiceData],
    period: str,
) -> dict[str, Any]:
    def group(inv_type: str) -> dict:
        lst = [i for i in invoices if i.invoice_type == inv_type]
        return {
            "type": inv_type,
            "count": len(lst),
            "taxable_value": float(sum(i.taxable_value for i in lst)),
            "igst": float(sum(i.igst for i in lst)),
            "cgst": float(sum(i.cgst for i in lst)),
            "sgst": float(sum(i.sgst for i in lst)),
            "cess": float(sum(i.cess for i in lst)),
        }

    total_igst = sum(i.igst for i in invoices)
    total_cgst = sum(i.cgst for i in invoices)
    total_sgst = sum(i.sgst for i in invoices)

    return {
        "b2b": [group("b2b")],
        "b2c_large": [group("b2c_large")],
        "b2c_small": [group("b2c_small")],
        "exports": [group("export")],
        "credit_notes": [group("credit_note")],
        "summary": {
            "invoice_count": len(invoices),
            "total_taxable_value": float(sum(i.taxable_value for i in invoices)),
            "total_igst": float(total_igst),
            "total_cgst": float(total_cgst),
            "total_sgst": float(total_sgst),
            "total_cess": float(sum(i.cess for i in invoices)),
            "total_tax": float(total_igst + total_cgst + total_sgst),
        },
    }


# ─── GSTR-3B Compute ──────────────────────────────────────────────────────────

def compute_gstr3b(
    outward: list[OutwardInvoiceData],
    inward: list[InwardInvoiceData],
    period: str,
    reconciliation_done: bool = False,
    rules: RulesBundle | None = None,
) -> dict[str, Any]:
    rules = rules or get_rules()

    out_igst = sum(i.igst for i in outward)
    out_cgst = sum(i.cgst for i in outward)
    out_sgst = sum(i.sgst for i in outward)
    out_cess = sum(i.cess for i in outward)

    gstr2b_lock_applied = any(inv.itc_2b_status != "unverified" for inv in inward)

    itc_igst = itc_cgst = itc_sgst = Decimal("0")
    blocked_count = expired_count = missing_2b_count = 0

    for inv in inward:
        if gstr2b_lock_applied and inv.itc_2b_status == "missing_in_2b":
            missing_2b_count += 1
            blocked_count += 1
            continue
        if gstr2b_lock_applied and inv.itc_2b_status == "unverified":
            missing_2b_count += 1
            continue

        if reconciliation_done or gstr2b_lock_applied:
            result = check_itc_eligibility(
                invoice_id=inv.id,
                supplier_name=inv.supplier_name,
                invoice_number=inv.invoice_number,
                invoice_date=inv.invoice_date,
                igst=inv.igst,
                cgst=inv.cgst,
                sgst=inv.sgst,
                itc_category=inv.itc_blocked_reason,
                is_rcm=inv.is_rcm,
                rules=rules,
            )
            if result.is_eligible:
                itc_igst += result.igst
                itc_cgst += result.cgst
                itc_sgst += result.sgst
            else:
                r_lower = result.blocked_reason.lower()
                if any(kw in r_lower for kw in ("lapsed", "time", "expir")):
                    expired_count += 1
                else:
                    blocked_count += 1

    itc_total = itc_igst + itc_cgst + itc_sgst
    setoff = compute_itc_setoff(itc_igst, itc_cgst, itc_sgst, out_igst, out_cgst, out_sgst)
    net_total = setoff.total_cash_required + max(out_cess, Decimal("0"))

    return {
        "outward_tax_liability": {
            "igst": float(out_igst), "cgst": float(out_cgst),
            "sgst": float(out_sgst), "cess": float(out_cess),
            "total": float(out_igst + out_cgst + out_sgst + out_cess),
        },
        "itc_available": {
            "igst": float(itc_igst), "cgst": float(itc_cgst),
            "sgst": float(itc_sgst), "cess": 0.0, "total": float(itc_total),
        },
        "itc_setoff": {
            "igst_credit_used": float(setoff.igst_credit_used),
            "cgst_credit_used": float(setoff.cgst_credit_used),
            "sgst_credit_used": float(setoff.sgst_credit_used),
            "igst_cash_required": float(setoff.igst_cash_required),
            "cgst_cash_required": float(setoff.cgst_cash_required),
            "sgst_cash_required": float(setoff.sgst_cash_required),
        },
        "net_cash_payable": {
            "igst": float(setoff.igst_cash_required),
            "cgst": float(setoff.cgst_cash_required),
            "sgst": float(setoff.sgst_cash_required),
            "cess": float(out_cess),
            "total": float(net_total),
        },
        "itc_blocked_count": blocked_count,
        "itc_expired_count": expired_count,
        "itc_missing_2b_count": missing_2b_count,
        "gstr2b_lock_applied": gstr2b_lock_applied,
        "reconciliation_done": reconciliation_done,
        "invoice_count": len(outward),
        "_net_tax_payable": net_total,
        "_itc_claimed": itc_total,
    }


# ─── GSTR-4 Compute (Composition) ────────────────────────────────────────────

def compute_gstr4(
    outward: list[OutwardInvoiceData],
    inward: list[InwardInvoiceData],
    period: str,
    business_type: str = "trader",
    rules: RulesBundle | None = None,
) -> dict[str, Any]:
    rules = rules or get_rules()

    # Get correct rate from rules (fixes hardcoded 0.01 bug)
    rate_pct = rules.composition_rates.get(business_type, rules.composition_rates.get("trader", Decimal("1.0")))
    rate_decimal = rate_pct / 100  # e.g. 1.0% → 0.01

    total_taxable = sum(i.taxable_value for i in outward)
    composition_tax = (total_taxable * rate_decimal).quantize(Decimal("0.01"))
    cgst_payable = (composition_tax / 2).quantize(Decimal("0.01"))
    sgst_payable = composition_tax - cgst_payable

    rcm_invoices = [i for i in inward if i.is_rcm]
    rcm_igst = sum(i.igst for i in rcm_invoices)
    rcm_cgst = sum(i.cgst for i in rcm_invoices)
    rcm_sgst = sum(i.sgst for i in rcm_invoices)
    rcm_total = rcm_igst + rcm_cgst + rcm_sgst

    total_payable = composition_tax + rcm_total

    return {
        "aggregate_turnover": float(total_taxable),
        "composition_tax_rate_pct": float(rate_pct),
        "composition_tax_rate_decimal": float(rate_decimal),
        "composition_tax": float(composition_tax),
        "cgst_payable": float(cgst_payable),
        "sgst_payable": float(sgst_payable),
        "rcm_liability": {
            "igst": float(rcm_igst), "cgst": float(rcm_cgst),
            "sgst": float(rcm_sgst), "total": float(rcm_total),
            "invoice_count": len(rcm_invoices),
        },
        "total_tax_payable": float(total_payable),
        "note": "Composition dealers cannot claim ITC. Tax charged on turnover at flat rate.",
        "invoice_count": len(outward),
        "_net_tax_payable": total_payable,
    }


# ─── GSTR-9 Compute (Annual) ──────────────────────────────────────────────────

def fy_periods(fy: str) -> list[str]:
    """'2024-25' → ['2024-04'..'2024-12', '2025-01'..'2025-03']"""
    y1, y2_short = fy.split("-")
    y2 = f"20{y2_short}" if len(y2_short) == 2 else y2_short
    return [f"{y1}-{m:02d}" for m in range(4, 13)] + [f"{y2}-{m:02d}" for m in range(1, 4)]


def compute_gstr9(
    outward: list[OutwardInvoiceData],
    inward: list[InwardInvoiceData],
    filed_returns: list[ReturnFilingData],
    fy: str,
) -> dict[str, Any]:
    periods = fy_periods(fy)

    total_taxable = float(sum(i.taxable_value for i in outward))
    total_igst_out = float(sum(i.igst for i in outward))
    total_cgst_out = float(sum(i.cgst for i in outward))
    total_sgst_out = float(sum(i.sgst for i in outward))
    total_cess_out = float(sum(i.cess for i in outward))

    total_igst_in = float(sum(i.igst for i in inward))
    total_cgst_in = float(sum(i.cgst for i in inward))
    total_sgst_in = float(sum(i.sgst for i in inward))

    gstr3b_returns = [r for r in filed_returns if r.return_type == "gstr3b"]
    gstr1_returns = [r for r in filed_returns if r.return_type == "gstr1"]
    gstr3b_tax_paid = float(sum(r.total_tax_payable for r in gstr3b_returns))
    gstr3b_itc_claimed = float(sum(r.itc_claimed for r in gstr3b_returns))

    by_type: dict[str, dict] = {}
    for inv_type in ("b2b", "b2c_large", "b2c_small", "export", "credit_note"):
        lst = [i for i in outward if i.invoice_type == inv_type]
        by_type[inv_type] = {
            "count": len(lst),
            "taxable_value": float(sum(i.taxable_value for i in lst)),
            "igst": float(sum(i.igst for i in lst)),
            "cgst": float(sum(i.cgst for i in lst)),
            "sgst": float(sum(i.sgst for i in lst)),
        }

    period_wise: dict[str, dict] = {}
    for p in periods:
        p_out = [i for i in outward if i.period == p]
        p_in = [i for i in inward if i.period == p]
        g1 = next((r for r in gstr1_returns if r.period == p), None)
        g3 = next((r for r in gstr3b_returns if r.period == p), None)
        period_wise[p] = {
            "outward_count": len(p_out),
            "outward_taxable": float(sum(i.taxable_value for i in p_out)),
            "outward_tax": float(sum(i.igst + i.cgst + i.sgst for i in p_out)),
            "inward_count": len(p_in),
            "inward_itc": float(sum(i.igst + i.cgst + i.sgst for i in p_in)),
            "gstr1_filed": g1.status == "filed" if g1 else False,
            "gstr3b_filed": g3.status == "filed" if g3 else False,
            "tax_paid": float(g3.total_tax_payable) if g3 else 0.0,
        }

    return {
        "financial_year": fy,
        "periods": periods,
        "outward_supplies": {
            "by_type": by_type,
            "total_taxable_value": total_taxable,
            "total_igst": total_igst_out,
            "total_cgst": total_cgst_out,
            "total_sgst": total_sgst_out,
            "total_cess": total_cess_out,
            "total_tax": total_igst_out + total_cgst_out + total_sgst_out + total_cess_out,
            "invoice_count": len(outward),
        },
        "inward_supplies": {
            "total_igst": total_igst_in,
            "total_cgst": total_cgst_in,
            "total_sgst": total_sgst_in,
            "total_itc": total_igst_in + total_cgst_in + total_sgst_in,
            "invoice_count": len(inward),
        },
        "returns_summary": {
            "gstr1_filed_count": sum(1 for r in gstr1_returns if r.status == "filed"),
            "gstr3b_filed_count": sum(1 for r in gstr3b_returns if r.status == "filed"),
            "gstr1_total": len(gstr1_returns),
            "gstr3b_total": len(gstr3b_returns),
            "tax_paid_via_gstr3b": gstr3b_tax_paid,
            "itc_claimed_via_gstr3b": gstr3b_itc_claimed,
        },
        "period_wise": period_wise,
        "_net_tax_payable": gstr3b_tax_paid,
        "_itc_claimed": gstr3b_itc_claimed,
    }


# ─── Mismatch (GSTR-1 vs GSTR-3B) ────────────────────────────────────────────

MISMATCH_THRESHOLD_PCT = Decimal("1.0")


def compute_mismatch(
    gstr1_payload: dict,
    gstr3b_payload: dict,
) -> dict[str, Any]:
    """Compare outward tax in GSTR-1 vs GSTR-3B. GSTN flags divergence > 1%."""
    g1_summary = gstr1_payload.get("summary", {})
    g3_out = gstr3b_payload.get("outward_tax_liability", {})

    g1_igst = Decimal(str(g1_summary.get("total_igst", 0)))
    g1_cgst = Decimal(str(g1_summary.get("total_cgst", 0)))
    g1_sgst = Decimal(str(g1_summary.get("total_sgst", 0)))
    g1_total = g1_igst + g1_cgst + g1_sgst

    g3_igst = Decimal(str(g3_out.get("igst", 0)))
    g3_cgst = Decimal(str(g3_out.get("cgst", 0)))
    g3_sgst = Decimal(str(g3_out.get("sgst", 0)))
    g3_total = g3_igst + g3_cgst + g3_sgst

    delta = abs(g1_total - g3_total)
    pct = (delta / g1_total * 100) if g1_total > 0 else Decimal("0")
    has_mismatch = pct > MISMATCH_THRESHOLD_PCT

    return {
        "has_mismatch": has_mismatch,
        "gstr1_total_tax": float(g1_total),
        "gstr3b_total_tax": float(g3_total),
        "total_tax_delta": float(delta),
        "delta_pct": float(pct),
        "igst_delta": float(abs(g1_igst - g3_igst)),
        "cgst_delta": float(abs(g1_cgst - g3_cgst)),
        "sgst_delta": float(abs(g1_sgst - g3_sgst)),
    }
