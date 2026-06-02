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

    if normalized in ("pid", "pt id", "mrn", "fot id"):
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


def suggest_mapping(columns: list[str]) -> ColumnMapping:
    """Suggest column mapping by matching known BMT headers or fuzzy labels."""
    col_set = set(columns)
    mapping_dict = BMT_DEFAULT_MAPPING.model_dump()
    suggested = {}
    for key, default_col in mapping_dict.items():
        if default_col and default_col in col_set:
            suggested[key] = default_col
        else:
            suggested[key] = None

    if not suggested.get("patient_id"):
        suggested["patient_id"] = resolve_patient_id_column(columns)

    # Fuzzy fallbacks for common alternate headers
    lower_map = {c.lower(): c for c in columns}
    aliases = {
        "sex": ["sex", "gender", "patient sex"],
        "height_cm": ["height", "test height", "height (cm)"],
        "age": ["age", "age (years)"],
        "FEV1": ["fev1", "fev1 (l)"],
        "FVC": ["fvc", "fvc (l)"],
    }
    for field, names in aliases.items():
        if suggested.get(field):
            continue
        for name in names:
            if name in lower_map:
                suggested[field] = lower_map[name]
                break

    return ColumnMapping(**suggested)
