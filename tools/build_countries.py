"""Builds docs/countries.json: every country, the regions that count as 'ours' for eligibility, and local job portals.
Run:  .venv\\Scripts\\python tools\\build_countries.py   (the site and the server both read the JSON)."""
import json
from pathlib import Path

REGIONS = {  # subregion -> (terms that count as 'ours', countries)
    "south asia": (["south asia", "asia", "apac", "asia pacific", "asia-pacific"],
                   ["Bangladesh", "India", "Pakistan", "Sri Lanka", "Nepal", "Bhutan", "Maldives", "Afghanistan"]),
    "southeast asia": (["southeast asia", "south east asia", "asia", "apac", "asia pacific", "asia-pacific", "asean"],
                       ["Indonesia", "Malaysia", "Philippines", "Singapore", "Thailand", "Vietnam", "Myanmar", "Cambodia",
                        "Laos", "Brunei", "Timor-Leste"]),
    "east asia": (["east asia", "asia", "apac", "asia pacific", "asia-pacific"],
                  ["China", "Japan", "South Korea", "Taiwan", "Hong Kong", "Mongolia", "North Korea"]),
    "central asia": (["central asia", "asia"], ["Kazakhstan", "Uzbekistan", "Kyrgyzstan", "Tajikistan", "Turkmenistan"]),
    "middle east": (["middle east", "mena", "emea", "gulf", "gcc", "asia"],
                    ["United Arab Emirates", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman", "Jordan", "Lebanon", "Iraq",
                     "Iran", "Israel", "Syria", "Yemen", "Turkey", "Palestine"]),
    "north africa": (["north africa", "mena", "africa", "emea", "middle east"],
                     ["Egypt", "Morocco", "Algeria", "Tunisia", "Libya", "Sudan"]),
    "sub-saharan africa": (["sub-saharan africa", "africa", "emea"],
                           ["Nigeria", "Kenya", "Ghana", "South Africa", "Ethiopia", "Tanzania", "Uganda", "Rwanda", "Senegal",
                            "Cameroon", "Zambia", "Zimbabwe", "Botswana", "Namibia", "Mozambique", "Angola", "Ivory Coast",
                            "Mauritius", "Malawi", "Somalia", "DR Congo", "Madagascar", "Mali", "Niger", "Chad"]),
    "western europe": (["western europe", "europe", "emea", "eu"],
                       ["United Kingdom", "Ireland", "France", "Germany", "Netherlands", "Belgium", "Luxembourg", "Switzerland",
                        "Austria", "Spain", "Portugal", "Italy", "Greece", "Malta", "Cyprus"]),
    "northern europe": (["northern europe", "nordics", "europe", "emea", "eu"],
                        ["Sweden", "Norway", "Denmark", "Finland", "Iceland", "Estonia", "Latvia", "Lithuania"]),
    "eastern europe": (["eastern europe", "cee", "europe", "emea"],
                       ["Poland", "Czechia", "Slovakia", "Hungary", "Romania", "Bulgaria", "Croatia", "Serbia", "Slovenia",
                        "Ukraine", "Belarus", "Moldova", "Bosnia and Herzegovina", "Albania", "North Macedonia", "Montenegro",
                        "Georgia", "Armenia", "Azerbaijan", "Russia"]),
    "north america": (["north america", "americas"], ["United States", "Canada", "Mexico"]),
    "central america & caribbean": (["latam", "latin america", "americas"],
                                   ["Guatemala", "Costa Rica", "Panama", "Honduras", "El Salvador", "Nicaragua", "Cuba",
                                    "Dominican Republic", "Jamaica", "Trinidad and Tobago", "Haiti", "Bahamas"]),
    "south america": (["south america", "latam", "latin america", "americas"],
                      ["Brazil", "Argentina", "Colombia", "Chile", "Peru", "Venezuela", "Ecuador", "Bolivia", "Uruguay",
                       "Paraguay"]),
    "oceania": (["oceania", "apac", "asia pacific", "asia-pacific", "anz"],
                ["Australia", "New Zealand", "Fiji", "Papua New Guinea"]),
}
# Local job portals (home pages only; the user opens them in their own browser).
PORTALS = {
    "Bangladesh": [("BDJobs", "https://bdjobs.com"), ("Skill.Jobs", "https://skill.jobs"), ("Chakri.com", "https://www.chakri.com")],
    "India": [("Naukri", "https://www.naukri.com"), ("Foundit", "https://www.foundit.in"), ("Shine", "https://www.shine.com")],
    "Pakistan": [("Rozee.pk", "https://www.rozee.pk"), ("Mustakbil", "https://www.mustakbil.com")],
    "Sri Lanka": [("TopJobs", "https://www.topjobs.lk"), ("Xpress Jobs", "https://www.xpress.jobs")],
    "Nepal": [("Merojob", "https://merojob.com"), ("Kumari Job", "https://www.kumarijob.com")],
    "Malaysia": [("JobStreet", "https://www.jobstreet.com.my"), ("Hiredly", "https://my.hiredly.com")],
    "Singapore": [("MyCareersFuture", "https://www.mycareersfuture.gov.sg"), ("JobStreet", "https://www.jobstreet.com.sg")],
    "Philippines": [("JobStreet", "https://www.jobstreet.com.ph"), ("Kalibrr", "https://www.kalibrr.com")],
    "Indonesia": [("JobStreet", "https://www.jobstreet.co.id"), ("Glints", "https://glints.com/id")],
    "Thailand": [("JobsDB", "https://th.jobsdb.com"), ("JobThai", "https://www.jobthai.com")],
    "Vietnam": [("VietnamWorks", "https://www.vietnamworks.com"), ("TopCV", "https://www.topcv.vn")],
    "Japan": [("GaijinPot Jobs", "https://jobs.gaijinpot.com"), ("Daijob", "https://www.daijob.com")],
    "South Korea": [("Saramin", "https://www.saramin.co.kr"), ("JobKorea", "https://www.jobkorea.co.kr")],
    "United Arab Emirates": [("Bayt", "https://www.bayt.com"), ("GulfTalent", "https://www.gulftalent.com"), ("Naukrigulf", "https://www.naukrigulf.com")],
    "Saudi Arabia": [("Bayt", "https://www.bayt.com"), ("Naukrigulf", "https://www.naukrigulf.com"), ("GulfTalent", "https://www.gulftalent.com")],
    "Qatar": [("Bayt", "https://www.bayt.com"), ("GulfTalent", "https://www.gulftalent.com")],
    "Egypt": [("Wuzzuf", "https://wuzzuf.net"), ("Bayt", "https://www.bayt.com")],
    "Turkey": [("Kariyer.net", "https://www.kariyer.net"), ("Secretcv", "https://www.secretcv.com")],
    "Nigeria": [("Jobberman", "https://www.jobberman.com"), ("MyJobMag", "https://www.myjobmag.com")],
    "Kenya": [("BrighterMonday", "https://www.brightermonday.co.ke"), ("MyJobMag Kenya", "https://www.myjobmag.co.ke")],
    "Ghana": [("Jobberman Ghana", "https://www.jobberman.com.gh"), ("MyJobMag Ghana", "https://www.myjobmag.com.gh")],
    "South Africa": [("PNet", "https://www.pnet.co.za"), ("CareerJunction", "https://www.careerjunction.co.za")],
    "Morocco": [("Rekrute", "https://www.rekrute.com"), ("Emploi.ma", "https://www.emploi.ma")],
    "United Kingdom": [("Reed", "https://www.reed.co.uk"), ("Totaljobs", "https://www.totaljobs.com"), ("CV-Library", "https://www.cv-library.co.uk"), ("Civil Service Jobs", "https://www.civilservicejobs.service.gov.uk")],
    "Ireland": [("IrishJobs", "https://www.irishjobs.ie"), ("Jobs.ie", "https://www.jobs.ie")],
    "Germany": [("StepStone", "https://www.stepstone.de"), ("Xing Jobs", "https://www.xing.com/jobs"), ("Arbeitsagentur", "https://www.arbeitsagentur.de/jobsuche")],
    "France": [("Welcome to the Jungle", "https://www.welcometothejungle.com"), ("France Travail", "https://www.francetravail.fr")],
    "Netherlands": [("Nationale Vacaturebank", "https://www.nationalevacaturebank.nl"), ("Werk.nl", "https://www.werk.nl")],
    "Belgium": [("VDAB", "https://www.vdab.be"), ("Le Forem", "https://www.leforem.be")],
    "Switzerland": [("Jobs.ch", "https://www.jobs.ch"), ("JobScout24", "https://www.jobscout24.ch")],
    "Austria": [("Karriere.at", "https://www.karriere.at"), ("AMS eJob-Room", "https://jobroom.ams.or.at")],
    "Spain": [("InfoJobs", "https://www.infojobs.net"), ("Tecnoempleo", "https://www.tecnoempleo.com")],
    "Portugal": [("Net-Empregos", "https://www.net-empregos.com"), ("Sapo Emprego", "https://emprego.sapo.pt")],
    "Italy": [("InfoJobs.it", "https://www.infojobs.it")],
    "Sweden": [("Platsbanken", "https://arbetsformedlingen.se/platsbanken"), ("Jobbsafari", "https://www.jobbsafari.se")],
    "Norway": [("Finn.no Jobb", "https://www.finn.no/job"), ("NAV Arbeidsplassen", "https://arbeidsplassen.nav.no")],
    "Denmark": [("Jobindex", "https://www.jobindex.dk"), ("Jobnet", "https://job.jobnet.dk")],
    "Finland": [("Tyomarkkinatori", "https://tyomarkkinatori.fi"), ("Duunitori", "https://duunitori.fi")],
    "Poland": [("Pracuj.pl", "https://www.pracuj.pl"), ("No Fluff Jobs", "https://nofluffjobs.com"), ("Just Join IT", "https://justjoin.it")],
    "Czechia": [("Jobs.cz", "https://www.jobs.cz"), ("Prace.cz", "https://www.prace.cz")],
    "Romania": [("eJobs", "https://www.ejobs.ro"), ("BestJobs", "https://www.bestjobs.eu")],
    "Ukraine": [("Work.ua", "https://www.work.ua"), ("DOU Jobs", "https://jobs.dou.ua")],
    "United States": [("USAJobs", "https://www.usajobs.gov"), ("Dice", "https://www.dice.com"), ("Built In", "https://builtin.com/jobs"), ("Wellfound", "https://wellfound.com/jobs")],
    "Canada": [("Job Bank", "https://www.jobbank.gc.ca"), ("Workopolis", "https://www.workopolis.com")],
    "Mexico": [("OCC Mundial", "https://www.occ.com.mx"), ("Computrabajo", "https://www.computrabajo.com.mx")],
    "Brazil": [("Vagas.com.br", "https://www.vagas.com.br"), ("Catho", "https://www.catho.com.br"), ("Gupy", "https://portal.gupy.io")],
    "Argentina": [("Zonajobs", "https://www.zonajobs.com.ar"), ("Computrabajo", "https://www.computrabajo.com.ar")],
    "Colombia": [("Computrabajo", "https://www.computrabajo.com.co"), ("elempleo", "https://www.elempleo.com")],
    "Chile": [("Trabajando.com", "https://www.trabajando.cl"), ("Laborum", "https://www.laborum.cl")],
    "Peru": [("Bumeran", "https://www.bumeran.com.pe"), ("Computrabajo", "https://www.computrabajo.com.pe")],
    "Australia": [("SEEK", "https://www.seek.com.au"), ("Jora", "https://au.jora.com")],
    "New Zealand": [("SEEK NZ", "https://www.seek.co.nz"), ("Trade Me Jobs", "https://www.trademe.co.nz/a/jobs")],
}


ALIASES = {"United States": ["usa", "us", "u.s.", "america"], "United Kingdom": ["uk", "great britain", "england", "scotland", "wales"],
           "United Arab Emirates": ["uae", "dubai", "abu dhabi"], "South Korea": ["korea"], "Czechia": ["czech republic"],
           "Netherlands": ["holland"], "Turkey": ["turkiye"], "Ivory Coast": ["cote d'ivoire"], "DR Congo": ["congo"]}


def build():
    out = []
    for sub, (terms, names) in REGIONS.items():
        for n in names:
            out.append({"name": n, "region": sub, "terms": [n.lower()] + ALIASES.get(n, []) + terms,
                        "portals": [{"name": a, "url": b} for a, b in PORTALS.get(n, [])]})
    out.sort(key=lambda c: c["name"])
    return out


if __name__ == "__main__":
    data = build()
    unknown = set(PORTALS) - {c["name"] for c in data}
    assert not unknown, f"portal list for unknown countries: {unknown}"
    Path(__file__).resolve().parent.parent.joinpath("docs", "countries.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(data), "countries,", sum(1 for c in data if c["portals"]), "with local portals")
