"""JobMatch backend. The browser app (static/) signs in with Firebase; this API does the CV work.
Every call needs  Authorization: Bearer <Firebase ID token>  and an approved member (or admin) account."""
import base64
import hashlib
import os
import time
import uuid
import datetime as dt
from pathlib import Path
from flask import Flask, request, send_file, send_from_directory, jsonify, Response
from . import fbauth
from .cv_parser import parse_cv
from .sources import search_all
from .matcher import rank
from .excel_export import export
from .deadlines import extract_deadline
from .eligibility import check as check_eligibility

ROOT = Path(__file__).resolve().parent.parent
UP, STATIC = ROOT / "uploads", ROOT / "docs"
UP.mkdir(exist_ok=True)
# Browser pages allowed to call this API (the GitHub Pages site). Comma separated; set JOBMATCH_ORIGINS on the host.
ORIGINS = {o.strip().rstrip("/") for o in os.getenv("JOBMATCH_ORIGINS", "https://tauhid1987.github.io").split(",") if o.strip()}
app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
COOLDOWN = 10  # seconds between searches per user, to be polite to the job sites
_last = {}


@app.after_request
def secure_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
        origin = request.headers.get("Origin", "")
        if origin in ORIGINS:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            resp.headers["Access-Control-Max-Age"] = "600"
            resp.headers["Vary"] = "Origin"
    return resp


def bearer():
    h = request.headers.get("Authorization", "")
    return h[7:] if h.startswith("Bearer ") else ""


def who(require=("member", "admin")):
    """Returns (uid, token, status) or raises fbauth.AuthError."""
    token = bearer()
    uid, _ = fbauth.verify_token(token)
    st = fbauth.status(uid, token)
    if st not in require:
        msg = {"pending": "Your account is waiting for admin approval.", "blocked": "Your access was turned off by an admin.",
               "none": "Request access first."}.get(st, "Not allowed.")
        raise fbauth.AuthError(msg)
    return uid, token, st


@app.errorhandler(fbauth.AuthError)
def auth_error(e):
    return jsonify(error=str(e)), 401


@app.get("/")
def index():
    return send_from_directory(STATIC, "index.html")


@app.get("/admin")
def admin():
    return send_from_directory(STATIC, "admin.html")


@app.route("/api/<path:_>", methods=["OPTIONS"])
def preflight(_):
    return "", 204


@app.get("/firebase-config.js")
def firebase_config_js():
    c = fbauth.config()
    pub = {k: c[k] for k in ("apiKey", "authDomain", "databaseURL", "projectId", "appId")}
    import json
    body = f"export const firebaseConfig = {json.dumps(pub)};\nexport const EMULATOR = {str(fbauth.EMULATOR).lower()};\nexport const API_BASE = '';\n"
    return Response(body, mimetype="text/javascript")


@app.get("/<path:name>")
def static_files(name):
    if name.startswith(("api/", ".")) or ".." in name:
        return "Not found", 404
    return send_from_directory(STATIC, name)


@app.get("/api/me")
def me():
    token = bearer()
    uid, _ = fbauth.verify_token(token)
    return jsonify(uid=uid, status=fbauth.status(uid, token))


@app.post("/api/search")
def search():
    uid, token, _ = who()
    if time.time() - _last.get(uid, 0) < COOLDOWN:
        return jsonify(error=f"Please wait {COOLDOWN} seconds between searches."), 429
    _last[uid] = time.time()
    f = request.files.get("cv")
    if not f or Path(f.filename).suffix.lower() not in (".pdf", ".docx", ".txt"):
        return jsonify(error="Upload a PDF, DOCX or TXT CV."), 400
    path = UP / f"{uuid.uuid4().hex}{Path(f.filename).suffix.lower()}"
    f.save(path)
    try:
        cv = parse_cv(path)
    finally:
        path.unlink(missing_ok=True)  # the CV is never kept
    if len(cv["text"].strip()) < 100:
        return jsonify(error="Could not read text from this CV (scanned image?). Try a text PDF or DOCX."), 400
    queries = [q.strip() for q in request.form.get("query", "").split(",") if q.strip()]
    if not queries:
        queries = cv["titles"][:1] or cv["skills"][:1]
    query = " ".join(queries)
    country = request.form.get("country", "").strip() or "Bangladesh"
    log = []
    jobs = search_all(queries, country, log.append)
    ranked = rank(cv, jobs, query, remote_only=request.form.get("remote") == "on",
                  min_score=float(request.form.get("min_score") or 0))
    for j in ranked:
        j["eligible"], j["eligible_why"] = check_eligibility(j, country)
    not_eligible = [j for j in ranked if j["eligible"] == "No"]
    if request.form.get("eligibility", "strict") == "strict":
        ranked = [j for j in ranked if j["eligible"] != "No"]
    today = dt.date.today()
    for j in ranked:
        j["deadline"] = j.get("deadline") or extract_deadline(j["description"])
        j["days_left"] = (j["deadline"] - today).days if j["deadline"] else None
    expired = [j for j in ranked if j["days_left"] is not None and j["days_left"] < 0]
    ranked = [j for j in ranked if j not in expired]
    sort = request.form.get("sort", "match")
    if sort == "deadline":  # closest deadline first; jobs with no stated deadline follow, best match first
        ranked = sorted([j for j in ranked if j["deadline"]], key=lambda j: j["deadline"]) + [j for j in ranked if not j["deadline"]]
    top = ranked[: max(10, min(int(request.form.get("limit") or 100), 500))]
    _last[uid] = time.time()  # the cooldown runs from the end of a search

    def record(shown):  # tracking: the server writes it, as the user, under the same database rules
        try:
            fbauth.log_activity(uid, token, titles=", ".join(queries)[:300], country=country[:60], found=len(jobs), shown=shown,
                                sort=sort, eligibility=request.form.get("eligibility", "strict"),
                                minScore=float(request.form.get("min_score") or 0), remote=request.form.get("remote") == "on",
                                skills=", ".join(cv["skills"])[:300])
            return True
        except Exception:
            return False

    if not top:
        record(0)
        return jsonify(error=f"{len(jobs)} jobs found, but none passed the filters (minimum match, eligibility for {country}). "
                             "Lower 'Minimum match %' or choose 'Show all jobs with status'."), 400
    tracked = record(len(top))
    name = f"job_search_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    tmp = UP / f"{uuid.uuid4().hex}.xlsx"
    try:
        export(top, tmp)
        xlsx = base64.b64encode(tmp.read_bytes()).decode()
    finally:
        tmp.unlink(missing_ok=True)  # nothing about the search is kept on the server
    keys =("title", "company", "source", "score", "salary", "type", "apply_url", "posted", "eligible", "eligible_why", "location")
    return jsonify(file=name, xlsx=xlsx, log=log, skills=cv["skills"], years=cv["years"], total=len(jobs), country=country,
                   not_eligible=len(not_eligible), expired=len(expired), tracked=tracked,
                   jobs=[{k: j[k] for k in keys} | {"key": hashlib.sha1(j["apply_url"].encode()).hexdigest()[:20],
                                                    "deadline": str(j["deadline"] or ""), "days_left": j["days_left"]} for j in top])


if __name__ == "__main__":
    app.run(os.getenv("JOBMATCH_HOST", "127.0.0.1"), int(os.getenv("JOBMATCH_PORT", "5000")))
