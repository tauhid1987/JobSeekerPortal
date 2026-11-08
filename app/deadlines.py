"""Find an application deadline in a job description, if the posting states one."""
import re
import datetime as dt

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
KEY = r"(?:deadline|apply\s+(?:by|before|until)|closing\s+date|closes?(?:\s+on)?|last\s+date|applications?\s+(?:close|due)|expires?(?:\s+on)?|due\s+date)"
DATE = (r"(\d{4}-\d{2}-\d{2}|\d{1,2}[/.]\d{1,2}[/.]\d{4}|\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]{3,9},?\s+\d{4}"
        r"|[A-Za-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})")
RX = re.compile(KEY + r"[^0-9A-Za-z]{0,12}(?:\w+\s+){0,3}?" + DATE, re.I)


def _parse(s):
    s = s.strip().replace(",", " ").replace(".", " ") if not re.match(r"\d{1,2}[/.]\d{1,2}[/.]\d{4}", s) else s
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", s)
    if m:
        return dt.date(int(m[1]), int(m[2]), int(m[3]))
    m = re.match(r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})$", s)
    if m:  # day first (Bangladesh / Europe convention)
        return dt.date(int(m[3]), int(m[2]), int(m[1]))
    m = re.match(r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\s+(\d{4})$", s)
    if m and m[2][:3].lower() in MONTHS:
        return dt.date(int(m[3]), MONTHS[m[2][:3].lower()], int(m[1]))
    m = re.match(r"([A-Za-z]{3,9})\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\d{4})$", s)
    if m and m[1][:3].lower() in MONTHS:
        return dt.date(int(m[3]), MONTHS[m[1][:3].lower()], int(m[2]))
    return None


def extract_deadline(text):
    """Return a datetime.date or None."""
    for m in RX.finditer(text or ""):
        try:
            d = _parse(m.group(1))
        except ValueError:
            d = None
        if d:
            return d
    return None
