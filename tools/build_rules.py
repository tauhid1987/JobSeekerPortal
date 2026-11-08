"""Builds firebase/database.rules.json = Quiz Arena rules + the JobMatch 'jm' section (nothing of Quiz Arena changes).
Publish the result in Firebase console > Realtime Database > Rules (or `firebase deploy --only database`)."""
import json
from pathlib import Path
F = Path(__file__).resolve().parent.parent / "firebase"
quiz = json.loads((F / "quiz-arena.rules.json").read_text())
jm = json.loads((F / "jm.rules.fragment.json").read_text())
quiz["rules"]["jm"] = {k: v for k, v in jm.items() if k == "members" or k == "requests"}
for k in ("activity", "applications", "applogs"):
    quiz["rules"]["jm"][k] = jm[k]
(F / "database.rules.json").write_text(json.dumps(quiz, indent=2))
print("wrote", F / "database.rules.json", "| top-level:", list(quiz["rules"]))
