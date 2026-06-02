"""GLI reference calculation service — wraps gli_spirometry and gli_TLC."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import gli_spirometry
import gli_TLC

from backend.app.config import SPIRO_EXCEL, TLC_EXCEL
from backend.app.schemas import ManualCalculateRequest, ParameterResult

_RATIO_PARAMS = frozenset({"FEV1FVC", "RVTLC"})
_SPIRO_PARAMS = ("FEV1", "FVC", "FEV1FVC")
_LV_PARAMS = tuple(gli_TLC.COEFF.keys())
_LV_AGE_MIN = 5.0
_LV_AGE_MAX = 80.0


class GliService:
    def __init__(self) -> None:
        self._tlc_splines: Optional[dict] = None
        self._spiro_splines: Optional[dict] = None

    @property
    def tlc_splines(self) -> dict:
        if self._tlc_splines is None:
            if not TLC_EXCEL.exists():
                raise FileNotFoundError(f"TLC reference file not found: {TLC_EXCEL}")
            self._tlc_splines = gli_TLC.load_splines(str(TLC_EXCEL))
        return self._tlc_splines

    @property
    def spiro_splines(self) -> dict:
        if self._spiro_splines is None:
            if not SPIRO_EXCEL.exists():
                raise FileNotFoundError(
                    f"Spirometry reference file not found: {SPIRO_EXCEL}"
                )
            self._spiro_splines = gli_spirometry.load_splines(str(SPIRO_EXCEL))
        return self._spiro_splines

    def calculate_manual(
        self, request: ManualCalculateRequest
    ) -> tuple[list[ParameterResult], list[ParameterResult]]:
        measured = request.measured.model_dump()
        spiro: list[ParameterResult] = []
        lv: list[ParameterResult] = []

        if "spirometry" in request.modules:
            spiro = self._report_spirometry(
                request.age, request.height_cm, request.sex, measured
            )
        if "lung_volumes" in request.modules:
            ref_age, _ = self._lung_volume_reference_age(request.age)
            lv = self._report_lung_volumes(
                ref_age, request.height_cm, request.sex, measured
            )
        return spiro, lv

    def calculate_patient(
        self,
        age: float,
        height_cm: float,
        sex: str,
        measured: dict[str, Any],
        modules: list[str] | None = None,
    ) -> tuple[list[ParameterResult], list[ParameterResult], list[str]]:
        modules = modules or ["spirometry", "lung_volumes"]
        errors: list[str] = []
        spiro: list[ParameterResult] = []
        lv: list[ParameterResult] = []

        try:
            if "spirometry" in modules:
                spiro = self._report_spirometry(age, height_cm, sex, measured)
        except Exception as exc:
            errors.append(f"Spirometry: {exc}")

        try:
            if "lung_volumes" in modules:
                ref_age, cap_note = self._lung_volume_reference_age(age)
                lv = self._report_lung_volumes(ref_age, height_cm, sex, measured)
                if cap_note:
                    errors.append(cap_note)
        except Exception as exc:
            errors.append(f"Lung volumes: {exc}")

        return spiro, lv, errors

    @staticmethod
    def _lung_volume_reference_age(age: float) -> tuple[float, Optional[str]]:
        """
        GLI-2021 lung volumes are defined for ages 5–80.

        Chronological age above 80 (or below 5) is capped so reference values
        are still computed; a note is returned for GLI_processing_note.
        """
        if age > _LV_AGE_MAX:
            return (
                _LV_AGE_MAX,
                f"Lung volumes: chronological age {age:.1f} capped at {_LV_AGE_MAX:.0f} "
                f"years for GLI-2021 reference (published equation limit).",
            )
        if age < _LV_AGE_MIN:
            return (
                _LV_AGE_MIN,
                f"Lung volumes: chronological age {age:.1f} capped at {_LV_AGE_MIN:.0f} "
                f"years for GLI-2021 reference (published equation limit).",
            )
        return age, None

    def _report_spirometry(
        self, age: float, height_cm: float, sex: str, measured: dict
    ) -> list[ParameterResult]:
        sex = sex.upper()
        df = gli_spirometry.report(
            age,
            height_cm,
            sex,
            self.spiro_splines,
            self._filter_measured(measured, _SPIRO_PARAMS),
        )
        return [_row_from_df(row) for _, row in df.iterrows()]

    def _report_lung_volumes(
        self, age: float, height_cm: float, sex: str, measured: dict
    ) -> list[ParameterResult]:
        sex = sex.upper()
        df = gli_TLC.report(
            age,
            height_cm,
            sex,
            self.tlc_splines,
            self._filter_measured(measured, _LV_PARAMS),
        )
        return [_row_from_df(row) for _, row in df.iterrows()]

    @staticmethod
    def _filter_measured(measured: dict, params: tuple) -> dict | None:
        out = {}
        for p in params:
            v = measured.get(p)
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                out[p] = GliService.normalize_value(p, v)
        return out or None

    @staticmethod
    def normalize_value(param: str, value: Any) -> float:
        v = float(value)
        if param in _RATIO_PARAMS and v > 2:
            return v / 100.0
        return v


def _row_from_df(row: pd.Series) -> ParameterResult:
    status_raw = row.get("Status")
    if isinstance(status_raw, str):
        if "BELOW" in status_raw:
            status = "below_lln"
        elif "ABOVE" in status_raw:
            status = "above_uln"
        else:
            status = "normal"
    else:
        status = None

    return ParameterResult(
        parameter=str(row["Parameter"]),
        full_name=str(row.get("Full name", row["Parameter"])),
        unit=str(row["Unit"]),
        predicted=float(row["Predicted"]),
        lln=float(row["LLN"]),
        uln=float(row["ULN"]),
        lln_pct_pred=float(row["LLN % pred"]),
        measured=_optional_float(row.get("Measured")),
        pct_pred=_optional_float(row.get("% pred")),
        z_score=_optional_float(row.get("z-score")),
        status=status,
    )


def _optional_float(val: Any) -> Optional[float]:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    return float(val)


gli_service = GliService()
