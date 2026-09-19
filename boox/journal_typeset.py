"""
journal_typeset.py: replace handwriting with typed text on every page EXCEPT Daily Log pages.
  python3 journal_typeset.py Journal.pdf typed.json
typed.json: [{"page": 27, "text": "make a study plan"},            # one entry per ink cluster, top to bottom
             {"page": 3,  "text": "! critical"}, {"page": 3, "text": "? question"},
             {"page": 4,  "text": "Thing #2", "link_to": 114}]     # optional: make the typed row a tap-link
Ink clusters are found from the page's stamp annotations (grouped by row, top to bottom). Each entry is
typed at its cluster's position (Helvetica, sized to the ink height), then the ink is removed. Pages inside
a DAILY LOG range (from the manifest) are never touched. Entries whose text is "" just drop the ink.
Run the clusters() helper first to count rows per page so the entry list lines up.
"""
import json, sys, os, io
from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, NameObject, DictionaryObject, FloatObject, RectangleObject
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth

PAGE_W, PAGE_H = 6.2*inch, 8.27*inch

def rect(a):
    r=[float(v) for v in a["/Rect"]]; return [min(r[0],r[2]),min(r[1],r[3]),max(r[0],r[2]),max(r[1],r[3])]

def clusters(page):
    ink=[rect(a.get_object()) for a in page.get("/Annots",[]) if a.get_object().get("/Subtype")!="/Link" and "/Rect" in a.get_object()]
    rows=[]
    for r in sorted(ink,key=lambda r:-r[3]):
        for row in rows:
            if abs((row[1]+row[3])/2-(r[1]+r[3])/2)<10:
                row[0],row[1],row[2],row[3]=min(row[0],r[0]),min(row[1],r[1]),max(row[2],r[2]),max(row[3],r[3]); break
        else: rows.append(list(r))
    return rows

def log_pages(manifest):
    pages=sorted(s["page"] for s in manifest["sections"] if s["title"].startswith("DAILY LOG"))
    ranges=[]
    for i,p in enumerate(pages):
        end = pages[i+1]-1 if i+1<len(pages) else p+39
        ranges.append((p,end))
    return ranges

def main():
    pdf, spec = sys.argv[1], json.load(open(sys.argv[2]))
    mp=os.path.splitext(pdf)[0]+"_manifest.json"; manifest=json.load(open(mp)) if os.path.exists(mp) else {"sections":[]}
    protected=log_pages(manifest)
    reader=PdfReader(pdf); w=PdfWriter(); w.append(reader)
    by_page={}
    for e in spec: by_page.setdefault(e["page"]-1,[]).append(e)
    for pi,entries in by_page.items():
        if any(a<=pi<=b for a,b in protected): print("page",pi+1,"is a Daily Log page, left alone"); continue
        page=w.pages[pi]; rows=clusters(page)
        buf=io.BytesIO(); c=canvas.Canvas(buf,pagesize=(PAGE_W,PAGE_H)); links=[]
        for e,r in zip(entries,rows):
            if not e.get("text"): continue
            h=r[3]-r[1]; size=max(7,min(10,h*0.55)); c.setFont("Helvetica",size)
            txt=e["text"]; maxw=max(PAGE_W-r[0]-0.3*inch, 1*inch)
            while stringWidth(txt,"Helvetica",size)>maxw and size>6: size-=0.5; c.setFont("Helvetica",size)
            c.drawString(r[0], r[1]+h*0.25, txt)
            if e.get("link_to"): links.append((r, e["link_to"]-1))
        c.showPage(); c.save(); buf.seek(0)
        page.merge_page(PdfReader(buf).pages[0])
        keep=ArrayObject([a for a in page.get("/Annots",[]) if a.get_object().get("/Subtype")=="/Link"])
        for r,t in links:
            keep.append(w._add_object(DictionaryObject({NameObject("/Type"):NameObject("/Annot"),NameObject("/Subtype"):NameObject("/Link"),
                NameObject("/Rect"):RectangleObject([r[0]-4,r[1]-4,r[2]+4,r[3]+4]),NameObject("/Border"):ArrayObject([FloatObject(0)]*3),
                NameObject("/Dest"):ArrayObject([w.pages[t].indirect_reference,NameObject("/Fit")])})))
        page[NameObject("/Annots")]=keep
        print("page",pi+1,": typed",sum(1 for e in entries if e.get("text")),"of",len(rows),"ink rows, ink removed")
    with open(pdf,"wb") as f: w.write(f)
    print("wrote",pdf)

if __name__=="__main__": main()
