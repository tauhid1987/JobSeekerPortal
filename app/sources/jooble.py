"""Jooble (covers Bangladesh and many countries). Needs a free API key in .env as JOOBLE_KEY
(register at https://jooble.org/api/about). Skipped silently when no key is set."""
import os
import requests
from . import clean

COUNTRIES = None  # any country, location comes from the user's country
NAME = "Jooble"
NEEDS_KEY = "JOOBLE_KEY"


def search(query, country="Bangladesh"):
    key = os.getenv("JOOBLE_KEY", "").strip()
    if not key:
        raise RuntimeError("no JOOBLE_KEY in .env (skipped)")
    r = requests.post(f"https://jooble.org/api/{key}", json={"keywords": query, "location": country, "page": 1},
                      timeout=40)
    r.raise_for_status()
    out = []
    for j in r.json().get("jobs", []):
        out.append({"title": clean(j.get("title")), "company": clean(j.get("company")), "salary": clean(j.get("salary")),
                    "apply_url": j.get("link", ""), "type": clean(j.get("type")),
                    "location": clean(j.get("location")), "remote": "remote" in (j.get("location") or "").lower(),
                    "posted": (j.get("updated") or "")[:10], "tags": [],
                    "description": clean(j.get("snippet")), "deadline": None, "country": country, "source": NAME})
    return out
