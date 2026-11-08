import requests
from . import clean

NAME = "Working Nomads"


def search(query):
    r = requests.get("https://www.workingnomads.com/api/exposed_jobs/", timeout=30, headers={"User-Agent": "JobMatch/1.0"})
    r.raise_for_status()
    return [{"title": j["title"], "company": j.get("company_name", ""), "salary": "", "apply_url": j["url"], "type": "",
             "location": j.get("location") or "Anywhere", "remote": True, "posted": (j.get("pub_date") or "")[:10],
             "tags": [t for t in (j.get("tags") or "").split(",") if t], "description": clean(j.get("description")),
             "source": "Working Nomads"} for j in r.json()]
