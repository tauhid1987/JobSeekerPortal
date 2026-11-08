"""Checks that the Firebase project is set up for JobMatch. Read-only: it signs in as YOUR admin and only reads.
Run:   .venv\\Scripts\\python tools\\verify_firebase.py
It asks for your admin email and password (typed here, not echoed, never saved or sent anywhere except Google).
Use --anon-only to run just the checks that need no login."""
import getpass
import json
import sys
from pathlib import Path
import requests

CFG = json.loads((Path(__file__).resolve().parent.parent / "firebase_config.json").read_text())
DB = CFG["databaseURL"].rstrip("/")
results = []


def check(name, ok, hint=""):
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else f"\n      -> {hint}"))


def get(path, token=None):
    return requests.get(f"{DB}/{path}.json", params={"auth": token} if token else None, timeout=25)


print(f"Project: {CFG['projectId']}\nDatabase: {DB}\n")
r = get(".settings/rules")  # not readable without auth; used only to confirm the database answers
check("Database address is reachable", r.status_code in (200, 401, 403), "Check databaseURL in firebase_config.json (region part).")
check("Anonymous people are locked out of the data", get("").status_code == 401 and get("jm/members").status_code == 401,
      "Rules are open! Publish firebase/database.rules.json now.")

if "--anon-only" in sys.argv:
    sys.exit(0 if all(results) else 1)

email = input("\nAdmin email: ").strip()
password = getpass.getpass("Admin password: ")
r = requests.post("https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword", params={"key": CFG["apiKey"]},
                  json={"email": email, "password": password, "returnSecureToken": True}, timeout=25)
body = r.json()
msg = body.get("error", {}).get("message", "")
check("Email/Password sign-in is turned on and the login works", r.status_code == 200,
      {"OPERATION_NOT_ALLOWED": "Turn on Email/Password in Authentication > Sign-in method.",
       "INVALID_LOGIN_CREDENTIALS": "Wrong email or password, or the user was not created under Authentication > Users."}.get(msg, msg or r.text[:120]))
if r.status_code != 200:
    sys.exit(1)
tok, uid = body["idToken"], body["localId"]
print(f"      your User UID: {uid}")
check("You are listed as an admin (hosts/<your UID> = true)", get(f"hosts/{uid}", tok).json() is True,
      f"In Realtime Database > Data add  hosts > {uid} = true  (boolean true, not the text \"true\").")
for node, what in (("jm/members", "member list"), ("jm/requests", "access requests"), ("jm/activity", "search history"),
                   ("jm/applications", "applications"), ("jm/applogs", "status log")):
    check(f"JobMatch rules published: admin can read {what} ({node})", get(node, tok).status_code == 200,
          "The 'jm' section is missing from the published rules. Paste firebase/database.rules.json into the Rules tab and Publish.")
check("Quiz Arena sections of the rules are present (history)", get("history", tok).status_code == 200,
      "Rules did not publish correctly. Paste firebase/database.rules.json again.")
print("\n" + ("ALL CHECKS PASSED" if all(results) else "SOME CHECKS FAILED: fix the lines marked FAIL, then run this again."))
sys.exit(0 if all(results) else 1)
