import requests
from . import clean


def search(query):
    r = requests.get("https://remoteok.com/api", timeout=30, headers={"User-Agent": "JobMatch/1.0"})
    r.raise_for_status()
    out = []
    for j in r.json():
        if not isinstance(j, dict) or "position" not in j:
            continue
        sal = ""
        if j.get("salary_min") and j.get("salary_max"):
            sal = f"${j['salary_min']:,} - ${j['salary_max']:,} / year"
        out.append({"title": j["position"], "company": j.get("company", ""), "salary": sal,
                    "apply_url": j.get("apply_url") or j.get("url", ""), "type": "Remote",
                    "location": j.get("location") or "Anywhere", "remote": True,
                    "posted": (j.get("date") or "")[:10], "tags": j.get("tags") or [],
                    "description": clean(j.get("description")), "source": "RemoteOK"})
    return out
