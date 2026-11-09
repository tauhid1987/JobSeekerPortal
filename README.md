# JobSeekerPortal (JobMatch)

Upload a CV, search job sources, and get a ranked Excel list of jobs you can apply for.

## Run
Double-click `JobMatch.cmd` (first run creates `.venv` and installs `requirements.txt`; then sign in at http://127.0.0.1:5000), or:

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

## Sign-in, control and tracking (Firebase, same project as Quiz Arena)
JobMatch looks like Quiz Arena and uses the same Firebase project, sign-in and approved-admin list.

- **Members** open the page, choose "I need an account", and wait. An **admin** approves or blocks them on `/admin`.
  Blocking takes effect at once (search, download and tracking all stop).
- **Admins** are the people listed under `hosts` in the Firebase database (the same list as Quiz Arena hosts).
- **Every search is saved** (who, when, titles, country, how many jobs found/listed) by the server, using server time.
  Members cannot edit or delete history.
- **Applications**: for each job a member can press "Open & mark applied" or "Save for later", then move it through
  Saved / Applied / Interview / Offer / Rejected, with notes. Applications can't be deleted, `createdAt` is fixed,
  and every status change is added to an append-only log (`jm/applogs`).
- **Admin page** (`/admin`): People (approve/block), Who used it (all searches, CSV), Applications (all, filter by person/status, CSV).
- CVs are read and deleted straight away; only the search summary and application records are stored.

### One-time setup on the real Firebase project
1. Run `python tools/build_rules.py`. It writes `firebase/database.rules.json` = the Quiz Arena rules **plus** a new `jm` section.
   Quiz Arena's own rules are unchanged (a test checks this).
2. In Firebase console > Realtime Database > Rules, paste that file and publish. *(Do this before using it for real: until then, tracking is refused by the database.)*
3. Your admin account must already be under `hosts` (it is, if you host Quiz Arena). Add other admins the same way.
4. Authentication > Settings > Authorized domains: add the address people will use, if it is not `localhost`.
5. `firebase_config.json` holds the project's public web config (same values as Quiz Arena's `firebase-config.js`).

### Testing without touching the real project
```
npm install
npm run test:rules      # 10 security-rule tests on the local emulator (needs Java)
npm run dev             # emulators; then run the server with the emulator variables set:
#   FIREBASE_AUTH_EMULATOR_HOST=127.0.0.1:9099 FIREBASE_DATABASE_EMULATOR_HOST=127.0.0.1:9000 python -m app.server
```
### Sharing on a network
Default is `127.0.0.1` (this PC only). To let colleagues reach it set `JOBMATCH_HOST=0.0.0.0` and `JOBMATCH_PORT`;
only signed-in, approved members can use it. Use HTTPS in front of it beyond a trusted office network.

## Job sources

| Source | Kind | Covers | Key needed |
|---|---|---|---|
| Remotive | remote feed | worldwide remote | no |
| RemoteOK | remote feed | worldwide remote | no |
| We Work Remotely | remote feed (RSS) | worldwide remote | no |
| Working Nomads | remote feed | worldwide remote | no |
| Himalayas | remote API | worldwide remote | no |
| Jobicy | remote API | worldwide remote | no |
| Arbeitnow | feed | Germany and Europe (on-site and remote) | no |
| BDJobs | local board | Bangladesh (newest ~50 jobs) | no |
| Skill.Jobs | local board | Bangladesh | no |
| Jooble | local, many countries | about 70 countries | `JOOBLE_KEY` (free) |
| Adzuna | local, 19 countries | UK, US, AU, CA, DE, FR, IN, IT, NL, NZ, PL, SG, ZA, BR, AT, BE, CH, MX, ES | `ADZUNA_ID` + `ADZUNA_KEY` (free) |

LinkedIn is not searched automatically (its terms forbid collecting its jobs). Each results page gives one-click LinkedIn and Google Jobs
searches for every title, plus local job sites for the chosen country (`docs/countries.json`, built by `tools/build_countries.py`).
Choose "Local", "Remote" or "Local + remote" per search. Add the keys as environment variables on the host (Render) to switch on Jooble / Adzuna.

## Put it online (GitHub Pages + a small hosted server)
GitHub Pages can only show static pages, so JobMatch is split in two:

1. **Pages** (`docs/`: sign-in, results, admin) on **GitHub Pages**: repo Settings > Pages > Deploy from a branch > `main` > `/docs`.
   Address: `https://tauhid1987.github.io/JobSeekerPortal/`
2. **Search server** (the Python part) on **Render** (free plan): New > Blueprint > pick this repo; it reads `render.yaml`.
   Optional: add `JOOBLE_KEY` in the Render dashboard. Copy the service address, e.g. `https://jobmatch-api.onrender.com`.
3. Put that address in `docs/firebase-config.js` as `API_BASE`, commit and push.
4. In Firebase: Authentication > Settings > Authorized domains, add `tauhid1987.github.io`.

Nothing about a search is kept on the server: the CV is deleted after reading and the Excel is sent straight back to the browser.
### Approval emails and email checks

- **Sign-up check:** the form rejects addresses that are not `name@domain.tld`, and suggests the right domain for common typos (`gmial.com` -> `gmail.com`). The database rules enforce the same format, so the check cannot be skipped. It cannot prove the mailbox exists.
- **Approval email:** when an admin presses **Approve**, the search server emails the person a link to sign in. The address is read from the database, not from the browser. Admin > Members has **Resend email**.
- **Turn it on (free Render):** Render's free plan blocks the SMTP ports, so use Brevo's web API. In Brevo create an API key (SMTP & API > API Keys), verify a sender (Senders), then set `BREVO_API_KEY` and `MAIL_FROM` (the verified sender) in the Render dashboard > Environment.
- **Or by SMTP** (paid Render plan, or your own PC): add `SMTP_HOST`, `SMTP_USER` and `SMTP_PASSWORD` (and optionally `SMTP_PORT`, `MAIL_FROM`, `SITE_URL`) in the Render dashboard > Environment. For Gmail use `smtp.gmail.com`, port 587 and an App Password. Without them, approving still works and the admin page says "no email was sent: Email is not set up on the server".
- **Publish the rules:** run `python tools/build_rules.py`, then publish `firebase/database.rules.json` (Firebase console > Realtime Database > Rules, or `firebase deploy --only database`).

The free Render plan sleeps when idle, so the first search after a quiet period can take about a minute.
`JOBMATCH_ORIGINS` (in `render.yaml`) lists the pages allowed to call the server.
