"""Batch PFT Excel import, GLI calculation, and augmented Excel export."""

from __future__ import annotations

import base64
import io
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Union

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
from backend.app.services.fields import (
    CANONICAL_PATIENT_ID_COLUMN,
    CANONICAL_PATIENT_ID_SOURCE_COLUMN,
    FIELD_DEFINITIONS,
    format_patient_id,
    suggest_mapping,
)
from backend.app.services.gli_service import gli_service, GliService

SPIRO_PARAMS = ("FEV1", "FVC", "FEV1FVC")
LV_PARAMS = ("TLC", "FRC", "RV", "RVTLC", "ERV", "IC", "VC")
EXCEL_GLOBS = ("*.xlsx", "*.xls", "*.XLSX", "*.XLS")


def read_pft_excel(
    source: Union[str, Path, io.BytesIO],
    filename: str | None = None,
) -> pd.DataFrame:
    """
    Read .xlsx (openpyxl) or legacy .xls (xlrd) PFT exports.
    """
    if isinstance(source, (str, Path)):
        path = Path(source)
        engine = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
        return pd.read_excel(path, engine=engine)

    name = (filename or "").lower()
    engine = "xlrd" if name.endswith(".xls") else "openpyxl"
    return pd.read_excel(source, engine=engine)

# Key parameters in the readable summary export (measured + LLN + classification)
COMPACT_SUMMARY_PARAMS = ("FEV1", "FVC", "FEV1FVC", "TLC", "RV", "RVTLC")
_CONTEXT_COLUMNS = (
    "GLI_test_date",
    "GLI_age_years",
    "GLI_sex",
    "GLI_height_cm",
    *(f"GLI_measured_{p}" for p in COMPACT_SUMMARY_PARAMS),
)


def discover_excel_files(
    root: Union[str, Path],
    recursive: bool = True,
) -> list[Path]:
    """
    Find Excel files under root. Skips Excel lock files (~$...).
    """
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    files: list[Path] = []
    for pattern in EXCEL_GLOBS:
        if recursive:
            files.extend(root.rglob(pattern))
        else:
            files.extend(root.glob(pattern))

    out = sorted(
        {
            f.resolve()
            for f in files
            if f.is_file()
            and not f.name.startswith("~$")
            and "_GLI" not in f.stem  # skip prior GLI outputs if named *_GLI.xlsx
        }
    )
    return out


def summary_csv_path(full_csv_path: Union[str, Path]) -> Path:
    """e.g. aggregated_PFT_GLI.csv → aggregated_PFT_GLI_summary.csv"""
    path = Path(full_csv_path)
    return path.with_name(f"{path.stem}_summary{path.suffix or '.csv'}")


_SUMMARY_FIXED_RENAMES: dict[str, str] = {
    "GLI_source_file": "source_file",
    CANONICAL_PATIENT_ID_COLUMN: "patient_id",
    CANONICAL_PATIENT_ID_SOURCE_COLUMN: "patient_id_source",
    "GLI_test_date": "test_date",
    "GLI_age_years": "age",
    "GLI_sex": "sex",
    "GLI_height_cm": "height",
    "GLI_PFT_Pattern": "PFT_pattern",
    "GLI_PFT_Pattern_detail": "PFT_pattern_detail",
    "GLI_processing_note": "processing_note",
}


def _rename_summary_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop GLI_ prefix in summary CSV for readability."""
    rename: dict[str, str] = {}
    for col in df.columns:
        if col in _SUMMARY_FIXED_RENAMES:
            rename[col] = _SUMMARY_FIXED_RENAMES[col]
            continue
        if col.startswith("GLI_measured_"):
            param = col[len("GLI_measured_") :]
            rename[col] = f"{param}_measured"
            continue
        if col.startswith("GLI_") and "_" in col[4:]:
            param, suffix = col[4:].split("_", 1)
            rename[col] = f"{param}_{suffix.lower()}"
    return df.rename(columns=rename)


def build_compact_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Slim table: patient, test date, age, key measured values, LLN/z/status,
    and PFT pattern — without hundreds of original Excel columns.
    Column names omit the GLI_ prefix (summary export only).
    """
    id_cols = [
        c
        for c in (
            "GLI_source_file",
            CANONICAL_PATIENT_ID_COLUMN,
            CANONICAL_PATIENT_ID_SOURCE_COLUMN,
            "GLI_test_date",
            "GLI_age_years",
            "GLI_sex",
            "GLI_height_cm",
        )
        if c in df.columns
    ]

    param_cols: list[str] = []
    for param in COMPACT_SUMMARY_PARAMS:
        measured_col = f"GLI_measured_{param}"
        if measured_col in df.columns:
            param_cols.append(measured_col)
        for suffix in ("Predicted", "LLN", "z", "pct_pred", "Status"):
            col = f"GLI_{param}_{suffix}"
            if col in df.columns:
                param_cols.append(col)

    tail_cols = [
        c
        for c in (
            "GLI_PFT_Pattern",
            "GLI_PFT_Pattern_detail",
            "GLI_processing_note",
        )
        if c in df.columns
    ]

    ordered = id_cols + param_cols + tail_cols
    if not ordered:
        return pd.DataFrame()
    return _rename_summary_columns(df[ordered].copy())


def save_batch_csv_outputs(
    combined_df: pd.DataFrame,
    full_csv_path: Union[str, Path],
) -> tuple[Path, Path]:
    """Write full aggregate CSV and compact summary CSV; return both paths."""
    full_path = Path(full_csv_path)
    if full_path.suffix.lower() != ".csv":
        full_path = full_path.with_suffix(".csv")
    full_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path = summary_csv_path(full_path)
    combined_df.to_csv(full_path, index=False)
    build_compact_summary(combined_df).to_csv(summary_path, index=False)
    return full_path, summary_path


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
    df = read_pft_excel(io.BytesIO(content), filename=filename)
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


def augment_pft_dataframe(
    df: pd.DataFrame,
    mapping: ColumnMapping,
    modules: list[str] | None = None,
    source_file: str | None = None,
) -> tuple[pd.DataFrame, list[BatchRowResult], int]:
    """
    Add GLI reference columns and PFT pattern classification to a DataFrame.

    Returns (augmented_df, per_row_results, skipped_count).
    """
    modules = modules or ["spirometry", "lung_volumes"]
    df = df.copy()

    if source_file is not None:
        df.insert(0, "GLI_source_file", source_file)

    _add_canonical_patient_id(df, mapping)
    _init_context_columns(df)

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
        _write_row_context(df, idx, parsed)
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

    return df, results, skipped


def process_excel_paths(
    paths: list[Union[str, Path]],
    mapping: ColumnMapping | None = None,
    modules: list[str] | None = None,
    auto_mapping_per_file: bool = True,
) -> tuple[pd.DataFrame, list[BatchRowResult], int]:
    """
    Read one or more Excel files, compute GLI LLN/ULN/z-scores, classify patterns,
    and return one combined DataFrame (with GLI_source_file column).
    """
    modules = modules or ["spirometry", "lung_volumes"]
    frames: list[pd.DataFrame] = []
    all_results: list[BatchRowResult] = []
    total_skipped = 0

    for path in paths:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)
        raw = read_pft_excel(path)
        file_mapping = mapping
        if file_mapping is None or auto_mapping_per_file:
            file_mapping = suggest_mapping([str(c) for c in raw.columns])
        aug, results, skipped = augment_pft_dataframe(
            raw, file_mapping, modules=modules, source_file=path.name
        )
        frames.append(aug)
        all_results.extend(results)
        total_skipped += skipped

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return combined, all_results, total_skipped


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
    df = read_pft_excel(io.BytesIO(content), filename=filename)
    df, results, skipped = augment_pft_dataframe(df, mapping, modules=modules)

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


def _add_canonical_patient_id(df: pd.DataFrame, mapping: ColumnMapping) -> None:
    """One patient ID column per row, regardless of source Excel header name."""
    source_col = mapping.patient_id
    if source_col and source_col in df.columns:
        ids = df[source_col].map(format_patient_id)
    else:
        ids = pd.Series([None] * len(df), dtype=object)

    insert_at = 1 if "GLI_source_file" in df.columns else 0
    df.insert(insert_at, CANONICAL_PATIENT_ID_COLUMN, ids)
    df.insert(
        insert_at + 1,
        CANONICAL_PATIENT_ID_SOURCE_COLUMN,
        source_col if source_col else None,
    )


def _write_gli_columns(
    df: pd.DataFrame, idx: int, param_results: list[ParameterResult]
) -> None:
    for r in param_results:
        p = r.parameter
        df.at[idx, f"GLI_{p}_Predicted"] = round(r.predicted, 3)
        df.at[idx, f"GLI_{p}_LLN"] = round(r.lln, 3)
        df.at[idx, f"GLI_{p}_ULN"] = round(r.uln, 3)
        if r.measured is not None:
            df.at[idx, f"GLI_{p}_Measured"] = round(float(r.measured), 4)
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

    patient_id = format_patient_id(_cell(row, m.get("patient_id")))
    sex = _normalize_sex(_cell(row, m.get("sex")))
    height_cm = _to_float(_cell(row, m.get("height_cm")))

    test_date = _to_date(_cell(row, m.get("test_date")))
    age = _to_float(_cell(row, m.get("age")))
    if age is None:
        dob = _to_date(_cell(row, m.get("dob")))
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
        "patient_id": patient_id,
        "test_date": test_date.date().isoformat() if test_date else None,
        "sex": sex,
        "age": round(age, 2) if age is not None else None,
        "height_cm": height_cm,
        "measured": measured,
        "errors": errors,
    }


def _init_context_columns(df: pd.DataFrame) -> None:
    insert_at = 0
    if CANONICAL_PATIENT_ID_SOURCE_COLUMN in df.columns:
        insert_at = df.columns.get_loc(CANONICAL_PATIENT_ID_SOURCE_COLUMN) + 1
    elif CANONICAL_PATIENT_ID_COLUMN in df.columns:
        insert_at = df.columns.get_loc(CANONICAL_PATIENT_ID_COLUMN) + 1

    for offset, col in enumerate(_CONTEXT_COLUMNS):
        if col not in df.columns:
            if col in ("GLI_test_date", "GLI_sex"):
                series: pd.Series = pd.Series([None] * len(df), dtype=object)
            else:
                series = pd.Series([np.nan] * len(df))
            df.insert(insert_at + offset, col, series)


def _write_row_context(df: pd.DataFrame, idx: int, parsed: dict[str, Any]) -> None:
    df.at[idx, "GLI_test_date"] = parsed.get("test_date")
    age = parsed.get("age")
    df.at[idx, "GLI_age_years"] = age if age is not None else np.nan
    df.at[idx, "GLI_sex"] = parsed.get("sex")
    height = parsed.get("height_cm")
    df.at[idx, "GLI_height_cm"] = height if height is not None else np.nan
    measured = parsed.get("measured") or {}
    for param in COMPACT_SUMMARY_PARAMS:
        val = measured.get(param)
        col = f"GLI_measured_{param}"
        if col in df.columns:
            df.at[idx, col] = round(val, 4) if val is not None else np.nan


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
