# GLI PFT Calculator

A web application and command-line toolkit for **Global Lung Function Initiative (GLI)** pulmonary function test (PFT) reference values. Computes predicted medians, lower and upper limits of normal (LLN / ULN), z-scores, percent predicted, and **pattern classification** (normal, obstruction, restriction, mixed) from spirometry and static lung volumes.

Developed by **Alireza Keshavarzian** under the supervision of **Dr. Chow** at **University Health Network (UHN)**, Toronto.

---

## Features

| Feature | Description |
|--------|-------------|
| **Manual entry** | Enter age, sex, height and optional measured values; view GLI reference tables and pattern classification |
| **Excel batch** | Upload a clinic PFT export, map columns, append GLI columns to your spreadsheet, download `*_GLI.xlsx` |
| **Pattern classification** | Normal / obstruction / restriction / mixed based on FEV₁/FVC and TLC vs GLI LLN |
| **CLI tools** | Standalone Python scripts for spirometry and lung volumes without the web UI |

### Reference equations

| Module | Standard | Parameters |
|--------|----------|------------|
| Spirometry | **GLI-2022** (Bowerman et al.) | FEV₁, FVC, FEV₁/FVC |
| Lung volumes | **GLI-2021** (Hall et al.) | TLC, FRC, RV, RV/TLC, ERV, IC, VC |

### Pattern classification rules

Interpretation uses measured values compared to **GLI LLN** (5th percentile):

| Pattern | Criteria |
|---------|----------|
| **Normal** | FEV₁/FVC ≥ LLN and TLC ≥ LLN |
| **Obstruction** | FEV₁/FVC &lt; LLN |
| **Restriction** | TLC &lt; LLN and FEV₁/FVC ≥ LLN |
| **Mixed** | FEV₁/FVC &lt; LLN and TLC &lt; LLN |

If FEV₁/FVC or TLC is missing, the app reports the best available pattern and notes what could not be assessed (e.g. cannot exclude mixed without TLC).

---

## Project structure

```
LLN-GLI-Pulmonary/
├── gli_spirometry.py          # CLI — GLI-2022 spirometry
├── gli_TLC.py                 # CLI — GLI-2021 lung volumes
├── requirements.txt           # Python dependencies
├── backend/
│   └── app/
│       ├── main.py            # FastAPI application
│       ├── schemas.py         # Request/response models
│       └── services/
│           ├── gli_service.py       # GLI calculations
│           ├── batch_service.py     # Excel import/export
│           └── classification.py  # PFT pattern logic
├── frontend/                  # React + Vite + Tailwind UI
├── data/
│   ├── reference/             # GLI lookup tables (required)
│   │   ├── spirometry_GLI.xlsx
│   │   └── TLC_GLI.xlsx
│   ├── samples/               # Example clinic exports
│   └── output/                # Notebook / batch exports (gitignored)
├── notebooks/
│   └── batch_gli_aggregate.ipynb   # Multi-file Excel → GLI + classification
└── scripts/
    ├── start-api.sh           # Run API with project venv
    └── run_dev.sh             # Run API + frontend together
```

---

## Prerequisites

- **Python** 3.10+ (3.11 or 3.13 recommended)
- **Node.js** 18+ and npm (for the web UI)
- GLI supplementary Excel files in `data/reference/` (see [References](#references))

---

## Installation

### 1. Clone and enter the project

```bash
cd /path/to/LLN-GLI-Pulmonary
```

### 2. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Reference data

Place the official GLI lookup workbooks in `data/reference/`:

- `spirometry_GLI.xlsx` — GLI-2022 global spirometry tables  
- `TLC_GLI.xlsx` — GLI-2021 static lung volume tables  

The CLI and API will also check the project root for legacy filenames if files are not in `data/reference/`.

---

## Running the application

### Option A — Two terminals (recommended)

**Terminal 1 — API** (always use the project venv; see [Troubleshooting](#troubleshooting)):

```bash
./scripts/start-api.sh
```

**Terminal 2 — Web UI**:

```bash
cd frontend && npm run dev
```

- **App:** http://127.0.0.1:5173  
- **API docs:** http://127.0.0.1:8000/docs  

### Option B — Single script

```bash
./scripts/run_dev.sh
```

### Manual API start

```bash
source .venv/bin/activate
export PYTHONPATH=.
.venv/bin/uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Production build (frontend only)

```bash
cd frontend && npm run build
```

Serve `frontend/dist/` behind any static file server; ensure `/api` is proxied to the FastAPI backend (see `frontend/vite.config.ts` for dev proxy settings).

---

## Using the web app

### Manual entry

1. Open **Manual entry**.
2. Enter **age**, **sex**, **height (cm)**.
3. Enable **GLI-2022 Spirometry** and/or **GLI-2021 Lung volumes**.
4. Optionally enter measured values (FEV₁, FVC, TLC, etc.).
5. Click **Calculate GLI reference**.

Results include predicted, LLN, ULN, measured (if provided), % predicted, z-score, status, and **PFT pattern** when FEV₁/FVC and/or TLC are available.

### Excel batch

1. Open **Excel batch** and upload your `.xlsx` file.
2. Map Excel columns to demographics and measurements (use **Use BMT sample mapping** for the sample file in `data/samples/`).
3. Click **Add GLI columns & download Excel**.

Your original columns are preserved. New columns are appended, including:

| Column pattern | Content |
|----------------|---------|
| `GLI_{param}_Predicted` | GLI median (predicted) |
| `GLI_{param}_LLN` | Lower limit of normal |
| `GLI_{param}_ULN` | Upper limit of normal |
| `GLI_{param}_z` | z-score (if measured) |
| `GLI_{param}_pct_pred` | % predicted (if measured) |
| `GLI_{param}_Status` | `normal` / `below_lln` / `above_uln` |
| `GLI_PFT_Pattern` | Normal, Obstruction, Restriction, Mixed, … |
| `GLI_PFT_Pattern_detail` | Short explanation |
| `GLI_processing_note` | Row-level warnings or errors |

**Age:** map an **Age** column, or **Date of birth** + **Test date** (age is computed automatically).

**Ratios as percent:** FEV₁/FVC and RV/TLC stored as percent (e.g. `72.5` meaning 72.5%) are converted to ratios when values are &gt; 2.

Tab state (upload, mapping, results) is kept when switching between Manual, Batch, and About.

---

## Batch notebook (multiple Excel files)

Process one or many PFT spreadsheets offline; outputs one combined file with GLI predicted / **LLN** / ULN / z-scores and **pattern classification**.

```bash
pip install jupyter ipykernel   # included in requirements.txt
export PYTHONPATH=.
jupyter notebook notebooks/batch_gli_aggregate.ipynb
```

Edit `INPUT_FILES` in the notebook, run all cells, get `data/output/aggregated_PFT_GLI.xlsx`. Details: [notebooks/README.md](notebooks/README.md).

---

## Command-line interface

### Spirometry (GLI-2022)

```bash
python gli_spirometry.py --age 40 --height 175 --sex M
python gli_spirometry.py --age 40 --height 175 --sex M --fev1 2.5 --fvc 3.2 --fev1fvc 0.78
```

### Lung volumes (GLI-2021)

```bash
python gli_TLC.py --age 40 --height 175 --sex M
python gli_TLC.py --age 40 --height 175 --sex M --tlc 5.2 --rv 1.8 --rvtlc 0.35
```

Run without arguments for interactive prompts. Valid age ranges: spirometry 3–95 years; lung volumes 5–80 years. For batch/API, chronological age outside 5–80 is **capped** to that bound for lung-volume GLI only (with a note in `GLI_processing_note`), so TLC/RV columns are still filled.

---

## API overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/schema/fields` | Mappable field definitions |
| `GET` | `/api/schema/default-mapping` | BMT sample column preset |
| `POST` | `/api/calculate/manual` | Single-patient GLI + classification (JSON) |
| `POST` | `/api/batch/preview` | Upload Excel → columns + suggested mapping |
| `POST` | `/api/batch/calculate` | Upload Excel + mapping → results + base64 `*_GLI.xlsx` |

Interactive documentation: http://127.0.0.1:8000/docs

---

## Output terminology

| Term | Meaning |
|------|---------|
| **Predicted** | GLI median expected value for age, sex, height |
| **LLN** | Lower limit of normal (5th percentile; z = −1.645) |
| **ULN** | Upper limit of normal (95th percentile; z = +1.645) |
| **% pred** | Measured ÷ predicted × 100 |
| **z-score** | Standardised deviation from predicted (GLI LMS / BCPE method per parameter) |

---

## Troubleshooting

### `python-multipart` / Form data error on startup

If Anaconda is active, `uvicorn` may run from conda instead of `.venv`:

```bash
which uvicorn   # should point to .../LLN-GLI-Pulmonary/.venv/bin/uvicorn
./scripts/start-api.sh
```

### `ModuleNotFoundError: backend`

Set the project root on `PYTHONPATH`:

```bash
export PYTHONPATH=.
```

### Excel file not found

Confirm `data/reference/spirometry_GLI.xlsx` and `data/reference/TLC_GLI.xlsx` exist.

### Frontend cannot reach API

Ensure the API is on port **8000** and Vite dev server proxies `/api` (default in `frontend/vite.config.ts`).

---

## References

- **GLI-2022 spirometry:** Bowerman C et al. *Am J Respir Crit Care Med.* 2023;207(8):1036-1045.  
- **GLI-2021 lung volumes:** Hall GL et al. *Eur Respir J.* 2021;57(3):2000289. DOI: [10.1183/13993003.00289-2020](https://doi.org/10.1183/13993003.00289-2020)  
- **GLI calculators:** [ersnet.org](https://www.ersnet.org/)

---

## Contact

**Alireza Keshavarzian**

- keshavarzian.alireza@gmail.com  
- alireza.keshavarzian@uhn.ca  

---

## Production deployment (AWS)

See **[deploy/DEPLOYMENT.md](deploy/DEPLOYMENT.md)** for a full guide (each command explained).

**Application root on server:** `/opt/gli-pft/GLI-pulmonary-measurment`  
**API environment file:** `/etc/gli-pft/env` (not the same as the project folder)

Quick summary:

1. Ubuntu EC2; security group: 22, 80, 443 only (not 8000).  
2. Code at `/opt/gli-pft/GLI-pulmonary-measurment`; GLI Excel in `data/reference/`.  
3. `.venv` + `pip install -r requirements.txt`; build or rsync `frontend/dist/`.  
4. `deploy/gli-pft-api.service` + `deploy/nginx-gli-pft.conf` + `certbot`.

---

## Disclaimer

This software is intended for **research and educational use**. Results should be verified against official GLI tools and interpreted by qualified clinicians before clinical decision-making. The authors and UHN assume no liability for clinical use of these outputs.
