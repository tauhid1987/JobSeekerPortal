"""Read a CV (PDF/DOCX/TXT) and pull out skills, titles, experience."""
import re
from pathlib import Path

PHRASES = [
    "api testing", "manual testing", "automation testing", "performance testing", "security testing", "test automation",
    "quality assurance", "machine learning", "deep learning", "data analysis", "power bi", "robot framework",
    "project management", "product management", "business analysis", "customer support", "content writing",
    "graphic design", "ci/cd", "node.js", "ui ux", "sql server", "web development", "software testing",
    "test management", "regression testing", "rest api", "unit testing"]
WORDS = """python java javascript typescript c# c++ go rust php ruby kotlin swift sql mysql postgresql mongodb oracle react
angular vue django flask spring .net aws azure gcp docker kubernetes terraform jenkins git linux selenium playwright cypress
pytest junit testng postman jmeter katalon appium jira confluence agile scrum kanban devops excel tableau pandas numpy
tensorflow pytorch html css graphql microservices erp sap odoo accounting finance audit tally sales marketing seo figma
photoshop qa bdd gherkin cucumber nlp""".split()

TITLE_WORDS = ["engineer", "developer", "tester", "analyst", "manager", "designer", "consultant", "officer", "executive",
               "architect", "lead", "specialist", "administrator", "accountant", "scientist", "coordinator", "writer",
               "assistant", "director"]


def read_text(path):
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
    if ext == ".docx":
        import docx
        d = docx.Document(str(p))
        parts = [x.text for x in d.paragraphs]
        for t in d.tables:
            for r in t.rows:
                parts += [c.text for c in r.cells]
        return "\n".join(parts)
    return p.read_text(encoding="utf-8", errors="ignore")


def _has(text, term):
    return re.search(r"(?<![\w+#.])" + re.escape(term) + r"(?![\w+#])", text) is not None


def extract_skills(text):
    t = text.lower()
    return sorted({s for s in PHRASES + WORDS if _has(t, s)})


def extract_years(text):
    ys = [int(m) for m in re.findall(r"(\d{1,2})\+?\s*(?:years|yrs)", text.lower()) if int(m) < 45]
    return max(ys) if ys else None


def extract_titles(text):
    titles = []
    for line in text.splitlines()[:60]:
        l = line.strip()
        if 3 < len(l) < 60 and any(w in l.lower() for w in TITLE_WORDS) and "@" not in l:
            titles.append(l)
    return titles[:5]


def parse_cv(path):
    text = read_text(path)
    return {"text": text, "skills": extract_skills(text), "years": extract_years(text), "titles": extract_titles(text)}
