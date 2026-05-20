"""
Fuzzy matching engine for GST reconciliation.
Matches supplier names across GSTR-2B and purchase register.
"""
import re
from dataclasses import dataclass

from rapidfuzz import fuzz
import jellyfish

STRIP_SUFFIXES = re.compile(
    r"\b(pvt|private|ltd|limited|llp|llc|inc|incorporated|co|corp|"
    r"industries|enterprises|solutions|services|trading|&)\b\.?",
    re.IGNORECASE,
)
WHITESPACE = re.compile(r"\s+")
NON_ALPHA = re.compile(r"[^a-z0-9\s]")


def normalize(name: str) -> str:
    name = name.lower()
    name = NON_ALPHA.sub(" ", name)
    name = STRIP_SUFFIXES.sub(" ", name)
    return WHITESPACE.sub(" ", name).strip()


@dataclass
class MatchResult:
    confidence: int  # 0-100
    match_type: str  # "exact_gstin" | "exact_name" | "fuzzy_high" | "fuzzy_medium" | "no_match"
    normalized_source: str
    normalized_target: str


def match_by_gstin(source_gstin: str | None, target_gstin: str | None) -> MatchResult | None:
    if source_gstin and target_gstin:
        if source_gstin.upper() == target_gstin.upper():
            return MatchResult(100, "exact_gstin", source_gstin, target_gstin)
    return None


def match_by_name(source_name: str, target_name: str) -> MatchResult:
    src = normalize(source_name)
    tgt = normalize(target_name)

    if src == tgt:
        return MatchResult(100, "exact_name", src, tgt)

    jw_score = int(jellyfish.jaro_winkler_similarity(src, tgt) * 100)
    token_score = fuzz.token_sort_ratio(src, tgt)
    set_score = fuzz.token_set_ratio(src, tgt)
    confidence = max(jw_score, token_score, set_score)

    if confidence >= 90:
        match_type = "fuzzy_high"
    elif confidence >= 75:
        match_type = "fuzzy_medium"
    else:
        match_type = "no_match"

    return MatchResult(confidence, match_type, src, tgt)


def reconcile_pair(
    source_gstin: str | None,
    source_name: str,
    target_gstin: str | None,
    target_name: str,
) -> MatchResult:
    gstin_result = match_by_gstin(source_gstin, target_gstin)
    if gstin_result:
        return gstin_result
    return match_by_name(source_name, target_name)


def find_best_match(
    source: dict,
    candidates: list[dict],
    threshold: int = 75,
) -> tuple[dict | None, MatchResult]:
    if not candidates:
        return None, MatchResult(0, "no_match", "", "")

    best_candidate = None
    best_result = MatchResult(0, "no_match", "", "")

    for candidate in candidates:
        result = reconcile_pair(
            source.get("gstin"), source["name"],
            candidate.get("gstin"), candidate["name"],
        )
        if result.confidence > best_result.confidence:
            best_result = result
            best_candidate = candidate

    if best_result.confidence < threshold:
        return None, best_result
    return best_candidate, best_result
