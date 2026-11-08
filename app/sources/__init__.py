"""Each source returns normalized job dicts:
title, company, salary, apply_url, type, location, remote, posted, tags, description, source
(optional: deadline (date), country)"""
import re
import html
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def fix_text(s):
    """Some feeds send text that was UTF-8 decoded twice (Sothebyâ€™s). Undo that when it is clearly the case."""
    if isinstance(s, str) and any(m in s for m in ("â€", "Ã", "Â")):
        try:
            return s.encode("cp1252").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return s
    return s


def search_all(queries, country="Bangladesh", log=print):
    """Global feeds run for everyone; country sources (BDJobs, Skill.Jobs...) only for their country."""
    from . import remotive, remoteok, arbeitnow, bdjobs, skilljobs, jooble
    jobs = []
    queries = queries or [""]

    def run(label, fn):
        try:
            got = fn()
            log(f"{label}: {len(got)} jobs")
            jobs.extend(got)
        except Exception as e:
            log(f"{label}: skipped ({type(e).__name__}: {str(e)[:80]})")

    for q in queries:
        run(f"Remotive '{q}'", lambda q=q: remotive.search(q))
    run("RemoteOK", lambda: remoteok.search(""))
    run("Arbeitnow", lambda: arbeitnow.search(""))
    for mod in (bdjobs, skilljobs):
        if country.lower() in mod.COUNTRIES:
            run(mod.NAME, lambda: mod.search(queries[0]))
    for q in queries:
        run(f"Jooble '{q}'", lambda q=q: jooble.search(q, country))
    for j in jobs:
        for k in ("title", "company", "location", "salary"):
            j[k] = fix_text(j.get(k))
    return jobs
