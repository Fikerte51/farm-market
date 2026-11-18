"""Accurate, selectable poster text on the user's illustrated three-column layout.

The background is a text-free adaptation of the supplied poster. All project
claims and diagrams are drawn from repository content, not generated lettering.
Coordinates below use the background's 1456 x 1088 design grid.
"""
import json
from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A1, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image

GREEN='#004b2c'; INK='#142d20'


def build_poster(docs, team, lab, results):
    fontdir=Path('/System/Library/Fonts/Supplemental')
    regular,bold='Helvetica','Helvetica-Bold'
    if (fontdir/'Arial Narrow.ttf').exists():
        pdfmetrics.registerFont(TTFont('PosterBody',str(fontdir/'Arial Narrow.ttf')))
        pdfmetrics.registerFont(TTFont('PosterBold',str(fontdir/'Arial Narrow Bold.ttf')))
        pdfmetrics.registerFontFamily('PosterBody',normal='PosterBody',bold='PosterBold')
        regular,bold='PosterBody','PosterBold'
    W,H=landscape(A1)
    c=canvas.Canvas(str(docs/'Poster.pdf'),pagesize=(W,H))
    c.setTitle('Local Farm and Market Food Availability System - COSC444')
    c.setAuthor('; '.join(n for n,_ in team))
    c.scale(W/1456,H/1088)
    c.drawImage(str(Path(__file__).parent/'assets/poster_background.png'),0,0,1456,1088)

    def text(txt,x,top,w,h,fs=22,color=INK,heavy=False,align=0):
        # Refuse overflow rather than painting over another panel.
        for size in [fs-i*.25 for i in range(int((fs-10)*4)+1)]:
            style=ParagraphStyle('poster',fontName=bold if heavy else regular,
                fontSize=size,leading=size*1.13,textColor=colors.HexColor(color),alignment=align)
            p=Paragraph(txt,style);pw,ph=p.wrap(w,h)
            if ph<=h:break
        else:raise ValueError('Poster text does not fit: '+txt)
        p.drawOn(c,x,1088-top-ph)
        return ph
    def heading(txt,x,top,w,fs=28):
        text(txt,x,top,w,45,fs,'#ffffff',True,1)
    def picture(name,x,top,w,h):
        path=docs/name;iw,ih=Image.open(path).size
        scale=min(w/iw,h/ih);ww,hh=iw*scale,ih*scale
        c.drawImage(str(path),x+(w-ww)/2,1088-top-(h+hh)/2,width=ww,height=hh,mask='auto')

    # Title and verified team details.
    text('Local Farm and Market Food Availability System',238,38,1164,58,47,'#fffced',True,1)
    text('COSC444 Database Systems | Khalifa University of Science and Technology | Fall 2026-2027',265,107,1000,30,25,'#fffced',True,1)
    text(f'Ahmed Hassen Mohammed (100064745)  |  Rewan Ramadan (100064842)<br/>'
         f'Lara Al-Omari (100064797)  |  Fikertemariam Aklilu (100064744)  |  Lab {lab}',
         268,148,1000,55,24,'#fffced',True,1)

    heading('1. PROJECT OVERVIEW',28,231,367)
    text('A farm-to-market system connecting local farmers with market buyers to improve visibility '
         'of food availability, inspired by UAE food-security priorities. Tracks forecasts, '
         'harvest stock, requests, allocations and actual deliveries.',45,286,365,99,21)

    heading('2. USER ROLES',28,414,400)
    for x,label,copy in [
        (36,'Farmers','Record harvest lots<br/>Manage crop cycles<br/>Allocate produce<br/>Upload lot images'),
        (170,'Market Buyers','Search produce<br/>Request supply<br/>Confirm deliveries'),
        (307,'Administrators','Manage users, roles,<br/>crops, units, markets<br/>Review audit / reports')]:
        text(label,x,546,115,32,21,GREEN,True,1)
        text(copy,x,587,115,55,15)

    heading('3. HOW IT WORKS',28,668,400)
    for x,w,label in [(36,66,'Farm'),(133,67,'Crop<br/>Cycle'),(232,69,'Harvest<br/>Lot'),(330,83,'Stock<br/>Movements')]:
        text(label,x,772,w,44,18,heavy=True,align=1)
    for x,w,label in [(83,89,'Market<br/>Request'),(207,95,'Allocation'),(333,87,'Delivery<br/>Receipt')]:
        text(label,x,876,w,40,18,heavy=True,align=1)

    heading('4. DATABASE DESIGN',464,237,488,35)
    text('11 core business entities',474,294,478,30,24,heavy=True,align=1)
    text('Farms, Users, Crops, CropCycles, HarvestLots, HarvestLotImages, StockMovements, '
         'Markets, MarketRequests, Allocations and DeliveryReceipts.',475,331,477,51,20)
    text('MySQL: 15 tables, 28 foreign keys, explicit units and validated constraints. '
         'Farmer-to-farm assignments are M:N in the conceptual ER.',475,387,477,44,18)
    # The same canonical ER used by the technical document and editable source.
    picture('ER_diagram.png',462,433,494,259)
    text('Conceptual Chen ER | Full-size PNG and editable Draw.io on GitHub',476,697,475,22,14,GREEN,align=1)

    heading('6. TECHNOLOGY STACK',464,743,489,32)
    for x,w,label in [(461,83,'Python'),(557,91,'MySQL 8<br/>Database'),(664,94,'Streamlit<br/>GUI'),
                      (773,91,'LangChain<br/>+ Gemini'),(872,82,'JPG / PNG<br/>File Storage')]:
        text(label,x,864,w,43,18,heavy=True,align=1)

    heading('5. KEY BUSINESS RULES',990,231,439,28)
    left=['Forecasts kept separate<br/>from sellable stock','Availability derived from<br/>dated stock movements',
          'No allocation beyond<br/>available lot quantity','Partial fulfilment and<br/>delivery losses supported']
    right=['Receipts record actual<br/>quantity and discrepancy','Explicit units on every<br/>quantity',
           'Role-based record<br/>ownership enforced','Audit trail: date, user<br/>and reason']
    for i,(a,b) in enumerate(zip(left,right)):
        y=296+i*53
        text(a,1024,y,167,46,18)
        text(b,1237,y,183,46,18)

    heading('7. KEY FEATURES',993,545,434,33)
    for y,copy in [(604,'Role-based workspaces for farmers,<br/>buyers and administrators'),
        (644,'Harvest image upload and display'),(675,'Search and status filters'),
        (705,'Read-only LangChain / Gemini assistant'),(735,'Answers show supporting records')]:
        text(copy,1141,y,276,40 if y==604 else 26,19,heavy=True)

    heading('8. ADVANCED FEATURE',993,783,433,29)
    text('Secure login &amp; activity audit',1010,836,407,27,24,GREEN,True,1)
    text('bcrypt passwords | 5-attempt lock-out | Role ownership<br/>'
         '30-minute session expiry | Append-only activity log',1008,868,407,33,17,align=1)

    heading('9. ERROR HANDLING AND TESTING',31,934,817,26)
    live=json.loads((docs/'live_assistant_validation.json').read_text())
    passed=sum(r['status']=='PASS' for r in results)
    verified=sum(r['passed'] for r in live['results'])
    text('Friendly validation messages',84,980,335,23,19)
    text('Atomic transactions prevent<br/>partial updates on failure',84,1013,335,31,18)
    text(f'{passed} tests pass: valid, invalid, boundary &amp; concurrency',462,980,384,24,18)
    text(f'{verified} live Gemini answers verified against SQL',462,1013,384,24,18)
    text('COSC444  |  Lab '+lab+'  |  github.com/Fikerte51/farm-market',100,1055,1256,25,18,'#fffced',True,1)
    c.showPage();c.save()
