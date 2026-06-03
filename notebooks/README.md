# GLI batch notebooks

## Setup

From the project root:

```bash
source .venv/bin/activate
pip install jupyter ipykernel xlrd
export PYTHONPATH=.
python -m ipykernel install --user --name=gli-pft
```

Open **`batch_gli_aggregate.ipynb`** in Jupyter or VS Code.

Ensure `data/reference/spirometry_GLI.xlsx` and `data/reference/TLC_GLI.xlsx` exist.

For the folder **Browse** button to work, run Jupyter on your Mac (tkinter). On a headless server, type the folder path instead.

## `batch_gli_aggregate.ipynb`

1. Run the **setup** cell (loads GLI tables).
2. Run the **folder picker** cell — a macOS dialog opens; choose the folder with PFT Excel files.
   - Cancel the dialog to use `BATCH_ROOT` from the setup cell instead.
   - Or edit `BATCH_ROOT` / `BATCH_RECURSIVE` in the setup cell and call `run_gli_batch()`.
3. Output (two files):
   - **`data/output/aggregated_PFT_GLI.csv`** — full merge (all original Excel columns + GLI)
   - **`data/output/aggregated_PFT_GLI_summary.csv`** — compact columns (`patient_id`, `test_date`, `age`, `sex`, `height`, `FEV1_measured`, `FEV1_lln`, `PFT_pattern`, …)

Each row keeps original columns plus:

- **`GLI_patient_id`** — one ID per row (from Patient ID, Patient Health Num, PID, FOT-ID, etc., detected per file)
- **`GLI_patient_id_source`** — which Excel column was used in that file
- `GLI_*` (predicted, LLN, ULN, z, status) and `GLI_PFT_Pattern` (Normal / Obstruction / Restriction / Mixed)

For analysis across many exports, use **`GLI_patient_id`** instead of the various raw ID column names.

### Column mapping across different Excel layouts

With **`AUTO_MAPPING_PER_FILE = True`** (default in the notebook), each file gets its own mapping via `suggest_mapping()`. Supported styles include:

- **BMT / Jaeger-style** paths, e.g. `Spirometry->FVC;PRE;TESTSELECT;VALUE`
- **Manual extraction sheets** (e.g. AGT), e.g. `ID`, `Pre FEV1`, `Pre FVC`, `Pre FEV1/FVC`, `Pre TLC` — not Jaeger paths; `%Pre FEV1` percent columns are ignored

Pre-bronch (**PRE**) measured values are preferred over post when both exist. Run the **Preview mapping** section — it shows the first file plus the first manual-extraction file when your folder has mixed layouts.
