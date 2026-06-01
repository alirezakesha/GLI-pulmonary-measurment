from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class MeasuredValues(BaseModel):
    FEV1: Optional[float] = None
    FVC: Optional[float] = None
    FEV1FVC: Optional[float] = None
    TLC: Optional[float] = None
    FRC: Optional[float] = None
    RV: Optional[float] = None
    RVTLC: Optional[float] = None
    ERV: Optional[float] = None
    IC: Optional[float] = None
    VC: Optional[float] = None


class ManualCalculateRequest(BaseModel):
    age: float = Field(..., ge=3, le=95)
    height_cm: float = Field(..., gt=0)
    sex: Literal["M", "F"]
    modules: list[Literal["spirometry", "lung_volumes"]] = Field(
        default_factory=lambda: ["spirometry", "lung_volumes"]
    )
    measured: MeasuredValues = Field(default_factory=MeasuredValues)


class ParameterResult(BaseModel):
    parameter: str
    full_name: str
    unit: str
    predicted: float
    lln: float
    uln: float
    lln_pct_pred: float
    measured: Optional[float] = None
    pct_pred: Optional[float] = None
    z_score: Optional[float] = None
    status: Optional[str] = None


class PatternClassification(BaseModel):
    pattern: Literal[
        "normal",
        "obstruction",
        "restriction",
        "mixed",
        "insufficient_data",
    ]
    label: str
    detail: str
    fev1fvc_below_lln: Optional[bool] = None
    tlc_below_lln: Optional[bool] = None


class ManualCalculateResponse(BaseModel):
    patient: dict[str, Any]
    spirometry: list[ParameterResult] = Field(default_factory=list)
    lung_volumes: list[ParameterResult] = Field(default_factory=list)
    classification: Optional[PatternClassification] = None


class FieldDefinition(BaseModel):
    key: str
    label: str
    group: Literal["demographics", "spirometry", "lung_volumes"]
    required: bool = False
    unit: Optional[str] = None
    hint: Optional[str] = None


class ColumnMapping(BaseModel):
    """Maps internal field keys to Excel column names (empty = skip)."""

    patient_id: Optional[str] = None
    sex: Optional[str] = None
    age: Optional[str] = None
    dob: Optional[str] = None
    test_date: Optional[str] = None
    height_cm: Optional[str] = None
    FEV1: Optional[str] = None
    FVC: Optional[str] = None
    FEV1FVC: Optional[str] = None
    TLC: Optional[str] = None
    FRC: Optional[str] = None
    RV: Optional[str] = None
    RVTLC: Optional[str] = None
    ERV: Optional[str] = None
    IC: Optional[str] = None
    VC: Optional[str] = None


class BatchPreviewResponse(BaseModel):
    filename: str
    columns: list[str]
    sample_rows: list[dict[str, Any]]
    row_count: int
    suggested_mapping: ColumnMapping
    available_fields: list[FieldDefinition]


class BatchRowResult(BaseModel):
    row_index: int
    patient_id: Optional[str] = None
    age: Optional[float] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    spirometry: list[ParameterResult] = Field(default_factory=list)
    lung_volumes: list[ParameterResult] = Field(default_factory=list)
    classification: Optional[PatternClassification] = None
    errors: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class BatchCalculateResponse(BaseModel):
    filename: str
    output_filename: str
    processed: int
    skipped: int
    results: list[BatchRowResult]
    excel_base64: str
    added_columns: list[str]
