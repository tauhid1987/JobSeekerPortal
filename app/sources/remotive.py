import requests
from . import clean


def search(query):
    r = requests.get("https://remotive.com/api/remote-jobs", params={"search": query, "limit": 100}, timeout=30,
                     headers={"User-Agent": "JobMatch/1.0"})
    r.raise_for_status()
    return [{"title": j["title"], "company": j["company_name"], "salary": j.get("salary") or "",
             "apply_url": j["url"], "type": (j.get("job_type") or "").replace("_", " ").title(),
             "location": j.get("candidate_required_location") or "Anywhere", "remote": True,
             "posted": (j.get("publication_date") or "")[:10], "tags": j.get("tags") or [],
             "description": clean(j.get("description")), "source": "Remotive"} for j in r.json().get("jobs", [])]
