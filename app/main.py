from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import uvicorn
import shutil
import uuid
from typing import Optional
# load env variables
from dotenv import load_dotenv
load_dotenv()

# Local modules
from app.infrastructure.storage import load_settings, save_settings, load_firmendaten, save_firmendaten
from app.infrastructure.pipeline import process_input_file

BASE_DIR = Path(__file__).resolve().parent.parent
UI_DIR = BASE_DIR / "app" / "ui"
UI_DIR = BASE_DIR / "ui"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

app = FastAPI(title="Rechnung Konverter (Offline)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories
for d in [DATA_DIR, OUTPUT_DIR, UI_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Serve static UI
app.mount("/static", StaticFiles(directory=str(UI_DIR), html=True), name="static")


@app.get("/api/settings")
def get_settings():
    settings = load_settings()
    return JSONResponse(settings)


@app.post("/api/settings")
def update_settings(payload: dict):
    save_settings(payload)
    return JSONResponse({"status": "ok"})


@app.get("/api/firmendaten")
def get_firmendaten():
    return JSONResponse(load_firmendaten())


@app.post("/api/firmendaten")
def update_firmendaten(payload: dict):
    save_firmendaten(payload)
    return JSONResponse({"status": "ok"})


@app.post("/api/process")
async def process(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Datei erforderlich")

    # Persist uploaded file to temp location
    tmp_dir = DATA_DIR / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{uuid.uuid4()}_{file.filename}"

    with tmp_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        settings = load_settings()
        result = process_input_file(
            input_path=tmp_path,
            output_root=OUTPUT_DIR,
            settings=settings,
        )
        # Persist last output directory for quick access in UI
        try:
            s = load_settings()
            s["last_output_path"] = result.get("output_directory")
            save_settings(s)
        except Exception:
            pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    return JSONResponse(result)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)