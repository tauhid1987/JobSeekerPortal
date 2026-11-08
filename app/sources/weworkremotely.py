import datetime
import email.utils
import feedparser
from . import clean

NAME = "We Work Remotely"


def search(query):
    feed = feedparser.parse("https://weworkremotely.com/remote-jobs.rss", agent="JobMatch/1.0")
    out = []
    for e in feed.entries:
        title, _, company = e.get("title", "").partition(": ")
        if not _:
            title, company = e.get("title", ""), ""
        else:
            title, company = company, title  # feed format is "Company: Job title"
        posted = ""
        if e.get("published"):
            try:
                posted = email.utils.parsedate_to_datetime(e.published).strftime("%Y-%m-%d")
            except Exception:
                pass
        out.append({"title": title, "company": company, "salary": "", "apply_url": e.get("link", ""), "type": e.get("type", ""),
                    "location": e.get("region") or "Anywhere", "remote": True, "posted": posted,
                    "tags": [t for t in (e.get("skills") or "").split(", ") if t],
                    "description": clean(e.get("summary")), "source": "We Work Remotely"})
    return out
