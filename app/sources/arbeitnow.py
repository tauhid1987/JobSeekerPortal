import datetime
import requests
from . import clean


def search(query):
    out = []
    for page in (1, 2, 3):
        r = requests.get("https://www.arbeitnow.com/api/job-board-api", params={"page": page}, timeout=30,
                         headers={"User-Agent": "JobMatch/1.0"})
        r.raise_for_status()
        for j in r.json().get("data", []):
            posted = datetime.datetime.fromtimestamp(j["created_at"]).strftime("%Y-%m-%d") if j.get("created_at") else ""
            out.append({"title": j["title"], "company": j["company_name"], "salary": "",
                        "apply_url": j["url"], "type": ", ".join(j.get("job_types") or []),
                        "location": j.get("location") or "", "remote": bool(j.get("remote")),
                        "posted": posted, "tags": j.get("tags") or [],
                        "description": clean(j.get("description")), "source": "Arbeitnow"})
    return out
