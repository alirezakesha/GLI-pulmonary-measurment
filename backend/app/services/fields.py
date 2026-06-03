"""Field definitions and default column mapping for PFT Excel imports."""

import re

from backend.app.schemas import ColumnMapping, FieldDefinition

# Canonical column written on every batch / aggregate export
CANONICAL_PATIENT_ID_COLUMN = "GLI_patient_id"
CANONICAL_PATIENT_ID_SOURCE_COLUMN = "GLI_patient_id_source"

# Exact header matches (case-insensitive); first match wins
PATIENT_ID_ALIASES: tuple[str, ...] = (
    "PATIENT ID",
    "PATIENT Health Num",
    "Patient Health Num",
    "PATIENT HEALTH NUM",
    "Patient Health Number",
    "PATIENT NUMBER",
    "Patient ID",
    "Patient Id",
    "PID",
    "Pt ID",
    "PT ID",
    "FOT ID",
    "FOT-ID",
    "FOT Id",
    "FOTID",
    "Subject ID",
    "STUDY ID",
    "Participant ID",
    "MRN",
    "Medical Record Number",
    "Hospital Number",
    "Health Number",
    "UHN",
    "EMR ID",
    "EMRID",
    "ID",
)

FIELD_DEFINITIONS: list[FieldDefinition] = [
    FieldDefinition(
        key="patient_id",
        label="Patient ID",
        group="demographics",
        hint="Optional identifier from your export",
    ),
    FieldDefinition(
        key="sex",
        label="Sex",
        group="demographics",
        required=True,
        hint="M or F",
    ),
    FieldDefinition(
        key="age",
        label="Age (years)",
        group="demographics",
        hint="Use this OR map date of birth + test date",
    ),
    FieldDefinition(
        key="dob",
        label="Date of birth",
        group="demographics",
        hint="Combined with test date to compute age",
    ),
    FieldDefinition(
        key="test_date",
        label="Test date",
        group="demographics",
        hint="Combined with date of birth to compute age",
    ),
    FieldDefinition(
        key="height_cm",
        label="Height (cm)",
        group="demographics",
        required=True,
    ),
    FieldDefinition(
        key="FEV1", label="FEV₁", group="spirometry", unit="L"
    ),
    FieldDefinition(key="FVC", label="FVC", group="spirometry", unit="L"),
    FieldDefinition(
        key="FEV1FVC",
        label="FEV₁/FVC",
        group="spirometry",
        unit="ratio",
        hint="Ratio (0.75) or percent (75) — auto-converted if > 2",
    ),
    FieldDefinition(key="TLC", label="TLC", group="lung_volumes", unit="L"),
    FieldDefinition(key="FRC", label="FRC", group="lung_volumes", unit="L"),
    FieldDefinition(key="RV", label="RV", group="lung_volumes", unit="L"),
    FieldDefinition(
        key="RVTLC",
        label="RV/TLC",
        group="lung_volumes",
        unit="ratio",
        hint="Ratio or percent — auto-converted if > 2",
    ),
    FieldDefinition(key="ERV", label="ERV", group="lung_volumes", unit="L"),
    FieldDefinition(key="IC", label="IC", group="lung_volumes", unit="L"),
    FieldDefinition(key="VC", label="VC", group="lung_volumes", unit="L"),
]

# Default mapping for BMT-style PFT exports (see data/samples/)
BMT_DEFAULT_MAPPING = ColumnMapping(
    patient_id="PATIENT ID",
    sex="PATIENT SEX",
    dob="PATIENT DOB",
    test_date="TEST DATE",
    height_cm="TEST HEIGHT",
    FEV1="Spirometry->FEV1;PRE;TESTSELECT;VALUE",
    FVC="Spirometry->FVC;PRE;TESTSELECT;VALUE",
    FEV1FVC="Spirometry->FEV1/FVC;PRE;TESTSELECT;VALUE",
    TLC="Tlc body->TLC;PRE;TESTMEAN;VALUE",
    RV="Tlc body->RV;PRE;TESTMEAN;VALUE",
    RVTLC="Tlc body->RV/TLC;PRE;TESTMEAN;VALUE",
    IC="SVC->IC;PRE;TESTMEAN;VALUE",
    VC="SVC->SVC;PRE;TESTMEAN;VALUE",
)


def _normalize_column_label(name: str) -> str:
    """Lowercase label with punctuation collapsed to spaces."""
    s = re.sub(r"[^a-z0-9]+", " ", str(name).lower().strip())
    return re.sub(r"\s+", " ", s).strip()


def _patient_id_column_score(normalized: str) -> int:
    """Higher score = more likely a patient identifier column (not sex/DOB/etc.)."""
    if not normalized:
        return 0

    for block in (
        "sex",
        "gender",
        "dob",
        "date of birth",
        "birth date",
        "height",
        "weight",
        "age",
        "name",
        "address",
        "phone",
        "email",
        "race",
        "ethnicity",
        "diagnosis",
        "note",
    ):
        if block in normalized:
            return 0

    high_phrases = (
        "patient health num",
        "patient health number",
        "patient id",
        "patient number",
        "pat health num",
        "health num",
        "fot id",
        "fotid",
        "subject id",
        "study id",
        "participant id",
        "medical record",
        "hospital number",
        "health number",
        "emr id",
    )
    for phrase in high_phrases:
        if phrase in normalized:
            return 100

    if normalized in ("pid", "pt id", "mrn", "fot id", "id"):
        return 95

    if "patient" in normalized and any(
        token in normalized for token in ("id", "num", "number", "no", "identifier", "code")
    ):
        return 85

    if normalized.endswith(" id") or normalized.endswith(" num"):
        return 75

    return 0


def resolve_patient_id_column(columns: list[str]) -> str | None:
    """
    Pick the best Excel column for patient identifier in this file.

    Used per file during batch aggregate so PATIENT ID / Patient Health Num /
    PID / FOT-ID etc. map to one logical field.
    """
    col_list = [str(c) for c in columns]
    col_set = set(col_list)

    default = BMT_DEFAULT_MAPPING.patient_id
    if default and default in col_set:
        return default

    lower_to_orig = {c.lower().strip(): c for c in col_list}
    for alias in PATIENT_ID_ALIASES:
        key = alias.lower().strip()
        if key in lower_to_orig:
            return lower_to_orig[key]

    best_col: str | None = None
    best_score = 0
    for col in col_list:
        score = _patient_id_column_score(_normalize_column_label(col))
        if score > best_score:
            best_score = score
            best_col = col

    if best_score >= 75:
        return best_col
    return None


def format_patient_id(value: object) -> str | None:
    """Normalize ID values for consistent CSV (strings, no float artifacts)."""
    if value is None:
        return None
    try:
        import pandas as pd

        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, float) and value == int(value):
        return str(int(value))
    text = str(value).strip()
    return text or None


# Internal keys for measured PFT parameters (batch column mapping)
_MEASURE_FIELD_KEYS: tuple[str, ...] = (
    "FEV1",
    "FVC",
    "FEV1FVC",
    "TLC",
    "FRC",
    "RV",
    "RVTLC",
    "ERV",
    "IC",
    "VC",
)

# BMT/Jaeger path-style headers — must match the parameter segment, not substrings (e.g. FVC in FEV1/FVC)
_BMT_RAW_PATTERNS: dict[str, re.Pattern[str]] = {
    "FEV1": re.compile(r"spirometry\s*->\s*fev\s*1\s*;", re.IGNORECASE),
    "FVC": re.compile(r"spirometry\s*->\s*fvc\s*;", re.IGNORECASE),
    "FEV1FVC": re.compile(r"spirometry\s*->\s*fev\s*1\s*/\s*fvc", re.IGNORECASE),
    "TLC": re.compile(r"tlc\s+body\s*->\s*tlc\s*;", re.IGNORECASE),
    "FRC": re.compile(r"tlc\s+body\s*->\s*frc\s*;", re.IGNORECASE),
    "RV": re.compile(r"tlc\s+body\s*->\s*rv\s*;", re.IGNORECASE),
    "RVTLC": re.compile(r"tlc\s+body\s*->\s*rv\s*/\s*tlc", re.IGNORECASE),
    "ERV": re.compile(r"svc\s*->\s*erv\s*;", re.IGNORECASE),
    "IC": re.compile(r"svc\s*->\s*ic\s*;", re.IGNORECASE),
    "VC": re.compile(r"svc\s*->\s*svc\s*;", re.IGNORECASE),
}

# Manual extraction workbooks (e.g. AGT): measured pre-bronch columns by normalized header
_MANUAL_PRE_MEASURES: dict[str, tuple[str, ...]] = {
    "FEV1": ("pre fev1",),
    "FVC": ("pre fvc",),
    "FEV1FVC": ("pre fev1 fvc",),
    "TLC": ("pre tlc",),
    "RV": ("pre rv",),
    "RVTLC": ("pre rv tlc",),
    "IC": ("pre ic pl",),
    "VC": ("pre vc pl",),
}

_MANUAL_PRE_DEMOGRAPHICS: dict[str, tuple[str, ...]] = {
    "sex": ("sex",),
    "age": ("age",),
    "dob": ("dob",),
    "test_date": ("test date",),
    "height_cm": ("height",),
    "patient_id": ("id",),
}

# Plain headers: "Pre FVC", "FEV1 (Pre)", "TLC pre-bronch", etc.
_PLAIN_PARAM_PATTERNS: dict[str, re.Pattern[str]] = {
    "FEV1": re.compile(r"\bfev\s*1\b(?!\s*[/]\s*fvc)"),
    "FVC": re.compile(r"(?<![\w/])fvc\b(?!\s*[/])"),
    "FEV1FVC": re.compile(r"\bfev\s*1\s*[/]\s*fvc\b|\bfev\s*1\s*fvc\b|\bfev1fvc\b"),
    "TLC": re.compile(r"\btlc\b(?!\s*[/])"),
    "FRC": re.compile(r"\bfrc\b"),
    "RV": re.compile(r"\brv\b(?!\s*[/])"),
    "RVTLC": re.compile(r"\brv\s*[/]\s*tlc\b|\brv\s*tlc\b"),
    "ERV": re.compile(r"\berv\b"),
    "IC": re.compile(r"\bic\b(?!\s*[/])"),
    "VC": re.compile(r"\bvc\b|\bsvc\b"),
}


def _column_looks_like_percent_or_derived(raw: str, normalized: str) -> bool:
    """Skip % predicted, delta, norm-only columns when picking measured values."""
    raw_l = raw.lower()
    if raw_l.startswith("%") or raw_l.startswith("percent "):
        return True
    if any(
        token in raw_l
        for token in (
            "%norm",
            "%pre",
            "deltapc",
            "delta",
            ";norm",
            "% pred",
            "percent",
            "pct ",
            " %",
        )
    ):
        return True
    if normalized.endswith(" pc") or " percent" in normalized:
        return True
    return False


def _measure_column_score(field_key: str, column: str) -> int:
    """
    Score how well an Excel column matches a GLI measure field.
    Higher = better. 0 = no match.
    """
    raw = str(column)
    norm = _normalize_column_label(raw)
    if not norm:
        return 0

    if _column_looks_like_percent_or_derived(raw, norm):
        return 0

    score = 0

    raw_l = raw.lower()
    bmt_pat = _BMT_RAW_PATTERNS.get(field_key)
    if bmt_pat and bmt_pat.search(raw):
        score = max(score, 85)

    pattern = _PLAIN_PARAM_PATTERNS.get(field_key)
    if pattern and pattern.search(norm):
        score = max(score, 70)

    if score == 0:
        return 0

    # Prefer pre-bronch / pre-test measured values (aligns with BMT PRE;TESTSELECT;VALUE)
    if re.search(r"\bpre\b", norm) or ";pre;" in raw_l:
        score += 35
    if re.search(r"\bpost\b", norm) or "postsel" in raw_l or ";post" in raw_l:
        score -= 40

    # Prefer actual measured value columns
    if "value" in raw_l or norm.endswith(" value") or norm in ("fev1", "fvc", "tlc"):
        score += 25
    if "testselect" in raw_l or "testmean" in raw_l:
        score += 15

    # Penalize wrong parameter (e.g. FEV1 column when we want FVC only)
    if field_key == "FVC" and re.search(r"\bfev\s*1\s*[/]\s*fvc\b", norm):
        return 0
    if field_key == "FEV1" and re.search(r"\bfev\s*1\s*[/]\s*fvc\b", norm):
        return 0
    if field_key == "TLC" and re.search(r"\brv\s*[/]\s*tlc\b", norm):
        return 0
    if field_key == "RV" and re.search(r"\brv\s*[/]\s*tlc\b", norm):
        return 0

    # Shorter plain labels ("Pre FVC") beat long BMT paths when both match
    if score >= 70 and len(norm) <= 24:
        score += 10

    return score


def _norm_column_lookup(columns: list[str]) -> dict[str, str]:
    """Map normalized header → original Excel column name (first measured-value column wins)."""
    out: dict[str, str] = {}
    for col in columns:
        raw = str(col)
        norm = _normalize_column_label(raw)
        if not norm or _column_looks_like_percent_or_derived(raw, norm):
            continue
        if norm.startswith("ref "):
            continue
        if norm not in out:
            out[norm] = raw
    return out


def is_manual_pre_export(columns: list[str]) -> bool:
    """
    Workbooks with separate Pre FEV1 / Pre FVC / … columns (manual extraction layout).
    Example: data/all/AGT/AGT PFT manual extraction until Mar 2020.xlsx
    """
    norms = {_normalize_column_label(c) for c in columns}
    return "pre fev1" in norms and "pre fvc" in norms


def suggest_mapping_manual_pre(columns: list[str]) -> ColumnMapping:
    """Exact normalized-header mapping for manual Pre* PFT extraction sheets."""
    by_norm = _norm_column_lookup(columns)

    def pick(field: str, *norm_names: str) -> str | None:
        for name in norm_names:
            if name in by_norm:
                return by_norm[name]
        return None

    suggested: dict[str, str | None] = {}
    for field, norm_names in _MANUAL_PRE_DEMOGRAPHICS.items():
        suggested[field] = pick(field, *norm_names)
    if not suggested.get("patient_id"):
        suggested["patient_id"] = resolve_patient_id_column(columns)

    for field, norm_names in _MANUAL_PRE_MEASURES.items():
        suggested[field] = pick(field, *norm_names)

    return ColumnMapping(**suggested)


def resolve_measure_column(field_key: str, columns: list[str]) -> str | None:
    """Best Excel column for one measured parameter (per-file auto mapping)."""
    best_col: str | None = None
    best_score = 0
    for col in columns:
        s = _measure_column_score(field_key, col)
        if s > best_score:
            best_score = s
            best_col = str(col)
    if best_score >= 60:
        return best_col
    return None


def suggest_mapping(columns: list[str]) -> ColumnMapping:
    """Suggest column mapping by matching known BMT headers or fuzzy labels."""
    col_list = [str(c) for c in columns]
    if is_manual_pre_export(col_list):
        return suggest_mapping_manual_pre(col_list)

    col_set = set(col_list)
    mapping_dict = BMT_DEFAULT_MAPPING.model_dump()
    suggested: dict[str, str | None] = {}
    for key, default_col in mapping_dict.items():
        if default_col and default_col in col_set:
            suggested[key] = default_col
        else:
            suggested[key] = None

    if not suggested.get("patient_id"):
        suggested["patient_id"] = resolve_patient_id_column(col_list)

    # Measured parameters: BMT exact match, else scored match ("Pre FVC", partial BMT paths, …)
    for field_key in _MEASURE_FIELD_KEYS:
        if suggested.get(field_key):
            continue
        suggested[field_key] = resolve_measure_column(field_key, col_list)

    # Demographics fuzzy fallbacks
    lower_map = {c.lower(): c for c in col_list}
    aliases = {
        "sex": ["sex", "gender", "patient sex"],
        "height_cm": ["height", "test height", "height (cm)"],
        "age": ["age", "age (years)"],
        "dob": ["dob", "date of birth", "patient dob", "birth date"],
        "test_date": ["test date", "date", "pft date", "study date"],
        "FEV1": ["fev1", "fev1 (l)", "pre fev1", "fev1 pre"],
        "FVC": ["fvc", "fvc (l)", "pre fvc", "fvc pre"],
        "FEV1FVC": ["fev1/fvc", "fev1 fvc", "pre fev1/fvc", "fev1/fvc pre"],
        "TLC": ["tlc", "tlc (l)", "pre tlc", "tlc pre"],
    }
    for field, names in aliases.items():
        if suggested.get(field):
            continue
        for name in names:
            if name in lower_map:
                suggested[field] = lower_map[name]
                break

    return ColumnMapping(**suggested)
