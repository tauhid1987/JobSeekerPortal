"""BDJobs (Bangladesh): reads the job list that the public listing page itself embeds.
Only the newest ~50 jobs are available this way (the page ignores keyword/page options)."""
import re
import json
import datetime as dt
import requests
from . import clean

COUNTRIES = {"bangladesh"}
NAME = "BDJobs"
UA = {"User-Agent": "JobMatch/1.0 (personal job-search tool)"}


def search(query):
    t = requests.get("https://bdjobs.com/h/jobs/", headers=UA, timeout=40).text
    m = re.search(r'<script id="ng-state" type="application/json">(.*?)</script>', t, re.S)
    if not m:
        raise RuntimeError("listing data not found (site layout changed?)")
    rows = []
    for v in json.loads(m.group(1)).values():
        b = v.get("b") if isinstance(v, dict) else None
        if isinstance(b, dict) and isinstance(b.get("data"), list) and b["data"] and "jobTitle" in b["data"][0]:
            rows = b["data"]
            break
    out = []
    for j in rows:
        try:
            deadline = dt.datetime.strptime(j["deadlineDB"][:10], "%Y-%m-%d").date()
        except Exception:
            deadline = None
        desc = clean(" ".join(str(j.get(k) or "") for k in ("jobTitle", "jobContext", "jobDescription", "eduRec")) +
                     f" Experience: {j.get('experience') or ''}")
        sal = (j.get("Salary") or "").strip()
        out.append({"title": clean(j["jobTitle"]), "company": clean(j["companyName"]),
                    "salary": "" if sal in ("", "--") else sal,
                    "apply_url": f"https://bdjobs.com/h/details/{j['Jobid']}",
                    "type": {"FullTime": "Full Time", "PartTime": "Part Time"}.get(j.get("JobType"), j.get("JobType") or ""),
                    "location": clean(j.get("location") or "Bangladesh"),
                    "remote": (j.get("WorkPlace") or "").lower() in ("remote", "work from home"),
                    "posted": (j.get("publishDate") or "")[:10], "tags": [], "description": desc,
                    "deadline": deadline, "country": "Bangladesh", "source": NAME})
    return out
