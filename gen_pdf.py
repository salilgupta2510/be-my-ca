from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import os

OUT = "/Users/salil.gupta/Documents/Dev/be-my-ca/bemyca-marketing.pdf"

W, H = A4  # 595.27, 841.89

# Colors
BG = colors.HexColor("#0f172a")
CARD = colors.HexColor("#1e293b")
BORDER = colors.HexColor("#334155")
AMBER = colors.HexColor("#f59e0b")
AMBER_DIM = colors.HexColor("#92400e")
WHITE = colors.HexColor("#f8fafc")
SLATE3 = colors.HexColor("#cbd5e1")
SLATE4 = colors.HexColor("#94a3b8")
SLATE5 = colors.HexColor("#64748b")
RED = colors.HexColor("#ef4444")
GREEN = colors.HexColor("#22c55e")
BLUE = colors.HexColor("#3b82f6")

def page_bg(c, pg):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    # subtle grid dots
    c.setFillColor(colors.HexColor("#1e293b"))
    for x in range(0, int(W)+1, 24):
        for y in range(0, int(H)+1, 24):
            c.circle(x, y, 0.8, fill=1, stroke=0)
    # page number
    c.setFillColor(SLATE5)
    c.setFont("Helvetica", 7)
    c.drawCentredString(W/2, 10*mm, f"{pg} / 4")

def amber_pill(c, x, y, text, w=None):
    c.setFont("Helvetica-Bold", 7)
    tw = c.stringWidth(text, "Helvetica-Bold", 7)
    pw = (w or tw) + 12
    ph = 14
    c.setFillColor(AMBER_DIM)
    c.roundRect(x, y, pw, ph, 4, fill=1, stroke=0)
    c.setFillColor(AMBER)
    c.drawString(x + 6, y + 3.5, text)
    return pw

def card_rect(c, x, y, w, h):
    c.setFillColor(CARD)
    c.setStrokeColor(BORDER)
    c.roundRect(x, y, w, h, 6, fill=1, stroke=1)

def draw_page1(c):
    page_bg(c, 1)

    # Amber top accent bar
    c.setFillColor(AMBER)
    c.rect(0, H - 3, W, 3, fill=1, stroke=0)

    # Logo / brand
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(24*mm, H - 22*mm, "BeMyCa")
    c.setFillColor(SLATE4)
    c.setFont("Helvetica", 9)
    c.drawString(24*mm, H - 27*mm, "bemyca.cloud  ·  GST Filing, Simplified")

    # Tagline hero block
    hero_y = H - 70*mm
    hero_h = 44*mm
    # gradient-like: layered rects
    c.setFillColor(colors.HexColor("#1a2a1a"))
    c.roundRect(20*mm, hero_y, W - 40*mm, hero_h, 10, fill=1, stroke=0)
    c.setFillColor(AMBER)
    c.roundRect(20*mm, hero_y, 4, hero_h, 0, fill=1, stroke=0)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(28*mm, hero_y + 28*mm, "Upload your bills.")
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(28*mm, hero_y + 20*mm, "We handle your GST.")
    c.setFillColor(SLATE3)
    c.setFont("Helvetica", 9)
    c.drawString(28*mm, hero_y + 13*mm, "AI-powered invoice reading  ·  Automatic return computation  ·  No CA fees")
    c.setFillColor(SLATE4)
    c.setFont("Helvetica", 8)
    c.drawString(28*mm, hero_y + 7*mm, "GSTR-1  ·  GSTR-3B  ·  GSTR-9  ·  GSTR-2B Reconciliation  ·  ITC Ledger")

    # Stats row
    stats = [
        ("13", "Features included"),
        ("₹999", "Per month Pro"),
        ("~3 min", "Avg filing time"),
        ("₹0", "CA consultation fees"),
    ]
    sx = 20*mm
    sw = (W - 40*mm) / 4
    sy = H - 120*mm
    sh = 28*mm
    for val, label in stats:
        card_rect(c, sx, sy, sw - 3, sh)
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(sx + (sw-3)/2, sy + 17*mm, val)
        c.setFillColor(SLATE4)
        c.setFont("Helvetica", 7)
        c.drawCentredString(sx + (sw-3)/2, sy + 10*mm, label)
        sx += sw

    # Section: what you get
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(24*mm, H - 158*mm, "EVERYTHING IN PRO — AVAILABLE TODAY")
    c.setFillColor(BORDER)
    c.rect(24*mm, H - 160*mm, W - 48*mm, 0.5, fill=1, stroke=0)

    features_short = [
        ("AI Invoice Reader", "Photo any bill → Claude extracts all fields automatically"),
        ("Sales Invoice Management", "Add, edit, search outward invoices — B2B / B2C / Export / Credit Note"),
        ("Purchase Invoice Management", "Inward invoices with RCM flag and GSTIN validation"),
        ("GSTR-1 Computation", "Auto-categorises B2B, B2C, Exports; Table 12 HSN/SAC summary"),
        ("GSTR-3B Computation", "Net tax payable after ITC, section-wise breakdown"),
        ("GSTR-9 Annual Return", "One-click aggregation of all 12 months, Table 4 outward breakdown"),
        ("GSTR-2B Reconciliation", "Purchase vs supplier-filed: matched / mismatched / missing + IMS actions"),
        ("ITC Ledger", "12-month rolling: ITC available, claimed, net cash paid, running balance"),
        ("PDF Invoice Generation", "Professional invoices with GSTIN, HSN, tax breakdown"),
        ("6-Month Trend Dashboard", "Visual chart: tax liability, ITC, turnover — spot cash flow patterns"),
        ("Late Fee & Interest Calculator", "GSTR-1/3B fees (₹50/day, capped ₹10k) + 18% p.a. interest"),
        ("CSV Export", "One-click export of any invoice list"),
        ("Real-time GSTIN Validation", "Format check on every form — catches errors before portal rejection"),
    ]

    col_w = (W - 48*mm) / 2
    row_h = 13.5*mm
    start_y = H - 170*mm
    for i, (name, desc) in enumerate(features_short):
        col = i % 2
        row = i // 2
        fx = 24*mm + col * col_w
        fy = start_y - row * row_h
        # dot
        c.setFillColor(AMBER)
        c.circle(fx + 3*mm, fy + 5*mm, 2, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(fx + 7*mm, fy + 6.5*mm, name)
        c.setFillColor(SLATE4)
        c.setFont("Helvetica", 6.5)
        c.drawString(fx + 7*mm, fy + 1.5*mm, desc)

    # CTA pill bottom
    pill_y = 20*mm
    c.setFillColor(AMBER)
    c.roundRect(W/2 - 60*mm, pill_y, 120*mm, 12*mm, 6, fill=1, stroke=0)
    c.setFillColor(BG)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(W/2, pill_y + 4*mm, "Start FREE 1-month Pro trial at bemyca.cloud")

def draw_page2(c):
    page_bg(c, 2)
    c.setFillColor(AMBER)
    c.rect(0, H - 3, W, 3, fill=1, stroke=0)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(24*mm, H - 20*mm, "What's included in Pro")
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(24*mm + c.stringWidth("What's included in Pro", "Helvetica-Bold", 16) + 4, H - 20*mm, "— available today")

    c.setFillColor(SLATE4)
    c.setFont("Helvetica", 8)
    c.drawString(24*mm, H - 26*mm, "13 features shipping now. No hidden paywalls within Pro.")

    features = [
        ("📷", "AI Invoice Reader",
         "Photograph any bill. Claude AI reads the invoice number, GSTIN, HSN code,",
         "taxable value, IGST/CGST/SGST — no manual entry needed."),
        ("📤", "Sales Invoice Management",
         "Add, edit, delete, search outward invoices. Categorise as B2B, B2C Large,",
         "B2C Small, Export, or Credit Note with full tax breakdown."),
        ("📥", "Purchase Invoice Management",
         "Inward invoices with RCM (Reverse Charge Mechanism) support.",
         "GSTIN validated on every entry before save."),
        ("📋", "GSTR-1 Computation",
         "Auto-categorises invoices into correct GSTR-1 sections. Table 12 HSN/SAC",
         "summary generated automatically — ready for portal upload."),
        ("🧾", "GSTR-3B Computation",
         "Computes net tax payable after ITC offset. Section-wise breakdown of",
         "liabilities and credits matches portal format exactly."),
        ("📅", "GSTR-9 Annual Return",
         "One-click aggregation of all 12 monthly returns. Table 4 outward by type,",
         "month-wise breakdown with filing status per month."),
        ("🔄", "GSTR-2B Reconciliation",
         "Compares your purchase register against supplier-filed data. Flags matched,",
         "mismatched, and missing invoices with IMS action recommendations."),
        ("💰", "ITC Ledger (12-Month)",
         "Rolling ledger showing ITC available, claimed, net cash paid, and running",
         "credit balance. 12 months at a glance."),
        ("📄", "PDF Invoice Generation",
         "Generate professional invoices instantly. Includes GSTIN, HSN codes,",
         "full tax breakdown — downloadable and shareable."),
        ("📊", "6-Month Trend Dashboard",
         "Visual chart of tax liability, ITC claimed, and turnover. Spot seasonal",
         "patterns and cash flow trends at a glance."),
        ("⏰", "Late Fee & Interest Calculator",
         "Calculate GSTR-1 and GSTR-3B late fees (₹50/day, capped ₹10,000) and",
         "18% p.a. interest on delayed tax payments automatically."),
        ("📁", "CSV Export",
         "One-click export of any invoice list. Download sales or purchase data",
         "as CSV for your accountant or reconciliation workflows."),
        ("✅", "Real-time GSTIN Validation",
         "Format-checks every GSTIN field on every form. Catches errors before",
         "portal rejection — 15-digit format, check digit, state code."),
    ]

    cols = 2
    card_w = (W - 52*mm) / 2
    card_h = 28*mm
    gap_x = 4*mm
    gap_y = 3*mm
    start_y = H - 35*mm

    for i, (icon, name, line1, line2) in enumerate(features):
        col = i % cols
        row = i // cols
        cx = 24*mm + col * (card_w + gap_x)
        cy = start_y - row * (card_h + gap_y) - card_h

        card_rect(c, cx, cy, card_w, card_h)
        # amber left accent
        c.setFillColor(AMBER)
        c.roundRect(cx, cy, 3, card_h, 3, fill=1, stroke=0)

        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(cx + 6*mm, cy + card_h - 8*mm, name)
        c.setFillColor(SLATE3)
        c.setFont("Helvetica", 6.5)
        c.drawString(cx + 6*mm, cy + card_h - 14*mm, line1)
        c.drawString(cx + 6*mm, cy + card_h - 19*mm, line2)

def draw_page3(c):
    page_bg(c, 3)
    c.setFillColor(AMBER)
    c.rect(0, H - 3, W, 3, fill=1, stroke=0)

    # Header
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(24*mm, H - 20*mm, "How BeMyCa compares")

    c.setFillColor(SLATE4)
    c.setFont("Helvetica", 8)
    c.drawString(24*mm, H - 26*mm, "Feature-for-feature, ₹ for ₹.")

    # Comparison table
    col_headers = ["Feature", "BeMyCa Pro", "ClearTax", "Zoho Books", "Tally Prime", "Vyapar"]
    rows = [
        ["AI invoice photo reading",   "✓", "✗", "✗", "✗", "✗"],
        ["GSTR-1 + 3B + 9",           "✓", "✓ paid", "✓ paid", "✓", "✓ basic"],
        ["GSTR-2B reconciliation",     "✓", "✓ paid", "✗", "✓", "✗"],
        ["ITC ledger (12-month)",      "✓", "✓ paid", "✓ paid", "✓", "✗"],
        ["PDF invoice generation",     "✓", "✗", "✓", "✗", "✓"],
        ["Late fee calculator",        "✓", "✗", "✗", "✗", "✗"],
        ["Annual GSTR-9",              "✓", "✓ paid", "✗", "✓", "✗"],
        ["Direct portal filing (GSP)", "Soon", "✓", "✓", "✓", "✗"],
        ["Monthly price",              "₹999", "₹1,249", "₹749–₹2,999", "₹1,500 EMI", "₹150–₹225"],
    ]

    table_data = [col_headers] + rows
    col_widths = [52*mm, 26*mm, 24*mm, 27*mm, 26*mm, 22*mm]
    row_heights = [8*mm] + [7.5*mm] * len(rows)

    tbl = Table(table_data, colWidths=col_widths, rowHeights=row_heights)

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a2a3a")),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#1a3a1a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), AMBER),
        ("TEXTCOLOR", (1, 0), (1, 0), AMBER),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("LEFTPADDING", (0, 0), (0, -1), 4),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#1e293b"), colors.HexColor("#1a2332")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    # Color ✓ green, ✗ red in BeMyCa col
    for r in range(1, len(table_data)):
        val = table_data[r][1]
        if val == "✓":
            style_cmds.append(("TEXTCOLOR", (1, r), (1, r), GREEN))
            style_cmds.append(("FONTNAME", (1, r), (1, r), "Helvetica-Bold"))
        elif val == "✗":
            style_cmds.append(("TEXTCOLOR", (1, r), (1, r), RED))
        elif val == "Soon":
            style_cmds.append(("TEXTCOLOR", (1, r), (1, r), AMBER))
        # All ✗ in other cols gray
        for col in range(2, 6):
            v = table_data[r][col]
            if v == "✗":
                style_cmds.append(("TEXTCOLOR", (col, r), (col, r), SLATE5))
            elif v == "✓":
                style_cmds.append(("TEXTCOLOR", (col, r), (col, r), SLATE3))

    tbl.setStyle(TableStyle(style_cmds))

    tbl_x = 22*mm
    tbl_y = H - 118*mm
    tbl.wrapOn(c, W, H)
    tbl.drawOn(c, tbl_x, tbl_y - sum(row_heights[1:]) - row_heights[0])

    # Pricing tiers
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(24*mm, H - 148*mm, "Pricing")

    tier_y = H - 196*mm
    tier_h = 44*mm
    tiers = [
        {
            "name": "Free Trial",
            "price": "1 Month FREE",
            "sub": "No credit card required",
            "color": colors.HexColor("#1e3a5f"),
            "accent": BLUE,
            "features": ["Full Pro access", "All 13 features", "Expires after 30 days", "Upgrade anytime"],
        },
        {
            "name": "Pro",
            "price": "₹999 / month",
            "sub": "or ₹8,999/year  (save 25%)",
            "color": colors.HexColor("#1a2a1a"),
            "accent": AMBER,
            "features": ["Everything in Free Trial", "Unlimited invoices", "Unlimited periods", "Priority support"],
        },
        {
            "name": "Enterprise",
            "price": "Custom Pricing",
            "sub": "For CAs managing 10+ clients",
            "color": colors.HexColor("#1a1a2e"),
            "accent": colors.HexColor("#a78bfa"),
            "features": ["Multi-client dashboard", "Bulk filing", "Dedicated support", "Custom integrations"],
        },
    ]
    tier_w = (W - 52*mm) / 3
    for i, tier in enumerate(tiers):
        tx = 24*mm + i * (tier_w + 2*mm)
        c.setFillColor(tier["color"])
        c.roundRect(tx, tier_y, tier_w, tier_h, 8, fill=1, stroke=0)
        c.setStrokeColor(tier["accent"])
        c.setLineWidth(1.2)
        c.roundRect(tx, tier_y, tier_w, tier_h, 8, fill=0, stroke=1)
        c.setLineWidth(1)
        # top accent line
        c.setFillColor(tier["accent"])
        c.roundRect(tx, tier_y + tier_h - 3, tier_w, 3, 3, fill=1, stroke=0)
        # name
        c.setFillColor(tier["accent"])
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(tx + tier_w/2, tier_y + tier_h - 10*mm, tier["name"].upper())
        # price
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(tx + tier_w/2, tier_y + tier_h - 16*mm, tier["price"])
        # sub
        c.setFillColor(SLATE4)
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(tx + tier_w/2, tier_y + tier_h - 21*mm, tier["sub"])
        # divider
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.4)
        c.line(tx + 4*mm, tier_y + tier_h - 24*mm, tx + tier_w - 4*mm, tier_y + tier_h - 24*mm)
        # features
        for j, feat in enumerate(tier["features"]):
            fy = tier_y + tier_h - 30*mm - j * 7
            c.setFillColor(tier["accent"])
            c.circle(tx + 6*mm, fy + 2, 2, fill=1, stroke=0)
            c.setFillColor(SLATE3)
            c.setFont("Helvetica", 6.5)
            c.drawString(tx + 9*mm, fy, feat)

    # Why not free callout
    wf_y = tier_y - 28*mm
    c.setFillColor(colors.HexColor("#1c1208"))
    c.roundRect(24*mm, wf_y, W - 48*mm, 23*mm, 6, fill=1, stroke=0)
    c.setStrokeColor(AMBER_DIM)
    c.setLineWidth(0.8)
    c.roundRect(24*mm, wf_y, W - 48*mm, 23*mm, 6, fill=0, stroke=1)
    c.setLineWidth(1)
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(28*mm, wf_y + 17*mm, "Why not free?")
    c.setFillColor(SLATE3)
    c.setFont("Helvetica", 7)
    c.drawString(28*mm, wf_y + 11*mm, "Free tools cut corners. We invest in AI infrastructure, GSP API integrations, and continuous compliance")
    c.drawString(28*mm, wf_y + 5.5*mm, "updates. ₹999/month is less than one CA consultation — and we file your returns every month.")

    # Competitor jab
    c.setFillColor(SLATE4)
    c.setFont("Helvetica", 7)
    c.drawString(24*mm, wf_y - 8*mm, '"ClearTax charges ₹14,999/year and doesn\'t read your invoices.')
    c.drawString(24*mm, wf_y - 14*mm, ' Tally costs ₹18,000 upfront and needs 2 days of training. BeMyCa Pro: ₹999/month, with AI, from day one."')

def draw_page4(c):
    page_bg(c, 4)
    c.setFillColor(AMBER)
    c.rect(0, H - 3, W, 3, fill=1, stroke=0)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(24*mm, H - 20*mm, "What's next — GSP API Integration")
    c.setFillColor(AMBER)
    c.setFont("Helvetica", 8)
    c.drawString(24*mm, H - 26*mm, "Pro roadmap  ·  Direct portal filing without manual re-entry")

    # Roadmap items
    roadmap = [
        ("Direct GSTR-1 Filing",
         "Submit GSTR-1 directly to GST portal via GSP API — no manual copy-paste.",
         "Status: In development  ·  Requires GSP tie-up (IRIS Business / ClearTax)"),
        ("Direct GSTR-3B Filing",
         "File GSTR-3B with EVC/OTP authentication. Tax liability computed and submitted in one flow.",
         "Status: Planned  ·  EVC integration after GSTR-1 filing ships"),
        ("Auto GSTR-2B Pull",
         "Automatically fetch GSTR-2B on the 14th each month. Fully automated reconciliation — zero manual download.",
         "Status: Planned  ·  Available after GSP credentials provisioned"),
        ("Live GSTIN Verification",
         "Verify GSTIN against live GSTN database — not just format check. Catch deregistered suppliers instantly.",
         "Status: Planned  ·  GSP lookup API"),
        ("Tax Payment Initiation",
         "Generate challan and initiate NEFT/RTGS/Net Banking payment link directly from GSTR-3B computation.",
         "Status: Roadmap  ·  Requires GSTN payment gateway integration"),
    ]

    ry = H - 38*mm
    rh = 24*mm
    for i, (name, desc, status) in enumerate(roadmap):
        rx = 24*mm
        rw = W - 48*mm
        card_rect(c, rx, ry - i*(rh + 3*mm), rw, rh)
        c.setFillColor(AMBER_DIM)
        c.roundRect(rx, ry - i*(rh+3*mm), 3, rh, 3, fill=1, stroke=0)
        # Step number
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(rx + 6*mm, ry - i*(rh+3*mm) + 14*mm, str(i+1))
        # Name
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(rx + 14*mm, ry - i*(rh+3*mm) + 14*mm, name)
        # Desc
        c.setFillColor(SLATE3)
        c.setFont("Helvetica", 7)
        c.drawString(rx + 14*mm, ry - i*(rh+3*mm) + 8*mm, desc)
        # Status
        c.setFillColor(SLATE5)
        c.setFont("Helvetica", 6.5)
        c.drawString(rx + 14*mm, ry - i*(rh+3*mm) + 3*mm, status)

    # CTA block
    cta_y = 42*mm
    c.setFillColor(colors.HexColor("#1a2a1a"))
    c.roundRect(20*mm, cta_y, W - 40*mm, 30*mm, 10, fill=1, stroke=0)
    c.setStrokeColor(AMBER)
    c.setLineWidth(1.5)
    c.roundRect(20*mm, cta_y, W - 40*mm, 30*mm, 10, fill=0, stroke=1)
    c.setLineWidth(1)

    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W/2, cta_y + 20*mm, "Start your free 1-month Pro trial")
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(W/2, cta_y + 13*mm, "bemyca.cloud")
    c.setFillColor(SLATE4)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(W/2, cta_y + 7*mm, "No credit card required  ·  All 13 Pro features  ·  Cancel anytime")

    # Footer
    c.setFillColor(BORDER)
    c.rect(24*mm, 26*mm, W - 48*mm, 0.5, fill=1, stroke=0)
    c.setFillColor(SLATE5)
    c.setFont("Helvetica", 7)
    c.drawString(24*mm, 20*mm, "BeMyCa  ·  bemyca.cloud  ·  GST filing for Indian businesses")
    c.drawRightString(W - 24*mm, 20*mm, "© 2025 BeMyCa. All rights reserved.")


c = canvas.Canvas(OUT, pagesize=A4)
draw_page1(c)
c.showPage()
draw_page2(c)
c.showPage()
draw_page3(c)
c.showPage()
draw_page4(c)
c.showPage()
c.save()
print(f"PDF saved: {OUT}")
