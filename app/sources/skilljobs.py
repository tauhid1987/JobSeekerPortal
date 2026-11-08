"""Skill.Jobs (Bangladesh): uses the site's own public search URL, then reads each job page's
schema.org JobPosting data (title, company, deadline, salary). A few jobs per title, with a short pause."""
import re
import json
import time
import datetime as dt
import requests
from . import clean

COUNTRIES = {"bangladesh"}
NAME = "Skill.Jobs"
UA = {"User-Agent": "JobMatch/1.0 (personal job-search tool)"}
PER_QUERY = 15


def _salary(b):
    try:
        v = b["value"]
        lo, hi, unit = v.get("minValue"), v.get("maxValue"), (v.get("unitText") or "").lower()
        cur = b.get("currency") or "BDT"
        if lo and hi:
            return f"{cur} {int(lo):,} - {int(hi):,} ({unit or 'month'})"
        if v.get("value"):
            return f"{cur} {int(v['value']):,} ({unit or 'month'})"
    except Exception:
        pass
    return ""


def _posting(url):
    t = requests.get(url, headers=UA, timeout=40).text
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
        try:
            d = json.loads(m)
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("@type") == "JobPosting":
            return d
    return None


def search(query):
    r = requests.get("https://skill.jobs/browse-jobs", params={"search": query}, headers=UA, timeout=40)
    links = list(dict.fromkeys(re.findall(r'href="(/jobs/[^"#?]+)"', r.text)))[:PER_QUERY]
    out = []
    for path in links:
        time.sleep(0.4)
        try:
            d = _posting("https://skill.jobs" + path)
        except Exception:
            continue
        if not d:
            continue
        deadline = None
        try:
            deadline = dt.datetime.strptime((d.get("validThrough") or "")[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
        loc = d.get("jobLocation") or {}
        loc = loc[0] if isinstance(loc, list) and loc else loc
        addr = (loc.get("address") or {}) if isinstance(loc, dict) else {}
        place = ", ".join(x for x in (addr.get("addressLocality"), addr.get("addressRegion")) if x) or "Bangladesh"
        et = d.get("employmentType") or ""
        et = ", ".join(et) if isinstance(et, list) else et
        out.append({"title": clean(d.get("title")), "company": clean((d.get("hiringOrganization") or {}).get("name")),
                    "salary": _salary(d.get("baseSalary") or {}), "apply_url": "https://skill.jobs" + path,
                    "type": et.replace("_", " ").title(), "location": place,
                    "remote": d.get("jobLocationType") == "TELECOMMUTE",
                    "posted": (d.get("datePosted") or "")[:10], "tags": [],
                    "description": clean(d.get("description")) + " " + clean(d.get("skills") or ""),
                    "deadline": deadline, "country": "Bangladesh", "source": NAME})
    return out
