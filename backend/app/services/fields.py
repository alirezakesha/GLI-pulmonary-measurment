"""Field definitions and default column mapping for PFT Excel imports."""

from backend.app.schemas import ColumnMapping, FieldDefinition

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
