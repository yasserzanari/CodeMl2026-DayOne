"""Download model weights only; never read or upload patient images during setup."""

from pathlib import Path
import easyocr


model_dir = Path(__file__).resolve().parent / ".models"
model_dir.mkdir(parents=True, exist_ok=True)
print("Installation des poids EasyOCR dans", model_dir)
easyocr.Reader(["fr", "en"], gpu=False, model_storage_directory=str(model_dir), download_enabled=True, verbose=False)
print("Poids installés. L'application utilisera download_enabled=False.")
