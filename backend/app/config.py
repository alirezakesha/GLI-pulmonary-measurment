import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"

TLC_EXCEL = REFERENCE_DIR / "TLC_GLI.xlsx"
SPIRO_EXCEL = REFERENCE_DIR / "spirometry_GLI.xlsx"

# Comma-separated origins for CORS, e.g. "https://pft.example.com,https://www.example.com"
# Use "*" only for local experiments — not recommended in production.
_default_origins = "http://localhost:5173,http://127.0.0.1:5173"
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")
    if o.strip()
]
