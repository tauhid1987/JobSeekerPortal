import re
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

HEAD = ["Sl No.", "Job Title", "Company", "Source", "Match %", "Can Apply?", "Salary", "Posted", "Deadline", "How to Apply", "Type", "Others"]
WIDTH = [8, 36, 26, 16, 12, 30, 20, 13, 16, 52, 16, 70]

# Opaque ARGB colours ("FF" prefix) so every Excel version paints them
NAVY, WHITE, BAND, TEXT, LINK = "FF1F3864", "FFFFFFFF", "FFEAF1FB", "FF1F1F1F", "FF0563C1"
GREEN, AMBER, RED = "FFC6EFCE", "FFFFEB9C", "FFFFC7CE"
GREEN_T, AMBER_T, RED_T = "FF006100", "FF9C5700", "FF9C0006"


def _fill(rgb):
    return PatternFill(fill_type="solid", start_color=rgb, end_color=rgb)


def _elig_text(j):
    return (j.get("eligible", "") + "\n" + j.get("eligible_why", "")).strip() or "Not checked"


def _deadline_text(j):
    d = j.get("deadline")
    if not d:
        return "Not listed"
    n = j["days_left"]
    return d.strftime("%Y-%m-%d") + "\n(" + ("today" if n == 0 else str(n) + " days left") + ")"


def export(jobs, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Job Search List"
    ws.sheet_view.showGridLines = False
    ws.append(HEAD)
    for i, j in enumerate(jobs, 1):
        others = [f"Location: {j['location']}" if j["location"] else "",
                  f"Matched skills: {', '.join(j['matched'])}" if j["matched"] else "",
                  f"Gaps: {', '.join(j['missing'])}" if j["missing"] else ""]
        emails = sorted(set(re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", j.get("description", ""))))
        how = j["apply_url"] + "".join("\nEmail: " + e for e in emails[:2])
        ws.append([i, j["title"], j["company"], j["source"], j["score"], _elig_text(j), j["salary"] or "Not listed",
                   j["posted"] or "Not listed", _deadline_text(j), how,
                   j["type"] or ("Remote" if j["remote"] else "Not listed"), "\n".join(x for x in others if x)])

    thin = Side(style="thin", color="FFD0D7E2")
    border = Border(top=thin, bottom=thin, left=thin, right=thin)

    # header
    ws.row_dimensions[1].height = 30
    for c in ws[1]:
        c.font = Font(name="Calibri", size=12, bold=True, color=WHITE)
        c.fill = _fill(NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border

    # body
    for r in range(2, ws.max_row + 1):
        band = _fill(BAND) if r % 2 == 0 else _fill(WHITE)
        for c in ws[r]:
            c.fill = band
            c.border = border
            c.font = Font(name="Calibri", size=11, color=TEXT)
            c.alignment = Alignment(wrap_text=True, vertical="center",
                                    horizontal="center" if c.column in (1, 4, 5, 8, 9, 11) else "left")
        ws.cell(r, 2).font = Font(name="Calibri", size=11, bold=True, color=NAVY)
        ws.cell(r, 4).font = Font(name="Calibri", size=11, bold=True, color="FF595959")
        link = ws.cell(r, 10)
        link.hyperlink = jobs[r - 2]["apply_url"]
        link.font = Font(name="Calibri", size=11, underline="single", color=LINK)
        m = ws.cell(r, 5)
        m.number_format = '0.0"%"'
        v = m.value
        bg, fg = (GREEN, GREEN_T) if v >= 60 else (AMBER, AMBER_T) if v >= 40 else (RED, RED_T)
        m.fill = _fill(bg)
        m.font = Font(name="Calibri", size=11, bold=True, color=fg)
        el = ws.cell(r, 6)
        st = jobs[r - 2].get("eligible", "")
        bg, fg = {"Yes": (GREEN, GREEN_T), "Check": (AMBER, AMBER_T), "Visa/relocation": ("FFDDEBF7", "FF1F4E78"),
                  "No": (RED, RED_T)}.get(st, (WHITE, TEXT))
        el.fill, el.font = _fill(bg), Font(name="Calibri", size=11, bold=True, color=fg)
        el.alignment = Alignment(wrap_text=True, vertical="center", horizontal="left")
        dl = ws.cell(r, 9)
        n = jobs[r - 2].get("days_left")
        if n is not None:
            bg, fg = (RED, RED_T) if n <= 3 else (AMBER, AMBER_T) if n <= 7 else (GREEN, GREEN_T)
            dl.fill, dl.font = _fill(bg), Font(name="Calibri", size=11, bold=True, color=fg)
        ws.row_dimensions[r].height = max(34, 16 * ((ws.cell(r, 12).value or "").count("\n") + 1))

    for i, w in enumerate(WIDTH):
        ws.column_dimensions[chr(65 + i)].width = w
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:L{ws.max_row}"
    ws.sheet_properties.tabColor = "1F3864"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToHeight = 0
    wb.save(path)
    _force_apply_flags(path)


def _force_apply_flags(path):
    """openpyxl omits applyFill/applyFont/applyBorder; some Excel builds (and Protected View)
    then ignore fills and borders. Add the flags to every cell format."""
    import zipfile, shutil, re, os
    tmp = str(path) + ".tmp"
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "xl/styles.xml":
                s = data.decode("utf-8")
                a, b = s.index("<cellXfs"), s.index("</cellXfs>")
                block = re.sub(r"<xf (?![^>]*applyFill)", '<xf applyFill="1" applyFont="1" applyBorder="1" applyNumberFormat="1" ', s[a:b])
                data = (s[:a] + block + s[b:]).encode("utf-8")
            zout.writestr(item, data)
    shutil.move(tmp, path)
