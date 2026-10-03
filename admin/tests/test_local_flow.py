"""Synthetic-only checks for the local admin flow."""

import base64
from io import BytesIO
import os
from pathlib import Path
import socket
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont
import pytest


TEMP_RUNTIME = tempfile.TemporaryDirectory(prefix="dayone-tests-")
os.environ["DAYONE_RUNTIME_DIR"] = TEMP_RUNTIME.name
os.environ["DAYONE_ADMIN_PASSWORD"] = "admin-synthetic-test-phrase-2026"
os.environ["DAYONE_REVIEWER_PASSWORD"] = "reviewer-synthetic-test-phrase-2026"

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "DB_PATH", tmp_path / "dayone-test.sqlite3")
    run.init_db()
    with TestClient(run.app) as test_client:
        yield test_client


def signed_client(client, password="admin-synthetic-test-phrase-2026"):
    response = client.post("/login", data={"password": password})
    assert response.status_code == 200
    csrf = client.get("/api/bootstrap").json()["csrf"]
    return {"X-CSRF-Token": csrf}


def synthetic_photo(value: str) -> str:
    image = Image.new("RGB", (1000, 440), "white")
    draw = ImageDraw.Draw(image)
    font_path = Path("C:/Windows/Fonts/arial.ttf")
    font = ImageFont.truetype(str(font_path), 62) if font_path.exists() else ImageFont.load_default()
    draw.text((80, 120), value, fill="black", font=font)
    output = BytesIO()
    image.save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()


def block_network(*_args, **_kwargs):
    raise RuntimeError("Network forbidden in local OCR check")


def test_login_roles_and_csrf(client):
    assert client.get("/api/bootstrap").status_code == 401
    admin = signed_client(client)
    assert client.post("/api/bot/conversation", json={}).status_code == 403
    assert client.post("/api/settings", headers=admin, json={"ocr_languages": "fr,en", "review_order": "uncertain_first"}).status_code == 200
    client.post("/logout", headers=admin)
    reviewer = signed_client(client, "reviewer-synthetic-test-phrase-2026")
    assert client.post("/api/settings", headers=reviewer, json={"ocr_languages": "fr", "review_order": "document_order"}).status_code == 403


def test_bot_requires_explicit_matching_confirmation(client):
    headers = signed_client(client)
    rid = client.post("/api/bot/conversation", headers=headers, json={}).json()["id"]
    assert client.post(f"/api/bot/{rid}/message", headers=headers, json={"text": "âge 28"}).json()["applied"] == 1
    assert client.post(f"/api/bot/{rid}/message", headers=headers, json={"text": "confirmer âge 29"}).json()["applied"] == 0
    assert client.post(f"/api/bot/{rid}/message", headers=headers, json={"text": "confirmer âge 28"}).json()["applied"] == 1
    assert client.post(f"/api/bot/{rid}/message", headers=headers, json={"text": "âge 30"}).json()["applied"] == 0
    age = next(field for field in client.get(f"/api/records/{rid}").json()["fields"] if field["key"] == "age")
    assert age["value"] == "28" and age["reviewed"] and age["status"] == "CONNU"


def test_multipage_offline_ocr_review_and_visits(client):
    headers = signed_client(client)
    record = client.post("/api/bot/conversation", headers=headers, json={}).json()
    rid = record["id"]
    assert client.post(f"/api/bot/{rid}/message", headers=headers, json={"text": "âge 28"}).json()["applied"] == 1
    record = client.get(f"/api/records/{rid}").json()
    age = next(field for field in record["fields"] if field["key"] == "age")
    assert age["value"] == "28" and not age["reviewed"]
    corrected = client.post(f"/api/records/{rid}/fields/{age['id']}/review", headers=headers,
                            json={"value": "29", "status": "CONNU", "expected_version": age["version"]}).json()
    assert next(field for field in corrected["fields"] if field["key"] == "age")["value"] == "29"
    assert client.post(f"/api/bot/{rid}/message", headers=headers, json={"text": "âge 30"}).json()["applied"] == 0
    for value in ("Age: 28", "Gestation: 2"):
        response = client.post(f"/api/records/{rid}/image", headers=headers,
                               json={"data_url": synthetic_photo(value), "masks": [[10, 10, 60, 45]], "synthetic_confirmed": True})
        assert response.status_code == 200, response.text
    record = client.get(f"/api/records/{rid}").json()
    assert len(record["pages"]) == 2
    with run.database() as conn:
        encrypted = conn.execute("SELECT image_enc FROM pages WHERE record_id=? LIMIT 1", (rid,)).fetchone()[0]
        assert not encrypted.startswith(b"\x89PNG") and b"Age:" not in encrypted
    key_headers = {**headers, "Idempotency-Key": "offline-ocr-synthetic-run-1"}
    with patch.object(socket.socket, "connect", block_network), patch.object(socket.socket, "connect_ex", block_network):
        result = client.post(f"/api/records/{rid}/ocr", headers=key_headers).json()
    assert result["job_state"] == "DONE", result
    duplicate = client.post(f"/api/records/{rid}/ocr", headers=key_headers).json()
    assert duplicate["job_id"] == result["job_id"] and duplicate["job_state"] == "DONE"
    after = client.get(f"/api/records/{rid}").json()
    assert next(field for field in after["fields"] if field["key"] == "age")["value"] == "29"
    visit = client.post(f"/api/records/{rid}/visits", headers=headers, json={"confirmed": True}).json()
    assert visit["patient_code"] == after["patient_code"] and len(visit["visits"]) == 2
    report = client.post(f"/api/bot/{rid}/message", headers=headers, json={"text": "rapport"}).json()
    assert "Rapport local" in report["reply"]


def test_missing_and_illegible_fields_block_validation_until_reviewed(client):
    headers = signed_client(client)
    record = client.post("/api/bot/conversation", headers=headers, json={}).json()
    rid = record["id"]
    assert client.post(f"/api/records/{rid}/validate", headers=headers).status_code == 409
    age = next(field for field in record["fields"] if field["key"] == "age")
    changed = client.post(f"/api/records/{rid}/fields/{age['id']}/review", headers=headers,
                          json={"value": "99", "status": "ILLISIBLE", "expected_version": age["version"]}).json()
    reviewed = next(field for field in changed["fields"] if field["key"] == "age")
    assert reviewed["status"] == "ILLISIBLE" and reviewed["value"] == "" and reviewed["reviewed"]
    assert client.post(f"/api/records/{rid}/validate", headers=headers).status_code == 409


def test_late_ocr_cannot_replace_concurrent_human_correction(client, monkeypatch):
    headers = signed_client(client)
    record = client.post("/api/bot/conversation", headers=headers, json={}).json()
    rid = record["id"]
    uploaded = client.post(f"/api/records/{rid}/image", headers=headers,
                           json={"data_url": synthetic_photo("Age: 28"), "masks": [[10, 10, 60, 45]], "synthetic_confirmed": True})
    assert uploaded.status_code == 200

    class DelayedReader:
        called = False

        def readtext(self, *_args, **_kwargs):
            if not self.called:
                self.called = True
                with run.database() as conn:
                    field = conn.execute("SELECT id FROM fields WHERE record_id=? AND key='age'", (rid,)).fetchone()
                    conn.execute("UPDATE fields SET value_enc=?,status='CONNU',reviewed=1,version=version+1 WHERE id=?",
                                 (run.seal("29"), field["id"]))
                    conn.execute("UPDATE records SET version=version+1,updated_at=? WHERE id=?", (run.stamp(), rid))
            return [([[0, 0], [20, 0], [20, 20], [0, 20]], "Age: 28", 0.95)]

    reader = DelayedReader()
    monkeypatch.setattr(run, "ocr_reader", lambda _languages: reader)
    first = client.post(f"/api/records/{rid}/ocr", headers={**headers, "Idempotency-Key": "late-ocr-synthetic"}).json()
    assert first["job_state"] == "PENDING"
    resumed = client.post("/api/jobs/resume", headers=headers).json()
    assert resumed["processed"][0]["job_state"] == "DONE"
    age = next(field for field in client.get(f"/api/records/{rid}").json()["fields"] if field["key"] == "age")
    assert age["value"] == "29" and age["reviewed"]


def test_explicit_link_and_pending_recovery(client):
    headers = signed_client(client)
    first = client.post("/api/bot/conversation", headers=headers, json={}).json()
    second = client.post("/api/bot/conversation", headers=headers, json={}).json()
    lookup = client.get("/api/patients/lookup", params={"code": first["code"]})
    assert lookup.status_code == 200
    assert client.get("/api/patients/lookup", params={"code": "D1-UNKNOWN"}).status_code == 404
    body = {"target_code": first["code"], "expected_version": second["version"], "confirmed": False}
    assert client.post(f"/api/records/{second['id']}/link", headers=headers, json=body).status_code == 400
    body["confirmed"] = True
    linked = client.post(f"/api/records/{second['id']}/link", headers=headers, json=body).json()
    assert linked["patient_code"] == first["patient_code"]
    with run.database() as conn:
        conn.execute("INSERT INTO jobs(id,record_id,idempotency_key,state,created_at,updated_at) VALUES(?,?,?,'RUNNING',?,?)",
                     ("synthetic-job", first["id"], "synthetic-key", run.stamp(), run.stamp()))
    run.init_db()
    with run.database() as conn:
        assert conn.execute("SELECT state FROM jobs WHERE id='synthetic-job'").fetchone()[0] == "PENDING"


def test_validation_never_echoes_rejected_patient_input(client):
    headers = signed_client(client)
    rid = client.post("/api/bot/conversation", headers=headers, json={}).json()["id"]
    marker = "SYNTHETIC_PRIVATE_MARKER"
    response = client.post(f"/api/records/{rid}/image", headers=headers,
                           json={"data_url": marker, "masks": marker, "synthetic_confirmed": True})
    assert response.status_code == 422 and marker not in response.text
    assert response.headers["Cache-Control"] == "no-store"


def test_unicode_login_is_rejected_without_server_error(client):
    response = client.post("/login", data={"password": "mauvais-mot-de-passe-é"}, follow_redirects=False)
    assert response.status_code == 303 and response.headers["location"] == "/login?error=1"


def test_redaction_pixels_duplicate_and_image_access(client):
    headers = signed_client(client)
    rid = client.post("/api/bot/conversation", headers=headers, json={}).json()["id"]
    body = {"data_url": synthetic_photo("Age: 28"), "masks": [[0, 0, 400, 300]], "synthetic_confirmed": True}
    saved = client.post(f"/api/records/{rid}/image", headers=headers, json=body).json()
    repeated = client.post(f"/api/records/{rid}/image", headers=headers, json=body).json()
    assert repeated["duplicate"] and repeated["page_id"] == saved["page_id"]
    url = f"/api/records/{rid}/pages/{saved['page_id']}/image"
    response = client.get(url)
    with Image.open(BytesIO(response.content)) as page:
        assert len(set(page.crop((0, 0, 400, 300)).getdata())) == 1
    assert response.headers["Cache-Control"] == "no-store"
    client.post("/logout", headers=headers)
    assert client.get(url).status_code == 401


def test_ocr_receipt_and_suggestions_roll_back_together(client, monkeypatch):
    headers = signed_client(client)
    rid = client.post("/api/bot/conversation", headers=headers, json={}).json()["id"]
    client.post(f"/api/records/{rid}/image", headers=headers,
                json={"data_url": synthetic_photo("Age: 28"), "masks": [[0, 0, 10, 10]], "synthetic_confirmed": True})
    class Reader:
        def readtext(self, *args, **kwargs):
            return [([], "Age: 28", 0.95)]
    monkeypatch.setattr(run, "ocr_reader", lambda languages: Reader())
    with run.database() as conn:
        conn.execute("CREATE TRIGGER reject_receipt BEFORE UPDATE OF state ON jobs WHEN NEW.state='DONE' BEGIN SELECT RAISE(ABORT, 'synthetic interruption'); END")
    result = client.post(f"/api/records/{rid}/ocr", headers={**headers, "Idempotency-Key": "atomic-receipt"}).json()
    assert result["job_state"] == "ERROR"
    age = next(f for f in client.get(f"/api/records/{rid}").json()["fields"] if f["key"] == "age")
    assert age["value"] == ""
    with run.database() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events WHERE record_id=? AND kind='OCR_LOCAL'", (rid,)).fetchone()[0] == 0
        conn.execute("DROP TRIGGER reject_receipt")
    result = client.post(f"/api/records/{rid}/ocr", headers={**headers, "Idempotency-Key": "atomic-receipt"}).json()
    assert result["job_state"] == "DONE"


def test_ciphertext_and_forged_session(client, monkeypatch):
    from cryptography.fernet import Fernet
    headers = signed_client(client)
    rid = client.post("/api/bot/conversation", headers=headers, json={}).json()["id"]
    marker = "SYNTHETIC_SECRET_SENTINEL_74291"
    assert client.post(f"/api/bot/{rid}/message", headers=headers, json={"text": marker}).status_code == 200
    assert marker.encode() not in run.DB_PATH.read_bytes()
    first, second = run.seal(marker), run.seal(marker)
    assert first != second and run.unseal(first) == marker
    with pytest.raises(RuntimeError):
        run.unseal(first[:-3] + b"xxx")
    monkeypatch.setattr(run, "VAULT", Fernet(Fernet.generate_key()))
    with pytest.raises(RuntimeError):
        run.unseal(first)
    client.cookies.clear()
    client.cookies.set("dayone_session", "forged.signature")
    assert client.get("/api/bootstrap").status_code == 401
