"""GLI PFT Calculator API — spirometry (GLI-2022) and lung volumes (GLI-2021)."""

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import PROJECT_ROOT, SAMPLES_DIR
from backend.app.schemas import (
    BatchCalculateResponse,
    BatchPreviewResponse,
    ColumnMapping,
    ManualCalculateRequest,
    ManualCalculateResponse,
)
from backend.app.services.batch_service import preview_excel, process_excel
from backend.app.services.fields import BMT_DEFAULT_MAPPING, FIELD_DEFINITIONS
from backend.app.services.classification import classify_pft
from backend.app.services.gli_service import gli_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm-load reference splines at startup
    _ = gli_service.tlc_splines
    _ = gli_service.spiro_splines
    yield


app = FastAPI(
    title="GLI PFT Calculator",
    description="GLI-2022 spirometry and GLI-2021 lung volume reference values",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok", "project": str(PROJECT_ROOT.name)}


@app.get("/api/schema/fields")
def get_fields():
    return {"fields": FIELD_DEFINITIONS}


@app.get("/api/schema/default-mapping")
def get_default_mapping():
    return {"mapping": BMT_DEFAULT_MAPPING, "note": "BMT PFT export format"}


@app.post("/api/calculate/manual", response_model=ManualCalculateResponse)
def calculate_manual(body: ManualCalculateRequest):
    try:
        spiro, lv = gli_service.calculate_manual(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    measured_dict = body.measured.model_dump(exclude_none=True)
    classification = classify_pft(spiro, lv)
    return ManualCalculateResponse(
        patient={
            "age": body.age,
            "height_cm": body.height_cm,
            "sex": body.sex,
            "modules": body.modules,
            "measured": measured_dict,
        },
        spirometry=spiro,
        lung_volumes=lv,
        classification=classification,
    )


@app.post("/api/batch/preview", response_model=BatchPreviewResponse)
async def batch_preview(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(400, "Upload an Excel file (.xlsx or .xls)")
    content = await file.read()
    try:
        return preview_excel(content, file.filename)
    except Exception as exc:
        raise HTTPException(400, f"Could not read Excel: {exc}") from exc


@app.post("/api/batch/calculate", response_model=BatchCalculateResponse)
async def batch_calculate(
    file: UploadFile = File(...),
    mapping: str = Form(...),
    modules: str = Form('["spirometry","lung_volumes"]'),
):
    if not file.filename:
        raise HTTPException(400, "Missing file")
    try:
        mapping_obj = ColumnMapping(**json.loads(mapping))
        module_list = json.loads(modules)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"Invalid JSON: {exc}") from exc

    content = await file.read()
    try:
        response, _ = process_excel(content, file.filename, mapping_obj, module_list)
        return response
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/samples")
def list_samples():
    if not SAMPLES_DIR.exists():
        return {"samples": []}
    samples = [
        {"name": p.name, "path": str(p.relative_to(PROJECT_ROOT))}
        for p in sorted(SAMPLES_DIR.glob("*.xlsx"))
    ]
    return {"samples": samples}
