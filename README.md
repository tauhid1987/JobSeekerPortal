# JobSeekerPortal (JobMatch)

Upload a CV, search job sources, and get a ranked Excel list of jobs you can apply for.

## Run
Double-click `JobMatch.cmd` (first run creates `.venv` and installs `requirements.txt`), or:

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m app.server
```
Open http://127.0.0.1:5000

## What it does
- Reads a PDF/DOCX/TXT CV locally (the file is deleted right after reading; nothing is sent to an AI service).
- Searches Remotive, RemoteOK, Arbeitnow, and for Bangladesh also BDJobs and Skill.Jobs. Jooble is used when `JOOBLE_KEY` is set in `.env`.
- Ranks jobs (TF-IDF + skill overlap + title match), checks if a candidate from the chosen country can apply
  (Yes / Check / Visa-relocation / No), reads deadlines, and exports an Excel sheet:
  Sl No., Job Title, Company, Source, Match %, Can Apply?, Salary, Posted, Deadline, How to Apply, Type, Others.

## Notes
- Eligibility is a rule-based screen of location and visa wording, not a guarantee; "Check" means read the posting.
- BDJobs exposes only its newest ~50 jobs through its public listing page.
- Keep secrets in `.env` (git-ignored). Never commit it.
