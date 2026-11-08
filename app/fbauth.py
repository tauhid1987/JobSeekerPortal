"""Firebase sign-in checks for the Flask backend (no service-account secret needed).

- The browser signs in with Firebase Auth and sends its ID token as  Authorization: Bearer <token>.
- We verify the token against Google's public keys, then talk to the Realtime Database REST API
  *as that user* (?auth=<token>), so the same security rules that protect the browser also protect the server.
- When FIREBASE_AUTH_EMULATOR_HOST is set (local testing only) tokens are unsigned, as Firebase documents,
  and only their claims are read.
"""
import base64
import json
import os
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
EMULATOR = bool(os.getenv("FIREBASE_AUTH_EMULATOR_HOST"))


def config():
    if EMULATOR:
        db = os.getenv("FIREBASE_DATABASE_EMULATOR_HOST", "127.0.0.1:9000")
        return {"projectId": "demo-jobmatch", "dbUrl": f"http://{db}", "ns": "demo-jobmatch-default-rtdb",
                "apiKey": "demo-key", "authDomain": "demo-jobmatch.firebaseapp.com",
                "databaseURL": "https://demo-jobmatch-default-rtdb.firebaseio.com", "appId": "demo-app"}
    c = json.loads((ROOT / "firebase_config.json").read_text())
    c.update(dbUrl=c["databaseURL"].rstrip("/"), ns=None)
    return c


class AuthError(Exception):
    pass


def verify_token(token):
    """Returns (uid, claims) or raises AuthError."""
    if not token:
        raise AuthError("Please sign in.")
    cfg = config()
    try:
        if EMULATOR:
            payload = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=" * (-len(token.split(".")[1]) % 4)))
            if payload.get("aud") != cfg["projectId"] or payload.get("exp", 0) < time.time():
                raise ValueError("bad claims")
            claims = payload
        else:
            from google.oauth2 import id_token
            from google.auth.transport import requests as grequests
            claims = id_token.verify_firebase_token(token, grequests.Request(), audience=cfg["projectId"])
    except Exception as e:
        raise AuthError("Your sign-in expired. Please sign in again.") from e
    uid = claims.get("user_id") or claims.get("sub")
    if not uid or claims.get("firebase", {}).get("sign_in_provider") == "anonymous":
        raise AuthError("Please sign in with your email.")
    return uid, claims


def _url(path, token):
    cfg = config()
    q = {"auth": token}
    if cfg.get("ns"):
        q["ns"] = cfg["ns"]
    return f"{cfg['dbUrl']}/{path}.json", q


def db_get(path, token):
    url, q = _url(path, token)
    r = requests.get(url, params=q, timeout=20)
    if r.status_code in (401, 403):
        return None  # rules said no
    r.raise_for_status()
    return r.json()


def db_post(path, data, token):
    url, q = _url(path, token)
    r = requests.post(url, params=q, json=data, timeout=20)
    r.raise_for_status()
    return r.json()


def status(uid, token):
    """'admin' | 'member' | 'blocked' | 'pending' | 'none'"""
    if db_get(f"hosts/{uid}", token) is True:
        return "admin"
    m = db_get(f"jm/members/{uid}", token)
    if m:
        return "member" if m.get("active") is True else "blocked"
    return "pending" if db_get(f"jm/requests/{uid}", token) else "none"


def log_activity(uid, token, **fields):
    data = {"at": {".sv": "timestamp"}}
    data.update(fields)
    return db_post(f"jm/activity/{uid}", data, token)
