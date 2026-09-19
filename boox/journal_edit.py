"""
journal_edit.py (v3.3): add or remove sheets in a live Journal PDF. Handwriting is never redrawn.
  python3 journal_edit.py Journal.pdf add meeting "dotgrid:Trip ideas"
  python3 journal_edit.py Journal.pdf add --link "dotgrid:Trip ideas"   # link it to penciled Index ink
  python3 journal_edit.py Journal.pdf remove 88 89
add:    appends the sheet. With --link, also puts a tap-link on the Index over the topmost
        handwriting there that isn't already a link (the title you penciled in).
remove: drops the page, whites out its printed Index row (leaves a write-in line), removes its links.
Manifest <journal>_manifest.json tracks title -> page and index_page (0-based).
"""
import json, os, sys, io
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject, DictionaryObject, FloatObject, RectangleObject

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX_PAGE = 3  # default; main() overrides from the manifest or by the page carrying the most links

def manifest_path(pdf): return os.path.splitext(pdf)[0] + "_manifest.json"

def rect(a):
    r = [float(v) for v in a["/Rect"]]; return (min(r[0],r[2]), min(r[1],r[3]), max(r[0],r[2]), max(r[1],r[3]))

def overlaps(a, b): return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])

def ink_targets(idx):
    annots = [a.get_object() for a in idx.get("/Annots", [])]
    links = [rect(a) for a in annots if a.get("/Subtype") == "/Link"]
    ink = [rect(a) for a in annots if a.get("/Subtype") != "/Link" and "/Rect" in a]
    free = [r for r in ink if not any(overlaps(r, l) for l in links)]
    rows = []
    for r in sorted(free, key=lambda r: -r[3]):
        for row in rows:
            if abs(((row[1]+row[3])/2) - ((r[1]+r[3])/2)) < 14:
                row[0], row[1], row[2], row[3] = min(row[0],r[0]), min(row[1],r[1]), max(row[2],r[2]), max(row[3],r[3]); break
        else: rows.append(list(r))
    return rows

def add_link(writer, page, r, target):
    a = DictionaryObject({NameObject("/Type"): NameObject("/Annot"), NameObject("/Subtype"): NameObject("/Link"),
        NameObject("/Rect"): RectangleObject([r[0]-4, r[1]-4, r[2]+4, r[3]+4]),
        NameObject("/Border"): ArrayObject([FloatObject(0), FloatObject(0), FloatObject(0)]),
        NameObject("/Dest"): ArrayObject([writer.pages[target].indirect_reference, NameObject("/Fit")])})
    if "/Annots" not in page: page[NameObject("/Annots")] = ArrayObject()
    page["/Annots"].append(writer._add_object(a))

def main():
    global INDEX_PAGE
    pdf, cmd, args = sys.argv[1], sys.argv[2], sys.argv[3:]
    reader = PdfReader(pdf); mp = manifest_path(pdf)
    manifest = json.load(open(mp)) if os.path.exists(mp) else {"sections": []}
    writer = PdfWriter(); writer.append(reader)
    INDEX_PAGE = manifest.get("index_page", max(range(min(6, len(writer.pages))), key=lambda i: sum(1 for a in writer.pages[i].get("/Annots", []) if a.get_object().get("/Subtype") == "/Link")))
    secs = manifest["sections"]; idx = writer.pages[INDEX_PAGE]
    if cmd == "add":
        tpl = PdfReader(os.path.join(HERE, "templates.pdf")); tmap = json.load(open(os.path.join(HERE, "templates.json")))
        want_link = "--link" in args; args = [a for a in args if a != "--link"]
        targets = ink_targets(idx) if want_link else []
        for key in args:
            title = None
            if ":" in key: key, title = key.split(":", 1)
            if key not in tmap: print("unknown sheet:", key, "choices:", ", ".join(tmap)); continue
            writer.add_page(tpl.pages[tmap[key]["page"]]); newp = writer.pages[-1]
            for a in newp.get("/Annots", []):
                o = a.get_object()
                if "/Dest" in o: o[NameObject("/Dest")] = ArrayObject([idx.indirect_reference, NameObject("/Fit")])
            n = len(writer.pages) - 1
            if targets: add_link(writer, idx, targets.pop(0), n); how = "linked to your penciled row"
            else: how = "no Index link (pencil a title and the next run links it)"
            secs.append({"title": title or tmap[key]["title"], "page": n})
            print("added", title or key, "as page", n + 1, how)
    elif cmd == "remove":
        for p in sorted({int(a)-1 for a in args}, reverse=True):
            if p <= INDEX_PAGE: print("won't remove page", p+1); continue
            gone = writer.pages[p].indirect_reference.idnum
            keep = ArrayObject(); rows = []
            for a in idx.get("/Annots", []):
                o = a.get_object(); d = o.get("/Dest")
                if d and d[0].idnum == gone: rows.append(rect(o)); continue
                keep.append(a)
            idx[NameObject("/Annots")] = keep
            if rows:   # white out the printed Index row(s) and leave a write-in line
                buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(6.2*inch, 8.27*inch))
                for x1, y1, x2, y2 in rows:
                    c.setFillColorRGB(1,1,1); c.rect(x1-2, y1-2, x2-x1+4, y2-y1+4, stroke=0, fill=1)
                    c.setStrokeColorRGB(0.65,0.65,0.65); c.setLineWidth(0.4); c.line(x1, y1+2, x2, y1+2)
                c.showPage(); c.save(); buf.seek(0); idx.merge_page(PdfReader(buf).pages[0])
            writer.remove_page(p)
            secs = [s for s in secs if s["page"] != p]
            for s in secs:
                if s["page"] > p: s["page"] -= 1
            print("removed page", p+1)
    manifest["sections"] = secs; manifest["index_page"] = INDEX_PAGE
    with open(pdf, "wb") as f: writer.write(f)
    json.dump(manifest, open(mp, "w"), indent=1)
    print("wrote", pdf, "pages:", len(writer.pages))

if __name__ == "__main__": main()
