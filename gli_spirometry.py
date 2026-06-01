"""
GLI-2022 Global Spirometry Reference Calculator
================================================
Source: Bowerman C et al., Am J Respir Crit Care Med. 2023;207(8):1036-1045
        Lookup tables: gli_global_lookuptables_dec6.xlsx

Computes predicted values, LLN, ULN, z-scores and % predicted for:
  FEV1, FVC, FEV1/FVC

Equations (BCPE/LMS method — L is NOT zero for spirometry):
  M = exp(a0 + a1·ln(height_cm) + a2·ln(age) + Mspline(age))
  S = exp(b0 + b1·ln(age)       + Sspline(age))
  L = constant  [FEV1, FVC]
      OR  c0 + c1·ln(age)  [FEV1/FVC — age-varying]

  predicted = M
  z-score   = [ (measured/M)^L − 1 ] / (L·S)
  LLN       = M · (1 + L·S·(−1.645))^(1/L)   [5th percentile]
  ULN       = M · (1 + L·S·(+1.645))^(1/L)   [95th percentile]

  NOTE: height must be in centimetres (not metres) for these equations.

Usage
-----
  python gli_spirometry.py                              # interactive
  python gli_spirometry.py --age 40 --height 175 --sex M
  python gli_spirometry.py --age 65 --height 162 --sex F \\
                           --fev1 2.1 --fvc 3.0 --fev1fvc 0.70

Arguments
---------
  --age      : years  (valid range 3–95)
  --height   : cm
  --sex      : M or F
  --excel    : path to GLI lookup table Excel file
               (default: looks in same folder as this script)
  --fev1     : measured FEV1 in litres  (optional)
  --fvc      : measured FVC in litres   (optional)
  --fev1fvc  : measured FEV1/FVC ratio  (optional)
"""

import numpy as np
import pandas as pd
import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Regression coefficients — embedded in the Excel file (col F–G, rows 4–6)
# ---------------------------------------------------------------------------
# M  = exp(a0 + a1·ln(height_cm) + a2·ln(age) + Mspline)
# S  = exp(b0 + b1·ln(age)       + Sspline)
# L  = l0  [constant]  OR  l0 + l1·ln(age)  [age-varying, FEV1/FVC only]
# ---------------------------------------------------------------------------
COEFF = {
    "FEV1": {
        "M": dict(a0=-11.399108, a1= 2.462664, a2=-0.011394,
                  b0= -2.256278, b1= 0.080729,
                  l0=  1.227030, l1= 0.0),
        "F": dict(a0=-10.901689, a1= 2.385928, a2=-0.076386,
                  b0= -2.364047, b1= 0.129402,
                  l0=  1.213880, l1= 0.0),
    },
    "FVC": {
        "M": dict(a0=-12.629131, a1= 2.727421, a2= 0.009174,
                  b0= -2.195595, b1= 0.068466,
                  l0=  0.934600, l1= 0.0),
        "F": dict(a0=-12.055901, a1= 2.621579, a2=-0.035975,
                  b0= -2.310148, b1= 0.120428,
                  l0=  0.899000, l1= 0.0),
    },
    "FEV1FVC": {   # ratio (dimensionless); L varies with age
        "M": dict(a0=  1.022608, a1=-0.218592, a2=-0.027586,
                  b0= -2.882025, b1= 0.068889,
                  l0=  3.824300, l1=-0.332800),   # L = l0 + l1·ln(age)
        "F": dict(a0=  0.918957, a1=-0.184067, a2=-0.046131,
                  b0= -3.171582, b1= 0.144358,
                  l0=  6.649000, l1=-0.992000),   # L = l0 + l1·ln(age)
    },
}

UNITS = {"FEV1": "L", "FVC": "L", "FEV1FVC": "ratio"}

FULL_NAMES = {
    "FEV1":    "Forced Expiratory Volume in 1 s",
    "FVC":     "Forced Vital Capacity",
    "FEV1FVC": "FEV1/FVC ratio",
}

SHEET_MAP = {
    ("FEV1",    "M"): "Male FEV1",
    ("FVC",     "M"): "Male FVC",
    ("FEV1FVC", "M"): "Male FEV1 FVC",
    ("FEV1",    "F"): "Female FEV1",
    ("FVC",     "F"): "Female FVC",
    ("FEV1FVC", "F"): "Female FEV1 FVC",
}


# ---------------------------------------------------------------------------
# Spline loading
# ---------------------------------------------------------------------------

def load_splines(excel_path: str) -> dict:
    """
    Load all 6 lookup-table sheets from the GLI spirometry Excel file.
    Returns: splines[(param, sex)] -> DataFrame[age, Mspline, Sspline]
    """
    xl = pd.ExcelFile(excel_path)
    splines = {}
    for (param, sex), sheet in SHEET_MAP.items():
        df = xl.parse(sheet)
        # Normalise column names — the age column header varies between sheets
        cols = list(df.columns)
        df = df.rename(columns={cols[0]: "age", cols[1]: "Mspline", cols[2]: "Sspline"})
        df = df[["age", "Mspline", "Sspline"]].dropna(subset=["age"])
        df = df[pd.to_numeric(df["age"], errors="coerce").notna()].copy()
        df = df.astype({"age": float, "Mspline": float, "Sspline": float})
        splines[(param, sex)] = df
    return splines


def _interp(splines, param, sex, age):
    df = splines[(param, sex)]
    ms = float(np.interp(age, df["age"].values, df["Mspline"].values))
    ss = float(np.interp(age, df["age"].values, df["Sspline"].values))
    return ms, ss


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def compute(age: float, height_cm: float, sex: str,
            param: str, splines: dict) -> dict:
    """
    Compute GLI spirometry reference values for one parameter.

    Parameters
    ----------
    age       : years (3–95)
    height_cm : height in centimetres
    sex       : 'M' or 'F'
    param     : 'FEV1', 'FVC', or 'FEV1FVC'
    splines   : dict from load_splines()

    Returns
    -------
    dict with keys:
      predicted  : median (M)
      LLN        : lower limit of normal (5th percentile)
      ULN        : upper limit of normal (95th percentile)
      S, L       : distribution parameters
      pct_lln    : LLN as % of predicted
    """
    sex = sex.upper()
    if sex not in ("M", "F"):
        raise ValueError("sex must be 'M' or 'F'")
    if not (3 <= age <= 95):
        raise ValueError(f"age {age} is outside the valid range (3–95 years)")
    if height_cm <= 0:
        raise ValueError("height must be positive")

    c = COEFF[param][sex]
    ms, ss = _interp(splines, param, sex, age)

    M = np.exp(c["a0"] + c["a1"] * np.log(height_cm) + c["a2"] * np.log(age) + ms)
    S = np.exp(c["b0"] + c["b1"] * np.log(age) + ss)
    L = c["l0"] + c["l1"] * np.log(age)   # l1=0 for FEV1 and FVC → constant L

    LLN = M * (1 + L * S * (-1.645)) ** (1 / L)
    ULN = M * (1 + L * S * ( 1.645)) ** (1 / L)

    return {
        "predicted": M,
        "LLN":       LLN,
        "ULN":       ULN,
        "S":         S,
        "L":         L,
        "pct_lln":   LLN / M * 100,
    }


def zscore(measured: float, age: float, height_cm: float,
           sex: str, param: str, splines: dict) -> float:
    """Compute z-score for a measured spirometry value (Box-Cox transform)."""
    r = compute(age, height_cm, sex, param, splines)
    return float(((measured / r["predicted"]) ** r["L"] - 1) / (r["L"] * r["S"]))


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def report(age: float, height_cm: float, sex: str,
           splines: dict, measured: dict = None) -> pd.DataFrame:
    """
    Build a summary DataFrame for all 3 spirometry parameters.

    Parameters
    ----------
    measured : optional dict, e.g. {'FEV1': 2.8, 'FVC': 3.5, 'FEV1FVC': 0.80}
    """
    rows = []
    for param in ("FEV1", "FVC", "FEV1FVC"):
        r = compute(age, height_cm, sex, param, splines)
        row = {
            "Parameter":  param,
            "Full name":  FULL_NAMES[param],
            "Unit":       UNITS[param],
            "Predicted":  round(r["predicted"], 3),
            "LLN":        round(r["LLN"],       3),
            "ULN":        round(r["ULN"],       3),
            "LLN % pred": round(r["pct_lln"],   1),
        }
        if measured and param in measured and measured[param] is not None:
            meas = float(measured[param])
            z = ((meas / r["predicted"]) ** r["L"] - 1) / (r["L"] * r["S"])
            pct = meas / r["predicted"] * 100
            flag = ("⚠ BELOW LLN" if meas < r["LLN"] else
                    "⚠ ABOVE ULN" if meas > r["ULN"] else "normal")
            row.update({
                "Measured": round(meas,  3),
                "% pred":   round(pct,   1),
                "z-score":  round(z,     2),
                "Status":   flag,
            })
        rows.append(row)
    return pd.DataFrame(rows)


def print_report(df: pd.DataFrame, age, height_cm, sex):
    print()
    print("=" * 70)
    print("  GLI-2022 Global Spirometry Reference Values")
    print(f"  Patient: Sex={sex}  Age={age} yrs  Height={height_cm} cm")
    print("  Ref: Bowerman C et al., Am J Respir Crit Care Med 2023;207(8):1036")
    print("=" * 70)
    base_cols  = ["Parameter", "Unit", "Predicted", "LLN", "ULN", "LLN % pred"]
    extra_cols = [c for c in ["Measured", "% pred", "z-score", "Status"]
                  if c in df.columns]
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

def _find_excel(hint=None):
    root = Path(__file__).parent
    candidates = [
        hint,
        root / "data" / "reference" / "spirometry_GLI.xlsx",
        root / "spirometry_GLI.xlsx",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return str(c)
    return None


def main():
    parser = argparse.ArgumentParser(
        description="GLI-2022 spirometry LLN calculator"
    )
    parser.add_argument("--age",     type=float, help="Age in years (3–95)")
    parser.add_argument("--height",  type=float, help="Height in cm")
    parser.add_argument("--sex",     type=str,   help="Sex: M or F")
    parser.add_argument("--excel",   type=str,   default=None,
                        help="Path to GLI spirometry Excel file")
    parser.add_argument("--fev1",    type=float, default=None, help="Measured FEV1 (L)")
    parser.add_argument("--fvc",     type=float, default=None, help="Measured FVC (L)")
    parser.add_argument("--fev1fvc", type=float, default=None, help="Measured FEV1/FVC ratio")
    args = parser.parse_args()

    excel_path = _find_excel(args.excel)
    interactive = (args.age is None or args.height is None or args.sex is None)

    if interactive:
        print("\nGLI-2022 Global Spirometry Reference Calculator")
        print("-" * 48)
        try:
            if args.age    is None: args.age    = float(input("Age (years, 3–95): "))
            if args.height is None: args.height = float(input("Height (cm): "))
            if args.sex    is None: args.sex    = input("Sex (M/F): ").strip().upper()
        except (ValueError, EOFError):
            print("Invalid input.")
            sys.exit(1)

        if excel_path is None:
            excel_path = input("Path to GLI spirometry Excel file: ").strip()

        print("\nOptional: enter measured values (press Enter to skip)")
        if args.fev1    is None:
            v = input("  FEV1 (L): ").strip()
            if v:
                try: args.fev1 = float(v)
                except ValueError: pass
        if args.fvc     is None:
            v = input("  FVC (L): ").strip()
            if v:
                try: args.fvc = float(v)
                except ValueError: pass
        if args.fev1fvc is None:
            v = input("  FEV1/FVC (ratio, e.g. 0.75): ").strip()
            if v:
                try: args.fev1fvc = float(v)
                except ValueError: pass
    else:
        if excel_path is None:
            print("ERROR: Excel file not found. Use --excel <path>.")
            sys.exit(1)

    measured = {
        "FEV1":    args.fev1,
        "FVC":     args.fvc,
        "FEV1FVC": args.fev1fvc,
    }
    measured = {k: v for k, v in measured.items() if v is not None}

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
