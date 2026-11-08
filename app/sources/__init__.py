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


def search_all(queries, country="Bangladesh", log=print, scope="both"):
    """scope: 'local' = job boards of the user's country, 'remote' = remote jobs open to other countries, 'both'.
    Sources run in parallel; one that fails is skipped and logged."""
    from concurrent.futures import ThreadPoolExecutor
    from . import remotive, remoteok, arbeitnow, jobicy, himalayas, weworkremotely, workingnomads, bdjobs, skilljobs, jooble, adzuna
    queries = queries or [""]
    tasks = []  # (label, function)
    if scope in ("remote", "both"):
        for q in queries:
            tasks.append((f"Remotive '{q}'", lambda q=q: remotive.search(q)))
            tasks.append((f"Himalayas '{q}'", lambda q=q: himalayas.search(q)))
            tasks.append((f"Jobicy '{q}'", lambda q=q: jobicy.search(q)))
        tasks += [("RemoteOK", lambda: remoteok.search("")), ("Arbeitnow", lambda: arbeitnow.search("")),
                  ("We Work Remotely", lambda: weworkremotely.search("")), ("Working Nomads", lambda: workingnomads.search(""))]
    if scope in ("local", "both"):
        for mod in (bdjobs, skilljobs):
            if country.lower() in mod.COUNTRIES:
                tasks.append((mod.NAME, lambda mod=mod: mod.search(queries[0])))
        for q in queries:
            tasks.append((f"Jooble '{q}'", lambda q=q: jooble.search(q, country)))
            tasks.append((f"Adzuna '{q}'", lambda q=q: adzuna.search(q, country)))

    def run(t):
        label, fn = t
        try:
            got = fn()
            return label, got, None
        except Exception as e:
            return label, [], f"{type(e).__name__}: {str(e)[:80]}"

    jobs = []
    with ThreadPoolExecutor(6) as ex:
        for label, got, err in ex.map(run, tasks):
            if err:
                log(f"{label}: skipped ({err})")
            elif got or not label.startswith("Adzuna"):
                log(f"{label}: {len(got)} jobs")
            jobs.extend(got)
    for j in jobs:
        for k in ("title", "company", "location", "salary"):
            j[k] = fix_text(j.get(k))
    return jobs
