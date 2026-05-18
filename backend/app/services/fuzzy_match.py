"""
Fuzzy matching engine for GST reconciliation.
Matches supplier names across GSTR-2B and purchase register.
"""
import re
from dataclasses import dataclass
from rapidfuzz import fuzz, process
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
    name = WHITESPACE.sub(" ", name).strip()
    return name


@dataclass
class MatchResult:
    confidence: int  # 0-100
    match_type: str  # "exact_gstin", "exact_name", "fuzzy_high", "fuzzy_medium", "no_match"
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

    # Jaro-Winkler for transpositions and abbreviations ("A.B. Corp" vs "AB Corp")
    jw_score = int(jellyfish.jaro_winkler_similarity(src, tgt) * 100)

    # Token sort ratio handles word order differences
    token_score = fuzz.token_sort_ratio(src, tgt)

    # Token set ratio handles subset matches ("ABC Industries" vs "ABC")
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
    # GSTIN is ground truth — if both present and match, done
    gstin_result = match_by_gstin(source_gstin, target_gstin)
    if gstin_result:
        return gstin_result

    # Fall back to name matching
    return match_by_name(source_name, target_name)


def find_best_match(
    source: dict,  # {gstin, name}
    candidates: list[dict],  # [{gstin, name, id}]
    threshold: int = 75,
) -> tuple[dict | None, MatchResult]:
    if not candidates:
        return None, MatchResult(0, "no_match", "", "")

    best_candidate = None
    best_result = MatchResult(0, "no_match", "", "")

    for candidate in candidates:
        result = reconcile_pair(
            source.get("gstin"),
            source["name"],
            candidate.get("gstin"),
            candidate["name"],
        )
        if result.confidence > best_result.confidence:
            best_result = result
            best_candidate = candidate

    if best_result.confidence < threshold:
        return None, best_result

    return best_candidate, best_result
