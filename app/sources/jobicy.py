import requests
from . import clean

NAME = "Jobicy"


def search(query):
    q = (query or "").strip()[:20]
    params = {"count": 50}
    if len(q) >= 3:
        params["tag"] = q
    r = requests.get("https://jobicy.com/api/v2/remote-jobs", params=params, timeout=30, headers={"User-Agent": "JobMatch/1.0"})
    data = r.json()
    if not data.get("success", True) and "tag" in params:  # no match for the tag: use the latest list instead
        r = requests.get("https://jobicy.com/api/v2/remote-jobs", params={"count": 50}, timeout=30, headers={"User-Agent": "JobMatch/1.0"})
        data = r.json()
    out = []
    for j in data.get("jobs", []):
        sal = ""
        if j.get("salaryMin"):
            sal = f"{j.get('salaryCurrency', '')} {j['salaryMin']}-{j.get('salaryMax', '')} {j.get('salaryPeriod', '')}".strip()
        out.append({"title": j["jobTitle"], "company": j.get("companyName", ""), "salary": sal, "apply_url": j["url"],
                    "type": ", ".join(j.get("jobType") or []), "location": j.get("jobGeo") or "Anywhere", "remote": True,
                    "posted": (j.get("pubDate") or "")[:10], "tags": j.get("jobIndustry") or [],
                    "description": clean(j.get("jobDescription") or j.get("jobExcerpt")), "source": "Jobicy"})
    return out
