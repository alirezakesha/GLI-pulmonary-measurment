from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"

TLC_EXCEL = REFERENCE_DIR / "TLC_GLI.xlsx"
SPIRO_EXCEL = REFERENCE_DIR / "spirometry_GLI.xlsx"
