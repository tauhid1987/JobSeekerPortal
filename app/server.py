"""JobMatch local web app: upload CV -> search free job APIs -> ranked Excel list."""
import time
import uuid
from pathlib import Path
from flask import Flask, render_template, request, send_file, jsonify
from .cv_parser import parse_cv
from .sources import search_all
from .matcher import rank
from .excel_export import export
from .deadlines import extract_deadline
from .eligibility import check as check_eligibility
import datetime as dt

ROOT = Path(__file__).resolve().parent.parent
UP, OUT = ROOT / "uploads", ROOT / "output"
UP.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/search")
def search():
    f = request.files.get("cv")
    if not f or Path(f.filename).suffix.lower() not in (".pdf", ".docx", ".txt"):
        return jsonify(error="Upload a PDF, DOCX or TXT CV."), 400
    path = UP / f"{uuid.uuid4().hex}{Path(f.filename).suffix.lower()}"
    f.save(path)
    try:
        cv = parse_cv(path)
    finally:
        path.unlink(missing_ok=True)  # CV is not kept on disk
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
    if request.form.get("sort") == "deadline":
        # closest deadline first; jobs with no stated deadline follow, best match first
        ranked = sorted([j for j in ranked if j["deadline"]], key=lambda j: j["deadline"]) +                  [j for j in ranked if not j["deadline"]]
    if not ranked:
        return jsonify(error=f"{len(jobs)} jobs found, but none reached the minimum match. Lower 'Minimum match %' (try 30)."), 400
    top = ranked[: int(request.form.get("limit") or 100)]
    name = f"job_search_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
    export(top, OUT / name)
    return jsonify(file=name, log=log, skills=cv["skills"], years=cv["years"], total=len(jobs), not_eligible=len(not_eligible), country=country, expired=len(expired), with_deadline=sum(1 for j in top if j['deadline']),
                   jobs=[{k: j[k] for k in ("title", "company", "score", "salary", "type", "apply_url", "posted", "eligible", "eligible_why")} | {"deadline": str(j["deadline"] or "")} for j in top[:15]])


@app.get("/download/<name>")
def download(name):
    p = OUT / Path(name).name
    return send_file(p, as_attachment=True) if p.exists() else ("Not found", 404)


if __name__ == "__main__":
    app.run("127.0.0.1", 5000)
