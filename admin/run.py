"""DayOne local admin console. No outbound network calls or patient-data exports."""

from __future__ import annotations

import base64
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from io import BytesIO
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageStat


BASE = Path(__file__).resolve().parent
RUNTIME = Path(os.environ.get("DAYONE_RUNTIME_DIR") or (BASE / ".runtime" / "local")).resolve()
MODELS = BASE / ".models"
DB_PATH = RUNTIME / "dayone.sqlite3"
SALT_PATH = RUNTIME / "salt.bin"
STATIC = BASE / "static"
PASSWORD = os.environ.get("DAYONE_ADMIN_PASSWORD", "")
if len(PASSWORD) < 16 or PASSWORD == "replace-with-a-long-local-password":
    raise RuntimeError("Définir DAYONE_ADMIN_PASSWORD avec au moins 16 caractères avant le démarrage.")
REVIEWER_PASSWORD = os.environ.get("DAYONE_REVIEWER_PASSWORD", "")
if REVIEWER_PASSWORD and (len(REVIEWER_PASSWORD) < 16 or REVIEWER_PASSWORD == PASSWORD):
    raise RuntimeError("DAYONE_REVIEWER_PASSWORD doit être distinct et contenir au moins 16 caractères.")

RUNTIME.mkdir(parents=True, exist_ok=True)
MODELS.mkdir(parents=True, exist_ok=True)
if not SALT_PATH.exists():
    SALT_PATH.write_bytes(secrets.token_bytes(16))
    try:
        SALT_PATH.chmod(0o600)
    except OSError:
        pass
SALT = SALT_PATH.read_bytes()
KEY = base64.urlsafe_b64encode(hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), SALT, 600_000, dklen=32))
VAULT = Fernet(KEY)
SESSION_SECRET = secrets.token_bytes(32)
SESSION_SECONDS = 8 * 60 * 60

app = FastAPI(title="DayOne Console locale", docs_url=None, redoc_url=None, openapi_url=None)

FIELD_SPEC = {
    "age": ("Âge", "ans"),
    "gestation": ("Gestité", ""),
    "parity": ("Parité", ""),
    "blood_pressure": ("Tension artérielle", "mmHg"),
    "weight": ("Poids maternel", "kg"),
    "hiv": ("Sérologie VIH", ""),
    "syphilis": ("Syphilis", ""),
    "hbs": ("Ag HBs", ""),
    "hcv": ("Hépatite C", ""),
}
STATUSES = {"CONNU", "INCONNU", "NON_FOURNI", "ILLISIBLE", "NON_APPLICABLE", "À_RÉVISER"}
REVIEW_STATES = {"À_RÉVISER", "VALIDÉ"}
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


@contextmanager
def database():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def seal(value: Any) -> bytes:
    return VAULT.encrypt(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def unseal(value: bytes) -> Any:
    try:
        return json.loads(VAULT.decrypt(value).decode("utf-8"))
    except InvalidToken as exc:
        raise RuntimeError("Impossible de déchiffrer les données. Vérifier le mot de passe administrateur.") from exc


def audit(conn: sqlite3.Connection, record_id: str | None, kind: str, detail: str) -> None:
    conn.execute(
        "INSERT INTO events(record_id,kind,detail,created_at) VALUES(?,?,?,?)",
        (record_id, kind, detail[:240], stamp()),
    )


def init_db() -> None:
    with database() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY, code TEXT NOT NULL UNIQUE, source TEXT NOT NULL,
                state TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                image_enc BLOB, image_confirmed INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT NOT NULL REFERENCES records(id),
                key TEXT NOT NULL, value_enc BLOB NOT NULL, status TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT '', confidence TEXT NOT NULL DEFAULT '',
                reviewed INTEGER NOT NULL DEFAULT 0, version INTEGER NOT NULL DEFAULT 1,
                UNIQUE(record_id,key)
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT REFERENCES records(id),
                kind TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bot_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT NOT NULL REFERENCES records(id),
                sender TEXT NOT NULL, text_enc BLOB NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pages (
                id TEXT PRIMARY KEY, record_id TEXT NOT NULL REFERENCES records(id),
                ordinal INTEGER NOT NULL, image_enc BLOB NOT NULL, sha256 TEXT NOT NULL,
                quality_json TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(record_id,ordinal), UNIQUE(record_id,sha256)
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, record_id TEXT NOT NULL REFERENCES records(id),
                idempotency_key TEXT NOT NULL UNIQUE, state TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0, result_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
        """)
        conn.execute("UPDATE jobs SET state='PENDING',updated_at=? WHERE state='RUNNING'", (stamp(),))
        if "patient_code" not in {row["name"] for row in conn.execute("PRAGMA table_info(records)")}:
            conn.execute("ALTER TABLE records ADD COLUMN patient_code TEXT")
        conn.execute("UPDATE records SET patient_code=code WHERE patient_code IS NULL")
        for key, value in {"ocr_languages": "fr,en", "bot_mode": "local", "review_order": "uncertain_first"}.items():
            conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (key, value))
        existing = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        if existing == 0:
            examples = [
                {"age": ("28", "CONNU", 0), "gestation": ("2", "CONNU", 0), "parity": ("1", "CONNU", 0), "blood_pressure": ("112/74", "À_RÉVISER", 0), "hiv": ("Négatif", "CONNU", 0)},
                {"age": ("31", "CONNU", 0), "gestation": ("3", "CONNU", 0), "parity": ("1", "CONNU", 0), "weight": ("", "ILLISIBLE", 0), "hbs": ("Négatif", "À_RÉVISER", 0)},
                {"age": ("", "NON_FOURNI", 0), "blood_pressure": ("104/68", "CONNU", 0), "syphilis": ("", "NON_FOURNI", 0)},
            ]
            for item in examples:
                create_record(conn, "DÉMO · données fictives", item)
            audit(conn, None, "DÉMO", "Trois dossiers fictifs créés pour explorer l'interface.")
        else:
            # Fails early if a previous database was encrypted with a different password.
            sample = conn.execute("SELECT value_enc FROM fields LIMIT 1").fetchone()
            if sample:
                unseal(sample[0])


def new_code(conn: sqlite3.Connection) -> str:
    for _ in range(20):
        code = "D1-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(7))
        if not conn.execute("SELECT 1 FROM records WHERE code=?", (code,)).fetchone():
            return code
    raise RuntimeError("Impossible de générer un code unique.")


def create_record(conn: sqlite3.Connection, source: str, values: dict[str, tuple[str, str, int]] | None = None,
                  patient_code: str | None = None) -> str:
    rid = secrets.token_hex(12)
    now = stamp()
    code = new_code(conn)
    conn.execute(
        "INSERT INTO records(id,code,patient_code,source,state,version,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
        (rid, code, patient_code or code, source, "À_RÉVISER", 1, now, now),
    )
    for key, (value, status, reviewed) in (values or {key: ("", "NON_FOURNI", 0) for key in FIELD_SPEC}).items():
        conn.execute(
            "INSERT INTO fields(record_id,key,value_enc,status,unit,confidence,reviewed) VALUES(?,?,?,?,?,?,?)",
            (rid, key, seal(value), status, FIELD_SPEC[key][1], "Démonstration" if values else "", reviewed),
        )
    audit(conn, rid, "CRÉATION", "Dossier fictif créé localement.")
    return rid


init_db()


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def read_b64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def make_cookie(role: str) -> tuple[str, str]:
    nonce = secrets.token_hex(16)
    body = b64url(json.dumps({"n": nonce, "role": role, "e": int((datetime.now(timezone.utc) + timedelta(seconds=SESSION_SECONDS)).timestamp())}).encode())
    signature = b64url(hmac.digest(SESSION_SECRET, body.encode(), "sha256"))
    csrf = b64url(hmac.digest(SESSION_SECRET, ("csrf:" + nonce).encode(), "sha256"))
    return body + "." + signature, csrf


def current_session(request: Request) -> dict[str, Any] | None:
    cookie = request.cookies.get("dayone_session", "")
    try:
        body, signature = cookie.split(".", 1)
        expected = b64url(hmac.digest(SESSION_SECRET, body.encode(), "sha256"))
        if not hmac.compare_digest(signature, expected):
            return None
        data = json.loads(read_b64url(body))
        if int(data["e"]) < int(datetime.now(timezone.utc).timestamp()):
            return None
        return data
    except (ValueError, KeyError, TypeError):
        return None


def require_admin(request: Request) -> dict[str, Any]:
    session = current_session(request)
    if not session:
        raise HTTPException(401, "Session expirée. Reconnectez-vous.")
    if request.method not in {"GET", "HEAD"}:
        actual = request.headers.get("X-CSRF-Token", "")
        expected = b64url(hmac.digest(SESSION_SECRET, ("csrf:" + session["n"]).encode(), "sha256"))
        if not hmac.compare_digest(actual, expected):
            raise HTTPException(403, "Jeton de session manquant ou invalide.")
    return session


def require_config_admin(request: Request) -> dict[str, Any]:
    session = require_admin(request)
    if session.get("role") != "admin":
        raise HTTPException(403, "Réglage réservé à l'administrateur.")
    return session


def record_summary(row: sqlite3.Row, pending: int | None = None) -> dict[str, Any]:
    result = {key: row[key] for key in ("id", "code", "patient_code", "source", "state", "version", "created_at", "updated_at")}
    result["has_image"] = row["image_enc"] is not None
    if pending is not None:
        result["pending"] = pending
    return result


def get_record(conn: sqlite3.Connection, rid: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM records WHERE id=?", (rid,)).fetchone()
    if not row:
        raise HTTPException(404, "Dossier introuvable.")
    data = record_summary(row)
    data["fields"] = [
        {"id": field["id"], "key": field["key"], "label": FIELD_SPEC[field["key"]][0],
         "value": unseal(field["value_enc"]), "status": field["status"], "unit": field["unit"],
         "confidence": field["confidence"], "reviewed": bool(field["reviewed"]), "version": field["version"]}
        for field in conn.execute("SELECT * FROM fields WHERE record_id=? ORDER BY id", (rid,))
    ]
    data["events"] = [dict(event) for event in conn.execute(
        "SELECT kind,detail,created_at FROM events WHERE record_id=? ORDER BY id DESC LIMIT 20", (rid,)
    )]
    data["pages"] = [dict(page) for page in conn.execute(
        "SELECT id,ordinal,quality_json,created_at FROM pages WHERE record_id=? ORDER BY ordinal", (rid,)
    )]
    for page in data["pages"]:
        page["quality"] = json.loads(page.pop("quality_json"))
    data["visits"] = [dict(visit) for visit in conn.execute(
        "SELECT id,code,state,created_at FROM records WHERE patient_code=? ORDER BY created_at,id", (row["patient_code"],)
    )]
    return data


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    if not current_session(request):
        return RedirectResponse("/login", status_code=303)
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if current_session(request):
        return RedirectResponse("/", status_code=303)
    return FileResponse(STATIC / "login.html", headers={"Cache-Control": "no-store"})


@app.post("/login")
async def login(request: Request):
    form = await request.form()
    supplied = str(form.get("password", ""))
    role = "admin" if hmac.compare_digest(supplied, PASSWORD) else "reviewer" if REVIEWER_PASSWORD and hmac.compare_digest(supplied, REVIEWER_PASSWORD) else ""
    if not role:
        return RedirectResponse("/login?error=1", status_code=303)
    cookie, _ = make_cookie(role)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("dayone_session", cookie, max_age=SESSION_SECONDS, httponly=True, samesite="strict", secure=False)
    return response


@app.post("/logout")
def logout(request: Request, _: dict = Depends(require_admin)):
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie("dayone_session")
    return response


@app.get("/static/{filename}")
def static_file(filename: str):
    if filename not in {"styles.css", "app.js", "login.css"}:
        raise HTTPException(404)
    return FileResponse(STATIC / filename, headers={"Cache-Control": "no-store"})


@app.get("/api/bootstrap")
def bootstrap(request: Request, session: dict = Depends(require_admin)):
    with database() as conn:
        counts = {row["state"]: row["n"] for row in conn.execute("SELECT state,COUNT(*) n FROM records GROUP BY state")}
        total = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        revisions = conn.execute("SELECT COUNT(*) FROM fields WHERE reviewed=0").fetchone()[0]
        events = [dict(row) for row in conn.execute("SELECT kind,detail,created_at FROM events ORDER BY id DESC LIMIT 8")]
        settings = {row["key"]: row["value"] for row in conn.execute("SELECT key,value FROM settings")}
    csrf = b64url(hmac.digest(SESSION_SECRET, ("csrf:" + session["n"]).encode(), "sha256"))
    return {"csrf": csrf, "role": session["role"], "counts": counts, "total": total, "revisions": revisions,
            "events": events, "settings": settings, "ocr_ready": model_files_present(),
            "mode": "Local · aucune API externe", "statuses": sorted(STATUSES)}


@app.get("/api/records")
def records(search: str = "", state: str = "", page: int = 1, _: dict = Depends(require_admin)):
    page = max(1, min(page, 10000))
    if state and state not in REVIEW_STATES:
        raise HTTPException(400, "Filtre de statut invalide.")
    search = search.strip().upper()[:30]
    terms = []
    params: list[Any] = []
    if search:
        terms.append("code LIKE ?")
        params.append("%" + search + "%")
    if state:
        terms.append("state=?")
        params.append(state)
    clause = " WHERE " + " AND ".join(terms) if terms else ""
    with database() as conn:
        total = conn.execute("SELECT COUNT(*) FROM records" + clause, params).fetchone()[0]
        rows = conn.execute(
            "SELECT r.*, (SELECT COUNT(*) FROM fields f WHERE f.record_id=r.id AND f.reviewed=0) pending "
            "FROM records r" + clause + " ORDER BY updated_at DESC,id DESC LIMIT 20 OFFSET ?",
            [*params, (page - 1) * 20],
        ).fetchall()
    return {"items": [record_summary(row, row["pending"]) for row in rows], "total": total, "page": page, "page_size": 20}


@app.get("/api/records/{rid}")
def record_detail(rid: str, _: dict = Depends(require_admin)):
    with database() as conn:
        return get_record(conn, rid)


class NewVisitBody(BaseModel):
    confirmed: bool


@app.post("/api/records/{rid}/visits")
def new_linked_visit(rid: str, body: NewVisitBody, _: dict = Depends(require_admin)):
    if not body.confirmed:
        raise HTTPException(400, "Confirmer manuellement la liaison de cette visite.")
    with database() as conn:
        parent = conn.execute("SELECT patient_code,code FROM records WHERE id=?", (rid,)).fetchone()
        if not parent:
            raise HTTPException(404, "Dossier de référence introuvable.")
        visit_id = create_record(conn, "Visite de suivi · saisie locale", patient_code=parent["patient_code"])
        audit(conn, visit_id, "LIAISON_VISITE", f"Visite liée manuellement au dossier {parent['code']}.")
        return get_record(conn, visit_id)


@app.get("/api/patients/lookup")
def lookup_patient(code: str, _: dict = Depends(require_admin)):
    code = code.strip().upper()[:30]
    with database() as conn:
        row = conn.execute("SELECT * FROM records WHERE code=?", (code,)).fetchone()
        if not row:
            raise HTTPException(404, "Aucun code de dossier exact trouvé. Aucune liaison automatique effectuée.")
        return record_summary(row)


class LinkBody(BaseModel):
    target_code: str = Field(min_length=4, max_length=30)
    confirmed: bool
    expected_version: int


@app.post("/api/records/{rid}/link")
def link_visit(rid: str, body: LinkBody, _: dict = Depends(require_admin)):
    if not body.confirmed:
        raise HTTPException(400, "La décision humaine explicite est requise.")
    with database() as conn:
        source = conn.execute("SELECT * FROM records WHERE id=?", (rid,)).fetchone()
        target = conn.execute("SELECT * FROM records WHERE code=?", (body.target_code.strip().upper(),)).fetchone()
        if not source or not target:
            raise HTTPException(404, "Dossier introuvable : aucune liaison créée.")
        if source["id"] == target["id"]:
            raise HTTPException(400, "Un dossier ne peut pas être lié à lui-même.")
        if source["version"] != body.expected_version:
            raise HTTPException(409, "Le dossier a changé. Vérifier le lien avant de réessayer.")
        if source["patient_code"] != source["code"]:
            raise HTTPException(409, "Ce dossier est déjà lié. Une réconciliation manuelle est nécessaire.")
        group_size = conn.execute("SELECT COUNT(*) FROM records WHERE patient_code=?", (source["patient_code"],)).fetchone()[0]
        if group_size != 1:
            raise HTTPException(409, "Ce code regroupe déjà plusieurs visites. Une réconciliation manuelle est nécessaire.")
        conn.execute("UPDATE records SET patient_code=?,version=version+1,updated_at=? WHERE id=?",
                     (target["patient_code"], stamp(), rid))
        audit(conn, rid, "LIAISON_VISITE", f"Liaison humaine au code {target['code']}.")
        return get_record(conn, rid)


class ReviewBody(BaseModel):
    value: str = Field(max_length=160)
    status: str
    expected_version: int


@app.post("/api/records/{rid}/fields/{field_id}/review")
def review_field(rid: str, field_id: int, body: ReviewBody, _: dict = Depends(require_admin)):
    if body.status not in STATUSES:
        raise HTTPException(400, "Statut de champ invalide.")
    if body.status == "CONNU" and not body.value.strip():
        raise HTTPException(400, "Une valeur connue doit être renseignée.")
    with database() as conn:
        field = conn.execute("SELECT * FROM fields WHERE id=? AND record_id=?", (field_id, rid)).fetchone()
        if not field:
            raise HTTPException(404, "Champ introuvable.")
        if field["version"] != body.expected_version:
            raise HTTPException(409, "Le champ a changé. Comparer la nouvelle version avant d'enregistrer.")
        value = body.value.strip() if body.status in {"CONNU", "À_RÉVISER"} else ""
        reviewed = 0 if body.status == "À_RÉVISER" else 1
        changed = conn.execute(
            "UPDATE fields SET value_enc=?,status=?,reviewed=?,version=version+1 WHERE id=? AND version=?",
            (seal(value), body.status, reviewed, field_id, body.expected_version),
        ).rowcount
        if not changed:
            raise HTTPException(409, "Le champ a changé.")
        conn.execute("UPDATE records SET state='À_RÉVISER',version=version+1,updated_at=? WHERE id=?", (stamp(), rid))
        audit(conn, rid, "RELECTURE", f"{field['key']} {'laissé à réviser' if not reviewed else 'confirmé ou corrigé'} par l'admin.")
        return get_record(conn, rid)


@app.post("/api/records/{rid}/validate")
def validate_record(rid: str, _: dict = Depends(require_admin)):
    with database() as conn:
        if not conn.execute("SELECT 1 FROM records WHERE id=?", (rid,)).fetchone():
            raise HTTPException(404, "Dossier introuvable.")
        pending = conn.execute("SELECT COUNT(*) FROM fields WHERE record_id=? AND reviewed=0", (rid,)).fetchone()[0]
        if pending:
            raise HTTPException(409, f"Il reste {pending} champ(s) à confirmer.")
        conn.execute("UPDATE records SET state='VALIDÉ',version=version+1,updated_at=? WHERE id=?", (stamp(), rid))
        audit(conn, rid, "VALIDATION", "Dossier fictif validé localement.")
        return get_record(conn, rid)


class NewBotBody(BaseModel):
    note: str = Field(default="", max_length=80)


@app.post("/api/bot/conversation")
def bot_conversation(body: NewBotBody, _: dict = Depends(require_admin)):
    with database() as conn:
        rid = create_record(conn, "Bot local · conversation simulée")
        conn.execute("INSERT INTO bot_messages(record_id,sender,text_enc,created_at) VALUES(?,?,?,?)",
                     (rid, "bot", seal("Bonjour. Envoyez une valeur fictive comme « âge 28 » ou « TA 112/74 ». Elle sera proposée à la relecture, jamais validée automatiquement."), stamp()))
        audit(conn, rid, "BOT_LOCAL", "Conversation locale ouverte. Aucun message envoyé à Meta.")
        return get_record(conn, rid)


@app.get("/api/bot/{rid}/messages")
def bot_messages(rid: str, _: dict = Depends(require_admin)):
    with database() as conn:
        row = conn.execute("SELECT source FROM records WHERE id=?", (rid,)).fetchone()
        if not row or not row["source"].startswith("Bot local"):
            raise HTTPException(404, "Conversation locale introuvable.")
        return [{"sender": message["sender"], "text": unseal(message["text_enc"]), "created_at": message["created_at"]}
                for message in conn.execute("SELECT sender,text_enc,created_at FROM bot_messages WHERE record_id=? ORDER BY id DESC LIMIT 30", (rid,))][::-1]


@app.get("/api/bot/conversations/list")
def bot_conversations(_: dict = Depends(require_admin)):
    with database() as conn:
        return [record_summary(row) for row in conn.execute(
            "SELECT * FROM records WHERE source LIKE 'Bot local%' ORDER BY updated_at DESC,id DESC LIMIT 30"
        )]


class BotMessageBody(BaseModel):
    text: str = Field(min_length=1, max_length=160)


@app.post("/api/bot/{rid}/message")
def bot_message(rid: str, body: BotMessageBody, _: dict = Depends(require_admin)):
    message = body.text.strip()
    if not message:
        raise HTTPException(400, "Message vide.")
    report_requested = message.casefold() in {"rapport", "rapport local", "bilan"}
    explicit = re.match(r"^(confirmer|corriger)\s+(.+)$", message, flags=re.IGNORECASE)
    mode = explicit.group(1).lower() if explicit else "suggestion"
    candidates = {} if report_requested else extract_candidates([explicit.group(2) if explicit else message])
    with database() as conn:
        row = conn.execute("SELECT source FROM records WHERE id=?", (rid,)).fetchone()
        if not row or not row["source"].startswith("Bot local"):
            raise HTTPException(404, "Conversation locale introuvable.")
        conn.execute("INSERT INTO bot_messages(record_id,sender,text_enc,created_at) VALUES(?,?,?,?)",
                     (rid, "admin", seal(message), stamp()))
        applied = []
        refused = []
        for key, value in candidates.items():
            field = conn.execute("SELECT id,reviewed,value_enc FROM fields WHERE record_id=? AND key=?", (rid, key)).fetchone()
            if not field or field["reviewed"]:
                refused.append(FIELD_SPEC[key][0])
                continue
            if mode == "confirmer" and unseal(field["value_enc"]) != value:
                refused.append(FIELD_SPEC[key][0])
                continue
            if mode in {"confirmer", "corriger"}:
                conn.execute("UPDATE fields SET value_enc=?,status='CONNU',reviewed=1,confidence='Validation explicite dans le bot local',version=version+1 WHERE id=?",
                             (seal(value), field["id"]))
            else:
                conn.execute("UPDATE fields SET value_enc=?,status='À_RÉVISER',confidence='Message du bot local',version=version+1 WHERE id=?",
                             (seal(value), field["id"]))
            applied.append(FIELD_SPEC[key][0])
        if report_requested:
            reviewed_count = conn.execute("SELECT COUNT(*) FROM fields WHERE record_id=? AND reviewed=1", (rid,)).fetchone()[0]
            page_count = conn.execute("SELECT COUNT(*) FROM pages WHERE record_id=?", (rid,)).fetchone()[0]
            visit_count = conn.execute("SELECT COUNT(*) FROM records WHERE patient_code=(SELECT patient_code FROM records WHERE id=?)", (rid,)).fetchone()[0]
            reply = f"Rapport local de démonstration : {reviewed_count} champ(s) confirmé(s), {page_count} page(s) expurgée(s), {visit_count} visite(s) liées. Consultez la relecture pour les valeurs et leurs preuves."
        elif applied:
            if mode == "suggestion":
                reply = "Valeur proposée pour " + ", ".join(applied) + ". Répondez « confirmer âge 28 » si la valeur est exacte, ou « corriger âge 29 »."
            else:
                reply = "Valeur " + ("confirmée" if mode == "confirmer" else "corrigée et confirmée") + " explicitement pour " + ", ".join(applied) + "."
            conn.execute("UPDATE records SET state='À_RÉVISER',version=version+1,updated_at=? WHERE id=?", (stamp(), rid))
        elif refused:
            reply = "Confirmation refusée pour " + ", ".join(refused) + ". Vérifiez la valeur proposée ou utilisez Relecture pour modifier un champ déjà confirmé."
        else:
            reply = "Je n'ai pas reconnu de champ. Essayez « âge 28 », « confirmer âge 28 », « corriger âge 29 », « TA 112/74 » ou « rapport ». Aucune recommandation médicale n'est fournie."
        conn.execute("INSERT INTO bot_messages(record_id,sender,text_enc,created_at) VALUES(?,?,?,?)",
                     (rid, "bot", seal(reply), stamp()))
        audit(conn, rid, "BOT_LOCAL", f"{len(applied)} champ(s) traité(s) en mode {mode} ; message chiffré localement.")
        return {"reply": reply, "applied": len(applied)}


class SettingsBody(BaseModel):
    ocr_languages: str
    review_order: str


@app.post("/api/settings")
def save_settings(body: SettingsBody, _: dict = Depends(require_config_admin)):
    if body.ocr_languages not in {"fr,en", "en", "fr"} or body.review_order not in {"uncertain_first", "document_order"}:
        raise HTTPException(400, "Configuration non prise en charge.")
    with database() as conn:
        for key, value in {"ocr_languages": body.ocr_languages, "review_order": body.review_order}.items():
            conn.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
        audit(conn, None, "CONFIGURATION", "Configuration locale mise à jour.")
    return {"saved": True}


class ImageBody(BaseModel):
    data_url: str = Field(max_length=11_000_000)
    masks: list[list[int]] = Field(min_length=1, max_length=50)
    synthetic_confirmed: bool


def image_quality(image: Image.Image) -> dict[str, Any]:
    sample = image.convert("L")
    sample.thumbnail((700, 700))
    stat = ImageStat.Stat(sample)
    brightness = round(stat.mean[0], 1)
    contrast = round(stat.stddev[0], 1)
    edge = ImageStat.Stat(sample.filter(ImageFilter.FIND_EDGES)).stddev[0]
    warnings = []
    if brightness < 55:
        warnings.append("Image très sombre")
    if brightness > 215:
        warnings.append("Image très claire")
    if contrast < 22:
        warnings.append("Contraste faible")
    if edge < 12:
        warnings.append("Netteté possiblement insuffisante")
    return {"brightness": brightness, "contrast": contrast, "focus_proxy": round(edge, 1),
            "warnings": warnings, "note": "Indicateurs heuristiques, sans étalonnage clinique."}


@app.post("/api/records/{rid}/image")
def save_redacted_image(rid: str, body: ImageBody, _: dict = Depends(require_admin)):
    if not body.synthetic_confirmed:
        raise HTTPException(400, "Confirmer que l'image est fictive et que toutes les zones identifiantes sont masquées.")
    match = re.fullmatch(r"data:image/(png|jpeg|jpg);base64,([A-Za-z0-9+/=]+)", body.data_url)
    if not match:
        raise HTTPException(400, "Image PNG ou JPEG attendue.")
    try:
        raw = base64.b64decode(match.group(2), validate=True)
        if len(raw) > 8_000_000:
            raise ValueError("image too large")
        with Image.open(BytesIO(raw)) as source:
            if source.width * source.height > 18_000_000:
                raise ValueError("image dimensions too large")
            image = ImageOps.exif_transpose(source).convert("RGB")
    except Exception as exc:
        raise HTTPException(400, "Image invalide ou trop volumineuse.") from exc
    quality = image_quality(image)
    draw = ImageDraw.Draw(image)
    for rect in body.masks:
        if len(rect) != 4:
            raise HTTPException(400, "Masque invalide.")
        x1, y1, x2, y2 = rect
        if not (0 <= x1 < x2 <= image.width and 0 <= y1 < y2 <= image.height):
            raise HTTPException(400, "Masque hors de l'image.")
        draw.rectangle((x1, y1, x2, y2), fill=(20, 31, 34))
    out = BytesIO()
    image.save(out, format="PNG", optimize=True)
    redacted = out.getvalue()
    digest = hashlib.sha256(redacted).hexdigest()
    with database() as conn:
        if not conn.execute("SELECT 1 FROM records WHERE id=?", (rid,)).fetchone():
            raise HTTPException(404, "Dossier introuvable.")
        existing = conn.execute("SELECT id,ordinal FROM pages WHERE record_id=? AND sha256=?", (rid, digest)).fetchone()
        if existing:
            return {"saved": True, "duplicate": True, "page_id": existing["id"], "ordinal": existing["ordinal"], "quality": quality}
        ordinal = conn.execute("SELECT COALESCE(MAX(ordinal),0)+1 FROM pages WHERE record_id=?", (rid,)).fetchone()[0]
        page_id = secrets.token_hex(12)
        encrypted = VAULT.encrypt(redacted)
        conn.execute("INSERT INTO pages(id,record_id,ordinal,image_enc,sha256,quality_json,created_at) VALUES(?,?,?,?,?,?,?)",
                     (page_id, rid, ordinal, encrypted, digest, json.dumps(quality), stamp()))
        conn.execute("UPDATE records SET image_enc=?,image_confirmed=1,version=version+1,updated_at=? WHERE id=?", (encrypted, stamp(), rid))
        audit(conn, rid, "IMAGE", f"Page {ordinal} fictive expurgée enregistrée ({len(body.masks)} masque(s)).")
    return {"saved": True, "duplicate": False, "page_id": page_id, "ordinal": ordinal, "masks": len(body.masks), "quality": quality}


@app.get("/api/records/{rid}/image")
def image(rid: str, _: dict = Depends(require_admin)):
    with database() as conn:
        row = conn.execute("SELECT image_enc FROM records WHERE id=?", (rid,)).fetchone()
    if not row or row["image_enc"] is None:
        raise HTTPException(404, "Image expurgée introuvable.")
    return Response(content=VAULT.decrypt(row["image_enc"]), media_type="image/png", headers={"Cache-Control": "no-store"})


@app.get("/api/records/{rid}/pages/{page_id}/image")
def page_image(rid: str, page_id: str, _: dict = Depends(require_admin)):
    with database() as conn:
        row = conn.execute("SELECT image_enc FROM pages WHERE id=? AND record_id=?", (page_id, rid)).fetchone()
    if not row:
        raise HTTPException(404, "Page introuvable.")
    return Response(content=VAULT.decrypt(row["image_enc"]), media_type="image/png", headers={"Cache-Control": "no-store"})


def model_files_present() -> bool:
    return all((MODELS / name).is_file() for name in ("craft_mlt_25k.pth", "latin_g2.pth"))


@lru_cache(maxsize=3)
def ocr_reader(languages: tuple[str, ...]):
    import easyocr
    return easyocr.Reader(list(languages), gpu=False, model_storage_directory=str(MODELS), download_enabled=False, verbose=False)


def extract_candidates(lines: list[str]) -> dict[str, str]:
    text = "  ".join(lines)
    rules = {
        "age": r"\b(?:âge|age)\s*[:\-]?\s*(\d{1,2})\b",
        "gestation": r"\b(?:gestation|gestité)\s*[:\-]?\s*(\d{1,2})\b",
        "parity": r"\bparit[ée]\s*[:\-]?\s*(\d{1,2})\b",
        "blood_pressure": r"\b(?:TA|tension)\s*[:\-]?\s*(\d{2,3}\s*[/\-]\s*\d{2,3})\b",
        "weight": r"\bpoids\s*[:\-]?\s*(\d{2,3}(?:[,.]\d)?)\s*(?:kg)?\b",
        "hiv": r"\b(?:VIH|HIV)\s*[:\-]?\s*(n[ée]gatif|positif|neg|pos)\b",
        "syphilis": r"\b(?:syphilis|TPHA|VDRL)\s*[:\-]?\s*(n[ée]gatif|positif|neg|pos)\b",
        "hbs": r"\b(?:Ag\s*HBs|HBs)\s*[:\-]?\s*(n[ée]gatif|positif|neg|pos)\b",
        "hcv": r"\b(?:h[ée]patite\s*C|HCV)\s*[:\-]?\s*(n[ée]gatif|positif|neg|pos)\b",
    }
    found = {}
    for key, pattern in rules.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            found[key] = re.sub(r"\s+", "", match.group(1))
    return found


def perform_local_ocr(rid: str) -> dict[str, Any]:
    with database() as conn:
        row = conn.execute("SELECT * FROM records WHERE id=?", (rid,)).fetchone()
        if not row:
            raise HTTPException(404, "Dossier introuvable.")
        if not row["image_enc"] or not row["image_confirmed"]:
            raise HTTPException(409, "Ajouter et vérifier une image fictive expurgée avant l'OCR.")
        langs = conn.execute("SELECT value FROM settings WHERE key='ocr_languages'").fetchone()[0]
        source_version = row["version"]
        pages = [VAULT.decrypt(page["image_enc"]) for page in conn.execute(
            "SELECT image_enc FROM pages WHERE record_id=? ORDER BY ordinal", (rid,)
        )]
        if not pages:
            pages = [VAULT.decrypt(row["image_enc"])]
    try:
        detected = []
        candidates: dict[str, tuple[str, int, float]] = {}
        reader = ocr_reader(tuple(langs.split(",")))
        for page_number, image_bytes in enumerate(pages, start=1):
            with Image.open(BytesIO(image_bytes)) as source:
                pixels = __import__("numpy").array(source.convert("RGB"))
            page_regions = reader.readtext(pixels, detail=1, paragraph=False)
            detected.extend(page_regions)
            for key, value in extract_candidates([item[1] for item in page_regions]).items():
                confidence = max((float(item[2]) for item in page_regions if value.lower() in str(item[1]).lower()), default=0.0)
                if key not in candidates or confidence > candidates[key][2]:
                    candidates[key] = (value, page_number, confidence)
    except Exception as exc:
        raise HTTPException(503, "OCR local indisponible. Installer les poids avec setup_models.py puis réessayer.") from exc
    applied = []
    with database() as conn:
        current = conn.execute("SELECT version FROM records WHERE id=?", (rid,)).fetchone()
        if not current or current["version"] != source_version:
            raise HTTPException(409, "Le dossier a changé pendant l'OCR. Relancer sur la version actuelle.")
        for key, (value, page_number, confidence) in candidates.items():
            field = conn.execute("SELECT id,reviewed FROM fields WHERE record_id=? AND key=?", (rid, key)).fetchone()
            if field and not field["reviewed"]:
                conn.execute(
                    "UPDATE fields SET value_enc=?,status='À_RÉVISER',confidence=?,version=version+1 WHERE id=?",
                    (seal(value), f"OCR page {page_number} · confiance brute {confidence:.2f} (non calibrée)", field["id"]),
                )
                applied.append(key)
        conn.execute("UPDATE records SET version=version+1,updated_at=? WHERE id=?", (stamp(), rid))
        audit(conn, rid, "OCR_LOCAL", f"{len(applied)} suggestion(s) sur {len(pages)} page(s) à vérifier ; aucun texte OCR libre stocké.")
        return {"record": get_record(conn, rid), "suggestions": len(applied), "detected_regions": len(detected), "pages": len(pages)}


def process_job(job_id: str) -> dict[str, Any]:
    with database() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(404, "Opération introuvable.")
        if job["state"] == "DONE":
            result = json.loads(job["result_json"])
            result["record"] = get_record(conn, job["record_id"])
            return result
        if job["state"] == "RUNNING":
            return {"job_id": job_id, "job_state": "RUNNING"}
        conn.execute("UPDATE jobs SET state='RUNNING',attempts=attempts+1,updated_at=? WHERE id=?", (stamp(), job_id))
    try:
        result = perform_local_ocr(job["record_id"])
        summary = {"job_id": job_id, "job_state": "DONE", "suggestions": result["suggestions"],
                   "detected_regions": result["detected_regions"], "pages": result["pages"]}
        with database() as conn:
            conn.execute("UPDATE jobs SET state='DONE',result_json=?,updated_at=? WHERE id=?",
                         (json.dumps(summary), stamp(), job_id))
        return {**summary, "record": result["record"]}
    except HTTPException as exc:
        next_state = "PENDING" if exc.status_code in {409, 503} else "ERROR"
        with database() as conn:
            conn.execute("UPDATE jobs SET state=?,result_json=?,updated_at=? WHERE id=?",
                         (next_state, json.dumps({"error": str(exc.detail)}), stamp(), job_id))
        return {"job_id": job_id, "job_state": next_state, "detail": exc.detail}
    except Exception:
        with database() as conn:
            conn.execute("UPDATE jobs SET state='ERROR',result_json=?,updated_at=? WHERE id=?",
                         (json.dumps({"error": "Erreur interne locale, sans détail médical."}), stamp(), job_id))
        return {"job_id": job_id, "job_state": "ERROR", "detail": "Erreur interne locale. Vérifier la configuration et réessayer."}


@app.post("/api/records/{rid}/ocr")
def run_local_ocr(rid: str, idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
                  _: dict = Depends(require_admin)):
    key = (idempotency_key or secrets.token_hex(16)).strip()[:100]
    if not key:
        raise HTTPException(400, "Clé d'idempotence vide.")
    with database() as conn:
        if not conn.execute("SELECT 1 FROM records WHERE id=?", (rid,)).fetchone():
            raise HTTPException(404, "Dossier introuvable.")
        existing = conn.execute("SELECT id,record_id FROM jobs WHERE idempotency_key=?", (key,)).fetchone()
        if existing and existing["record_id"] != rid:
            raise HTTPException(409, "Clé d'idempotence déjà utilisée pour un autre dossier.")
        job_id = existing["id"] if existing else secrets.token_hex(12)
        if not existing:
            conn.execute("INSERT INTO jobs(id,record_id,idempotency_key,state,created_at,updated_at) VALUES(?,?,?,'PENDING',?,?)",
                         (job_id, rid, key, stamp(), stamp()))
    return process_job(job_id)


@app.get("/api/jobs")
def jobs(_: dict = Depends(require_admin)):
    with database() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT id,record_id,state,attempts,created_at,updated_at FROM jobs ORDER BY created_at DESC LIMIT 40"
        )]


@app.post("/api/jobs/resume")
def resume_jobs(_: dict = Depends(require_config_admin)):
    with database() as conn:
        pending = [row["id"] for row in conn.execute("SELECT id FROM jobs WHERE state='PENDING' ORDER BY created_at LIMIT 10")]
    return {"processed": [process_job(job_id) for job_id in pending]}


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers={"Cache-Control": "no-store"})


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("DAYONE_BIND_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("Le prototype doit rester lié à 127.0.0.1.")
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("DAYONE_BIND_PORT", "8765")), access_log=False)
