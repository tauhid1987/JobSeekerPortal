"""Local ranking: TF-IDF similarity + skill overlap + title match. No network, CV stays private."""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .cv_parser import extract_skills


GENERIC = {"engineer", "senior", "junior", "lead", "manager", "developer", "specialist", "analyst", "the", "and",
           "for", "with", "intern", "staff", "principal", "associate", "executive", "officer", "assistant"}


def _words(s):
    """Meaningful words only; generic role words must not count as a title match."""
    return set(re.findall(r"[a-z]{2,}", s.lower())) - GENERIC


def rank(cv, jobs, query="", remote_only=False, min_score=0, keep=None):
    """keep(job) -> bool runs on every unique job BEFORE the relevance cut, so a job the user cannot
    apply for (visa, region) never takes a place that an eligible job should have had."""
    seen, uniq = set(), []
    for j in jobs:
        k = (j["title"].lower().strip(), j["company"].lower().strip())
        if k in seen or not j["apply_url"]:
            continue
        seen.add(k)
        uniq.append(j)
    if remote_only:
        uniq = [j for j in uniq if j["remote"]]
    if keep:
        uniq = [j for j in uniq if keep(j)]
    if not uniq:
        return []
    docs = [f"{j['title']} {j['title']} {' '.join(j['tags'])} {j['description'][:3000]}" for j in uniq]
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True, max_features=40000)
    m = vec.fit_transform([cv["text"]] + docs)
    sim = cosine_similarity(m[0:1], m[1:])[0]
    top = sim.max() or 1
    cv_sk = set(cv["skills"])
    cv_title_words = _words(" ".join(cv["titles"] + [query]))
    out = []
    for j, s in zip(uniq, sim):
        jd_sk = set(extract_skills(f"{j['title']} {' '.join(j['tags'])} {j['description']}"))
        shared = sorted(cv_sk & jd_sk)
        skill_score = len(shared) / len(jd_sk) if jd_sk else 0
        title_score = len(cv_title_words & _words(j["title"])) / max(len(_words(j["title"])), 1)
        w = (0.25, 0.25, 0.50) if len(j["description"]) < 700 else (0.45, 0.35, 0.20)  # short ads: lean on the title
        score = 100 * (w[0] * min(1, s * 4) + w[1] * min(1, skill_score * 1.5) + w[2] * min(1, title_score * 1.5))
        relevant = bool(cv_title_words & _words(j["title"])) or len(shared) >= 2
        out.append(dict(j, score=round(score, 1), matched=shared, missing=sorted(jd_sk - cv_sk)[:8], relevant=relevant))
    out.sort(key=lambda x: -x["score"])
    rel = [j for j in out if j["relevant"]]
    if len(rel) < 20:  # CV/query not recognised well: fall back to best similarity matches
        rel = out[:50]
    return [j for j in rel if j["score"] >= min_score]
