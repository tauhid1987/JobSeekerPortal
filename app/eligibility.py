"""Can a candidate from <country> realistically apply? Rule-based check of location + visa wording.

Status:  Yes | Check | Visa/relocation | No      (always with a short reason)
It is a screening aid, not a guarantee: 'Check' means read the posting before applying.
"""
import re

# Places a candidate in each country counts as 'ours' (regions that include them)
PROFILES = {
    "bangladesh": ["bangladesh", "dhaka", "south asia", "asia", "apac", "asia pacific", "asia-pacific", "asean"],
    "india": ["india", "south asia", "asia", "apac", "asia pacific", "asia-pacific"],
    "pakistan": ["pakistan", "south asia", "asia", "apac", "asia pacific", "asia-pacific"],
    "sri lanka": ["sri lanka", "south asia", "asia", "apac", "asia pacific", "asia-pacific"],
    "nepal": ["nepal", "south asia", "asia", "apac", "asia pacific", "asia-pacific"],
    "philippines": ["philippines", "southeast asia", "asia", "apac", "asia pacific", "asia-pacific", "asean"],
    "nigeria": ["nigeria", "africa", "emea"],
    "egypt": ["egypt", "africa", "mena", "emea", "middle east"],
}
OPEN = ["worldwide", "anywhere", "global", "any location", "world wide", "international", "all countries", "remote"]
OTHER_PLACES = ["usa", "us", "u.s.", "united states", "america", "americas", "north america", "canada", "uk", "united kingdom",
                "europe", "eu", "european union", "emea", "germany", "france", "netherlands", "spain", "italy", "poland",
                "portugal", "ireland", "austria", "switzerland", "sweden", "norway", "denmark", "finland", "belgium",
                "czechia", "romania", "latam", "latin america", "brazil", "mexico", "argentina", "colombia", "chile",
                "australia", "new zealand", "israel", "uae", "dubai", "singapore", "japan", "south africa", "turkey",
                "ukraine", "estonia", "lithuania", "latvia", "greece", "hungary", "bulgaria", "croatia", "serbia"]
SPONSOR_YES = re.compile(r"visa sponsor|sponsor(?:ship)? (?:is )?(?:available|provided|offered)|we (?:can )?sponsor|"
                         r"relocation (?:assistance|support|package|budget|bonus)|relocat\w+ (?:is )?(?:provided|offered|supported)|"
                         r"blue card|work permit (?:is )?(?:provided|arranged)", re.I)
SPONSOR_NO = re.compile(r"no visa sponsor|(?:unable|not able|cannot|can't|can not|do not|don't|does not|won't|will not) "
                        r"(?:to )?(?:offer |provide )?(?:visa )?sponsor|not (?:offer|provide)\w* (?:visa )?sponsor|"
                        r"without (?:visa )?sponsor|sponsorship (?:is )?not (?:available|offered|provided)", re.I)
WORKAUTH = re.compile(r"(?:authori[sz]ed|authori[sz]ation|eligib\w+|right|permit|legally allowed)\s+to\s+work\s+(?:in|within)|"
                      r"work (?:authori[sz]ation|permit)|citizen(?:ship)?s? (?:of|required)|green card|security clearance|"
                      r"must (?:currently )?(?:live|reside|be (?:located|based|resident))\s+in|"
                      r"(?:based|located|residing|resident)\s+in\s+(?:the\s+)?(?:us|usa|united states|eu|europe|uk|canada)\b", re.I)


def _has(text, term):
    return re.search(r"(?<![a-z])" + re.escape(term) + r"(?![a-z])", text) is not None


def check(job, country="Bangladesh"):
    country = (country or "Bangladesh").strip()
    ours = PROFILES.get(country.lower(), [country.lower()])
    loc = (job.get("location") or "").lower()
    desc = (job.get("description") or "").lower()
    text = f"{loc} {desc}"
    remote = bool(job.get("remote"))
    if (job.get("country") or "").lower() == country.lower():  # listed on a local job board of that country
        if re.search(r"outside " + re.escape(country.lower()) + r"|overseas|abroad", loc):
            return "Check", "Local board but location looks overseas"
        return "Yes", f"Local job in {country}"

    if SPONSOR_NO.search(text) and not remote:
        return "No", "On-site abroad and posting says no visa sponsorship"

    in_ours = [t for t in ours if t != "asia" and _has(loc, t)] or ([t for t in ours if _has(loc, t)])
    is_open = any(_has(loc, t) for t in OPEN if t != "remote") or loc.strip() in ("", "remote", "homeoffice", "home office", "home-office")
    others = [t for t in OTHER_PLACES if _has(loc, t)]

    # 1) explicit regional restriction that excludes us
    if others and not in_ours and not any(_has(loc, t) for t in ("worldwide", "anywhere", "global")):
        return "No", f"Restricted to {', '.join(others[:3]).upper() if len(others[0]) <= 3 else ', '.join(others[:3]).title()}"

    # 2) remote jobs open to us
    if remote and (in_ours or is_open):
        base = f"Open to {country}" if in_ours else "Remote, location open"
        if WORKAUTH.search(text) and not in_ours:
            return "Check", "Remote but mentions work authorization / residency - read the posting"
        if re.search(r"\b(?:utc|gmt)\s*[-+]\s*\d|\b(?:est|pst|cst|cet|eastern|pacific)\b.{0,15}(?:hours|time|overlap)", text):
            return "Check", base + "; needs time-zone overlap"
        return ("Yes", base) if (in_ours or loc.strip() not in ("", "remote", "homeoffice", "home office", "home-office")) else ("Check", "Remote, no location stated - confirm before applying")

    # 3) on-site abroad
    if not remote:
        if SPONSOR_YES.search(text):
            return "Visa/relocation", "On-site abroad; visa sponsorship / relocation mentioned"
        if in_ours:
            return "Yes", f"Located in {country}"
        return "No", "On-site abroad, no visa sponsorship or relocation mentioned"

    # 4) remote but tied to a specific place (city/country) that is not ours
    if SPONSOR_YES.search(text):
        return "Visa/relocation", "Tied to a location abroad; visa / relocation mentioned"
    if re.search(r"work from anywhere|from anywhere|anywhere in the world|worldwide|globally distributed|fully distributed", desc):
        return "Check", f"Based in {job.get('location')} but posting mentions working from anywhere - confirm"
    return "No", f"Remote but tied to {job.get('location') or 'one location'}; no worldwide or relocation wording"
