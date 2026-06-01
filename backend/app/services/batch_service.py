"""Batch PFT Excel import, GLI calculation, and augmented Excel export."""

from __future__ import annotations

import base64
import io
from datetime import datetime
from typing import Any, Optional

import numpy as np
import pandas as pd

from backend.app.schemas import (
    BatchCalculateResponse,
    BatchPreviewResponse,
    BatchRowResult,
    ColumnMapping,
    ParameterResult,
)
from backend.app.services.classification import classify_pft
from backend.app.services.fields import FIELD_DEFINITIONS, suggest_mapping
from backend.app.services.gli_service import gli_service, GliService

SPIRO_PARAMS = ("FEV1", "FVC", "FEV1FVC")
LV_PARAMS = ("TLC", "FRC", "RV", "RVTLC", "ERV", "IC", "VC")


def _params_for_modules(modules: list[str]) -> list[str]:
    params: list[str] = []
    if "spirometry" in modules:
        params.extend(SPIRO_PARAMS)
    if "lung_volumes" in modules:
        params.extend(LV_PARAMS)
    return params


def _gli_column_names(modules: list[str]) -> list[str]:
    """New columns appended to the user's Excel (reference + interpretation)."""
    cols: list[str] = []
    for p in _params_for_modules(modules):
        cols.extend(
            [
                f"GLI_{p}_Predicted",
                f"GLI_{p}_LLN",
                f"GLI_{p}_ULN",
                f"GLI_{p}_z",
                f"GLI_{p}_pct_pred",
                f"GLI_{p}_Status",
            ]
        )
    cols.extend(["GLI_PFT_Pattern", "GLI_PFT_Pattern_detail"])
    cols.append("GLI_processing_note")
    return cols


def preview_excel(content: bytes, filename: str) -> BatchPreviewResponse:
    df = pd.read_excel(io.BytesIO(content))
    columns = [str(c) for c in df.columns]
    sample = df.head(5).replace({np.nan: None}).to_dict(orient="records")
    for row in sample:
        for k, v in row.items():
            if isinstance(v, (pd.Timestamp, datetime)):
                row[k] = v.isoformat()[:10]
            elif isinstance(v, (np.floating, float)) and np.isnan(v):
                row[k] = None

    return BatchPreviewResponse(
        filename=filename,
        columns=columns,
        sample_rows=sample,
        row_count=len(df),
        suggested_mapping=suggest_mapping(columns),
        available_fields=FIELD_DEFINITIONS,
    )


def process_excel(
    content: bytes,
    filename: str,
    mapping: ColumnMapping,
    modules: list[str] | None = None,
) -> tuple[BatchCalculateResponse, bytes]:
    """
    Process all rows and return JSON summary plus augmented Excel bytes
    (original columns + GLI predicted / LLN / ULN / z / status columns).
    """
    df = pd.read_excel(io.BytesIO(content))
    modules = modules or ["spirometry", "lung_volumes"]

    gli_new = {}
    for col in _gli_column_names(modules):
        if col not in df.columns:
            if (
                col.endswith("_Status")
                or col
                in (
                    "GLI_processing_note",
                    "GLI_PFT_Pattern",
                    "GLI_PFT_Pattern_detail",
                )
            ):
                gli_new[col] = pd.Series([None] * len(df), dtype=object)
            else:
                gli_new[col] = np.nan
    if gli_new:
        df = pd.concat([df, pd.DataFrame(gli_new)], axis=1)

    results: list[BatchRowResult] = []
    skipped = 0

    for idx, row in df.iterrows():
        parsed = _parse_row(row, mapping)
        if parsed.get("skip"):
            skipped += 1
            note = "; ".join(parsed.get("errors", ["Missing demographics"]))
            df.at[idx, "GLI_processing_note"] = note
            results.append(
                BatchRowResult(
                    row_index=int(idx),
                    patient_id=parsed.get("patient_id"),
                    errors=[note],
                )
            )
            continue

        spiro, lv, calc_errors = gli_service.calculate_patient(
            parsed["age"],
            parsed["height_cm"],
            parsed["sex"],
            parsed["measured"],
            modules=modules,
        )
        _write_gli_columns(df, idx, spiro + lv)
        classification = classify_pft(spiro, lv)
        df.at[idx, "GLI_PFT_Pattern"] = classification.label
        df.at[idx, "GLI_PFT_Pattern_detail"] = classification.detail
        flags = _collect_flags(spiro + lv)
        notes = parsed.get("errors", []) + calc_errors
        if notes:
            df.at[idx, "GLI_processing_note"] = "; ".join(notes)
        results.append(
            BatchRowResult(
                row_index=int(idx),
                patient_id=parsed.get("patient_id"),
                age=parsed["age"],
                sex=parsed["sex"],
                height_cm=parsed["height_cm"],
                spirometry=spiro,
                lung_volumes=lv,
                classification=classification,
                errors=notes,
                flags=flags,
            )
        )

    excel_bytes = _dataframe_to_excel(df)
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    output_filename = f"{stem}_GLI.xlsx"

    response = BatchCalculateResponse(
        filename=filename,
        output_filename=output_filename,
        processed=len(df) - skipped,
        skipped=skipped,
        results=results,
        excel_base64=base64.b64encode(excel_bytes).decode("ascii"),
        added_columns=_gli_column_names(modules),
    )
    return response, excel_bytes


def _write_gli_columns(
    df: pd.DataFrame, idx: int, param_results: list[ParameterResult]
) -> None:
    for r in param_results:
        p = r.parameter
        df.at[idx, f"GLI_{p}_Predicted"] = round(r.predicted, 3)
        df.at[idx, f"GLI_{p}_LLN"] = round(r.lln, 3)
        df.at[idx, f"GLI_{p}_ULN"] = round(r.uln, 3)
        if r.measured is not None:
            if r.z_score is not None:
                df.at[idx, f"GLI_{p}_z"] = r.z_score
            if r.pct_pred is not None:
                df.at[idx, f"GLI_{p}_pct_pred"] = r.pct_pred
            if r.status:
                df.at[idx, f"GLI_{p}_Status"] = r.status


def _dataframe_to_excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


def _parse_row(row: pd.Series, mapping: ColumnMapping) -> dict[str, Any]:
    errors: list[str] = []
    m = mapping.model_dump()

    patient_id = _cell(row, m.get("patient_id"))
    sex = _normalize_sex(_cell(row, m.get("sex")))
    height_cm = _to_float(_cell(row, m.get("height_cm")))

    age = _to_float(_cell(row, m.get("age")))
    if age is None:
        dob = _to_date(_cell(row, m.get("dob")))
        test_date = _to_date(_cell(row, m.get("test_date")))
        if dob and test_date:
            age = (test_date - dob).days / 365.25
        elif dob:
            errors.append("Test date required to compute age from DOB")

    measured: dict[str, Any] = {}
    for param in (
        "FEV1", "FVC", "FEV1FVC", "TLC", "FRC", "RV", "RVTLC", "ERV", "IC", "VC"
    ):
        col = m.get(param)
        if col:
            val = _to_float(_cell(row, col))
            if val is not None:
                measured[param] = GliService.normalize_value(param, val)

    if not sex:
        errors.append("Sex is required (M or F)")
    if height_cm is None or height_cm <= 0:
        errors.append("Valid height (cm) is required")
    if age is None or age <= 0:
        errors.append("Valid age is required (map age or DOB + test date)")

    skip = bool(errors and (not sex or not height_cm or age is None))
    return {
        "skip": skip,
        "patient_id": str(patient_id) if patient_id is not None else None,
        "sex": sex,
        "age": round(age, 2) if age is not None else None,
        "height_cm": height_cm,
        "measured": measured,
        "errors": errors,
    }


def _collect_flags(rows: list[ParameterResult]) -> list[str]:
    flags = []
    for r in rows:
        if r.status == "below_lln":
            flags.append(f"{r.parameter} below LLN")
        elif r.status == "above_uln":
            flags.append(f"{r.parameter} above ULN")
    return flags


def _cell(row: pd.Series, col: Optional[str]) -> Any:
    if not col or col not in row.index:
        return None
    val = row[col]
    if pd.isna(val):
        return None
    return val


def _to_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        f = float(val)
        if np.isnan(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _to_date(val: Any) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, pd.Timestamp):
        return val.to_pydatetime()
    try:
        return pd.to_datetime(val).to_pydatetime()
    except Exception:
        return None


def _normalize_sex(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip().upper()
    if s in ("M", "MALE", "MAN"):
        return "M"
    if s in ("F", "FEMALE", "WOMAN"):
        return "F"
    if s.startswith("M"):
        return "M"
    if s.startswith("F"):
        return "F"
    return None
