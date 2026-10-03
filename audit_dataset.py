"""Audit local et reproductible de l'archive DayOne, sans modifier les sources.

Usage depuis la racine : python audit_dataset.py (DAYONE_ARCHIVE pointe vers le ZIP local non versionné).
Dependencies: pandas, Pillow. Aucun appel réseau ni entraînement.
"""
from collections import Counter, defaultdict
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import os
import zipfile

import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parent
ARCHIVE = Path(os.environ.get("DAYONE_ARCHIVE") or (ROOT / "dayone-participants.zip"))
OUT = ROOT / "data" / "audit"


def main():
    if not ARCHIVE.is_file():
        raise SystemExit("Définir DAYONE_ARCHIVE vers le ZIP local non versionné.")
    OUT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ARCHIVE) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        mismatches = []
        for entry in manifest["files"]:
            raw = archive.read(entry["path"])
            if len(raw) != entry["bytes"] or sha256(raw).hexdigest() != entry["sha256"]:
                mismatches.append(entry["path"])
        image_paths = [n for n in archive.namelist() if n.lower().endswith((".jpg", ".png", ".jpeg"))]
        groups = defaultdict(list)
        dimensions = Counter()
        inventory = []
        for name in image_paths:
            raw = archive.read(name)
            digest = sha256(raw).hexdigest()
            groups[digest].append(name)
            with Image.open(BytesIO(raw)) as image:
                width, height = image.size
                dimensions[f"{width}x{height}/{image.mode}"] += 1
            inventory.append({"path": name, "sha256": digest, "bytes": len(raw), "width": width, "height": height})
        frame = pd.read_csv(BytesIO(archive.read("data/maternal_registry_synthetic.csv")))
        columns = []
        for col in frame:
            series = frame[col]
            counts = series.value_counts(dropna=True)
            columns.append({
                "field": col, "dtype": str(series.dtype), "missing": int(series.isna().sum()),
                "missing_pct": round(float(series.isna().mean() * 100), 2),
                "unique_non_null": int(series.nunique()), "min": float(series.min()),
                "max": float(series.max()), "mean": float(series.mean()),
                "value_counts": {str(k): int(v) for k, v in counts.items()} if series.nunique() <= 20 else None,
            })
        summary = {
            "archive_sha256": sha256(ARCHIVE.read_bytes()).hexdigest(),
            "manifest_file_count": len(manifest["files"]), "manifest_mismatches": mismatches,
            "archive_file_count": len(archive.namelist()),
            "image_count": len(image_paths), "unique_image_count": len(groups),
            "duplicate_image_groups": sum(len(v) > 1 for v in groups.values()),
            "redundant_image_copies": sum(len(v) - 1 for v in groups.values()),
            "image_dimensions": dict(dimensions),
            "csv_rows": len(frame), "csv_columns": len(frame.columns),
            "csv_unique_ids": int(frame["id"].nunique()),
            "csv_duplicate_rows": int(frame.duplicated().sum()),
            "csv_duplicate_rows_without_id": int(frame.drop(columns="id").duplicated().sum()),
            "csv_total_missing_cells": int(frame.isna().sum().sum()),
            "csv_rows_with_missing": int(frame.isna().any(axis=1).sum()),
            "csv_has_page_or_visit_key": any("page" in c.lower() or "visit" in c.lower() or "file" in c.lower() for c in frame),
            "newborn_weight_at_max_4800_count": int(frame["child birth weight (g)"].eq(4800).sum()),
            "head_circumference_at_max_40_count": int(frame["head circumference (cm)"].eq(40).sum()),
            "parity_equals_gravidity_count": int(frame["parity (number)"].eq(frame["gravidity (number)"]).sum()),
            "living_children_exceed_parity_count": int(frame["living children (number)"].gt(frame["parity (number)"]).sum()),
            "parity_plus_abortions_exceed_gravidity_count": int((frame["parity (number)"] + frame["abortions (number)"]).gt(frame["gravidity (number)"]).sum()),
        }
        audit = {"summary": summary, "fields": columns, "duplicate_groups": [v for v in groups.values() if len(v) > 1]}
        (OUT / "audit_dataset.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
        pd.DataFrame(inventory).to_csv(OUT / "inventaire_images.csv", index=False)
        pd.DataFrame(columns).drop(columns="value_counts").to_csv(OUT / "profil_champs.csv", index=False)
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
