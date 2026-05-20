"""
Rules loader — finds the correct rules bundle for a given effective date.
Rules live in rules/YYYY-QN/ directories. The loader picks the latest bundle
whose effective date is <= the requested date.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

RULES_ROOT = Path(__file__).parent.parent / "rules"

_QUARTER_PATTERN = re.compile(r"^(\d{4})-Q([1-4])$")


def _quarter_start(folder: str) -> date | None:
    m = _QUARTER_PATTERN.match(folder)
    if not m:
        return None
    year, q = int(m.group(1)), int(m.group(2))
    month = {1: 1, 2: 4, 3: 7, 4: 10}[q]
    return date(year, month, 1)


@dataclass
class RulesBundle:
    effective_date: date
    folder: str

    # states
    state_codes: dict[str, str] = field(default_factory=dict)
    special_category_states: set[str] = field(default_factory=set)

    # thresholds (INR, as Decimal)
    normal_registration: Decimal = Decimal("2000000")
    special_registration: Decimal = Decimal("1000000")
    composition_threshold: Decimal = Decimal("5000000")
    hsn_mandatory_threshold: Decimal = Decimal("50000000")
    hsn_optional_threshold: Decimal = Decimal("15000000")

    # rates
    standard_rates: set[int] = field(default_factory=lambda: {0, 5, 12, 18, 28})
    composition_rates: dict[str, Decimal] = field(default_factory=dict)

    # late fees (raw dict, consumed by compute_late_fee)
    late_fee: dict = field(default_factory=dict)

    # due dates (raw dict)
    due_dates: dict = field(default_factory=dict)

    # ITC blocked
    itc_blocked_categories: set[str] = field(default_factory=set)
    blocked_hsn_prefixes: dict[str, str] = field(default_factory=dict)
    blocked_sac_prefixes: dict[str, str] = field(default_factory=dict)

    # RCM
    rcm_sac_prefixes: dict[str, str] = field(default_factory=dict)
    rcm_hsn_prefixes: dict[str, str] = field(default_factory=dict)
    rcm_supplier_keywords: dict[str, str] = field(default_factory=dict)


def _load(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)


def load_rules(effective_date: date | None = None) -> RulesBundle:
    """
    Load the rules bundle whose effective date is <= effective_date.
    Defaults to today if not given.
    """
    target = effective_date or date.today()

    candidates: list[tuple[date, str]] = []
    for folder in RULES_ROOT.iterdir():
        if not folder.is_dir():
            continue
        qdate = _quarter_start(folder.name)
        if qdate and qdate <= target:
            candidates.append((qdate, folder.name))

    if not candidates:
        raise RuntimeError(f"No rules bundle found for {target} in {RULES_ROOT}")

    candidates.sort(key=lambda x: x[0], reverse=True)
    chosen_date, chosen_folder = candidates[0]
    folder_path = RULES_ROOT / chosen_folder

    # Load individual files
    states_raw = _load(folder_path / "states.json")
    thresh_raw = _load(folder_path / "thresholds.json")
    rates_raw = _load(folder_path / "rates.json")
    blocked_raw = _load(folder_path / "blocked.json")
    rcm_raw = _load(folder_path / "rcm.json")

    bundle = RulesBundle(
        effective_date=chosen_date,
        folder=chosen_folder,
        state_codes=states_raw["state_codes"],
        special_category_states=set(states_raw["special_category_states"]),
        normal_registration=Decimal(str(thresh_raw["normal_registration_inr"])),
        special_registration=Decimal(str(thresh_raw["special_category_registration_inr"])),
        composition_threshold=Decimal(str(thresh_raw["composition_threshold_inr"])),
        hsn_mandatory_threshold=Decimal(str(thresh_raw["hsn_mandatory_threshold_inr"])),
        hsn_optional_threshold=Decimal(str(thresh_raw["hsn_optional_threshold_inr"])),
        standard_rates=set(rates_raw["standard_rates"]),
        composition_rates={k: Decimal(str(v)) for k, v in rates_raw["composition_rates"].items()},
        late_fee=rates_raw["late_fee"],
        due_dates=rates_raw["due_dates"],
        itc_blocked_categories=set(blocked_raw["itc_blocked_categories"]),
        blocked_hsn_prefixes=blocked_raw["blocked_hsn_prefixes"],
        blocked_sac_prefixes=blocked_raw["blocked_sac_prefixes"],
        rcm_sac_prefixes=rcm_raw["rcm_sac_prefixes"],
        rcm_hsn_prefixes=rcm_raw["rcm_hsn_prefixes"],
        rcm_supplier_keywords=rcm_raw["rcm_supplier_keywords"],
    )
    return bundle


# Module-level default bundle (cached for performance; reload by calling load_rules explicitly)
_default_bundle: RulesBundle | None = None


def get_rules(effective_date: date | None = None) -> RulesBundle:
    """Return cached default bundle, or load a dated one."""
    global _default_bundle
    if effective_date is not None:
        return load_rules(effective_date)
    if _default_bundle is None:
        _default_bundle = load_rules()
    return _default_bundle
