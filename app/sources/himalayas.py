import datetime
import requests
from . import clean

NAME = "Himalayas"


def search(query):
    r = requests.get("https://himalayas.app/jobs/api/search", params={"q": query, "sort": "recent"}, timeout=30,
                     headers={"User-Agent": "JobMatch/1.0"})
    r.raise_for_status()
    out = []
    for j in r.json().get("jobs", []):
        sal = ""
        if j.get("minSalary"):
            sal = f"{j.get('currency') or ''} {j['minSalary']}-{j.get('maxSalary') or ''} {j.get('salaryPeriod') or ''}".strip()
        posted = datetime.datetime.fromtimestamp(j["pubDate"]).strftime("%Y-%m-%d") if j.get("pubDate") else ""
        loc = ", ".join(j.get("locationRestrictions") or []) or "Anywhere"
        out.append({"title": j["title"], "company": j.get("companyName", ""), "salary": sal,
                    "apply_url": j.get("applicationLink") or j.get("guid"), "type": j.get("employmentType") or "",
                    "location": loc, "remote": True, "posted": posted, "tags": j.get("categories") or [],
                    "description": clean(j.get("description") or j.get("excerpt")), "source": "Himalayas"})
    return out
