"""
Capital gains CSV parser and tax computer.

Supports:
  - Zerodha Tax P&L report (Console → Reports → Tax P&L)
  - Groww Realized P&L report
  - Generic fallback (required columns: symbol, buy_date, sell_date, gain_loss)

Tax rates:
  Budget 2024 (July 23, 2024) changed equity capital gains rates.
  FY 2024-25 is a split year:
    Sells before Jul 23 2024 → STCG 15%, LTCG 10%, ₹1L exemption
    Sells from Jul 23 2024   → STCG 20%, LTCG 12.5%, ₹1.25L exemption
  FY 2025-26 onwards: new rates only.
  FY 2023-24 and earlier: old rates only.

  Debt instruments (purchased after Apr 1 2023): slab rate regardless of holding.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas.itr import (
    CapitalGainsCategory,
    CapitalGainsSummary,
    CapitalGainsTrade,
)

_BUDGET_2024 = date(2024, 7, 23)

# Pre-Budget 2024 equity rates
_STCG_OLD = Decimal("0.15")
_LTCG_OLD = Decimal("0.10")
_LTCG_EXEMPT_OLD = Decimal("100000")

# Post-Budget 2024 equity rates
_STCG_NEW = Decimal("0.20")
_LTCG_NEW = Decimal("0.125")
_LTCG_EXEMPT_NEW = Decimal("125000")


def _parse_date(val: str) -> date | None:
    val = val.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%b %d, %Y", "%d %b %Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _d(val: Any) -> Decimal:
    try:
        cleaned = str(val).replace(",", "").replace("₹", "").replace("(", "-").replace(")", "").strip()
        if cleaned in ("", "-", "N/A", "NA", "nan", "NaN"):
            return Decimal("0")
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _detect_broker(headers: list[str]) -> str:
    h = {c.lower().strip() for c in headers}
    # Zerodha Tax P&L: has "trade type" + "isin" + ("realized p&l" or "p&l")
    if "isin" in h and "trade type" in h and ("realized p&l" in h or "p&l" in h):
        return "zerodha"
    # Groww: "net profit/loss" or "net gain/loss"
    if "net profit/loss" in h or "net gain/loss" in h:
        return "groww"
    # Generic: must have buy_date + sell_date + gain
    if {"buy date", "sell date"} <= h or {"buy_date", "sell_date"} <= h:
        return "generic"
    return "unknown"


def _category_from_days(days: int, is_debt: bool = False) -> CapitalGainsCategory:
    if is_debt:
        return CapitalGainsCategory.DEBT_STCG if days <= 1095 else CapitalGainsCategory.DEBT_LTCG
    return CapitalGainsCategory.EQUITY_STCG if days <= 365 else CapitalGainsCategory.EQUITY_LTCG


def _tax_rate_pct(cat: CapitalGainsCategory, sell: date) -> float | None:
    if cat == CapitalGainsCategory.EQUITY_STCG:
        return 15.0 if sell < _BUDGET_2024 else 20.0
    if cat == CapitalGainsCategory.EQUITY_LTCG:
        return 10.0 if sell < _BUDGET_2024 else 12.5
    return None  # slab-rated


def _parse_zerodha(rows: list[dict]) -> list[CapitalGainsTrade]:
    trades = []
    for row in rows:
        symbol = (row.get("Symbol") or "").strip()
        if not symbol:
            continue
        isin = (row.get("ISIN") or "").strip() or None
        qty = _d(row.get("Quantity") or 0)

        buy_raw = str(row.get("Buy Date") or "")
        sell_raw = str(row.get("Sell Date") or "")
        buy_date = _parse_date(buy_raw)
        sell_date = _parse_date(sell_raw)
        if buy_date is None or sell_date is None:
            continue

        buy_amt = _d(row.get("Buy Value") or row.get("Buy Amount") or 0)
        sell_amt = _d(row.get("Sell Value") or row.get("Sell Amount") or 0)
        pnl = _d(row.get("Realized P&L") or row.get("P&L") or 0)

        days = (sell_date - buy_date).days
        trade_type_raw = str(row.get("Trade Type") or "").lower()
        if "long" in trade_type_raw:
            cat = CapitalGainsCategory.EQUITY_LTCG
        elif "short" in trade_type_raw:
            cat = CapitalGainsCategory.EQUITY_STCG
        else:
            cat = _category_from_days(days)

        trades.append(CapitalGainsTrade(
            symbol=symbol,
            isin=isin,
            quantity=qty,
            buy_date=str(buy_date),
            sell_date=str(sell_date),
            buy_amount=buy_amt,
            sell_amount=sell_amt,
            gain_loss=pnl,
            holding_days=days,
            category=cat,
            tax_rate_pct=_tax_rate_pct(cat, sell_date),
        ))
    return trades


def _parse_groww(rows: list[dict]) -> list[CapitalGainsTrade]:
    trades = []
    for row in rows:
        symbol = (row.get("Name") or row.get("Stock Name") or row.get("Symbol") or "").strip()
        if not symbol:
            continue
        isin = (row.get("ISIN") or "").strip() or None
        qty = _d(row.get("Quantity Sold") or row.get("Quantity") or 0)

        buy_date = _parse_date(str(row.get("Purchase Date") or row.get("Buy Date") or ""))
        sell_date = _parse_date(str(row.get("Selling Date") or row.get("Sell Date") or ""))
        if buy_date is None or sell_date is None:
            continue

        # Groww gives per-unit price; compute totals
        buy_price = _d(row.get("Purchase Price") or row.get("Average Buy Price") or row.get("Buy Value") or 0)
        sell_price = _d(row.get("Selling Price") or row.get("Average Sell Price") or row.get("Sell Value") or 0)
        pnl = _d(row.get("Net Profit/Loss") or row.get("Net Gain/Loss") or row.get("P&L") or 0)

        # Heuristic: if "Total Buy Value" or "Total Sell Value" present, use those as amounts
        buy_total_raw = row.get("Total Buy Value") or row.get("Buy Amount")
        sell_total_raw = row.get("Total Sell Value") or row.get("Sell Amount")
        if buy_total_raw and sell_total_raw:
            buy_amt = _d(buy_total_raw)
            sell_amt = _d(sell_total_raw)
        elif qty > 0:
            buy_amt = buy_price * qty
            sell_amt = sell_price * qty
        else:
            buy_amt = buy_price
            sell_amt = sell_price

        days = (sell_date - buy_date).days
        type_raw = str(row.get("Type") or "").upper()
        if "LONG" in type_raw:
            cat = CapitalGainsCategory.EQUITY_LTCG
        elif "SHORT" in type_raw:
            cat = CapitalGainsCategory.EQUITY_STCG
        else:
            cat = _category_from_days(days)

        trades.append(CapitalGainsTrade(
            symbol=symbol,
            isin=isin,
            quantity=qty,
            buy_date=str(buy_date),
            sell_date=str(sell_date),
            buy_amount=buy_amt,
            sell_amount=sell_amt,
            gain_loss=pnl,
            holding_days=days,
            category=cat,
            tax_rate_pct=_tax_rate_pct(cat, sell_date),
        ))
    return trades


def _parse_generic(rows: list[dict], headers: list[str]) -> list[CapitalGainsTrade]:
    h = {c.lower().strip(): c for c in headers}

    def _col(*candidates: str) -> str | None:
        for c in candidates:
            if c in h:
                return h[c]
        return None

    sym_col = _col("symbol", "scrip", "name", "stock name", "stock")
    bd_col = _col("buy date", "buy_date", "purchase date")
    sd_col = _col("sell date", "sell_date", "selling date", "sale date")
    pnl_col = _col("gain_loss", "p&l", "profit/loss", "net profit/loss", "realized p&l", "gain")
    buy_col = _col("buy value", "buy amount", "buy_amount", "cost")
    sell_col = _col("sell value", "sell amount", "sell_amount", "proceeds")

    if not all([sym_col, bd_col, sd_col, pnl_col]):
        raise ValueError(
            "Generic CSV missing required columns. Need: symbol, buy_date, sell_date, "
            "and one of: gain_loss/p&l/profit/loss. "
            f"Found headers: {headers}"
        )

    trades = []
    for row in rows:
        symbol = (row.get(sym_col) or "").strip()  # type: ignore[arg-type]
        if not symbol:
            continue
        buy_date = _parse_date(str(row.get(bd_col) or ""))  # type: ignore[arg-type]
        sell_date = _parse_date(str(row.get(sd_col) or ""))  # type: ignore[arg-type]
        if buy_date is None or sell_date is None:
            continue
        pnl = _d(row.get(pnl_col) or 0)  # type: ignore[arg-type]
        buy_amt = _d(row.get(buy_col) or 0) if buy_col else Decimal("0")
        sell_amt = _d(row.get(sell_col) or 0) if sell_col else Decimal("0")
        days = (sell_date - buy_date).days
        cat = _category_from_days(days)
        trades.append(CapitalGainsTrade(
            symbol=symbol,
            isin=None,
            quantity=Decimal("0"),
            buy_date=str(buy_date),
            sell_date=str(sell_date),
            buy_amount=buy_amt,
            sell_amount=sell_amt,
            gain_loss=pnl,
            holding_days=days,
            category=cat,
            tax_rate_pct=_tax_rate_pct(cat, sell_date),
        ))
    return trades


def _fy_ay_from_trades(trades: list[CapitalGainsTrade]) -> tuple[str, str]:
    sell_dates = [d for t in trades if (d := _parse_date(t.sell_date)) is not None]
    if not sell_dates:
        return "2024-25", "2025-26"
    latest = max(sell_dates)
    fy_start = latest.year if latest.month >= 4 else latest.year - 1
    return f"{fy_start}-{str(fy_start + 1)[2:]}", f"{fy_start + 1}-{str(fy_start + 2)[2:]}"


def _aggregate(trades: list[CapitalGainsTrade], broker: str) -> CapitalGainsSummary:
    pre_stcg = Decimal("0")
    post_stcg = Decimal("0")
    pre_ltcg = Decimal("0")
    post_ltcg = Decimal("0")
    debt_stcg = Decimal("0")
    debt_ltcg = Decimal("0")
    other_stcg = Decimal("0")
    other_ltcg = Decimal("0")
    total_gains = Decimal("0")
    total_losses = Decimal("0")
    warnings: list[str] = []

    for t in trades:
        g = t.gain_loss
        sell = _parse_date(t.sell_date)
        pre_budget = sell is not None and sell < _BUDGET_2024

        if g >= 0:
            total_gains += g
        else:
            total_losses += abs(g)

        if t.category == CapitalGainsCategory.EQUITY_STCG:
            if pre_budget:
                pre_stcg += g
            else:
                post_stcg += g
        elif t.category == CapitalGainsCategory.EQUITY_LTCG:
            if pre_budget:
                pre_ltcg += g
            else:
                post_ltcg += g
        elif t.category == CapitalGainsCategory.DEBT_STCG:
            debt_stcg += g
        elif t.category == CapitalGainsCategory.DEBT_LTCG:
            debt_ltcg += g
        elif t.category == CapitalGainsCategory.OTHER_STCG:
            other_stcg += g
        else:
            other_ltcg += g

    eq_stcg = pre_stcg + post_stcg
    eq_ltcg = pre_ltcg + post_ltcg

    # Cross-period netting within same category:
    # STCG losses (pre or post) offset STCG gains regardless of period.
    # When one period has a net positive after cross-netting, apply that period's rate.
    def _net_and_tax(gain_a: Decimal, rate_a: Decimal, gain_b: Decimal, rate_b: Decimal) -> Decimal:
        """Net gains across two periods and compute tax at respective rates."""
        if gain_a >= 0 and gain_b >= 0:
            return gain_a * rate_a + gain_b * rate_b
        if gain_a <= 0 and gain_b <= 0:
            return Decimal("0")
        if gain_a > 0 and gain_b < 0:
            net = gain_a + gain_b
            return max(Decimal("0"), net) * rate_a
        # gain_a < 0 and gain_b > 0
        net = gain_a + gain_b
        return max(Decimal("0"), net) * rate_b

    # LTCG exemption applied before cross-period netting:
    # Apply ₹1.25L exemption first against pre-budget (lower rate), then post-budget.
    remaining_exempt = _LTCG_EXEMPT_NEW
    pre_ltcg_taxable = Decimal("0")
    post_ltcg_taxable = Decimal("0")

    if pre_ltcg > 0:
        absorb = min(pre_ltcg, remaining_exempt)
        pre_ltcg_taxable = pre_ltcg - absorb
        remaining_exempt -= absorb

    if post_ltcg > 0:
        absorb = min(post_ltcg, remaining_exempt)
        post_ltcg_taxable = post_ltcg - absorb

    eq_ltcg_taxable = max(Decimal("0"), pre_ltcg_taxable + post_ltcg_taxable)

    tax_stcg = _net_and_tax(pre_stcg, _STCG_OLD, post_stcg, _STCG_NEW)
    tax_ltcg = _net_and_tax(pre_ltcg_taxable, _LTCG_OLD, post_ltcg_taxable, _LTCG_NEW)
    total_cg_tax = tax_stcg + tax_ltcg

    # Warnings
    if debt_stcg != 0 or debt_ltcg != 0:
        warnings.append(
            "Debt gains taxed at slab rate — add to total income in regime optimizer, "
            "not included in capital_gains_tax figure."
        )
    if eq_stcg < 0:
        warnings.append(
            f"Equity STCG net loss ₹{abs(eq_stcg):,.0f} — can offset STCG or LTCG gains. "
            "Carry forward 8 years if unabsorbed (file ITR before due date)."
        )
    if eq_ltcg < 0:
        warnings.append(
            f"Equity LTCG net loss ₹{abs(eq_ltcg):,.0f} — can offset LTCG only. "
            "Carry forward 8 years."
        )
    if pre_ltcg > 0 or pre_stcg > 0:
        warnings.append(
            "Pre-July 23, 2024 equity sells: STCG taxed at 15%, LTCG at 10% (old Budget 2024 rates)."
        )
    if eq_ltcg > 0 and eq_ltcg_taxable == 0:
        warnings.append(f"LTCG ₹{eq_ltcg:,.0f} fully within ₹1.25L exemption — zero LTCG tax.")

    fy, ay = _fy_ay_from_trades(trades)

    return CapitalGainsSummary(
        trades=trades,
        pre_budget_eq_stcg=pre_stcg,
        post_budget_eq_stcg=post_stcg,
        pre_budget_eq_ltcg=pre_ltcg,
        post_budget_eq_ltcg=post_ltcg,
        equity_stcg=eq_stcg,
        equity_ltcg=eq_ltcg,
        equity_ltcg_taxable=eq_ltcg_taxable,
        debt_stcg=debt_stcg,
        debt_ltcg=debt_ltcg,
        other_stcg=other_stcg,
        other_ltcg=other_ltcg,
        total_gains=total_gains,
        total_losses=total_losses,
        tax_equity_stcg=tax_stcg,
        tax_equity_ltcg=tax_ltcg,
        total_capital_gains_tax=total_cg_tax,
        broker=broker,
        total_trades=len(trades),
        financial_year=fy,
        assessment_year=ay,
        warnings=warnings,
    )


def parse_capital_gains_csv(csv_bytes: bytes, filename: str = "trades.csv") -> CapitalGainsSummary:
    """
    Parse broker P&L CSV and compute capital gains with Budget 2024 rate split.
    Raises ValueError for unrecognized format or empty files.
    """
    text = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        raise ValueError("CSV appears empty or has no header row.")

    headers = list(reader.fieldnames)
    rows = list(reader)

    if not rows:
        raise ValueError("No trade rows found in CSV.")

    broker = _detect_broker(headers)

    if broker == "zerodha":
        trades = _parse_zerodha(rows)
    elif broker == "groww":
        trades = _parse_groww(rows)
    elif broker == "generic":
        trades = _parse_generic(rows, headers)
    else:
        raise ValueError(
            "Unrecognized CSV format. "
            "Supported: Zerodha Tax P&L (Console → Reports → Tax P&L), "
            "Groww Realized P&L, or a generic CSV with symbol/buy_date/sell_date/gain_loss columns. "
            f"Found headers: {headers[:8]}"
        )

    if not trades:
        raise ValueError(f"Parsed 0 trades from {broker} CSV. Check date formats and required columns.")

    return _aggregate(trades, broker)
