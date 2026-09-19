"""
build_custom.py: render one sheet from a small JSON spec, on the Boox page, with an Index button.
  python3 build_custom.py spec.json out.pdf
  python3 build_custom.py spec.json --template     # also appends it to templates.pdf / templates.json
spec: {"key":"radical_candor","title":"RADICAL CANDOR","index_title":"Radical Candor","subtitle":"...",
       "elements":[ {"type":"lines","label":"Context","count":4},
                    {"type":"box","title":"...","lines":3},
                    {"type":"checklist","label":"...","items":["a","b"],"cols":2},
                    {"type":"table","cols":[["Date",0.15],["Topic",0.6],["Hrs",0.25]],"rows":8,"check_cols":[2]},
                    {"type":"quad","titles":["TL","TR","BL","BR"],"h":2.6},
                    {"type":"dots","h":2.0},
                    {"type":"text","text":"small gray note"} ]}
Used by the pipeline to turn a hand-drawn TEMPLATE DRAFT page into a real template.
"""
import json, sys, os
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import Color
from pypdf import PdfReader, PdfWriter

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE_W, PAGE_H, MARGIN = 6.2*inch, 8.27*inch, 0.32*inch
CW = PAGE_W - 2*MARGIN
BLACK=Color(0,0,0); GRAY_LINE=Color(0.65,0.65,0.65); GRAY_BOX=Color(0.45,0.45,0.45); GRAY_DOT=Color(0.38,0.38,0.38)

def label(c,x,y,t,size=8.5): c.setFont("Helvetica-Bold",size); c.setFillColor(GRAY_BOX); c.drawString(x,y,t); c.setFillColor(BLACK)
def ruled(c,x,y,w,n,gap=0.24*inch):
    c.setStrokeColor(GRAY_LINE); c.setLineWidth(0.5)
    for _ in range(n): c.line(x,y,x+w,y); y-=gap
    return y
def checkbox(c,x,y,s=8): c.setStrokeColor(BLACK); c.setLineWidth(0.7); c.rect(x,y,s,s,stroke=1,fill=0)
def dots(c,y_top,y_bot,sp=0.28*inch):
    c.setStrokeColor(GRAY_DOT); c.setLineWidth(1.5); c.setLineCap(1); c.setDash([0.1,sp-0.1]); y=y_top
    while y>=y_bot: c.line(MARGIN,y,PAGE_W-MARGIN,y); y-=sp
    c.setDash([]); c.setLineCap(0); c.setStrokeColor(BLACK)

def render(spec, out):
    c = canvas.Canvas(out, pagesize=(PAGE_W,PAGE_H), pageCompression=1)
    c.setFont("Helvetica-Bold",13); c.drawString(MARGIN, PAGE_H-MARGIN-0.12*inch, spec["title"])
    if spec.get("subtitle"):
        c.setFont("Helvetica",8); c.setFillColor(GRAY_BOX); c.drawString(MARGIN, PAGE_H-MARGIN-0.30*inch, spec["subtitle"]); c.setFillColor(BLACK)
    c.setStrokeColor(GRAY_LINE); c.setLineWidth(0.7); c.line(MARGIN,PAGE_H-MARGIN-0.42*inch,PAGE_W-MARGIN,PAGE_H-MARGIN-0.40*inch)
    c.bookmarkPage("index")
    w,h=0.62*inch,0.22*inch; x1=PAGE_W-MARGIN-w; y1=PAGE_H-MARGIN-h+0.06*inch
    c.setStrokeColor(GRAY_BOX); c.setLineWidth(0.6); c.roundRect(x1,y1,w,h,3,stroke=1,fill=0)
    c.setFont("Helvetica",7.5); c.setFillColor(GRAY_BOX); c.drawCentredString(x1+w/2,y1+0.06*inch,"Index"); c.setFillColor(BLACK)
    c.linkAbsolute("","index",(x1,y1,x1+w,y1+h))
    y = PAGE_H-MARGIN-0.62*inch
    for e in spec.get("elements",[]):
        t=e["type"]
        if t=="lines":
            if e.get("label"): label(c,MARGIN,y,e["label"]); y-=0.10*inch
            y = ruled(c,MARGIN,y-0.08*inch,CW,e.get("count",4)) - 0.04*inch
        elif t=="box":
            bh = (0.32+0.24*e.get("lines",3))*inch
            c.setStrokeColor(GRAY_BOX); c.setLineWidth(0.7); c.rect(MARGIN,y-bh,CW,bh,stroke=1,fill=0)
            if e.get("title"): label(c,MARGIN+0.07*inch,y-0.18*inch,e["title"])
            ruled(c,MARGIN+0.07*inch,y-0.42*inch,CW-0.14*inch,e.get("lines",3))
            y -= bh+0.12*inch
        elif t=="checklist":
            if e.get("label"): label(c,MARGIN,y,e["label"]); y-=0.20*inch
            cols=e.get("cols",1); colw=CW/cols
            for i,it in enumerate(e["items"]):
                cx=MARGIN+(i%cols)*colw; cy=y-(i//cols)*0.23*inch
                checkbox(c,cx,cy-2); c.setFont("Helvetica",8.5); c.drawString(cx+0.2*inch,cy,it)
            y -= ((len(e["items"])+cols-1)//cols)*0.23*inch + 0.10*inch
        elif t=="table":
            x=MARGIN; xs=[]
            for title,frac in e["cols"]:
                xs.append(x); label(c,x+0.03*inch,y,title,7.5); x+=frac*CW
            xs.append(PAGE_W-MARGIN)
            c.setStrokeColor(GRAY_LINE); c.setLineWidth(0.6); c.line(MARGIN,y-0.06*inch,PAGE_W-MARGIN,y-0.06*inch)
            yy=y-0.06*inch; rh=e.get("row_h",0.24)*inch
            for r in range(e.get("rows",8)):
                yy-=rh; c.setLineWidth(0.4); c.line(MARGIN,yy,PAGE_W-MARGIN,yy)
                for ci in e.get("check_cols",[]): checkbox(c,(xs[ci]+xs[ci+1])/2-3.5,yy+rh/2-3.5,7)
            for vx in xs[1:-1]: c.line(vx,y-0.06*inch,vx,yy)
            y = yy-0.15*inch
        elif t=="quad":
            qh=e.get("h",2.6)*inch; qw=CW/2
            for i,tt in enumerate(e["titles"]):
                qx=MARGIN+(i%2)*qw; qy=y-(i//2+1)*qh
                c.setStrokeColor(GRAY_BOX); c.setLineWidth(0.7); c.rect(qx,qy,qw,qh,stroke=1,fill=0)
                label(c,qx+0.07*inch,qy+qh-0.18*inch,tt)
            y -= 2*qh+0.12*inch
        elif t=="dots":
            dh=e.get("h",2.0)*inch; dots(c,y-0.1*inch,y-dh); y-=dh+0.1*inch
        elif t=="text":
            c.setFont("Helvetica-Oblique",7.5); c.setFillColor(GRAY_BOX); c.drawString(MARGIN,y,e["text"]); c.setFillColor(BLACK); y-=0.2*inch
    c.showPage(); c.save()

if __name__=="__main__":
    spec=json.load(open(sys.argv[1]))
    if sys.argv[2]=="--template":
        tmp=os.path.join(HERE,"_new.pdf"); render(spec,tmp)
        tp=os.path.join(HERE,"templates.pdf"); tj=os.path.join(HERE,"templates.json")
        w=PdfWriter(); w.append(PdfReader(tp)); w.append(PdfReader(tmp)); w.write(tp)
        m=json.load(open(tj)); m[spec["key"]]={"page":len(w.pages)-1,"title":spec.get("index_title",spec["title"].title())}; json.dump(m,open(tj,"w"),indent=1)
        os.remove(tmp); print("template added:",spec["key"],"page",len(w.pages))
    else: render(spec,sys.argv[2]); print("wrote",sys.argv[2])
