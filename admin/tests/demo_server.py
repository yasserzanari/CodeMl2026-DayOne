"""Isolated synthetic UI demo. Never point its runtime at a production database.

Run from repository root with a synthetic DAYONE_ADMIN_PASSWORD in the environment.
--hold-ocr is a fault-injection checkpoint: kill this process once ocr-started exists,
then restart without the flag and resume the durable queue through the UI.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import socket
import sys
import time

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=8876)
parser.add_argument("--runtime", type=Path, default=ROOT / ".verification" / "ui-demo")
parser.add_argument("--hold-ocr", action="store_true")
args = parser.parse_args()
runtime = args.runtime.resolve()
runtime.mkdir(parents=True, exist_ok=True)
os.environ["DAYONE_RUNTIME_DIR"] = str(runtime)

font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 46) if Path("C:/Windows/Fonts/arial.ttf").exists() else ImageFont.load_default(size=46)
for number, lines in enumerate((("Age: 28", "Gestation: 2"), ("Parite: 1", "Poids: 65 kg")), 1):
    page = Image.new("RGB", (900, 1200), "white")
    draw = ImageDraw.Draw(page)
    draw.text((50, 40), "SYNTHETIC MASK TARGET", font=font, fill="black")
    for index, line in enumerate(lines):
        draw.text((70, 250 + index * 130), line, font=font, fill="black")
    page.save(runtime / f"synthetic-page-{number}.png")

guard_path = runtime / "network-guard.json"
guard = {"blocked_attempts": 0, "scope": "Python non-loopback socket connect/connect_ex/getaddrinfo"}
if guard_path.exists():
    guard["blocked_attempts"] = json.loads(guard_path.read_text(encoding="utf-8"))["blocked_attempts"]
guard_path.write_text(json.dumps(guard), encoding="utf-8")
original_connect, original_connect_ex, original_dns = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo

def allowed(host):
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False

def check(host):
    if not allowed(host):
        guard["blocked_attempts"] += 1
        guard_path.write_text(json.dumps(guard), encoding="utf-8")
        raise OSError("External network disabled for synthetic verification")

def connect(sock, address):
    check(address[0])
    return original_connect(sock, address)

def connect_ex(sock, address):
    check(address[0])
    return original_connect_ex(sock, address)

def dns(host, *rest, **kwargs):
    if host is not None:
        check(host)
    return original_dns(host, *rest, **kwargs)

socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo = connect, connect_ex, dns
sys.path.insert(0, str(ROOT / "admin"))
import run
import uvicorn

if args.hold_ocr:
    original_reader = run.ocr_reader
    def hold_reader(languages):
        (runtime / "ocr-started").write_text("Synthetic fault-injection checkpoint", encoding="utf-8")
        while not (runtime / "release-ocr").exists():
            time.sleep(0.1)
        return original_reader(languages)
    run.ocr_reader = hold_reader

uvicorn.run(run.app, host="127.0.0.1", port=args.port, access_log=False)
