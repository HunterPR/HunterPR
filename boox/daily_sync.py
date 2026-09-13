"""
daily_sync.py: stamp the day's brief onto a Daily Log page of the live Journal (typed overlay, never redrawn).
    python3 daily_sync.py Journal.pdf brief.json ripple_state.json [--date YYYY-MM-DD]
Rules:
  - One Daily Log page per day, chosen from the month's DAILY LOG range in <journal>_manifest.json,
    skipping the "carried over" page and any page already assigned in ripple_state["daily_pages"].
  - A day already stamped is left alone (prints its page); if its page is still blank (the Journal in
    Drive was never replaced) the block is stamped there. Ink on the page is never touched.
  - The block is typed at the top of the page under the header: date, today's events, tomorrow's
    first events, due items with checkboxes. Everything below stays free for the rapid log.
Writes the page number (1-based) into brief.json as "log_page" so build_brief.py can show it.
"""
import io, json, os, sys, datetime
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth

PAGE_W, PAGE_H, MARGIN = 6.2 * inch, 8.27 * inch, 0.32 * inch
TOP = PAGE_H - 0.62 * inch
LINE = 0.19 * inch
LEAD_W = 0.62 * inch
MAX_LINES = 9
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def log_ranges(manifest):
    secs = sorted((s["page"], s["title"]) for s in manifest["sections"] if s["title"].startswith("DAILY LOG"))
    out = {}
    for i, (p, title) in enumerate(secs):
        end = secs[i + 1][0] - 1 if i + 1 < len(secs) else p + 39
        out[title.split(":", 1)[1].strip()] = (p, end)
    return out


def pick_page(ranges, state, day):
    rng = ranges.get(MONTHS[day.month - 1])
    if not rng:
        sys.exit(f"no DAILY LOG section for {MONTHS[day.month - 1]} in the manifest")
    used = set(state.setdefault("daily_pages", {}).values())
    for p in range(rng[0] + 1, rng[1] + 1):  # rng[0] is the carried-over page
        if p not in used:
            return p
    sys.exit(f"{MONTHS[day.month - 1]} Daily Log is out of pages; add sheets with journal_edit.py")


def wrap(text, width, font, size):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if stringWidth(t, font, size) <= width: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines or [""]


def block_lines(brief, day):
    """(kind, lead, text) rows: kind is 'event' or 'due'."""
    rows, seen = [], set()
    w, p = brief.get("work", {}), brief.get("personal", {})
    tmrw = (day + datetime.timedelta(days=1)).strftime("%a")

    def key(r): return (r.get("time"), str(r.get("title", ""))[:40].lower())

    today = w.get("today", []) + p.get("today", [])
    for r in today:
        if key(r) in seen: continue
        seen.add(key(r)); rows.append(("event", r.get("time", ""), r.get("title", "") + (f" ({r['loc']})" if r.get("loc") else "")))
    if not today: rows.append(("event", "", "open day"))
    for r in (w.get("tomorrow", []) + p.get("tomorrow", []))[:2]:
        if key(r) in seen: continue
        seen.add(key(r)); rows.append(("event", f"{tmrw} {r.get('time', '')}".strip(), r.get("title", "")))
    for r in (w.get("due", []) + p.get("due", []))[:4]:
        rows.append(("due", r.get("due", ""), r.get("title", "")))
    return rows[:MAX_LINES]


def overlay(rows, date_label):
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    y = TOP
    c.setFont("Helvetica-Bold", 10); c.drawString(MARGIN, y, date_label); y -= LINE * 1.15
    c.setLineWidth(0.6)
    for kind, lead, text in rows:
        x = MARGIN + 0.05 * inch
        if kind == "due":
            c.rect(x, y - 1, 7, 7, stroke=1, fill=0); lead = "due " + lead
        else:
            c.circle(x + 3.5, y + 2.5, 3.2, stroke=1, fill=0)
        x += 0.16 * inch
        c.setFont("Helvetica", 8.5)
        if lead: c.drawString(x, y, lead); x += LEAD_W
        for ln in wrap(text, PAGE_W - MARGIN - x, "Helvetica", 8.5):
            c.drawString(x, y, ln); y -= LINE
    c.setStrokeColorRGB(0.65, 0.65, 0.65); c.setLineWidth(0.5); c.line(MARGIN, y + 0.06 * inch, PAGE_W - MARGIN, y + 0.06 * inch)
    c.showPage(); c.save(); buf.seek(0)
    return PdfReader(buf).pages[0]


def main():
    args = sys.argv[1:]
    day = datetime.date.today()
    if "--date" in args:
        i = args.index("--date"); day = datetime.date.fromisoformat(args[i + 1]); del args[i:i + 2]
    pdf, brief_path, state_path = args
    brief, state = json.load(open(brief_path)), json.load(open(state_path))
    manifest = json.load(open(os.path.splitext(pdf)[0] + "_manifest.json"))
    key, date_label = day.isoformat(), day.strftime("%a %d %b %Y").upper()
    w = PdfWriter(clone_from=pdf)
    p = state.get("daily_pages", {}).get(key)
    if p is not None and date_label in (w.pages[p].extract_text() or ""):
        print(f"{key} already stamped on page {p + 1}, left alone")
        brief["log_page"] = p + 1; json.dump(brief, open(brief_path, "w"), indent=1); return
    if p is None: p = pick_page(log_ranges(manifest), state, day)
    rows = block_lines(brief, day)
    w.pages[p].merge_page(overlay(rows, date_label))
    with open(pdf, "wb") as f: w.write(f)
    state["daily_pages"][key] = p
    json.dump(state, open(state_path, "w"), indent=1)
    brief["log_page"] = p + 1; json.dump(brief, open(brief_path, "w"), indent=1)
    print(f"stamped {key} on Daily Log page {p + 1} ({len(rows)} rows); wrote {pdf}")


if __name__ == "__main__": main()
