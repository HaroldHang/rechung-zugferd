from pathlib import Path
import json
from typing import Dict, Any

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SETTINGS_PATH = DATA_DIR / "einstellungen.json"
FIRMENDATEN_PATH = DATA_DIR / "firmendaten.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "output_directory": str((BASE_DIR / "output").resolve()),
    "llm_model_path": str((BASE_DIR / "models" / "model.gguf").resolve()),
    "logo_path": "",
}

DEFAULT_FIRMENDATEN: Dict[str, Any] = {
    "name": "",
    "umsatzsteuer_id": "",
    "steuernummer": "",
    "anschrift": {
        "strasse": "",
        "plz": "",
        "ort": "",
        "land": "DE",
    },
    "zahlung": {
        "zahlungsart": "SEPA",
        "iban": "",
        "bic": "",
    },
}

DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        path.write_text(json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8")
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_settings() -> Dict[str, Any]:
    return _load_json(SETTINGS_PATH, DEFAULT_SETTINGS)


def save_settings(data: Dict[str, Any]) -> None:
    _save_json(SETTINGS_PATH, data)


def load_firmendaten() -> Dict[str, Any]:
    return _load_json(FIRMENDATEN_PATH, DEFAULT_FIRMENDATEN)


def save_firmendaten(data: Dict[str, Any]) -> None:
    _save_json(FIRMENDATEN_PATH, data)