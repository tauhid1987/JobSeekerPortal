"""Adzuna: local jobs in 19 countries. Free key from developer.adzuna.com; set ADZUNA_ID and ADZUNA_KEY (skipped without them)."""
import os
import requests
from . import clean

NAME = "Adzuna"
CODES = {"united kingdom": "gb", "united states": "us", "australia": "au", "canada": "ca", "germany": "de", "france": "fr",
         "india": "in", "italy": "it", "netherlands": "nl", "new zealand": "nz", "poland": "pl", "singapore": "sg",
         "south africa": "za", "brazil": "br", "austria": "at", "belgium": "be", "switzerland": "ch", "mexico": "mx", "spain": "es"}


def search(query, country):
    cc, aid, key = CODES.get((country or "").lower()), os.getenv("ADZUNA_ID"), os.getenv("ADZUNA_KEY")
    if not (cc and aid and key):
        return []
    r = requests.get(f"https://api.adzuna.com/v1/api/jobs/{cc}/search/1", timeout=30, headers={"User-Agent": "JobMatch/1.0"},
                     params={"app_id": aid, "app_key": key, "results_per_page": 50, "what": query, "content-type": "application/json"})
    r.raise_for_status()
    out = []
    for j in r.json().get("results", []):
        sal = f"{int(j['salary_min'])}-{int(j['salary_max'])}" if j.get("salary_min") and j.get("salary_max") else ""
        out.append({"title": clean(j.get("title")), "company": (j.get("company") or {}).get("display_name", ""), "salary": sal,
                    "apply_url": j.get("redirect_url", ""), "type": (j.get("contract_time") or "").replace("_", " ").title(),
                    "location": (j.get("location") or {}).get("display_name", ""), "remote": False,
                    "posted": (j.get("created") or "")[:10], "tags": [], "description": clean(j.get("description")),
                    "source": "Adzuna", "country": country})
    return out
