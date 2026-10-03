"""Real HTTP/server restart scenario; synthetic documents, actual local OCR.

Requires the two EasyOCR weights installed beforehand. No browser automation:
this test covers the HTTP boundary, durable storage and process lifecycle.
"""
import base64
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def wait_until(predicate, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.15)
    raise AssertionError("Synthetic lifecycle checkpoint timed out")


def test_real_process_interruption_resume_and_persistence(tmp_path):
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    runtime = tmp_path / "synthetic-runtime"
    runtime.mkdir()
    env = {**os.environ, "DAYONE_ADMIN_PASSWORD": "synthetic-process-test-2026",
           "DAYONE_REVIEWER_PASSWORD": ""}
    processes = []
    handles = []
    base = f"http://127.0.0.1:{port}"

    def start(hold=False):
        log = (runtime / f"server-{len(processes)}.log").open("wb")
        handles.append(log)
        args = [sys.executable, str(ROOT / "admin/tests/demo_server.py"),
                "--runtime", str(runtime), "--port", str(port)]
        if hold:
            args.append("--hold-ocr")
        proc = subprocess.Popen(args, env=env, stdout=log, stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        processes.append(proc)
        def ready():
            assert proc.poll() is None, "Synthetic server exited during startup"
            try:
                return httpx.get(base + "/login", timeout=1, trust_env=False).status_code == 200
            except httpx.TransportError:
                return False
        wait_until(ready)
        return proc

    def login(client):
        response = client.post("/login", data={"password": env["DAYONE_ADMIN_PASSWORD"]})
        assert response.status_code == 303
        client.headers["X-CSRF-Token"] = client.get("/api/bootstrap").json()["csrf"]

    try:
        first = start(hold=True)
        with httpx.Client(base_url=base, timeout=180, trust_env=False) as client:
            login(client)
            record = client.post("/api/bot/conversation", json={}).json()
            rid = record["id"]
            for number in (1, 2):
                raw = (runtime / f"synthetic-page-{number}.png").read_bytes()
                body = {"data_url": "data:image/png;base64," + base64.b64encode(raw).decode(),
                        "masks": [[0, 0, 900, 160]], "synthetic_confirmed": True}
                saved = client.post(f"/api/records/{rid}/image", json=body)
                assert saved.status_code == 200
                page_id = saved.json()["page_id"]
                masked = client.get(f"/api/records/{rid}/pages/{page_id}/image")
                with Image.open(BytesIO(masked.content)) as image:
                    assert len(set(image.crop((0, 0, 900, 160)).getdata())) == 1
                assert client.post(f"/api/records/{rid}/image", json=body).json()["duplicate"]
            record = client.get(f"/api/records/{rid}").json()
            age = next(field for field in record["fields"] if field["key"] == "age")
            assert client.post(f"/api/records/{rid}/fields/{age['id']}/review",
                               json={"value": "29", "status": "CONNU", "expected_version": age["version"]}).status_code == 200
            def interrupted_request():
                try:
                    client.post(f"/api/records/{rid}/ocr", headers={"Idempotency-Key": "restart-proof"})
                except httpx.TransportError:
                    pass
            request = threading.Thread(target=interrupted_request, daemon=True)
            request.start()
            wait_until(lambda: (runtime / "ocr-started").exists())
            first.kill()
            first.wait(timeout=10)
            request.join(timeout=10)
            assert not request.is_alive()
            start()
            # Session signing key changes on restart; persistent content does not.
            assert client.get(f"/api/records/{rid}").status_code == 401
            login(client)
            jobs = client.get("/api/jobs").json()
            assert len(jobs) == 1 and jobs[0]["state"] == "PENDING"
            resumed = client.post("/api/jobs/resume").json()["processed"]
            assert len(resumed) == 1 and resumed[0]["job_state"] == "DONE"
            replay = client.post(f"/api/records/{rid}/ocr", headers={"Idempotency-Key": "restart-proof"}).json()
            assert replay["job_id"] == resumed[0]["job_id"] and replay["job_state"] == "DONE"
            after = client.get(f"/api/records/{rid}").json()
            assert len(after["pages"]) == 2
            assert next(f for f in after["fields"] if f["key"] == "age")["value"] == "29"
            assert next(f for f in after["fields"] if f["key"] == "gestation")["value"] == "2"
            second = client.post("/api/bot/conversation", json={}).json()
            link = {"target_code": after["code"], "expected_version": second["version"], "confirmed": False}
            assert client.post(f"/api/records/{second['id']}/link", json=link).status_code == 400
            link["confirmed"] = True
            assert client.post(f"/api/records/{second['id']}/link", json=link).status_code == 200
            processes[-1].kill()
            processes[-1].wait(timeout=10)
            start()
            login(client)
            final = client.get(f"/api/records/{rid}").json()
            assert len(final["visits"]) == 2 and len(final["pages"]) == 2
            assert next(f for f in final["fields"] if f["key"] == "age")["value"] == "29"
            assert client.post("/api/jobs/resume").json()["processed"] == []
            report = client.post(f"/api/bot/{rid}/message", json={"text": "rapport"}).json()["reply"]
            assert "âge" not in report.lower() and "29" not in report
        assert json.loads((runtime / "network-guard.json").read_text())["blocked_attempts"] == 0
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=10)
        for handle in handles:
            handle.close()
    for log in runtime.glob("server-*.log"):
        text = log.read_text(errors="replace")
        assert "SYNTHETIC MASK TARGET" not in text and "data:image" not in text and "Age: 28" not in text
