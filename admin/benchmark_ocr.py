"""Offline OCR smoke benchmark on cards rendered from the supplied synthetic CSV.

This measures generated cards, not the unmapped specimen photographs. No row values
or images are written; only aggregate counts are saved.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import socket
import tempfile
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import numpy as np

TEMP_RUNTIME = tempfile.TemporaryDirectory(prefix="dayone-benchmark-")
os.environ["DAYONE_RUNTIME_DIR"] = TEMP_RUNTIME.name
os.environ.setdefault("DAYONE_ADMIN_PASSWORD", "benchmark-local-only-phrase-2026")
from run import extract_candidates, ocr_reader  # noqa: E402


HERE = Path(__file__).resolve().parent
CSV = Path(os.environ.get("DAYONE_SYNTHETIC_CSV") or (HERE.parent / "data" / "maternal_registry_synthetic.csv"))
OUTPUT = HERE / "benchmark-results.json"
FONT_PATH = Path("C:/Windows/Fonts/arial.ttf")


def card(truth: dict[str, str], variant: str) -> Image.Image:
    image = Image.new("RGB", (1150, 570), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(FONT_PATH), 56) if FONT_PATH.exists() else ImageFont.load_default()
    lines = [f"Age: {truth['age']}", f"Gestation: {truth['gestation']}", f"Parite: {truth['parity']}"]
    for index, line in enumerate(lines):
        draw.text((85, 85 + index * 145), line, fill=(15, 20, 20), font=font)
    if variant == "low_contrast":
        image = ImageEnhance.Contrast(image).enhance(0.32)
        image = image.rotate(2, expand=False, fillcolor=(235, 235, 235))
    return image


def blocked_network(*_args, **_kwargs):
    raise RuntimeError("Toute connexion réseau est bloquée durant le benchmark local.")


def main() -> None:
    if not CSV.is_file():
        raise SystemExit("Définir DAYONE_SYNTHETIC_CSV vers le CSV synthétique local non versionné.")
    with CSV.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))[:8]
    counts = {variant: {key: {"correct": 0, "total": 0, "abstained": 0} for key in ("age", "gestation", "parity")}
              for variant in ("clean", "low_contrast")}
    negative = {variant: {"false_positive_hcv": 0, "total": 0} for variant in counts}
    with patch.object(socket.socket, "connect", blocked_network), patch.object(socket.socket, "connect_ex", blocked_network):
        reader = ocr_reader(("fr", "en"))
        for row in rows:
            truth = {"age": row["age (years)"], "gestation": row["gravidity (number)"], "parity": row["parity (number)"]}
            for variant in counts:
                detected = reader.readtext(np.array(card(truth, variant)), detail=1, paragraph=False)
                found = extract_candidates([item[1] for item in detected])
                for key, expected in truth.items():
                    result = counts[variant][key]
                    result["total"] += 1
                    result["correct"] += int(found.get(key) == expected)
                    result["abstained"] += int(key not in found)
                negative[variant]["total"] += 1
                negative[variant]["false_positive_hcv"] += int("hcv" in found)
    for variant in counts:
        for values in counts[variant].values():
            values["accuracy"] = round(values["correct"] / values["total"], 4) if values["total"] else None
    report = {"dataset": "8 premières lignes du CSV synthétique fourni, rendues en cartes artificielles",
              "scope": "Cartes imprimées générées, non comparables aux photos manuscrites fournies",
              "network": "Bloqué pendant chargement et inférence", "model": "EasyOCR fr+en, CPU, poids locaux",
              "by_variant_and_field": counts, "absent_field_control": negative,
              "limitations": ["Aucun mapping officiel photo-vers-ligne CSV", "Aucune référence annotée pour les photos de registres",
                              "Les scores ne mesurent ni tableaux manuscrits ni liaison entre visites", "Confiance OCR brute non calibrée"]}
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    TEMP_RUNTIME.cleanup()


if __name__ == "__main__":
    main()
