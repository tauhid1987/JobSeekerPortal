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

## Put it online (GitHub Pages + a small hosted server)
GitHub Pages can only show static pages, so JobMatch is split in two:

1. **Pages** (`docs/`: sign-in, results, admin) on **GitHub Pages**: repo Settings > Pages > Deploy from a branch > `main` > `/docs`.
   Address: `https://tauhid1987.github.io/JobSeekerPortal/`
2. **Search server** (the Python part) on **Render** (free plan): New > Blueprint > pick this repo; it reads `render.yaml`.
   Optional: add `JOOBLE_KEY` in the Render dashboard. Copy the service address, e.g. `https://jobmatch-api.onrender.com`.
3. Put that address in `docs/firebase-config.js` as `API_BASE`, commit and push.
4. In Firebase: Authentication > Settings > Authorized domains, add `tauhid1987.github.io`.

Nothing about a search is kept on the server: the CV is deleted after reading and the Excel is sent straight back to the browser.
The free Render plan sleeps when idle, so the first search after a quiet period can take about a minute.
`JOBMATCH_ORIGINS` (in `render.yaml`) lists the pages allowed to call the server.
