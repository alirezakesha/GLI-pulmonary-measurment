"""
PFT pattern classification from FEV1/FVC and TLC vs GLI LLN.

ATS/ERS-style interpretive approach:
  - Obstruction:  FEV1/FVC below LLN
  - Restriction:  TLC below LLN with FEV1/FVC not below LLN
  - Mixed:        FEV1/FVC and TLC both below LLN
  - Normal:       both measured and neither below LLN
"""

from __future__ import annotations

from typing import Literal, Optional

from backend.app.schemas import ParameterResult, PatternClassification

PatternType = Literal[
    "normal",
    "obstruction",
    "restriction",
    "mixed",
    "insufficient_data",
]

_LABELS: dict[PatternType, str] = {
    "normal": "Normal",
    "obstruction": "Obstruction",
    "restriction": "Restriction",
    "mixed": "Mixed (obstructive + restrictive)",
    "insufficient_data": "Insufficient data",
}


def _find_param(results: list[ParameterResult], name: str) -> Optional[ParameterResult]:
    for r in results:
        if r.parameter == name:
            return r
    return None


def _below_lln(result: Optional[ParameterResult]) -> Optional[bool]:
    """True/False if measured vs LLN is known; None if not measured."""
    if result is None or result.measured is None:
        return None
    if result.status == "below_lln":
        return True
    if result.status in ("normal", "above_uln"):
        return False
    return result.measured < result.lln


def classify_pft(
    spirometry: list[ParameterResult],
    lung_volumes: list[ParameterResult],
) -> PatternClassification:
    fev1fvc = _find_param(spirometry, "FEV1FVC")
    tlc = _find_param(lung_volumes, "TLC")

    obstructive = _below_lln(fev1fvc)
    restrictive = _below_lln(tlc)

    pattern, detail = _decide_pattern(obstructive, restrictive, fev1fvc, tlc)

    return PatternClassification(
        pattern=pattern,
        label=_LABELS[pattern],
        detail=detail,
        fev1fvc_below_lln=obstructive,
        tlc_below_lln=restrictive,
    )


def _decide_pattern(
    obstructive: Optional[bool],
    restrictive: Optional[bool],
    fev1fvc: Optional[ParameterResult],
    tlc: Optional[ParameterResult],
) -> tuple[PatternType, str]:
    if obstructive is None and restrictive is None:
        return (
            "insufficient_data",
            "Map and provide measured FEV1/FVC and TLC to classify pattern.",
        )

    if obstructive is True and restrictive is True:
        return (
            "mixed",
            "FEV1/FVC below LLN and TLC below LLN.",
        )

    if obstructive is True and restrictive is False:
        return (
            "obstruction",
            "FEV1/FVC below LLN; TLC at or above LLN.",
        )

    if obstructive is False and restrictive is True:
        return (
            "restriction",
            "TLC below LLN; FEV1/FVC at or above LLN.",
        )

    if obstructive is False and restrictive is False:
        return (
            "normal",
            "FEV1/FVC and TLC at or above LLN.",
        )

    # Partial data
    if obstructive is True and restrictive is None:
        return (
            "obstruction",
            "FEV1/FVC below LLN. TLC not measured — cannot exclude mixed defect.",
        )

    if obstructive is False and restrictive is None:
        return (
            "insufficient_data",
            "FEV1/FVC not obstructive; TLC not measured — cannot confirm restriction.",
        )

    if obstructive is None and restrictive is True:
        return (
            "restriction",
            "TLC below LLN. FEV1/FVC not measured — cannot exclude mixed defect.",
        )

    if obstructive is None and restrictive is False:
        return (
            "insufficient_data",
            "TLC normal; FEV1/FVC not measured — cannot assess obstruction.",
        )

    return ("insufficient_data", "Unable to classify pattern.")
