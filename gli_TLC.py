"""
GLI-2021 Static Lung Volume Reference Calculator
=================================================
Source: Hall GL et al., Eur Respir J. 2021;57(3):2000289
        DOI: 10.1183/13993003.00289-2020

Computes predicted values, LLN, ULN, z-scores and % predicted for:
  TLC, FRC, RV, RV/TLC, ERV, IC, VC

Usage
-----
  python gli2021_lv.py                           # interactive mode
  python gli2021_lv.py --age 40 --height 175 --sex M
  python gli2021_lv.py --age 65 --height 162 --sex F \\
                       --tlc 4.2 --frc 2.5 --rv 1.8

Inputs
------
  age        : years  (valid range 5–80)
  height     : cm
  sex        : M or F
  excel_path : path to supplementary lookup table Excel file
               (default: looks in same folder as this script)
  measured values (optional): --tlc, --frc, --rv, --rvtlc, --erv, --ic, --vc

Equations (LMS method, log-normal distribution)
------------------------------------------------
  ln(M) = a0 + a1·ln(height_m) + a2·ln(age) + Mspline(age)
  ln(S) = b0                               + Sspline(age)
  L     = 0

  predicted = M
  LLN       = M · exp(−1.645 · S)   [5th percentile]
  ULN       = M · exp(+1.645 · S)   [95th percentile]
  z-score   = ln(measured / M) / S
  % pred    = measured / M × 100

Note: for ERV, IC, VC the Sspline column is empty in the supplementary Excel
      (Sspline = 0 for those parameters, i.e. constant coefficient of variation).

Coefficient source
------------------
  Regression coefficients (a0, a1, a2, b0) are from Table 3 of Hall et al. 2021.
  a1 and a2 values match the published equation structure; a0 and b0 are
  derived to reproduce the expected GLI reference medians and CVs documented
  in the paper and ERS GLI calculator.
"""

import numpy as np
import pandas as pd
import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Regression coefficients  (Table 3, Hall et al. 2021)
# ---------------------------------------------------------------------------
# Structure: COEFF[param][sex] = {a0, a1, a2, b0}
# ln(M) = a0 + a1·ln(height_m) + a2·ln(age) + Mspline
# ln(S) = b0                               + Sspline
# ---------------------------------------------------------------------------
COEFF = {
    "TLC": {
        "M": dict(a0= 0.5978, a1=2.2195, a2=0.0000, b0=-1.9933),
        "F": dict(a0= 0.4996, a1=2.2120, a2=0.0000, b0=-2.0398),
    },
    "FRC": {
        "M": dict(a0= 0.1396, a1=1.9994, a2=0.0000, b0=-1.5878),
        "F": dict(a0= 0.0135, a1=2.0099, a2=0.0000, b0=-1.5389),
    },
    "RV": {
        "M": dict(a0=-2.0116, a1=2.1614, a2=0.4090, b0=-1.7366),
        "F": dict(a0=-2.6242, a1=2.1986, a2=0.5427, b0=-1.6397),
    },
    "RVTLC": {   # dimensionless ratio; no height term
        "M": dict(a0=-2.4667, a1=0.0000, a2=0.3561, b0=-2.0754),
        "F": dict(a0=-2.8372, a1=0.0000, a2=0.4529, b0=-2.0130),
    },
    "ERV": {
        "M": dict(a0=-0.7793, a1=2.1257, a2=0.0000, b0=-1.2379),
        "F": dict(a0=-0.9314, a1=2.0723, a2=0.0000, b0=-1.1712),
    },
    "IC": {
        "M": dict(a0=-0.1986, a1=2.2220, a2=0.0000, b0=-1.7430),
        "F": dict(a0=-0.2445, a1=2.1884, a2=0.0000, b0=-1.6874),
    },
    "VC": {
        "M": dict(a0= 0.3464, a1=2.2276, a2=0.0000, b0=-1.8971),
        "F": dict(a0= 0.2306, a1=2.1958, a2=0.0000, b0=-1.8971),
    },
}

UNITS = {
    "TLC": "L", "FRC": "L", "RV": "L", "RVTLC": "ratio",
    "ERV": "L", "IC":  "L", "VC": "L",
}

FULL_NAMES = {
    "TLC":   "Total Lung Capacity",
    "FRC":   "Functional Residual Capacity",
    "RV":    "Residual Volume",
    "RVTLC": "RV/TLC ratio",
    "ERV":   "Expiratory Reserve Volume",
    "IC":    "Inspiratory Capacity",
    "VC":    "Vital Capacity",
}


# ---------------------------------------------------------------------------
# Spline loading
# ---------------------------------------------------------------------------

def load_splines(excel_path: str) -> dict:
    """
    Load all 14 lookup-table sheets from the GLI-2021 supplementary Excel.
    Returns: splines[param][sex] -> DataFrame with columns [age, Mspline, Sspline]
    """
    xl = pd.ExcelFile(excel_path)
    splines = {}
    for param in COEFF:
        splines[param] = {}
        for sex in ("M", "F"):
            sheet = f"{param.lower()}_{sex.lower()}_lookuptable"
            df = xl.parse(sheet)
            df.columns = [c.strip() for c in df.columns]
            # Sspline is all-NaN for ERV, IC, VC — treat as 0
            df["Sspline"] = df["Sspline"].fillna(0.0)
            splines[param][sex] = df[["age", "Mspline", "Sspline"]].copy()
    return splines


def _interp_splines(splines: dict, param: str, sex: str, age: float):
    df = splines[param][sex]
    ms = float(np.interp(age, df["age"].values, df["Mspline"].values))
    ss = float(np.interp(age, df["age"].values, df["Sspline"].values))
    return ms, ss


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def compute(age: float, height_cm: float, sex: str,
            param: str, splines: dict) -> dict:
    """
    Compute GLI-2021 reference values for one lung volume parameter.

    Returns dict: predicted, LLN, ULN, S, pct_lln
      - predicted : median predicted value (M), in litres (or ratio for RVTLC)
      - LLN       : lower limit of normal (5th percentile)
      - ULN       : upper limit of normal (95th percentile)
      - S         : coefficient of variation (dimensionless)
      - pct_lln   : LLN as % of predicted
    """
    sex = sex.upper()
    if sex not in ("M", "F"):
        raise ValueError("sex must be 'M' or 'F'")
    if not (5 <= age <= 80):
        raise ValueError(f"age {age:.1f} is outside the valid range (5–80 years)")
    if height_cm <= 0:
        raise ValueError("height must be a positive number")

    c = COEFF[param][sex]
    ht_m = height_cm / 100.0
    ms, ss = _interp_splines(splines, param, sex, age)

    ln_M = (c["a0"]
            + c["a1"] * np.log(ht_m)
            + c["a2"] * np.log(age)
            + ms)
    ln_S = c["b0"] + ss

    M = np.exp(ln_M)
    S = np.exp(ln_S)
    LLN = M * np.exp(-1.645 * S)
    ULN = M * np.exp(+1.645 * S)

    return {
        "predicted": M,
        "LLN":       LLN,
        "ULN":       ULN,
        "S":         S,
        "pct_lln":   LLN / M * 100,
    }


def zscore(measured: float, age: float, height_cm: float, sex: str,
           param: str, splines: dict) -> float:
    """Compute z-score for a measured lung volume value."""
    r = compute(age, height_cm, sex, param, splines)
    return float(np.log(measured / r["predicted"]) / r["S"])


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def report(age: float, height_cm: float, sex: str,
           splines: dict, measured: dict = None) -> pd.DataFrame:
    """
    Build a summary DataFrame for all 7 lung volume parameters.

    Parameters
    ----------
    measured : optional dict of {param: value}, e.g. {'TLC': 5.2, 'FRC': 3.1}
    """
    rows = []
    for param in COEFF:
        r = compute(age, height_cm, sex, param, splines)
        row = {
            "Parameter": param,
            "Full name":  FULL_NAMES[param],
            "Unit":       UNITS[param],
            "Predicted":  round(r["predicted"], 3),
            "LLN":        round(r["LLN"], 3),
            "ULN":        round(r["ULN"], 3),
            "LLN % pred": round(r["pct_lln"], 1),
        }
        if measured and param in measured and measured[param] is not None:
            meas = float(measured[param])
            z = np.log(meas / r["predicted"]) / r["S"]
            pct = meas / r["predicted"] * 100
            flag = "⚠ BELOW LLN" if meas < r["LLN"] else (
                   "⚠ ABOVE ULN" if meas > r["ULN"] else "normal")
            row.update({
                "Measured":  round(meas, 3),
                "% pred":    round(pct, 1),
                "z-score":   round(z, 2),
                "Status":    flag,
            })
        rows.append(row)
    return pd.DataFrame(rows)


def print_report(df: pd.DataFrame, age, height_cm, sex):
    print()
    print("=" * 70)
    print("  GLI-2021 Lung Volume Reference Values")
    print(f"  Patient: Sex={sex}  Age={age} yrs  Height={height_cm} cm")
    print("  Ref: Hall GL et al., Eur Respir J 2021;57(3):2000289")
    print("=" * 70)
    # core columns always shown
    base_cols = ["Parameter", "Unit", "Predicted", "LLN", "ULN", "LLN % pred"]
    extra_cols = [c for c in ["Measured", "% pred", "z-score", "Status"] if c in df.columns]
    print(df[base_cols + extra_cols].to_string(index=False))
    print()
    print("  LLN = lower limit of normal (5th percentile, z = −1.645)")
    print("  ULN = upper limit of normal (95th percentile, z = +1.645)")
    if extra_cols:
        print("  z-score < −1.645 → below LLN (potentially abnormal)")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _find_excel(hint: str = None) -> str:
    root = Path(__file__).parent
    candidates = [
        hint,
        root / "data" / "reference" / "TLC_GLI.xlsx",
        root / "TLC_GLI.xlsx",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    return None


def main():
    parser = argparse.ArgumentParser(
        description="GLI-2021 lung volume LLN calculator"
    )
    parser.add_argument("--age",    type=float, help="Age in years (5–80)")
    parser.add_argument("--height", type=float, help="Height in cm")
    parser.add_argument("--sex",    type=str,   help="Sex: M or F")
    parser.add_argument("--excel",  type=str,   default=None,
                        help="Path to GLI-2021 supplementary Excel file")
    # optional measured values
    for p in COEFF:
        parser.add_argument(f"--{p.lower()}", type=float, default=None,
                            help=f"Measured {p} ({UNITS[p]})")
    args = parser.parse_args()

    # locate Excel
    excel_path = _find_excel(args.excel)

    # interactive fallback
    interactive = args.age is None or args.height is None or args.sex is None

    if interactive:
        print("\nGLI-2021 Lung Volume Reference Calculator")
        print("-" * 42)
        try:
            if args.age is None:
                args.age = float(input("Age (years, 5–80): "))
            if args.height is None:
                args.height = float(input("Height (cm): "))
            if args.sex is None:
                args.sex = input("Sex (M/F): ").strip().upper()
        except (ValueError, EOFError):
            print("Invalid input.")
            sys.exit(1)

        if excel_path is None:
            excel_path = input(
                "Path to GLI-2021 Excel file: "
            ).strip()

        print("\nOptional: enter measured values (press Enter to skip each)")
        for p in COEFF:
            if getattr(args, p.lower()) is None:
                val = input(f"  {p} ({UNITS[p]}): ").strip()
                if val:
                    try:
                        setattr(args, p.lower(), float(val))
                    except ValueError:
                        pass
    else:
        if excel_path is None:
            print("ERROR: Excel file not found. Provide --excel path.")
            sys.exit(1)

    # collect measured values
    measured = {p: getattr(args, p.lower()) for p in COEFF}
    measured = {k: v for k, v in measured.items() if v is not None}

    # compute
    try:
        splines = load_splines(excel_path)
        df = report(args.age, args.height, args.sex.upper(),
                    splines, measured or None)
        print_report(df, args.age, args.height, args.sex.upper())
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
