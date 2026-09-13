"""
build_brief.py  --  render Brief.pdf for the BOOX Go 10.3 from brief.json
Usage:  python3 build_brief.py brief.json Brief.pdf
brief.json: {"date":..., "generated":..., "work": {...}, "personal": {...}}
Each side (all lists optional): weather (str), today/tomorrow [{time,title,loc}],
due [{due,title}], followups/waiting [{who,item,since}], mail [{from,subject}],
proposed [str], stats [str]
"""
import json
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import Color
from reportlab.pdfbase.pdfmetrics import stringWidth

PAGE_W, PAGE_H, MARGIN = 6.2 * inch, 8.27 * inch, 0.32 * inch
CONTENT_W = PAGE_W - 2 * MARGIN
BLACK = Color(0, 0, 0)
GRAY_DOT = Color(0.55, 0.55, 0.55)
GRAY_LINE = Color(0.65, 0.65, 0.65)
GRAY_BOX = Color(0.45, 0.45, 0.45)


def header(c, title, key, subtitle=None):
    c.setFont("Helvetica-Bold", 13); c.setFillColor(BLACK)
    c.drawString(MARGIN, PAGE_H - MARGIN - 0.12 * inch, title)
    if subtitle:
        c.setFont("Helvetica", 8); c.setFillColor(GRAY_BOX)
        c.drawString(MARGIN, PAGE_H - MARGIN - 0.30 * inch, subtitle); c.setFillColor(BLACK)
    c.setStrokeColor(GRAY_LINE); c.setLineWidth(0.7)
    c.line(MARGIN, PAGE_H - MARGIN - 0.40 * inch, PAGE_W - MARGIN, PAGE_H - MARGIN - 0.40 * inch)
    c.bookmarkPage(key)


def nav(c, key, label, x_right):
    w, h = 0.62 * inch, 0.22 * inch
    x1, y1 = x_right - w, PAGE_H - MARGIN - h + 0.06 * inch
    c.setStrokeColor(GRAY_BOX); c.setLineWidth(0.6)
    c.roundRect(x1, y1, w, h, 3, stroke=1, fill=0)
    c.setFont("Helvetica", 7.5); c.setFillColor(GRAY_BOX)
    c.drawCentredString(x1 + w / 2, y1 + 0.06 * inch, label); c.setFillColor(BLACK)
    c.linkAbsolute("", key, (x1, y1, x1 + w, y1 + h))


def label(c, x, y, text, size=8.5):
    c.setFont("Helvetica-Bold", size); c.setFillColor(GRAY_BOX)
    c.drawString(x, y, text); c.setFillColor(BLACK)


def wrap(text, width, font="Helvetica", size=8.5):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if stringWidth(t, font, size) <= width: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines or [""]


def item(c, y, lead, text, x=MARGIN, lead_w=0.55 * inch, size=8.5, check=False):
    if check:
        c.setStrokeColor(BLACK); c.setLineWidth(0.6); c.rect(x, y - 1, 7, 7, stroke=1, fill=0); x += 0.16 * inch
    c.setFont("Helvetica-Bold", size); c.setFillColor(BLACK); c.drawString(x, y, lead)
    c.setFont("Helvetica", size)
    for ln in wrap(text, PAGE_W - MARGIN - (x + lead_w), size=size):
        c.drawString(x + lead_w, y, ln); y -= 0.16 * inch
    return y - 0.04 * inch


def section(c, y, title, rows, fmt, empty="none"):
    label(c, MARGIN, y, title); y -= 0.19 * inch
    if not rows:
        c.setFont("Helvetica-Oblique", 8); c.setFillColor(GRAY_BOX); c.drawString(MARGIN + 0.1 * inch, y, empty)
        c.setFillColor(BLACK); return y - 0.24 * inch
    for r in rows:
        y = fmt(c, y, r)
    return y - 0.06 * inch


def dot_grid(c, y_top, y_bottom, spacing=0.20 * inch):
    c.setStrokeColor(GRAY_DOT); c.setLineWidth(1.1); c.setLineCap(1); c.setDash([0.1, spacing - 0.1])
    y = y_top
    while y >= y_bottom:
        c.line(MARGIN, y, PAGE_W - MARGIN, y); y -= spacing
    c.setDash([]); c.setLineCap(0); c.setStrokeColor(BLACK)


def page(c, side, d, other_key, other_label):
    TOP = PAGE_H - MARGIN - 0.62 * inch
    header(c, side.upper(), side.lower(), subtitle=d.get("date", ""))
    nav(c, other_key, other_label, PAGE_W - MARGIN)
    y = TOP
    if d.get("weather"):
        label(c, MARGIN, y, "Pass weather")
        c.setFont("Helvetica", 8.5)
        for ln in wrap(d["weather"], CONTENT_W - 1.1 * inch): c.drawString(MARGIN + 1.0 * inch, y, ln); y -= 0.16 * inch
        y -= 0.10 * inch
    ev = lambda c, y, r: item(c, y, r.get("time", ""), r.get("title", "") + (f"   ({r['loc']})" if r.get("loc") else ""))
    y = section(c, y, "Today", d.get("today", []), ev, empty="open day")
    y = section(c, y, "Tomorrow", d.get("tomorrow", []), ev, empty="nothing scheduled")
    due = lambda c, y, r: item(c, y, r.get("due", ""), r.get("title", ""), check=True)
    y = section(c, y, "Due soon", d.get("due", []), due)
    fu = lambda c, y, r: item(c, y, r.get("who", ""), r.get("item", "") + (f"  (since {r['since']})" if r.get("since") else ""), lead_w=0.65 * inch, check=True)
    y = section(c, y, "Follow-ups", d.get("followups", []), fu)
    y = section(c, y, "Waiting on", d.get("waiting", []), fu)
    mail = lambda c, y, r: item(c, y, r.get("from", ""), r.get("subject", ""), lead_w=0.75 * inch, check=True)
    y = section(c, y, "Mail needing a reply", d.get("mail", []), mail)
    fn = lambda c, y, r: item(c, y, "", r, lead_w=0.05 * inch)
    y = section(c, y, "Proposed from your log (staging: not yet in Asana)", d.get("proposed", []), fn, empty="nothing new")
    for line in d.get("stats", []):
        for ln in wrap(line, CONTENT_W, font="Helvetica-Bold", size=8.5):
            label(c, MARGIN, y, ln); y -= 0.16 * inch
        y -= 0.04 * inch
    y -= 0.05 * inch
    c.setStrokeColor(GRAY_LINE); c.setLineWidth(0.7); c.line(MARGIN, y, PAGE_W - MARGIN, y)
    label(c, MARGIN, y - 0.18 * inch, "Intake  (weather, meeting notes, anything; tags get read next run)")
    dot_grid(c, y - 0.40 * inch, 0.35 * inch)
    c.showPage()


def build(data, out):
    c = canvas.Canvas(out, pagesize=(PAGE_W, PAGE_H), pageCompression=1)
    c.setTitle("Brief - " + data.get("date", ""))
    for side in ("work", "personal"):
        d = dict(data.get(side, {})); d["date"] = data.get("date", "") + "   generated " + data.get("generated", "") + (f"   Daily Log p{data['log_page']}" if data.get("log_page") else "")
        page(c, side, d, "personal" if side == "work" else "work", "Personal" if side == "work" else "Work")
    c.save()


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    with open(src) as f:
        build(json.load(f), out)
    print("wrote", out)
