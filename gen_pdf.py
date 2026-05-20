from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

OUT = "/Users/salil.gupta/Documents/Dev/be-my-ca/bemyca-marketing.pdf"
W, H = A4  # 595.27 x 841.89 pts

BG        = colors.HexColor("#0f172a")
CARD      = colors.HexColor("#1e293b")
BORDER    = colors.HexColor("#334155")
AMBER     = colors.HexColor("#f59e0b")
AMBER_DIM = colors.HexColor("#78350f")
WHITE     = colors.HexColor("#f8fafc")
SLATE3    = colors.HexColor("#cbd5e1")
SLATE4    = colors.HexColor("#94a3b8")
SLATE5    = colors.HexColor("#64748b")
RED       = colors.HexColor("#ef4444")
GREEN     = colors.HexColor("#22c55e")
BLUE      = colors.HexColor("#3b82f6")
PURPLE    = colors.HexColor("#a78bfa")


def draw_bg(c, pg):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#141f33"))
    for x in range(0, int(W) + 1, 28):
        for y in range(0, int(H) + 1, 28):
            c.circle(x, y, 0.7, fill=1, stroke=0)
    c.setFillColor(AMBER)
    c.rect(0, H - 3, W, 3, fill=1, stroke=0)
    c.setFillColor(SLATE5)
    c.setFont("Helvetica", 7)
    c.drawCentredString(W / 2, 10 * mm, f"{pg} / 4")


def draw_card(c, x, y, w, h, accent=None):
    c.setFillColor(CARD)
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.roundRect(x, y, w, h, 5, fill=1, stroke=1)
    if accent:
        c.setFillColor(accent)
        c.roundRect(x, y, 3.5, h, 3, fill=1, stroke=0)


# ── PAGE 1: Hero ───────────────────────────────────────────────────────────────

def page1(c):
    draw_bg(c, 1)

    # Brand — 15mm from top
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(24 * mm, H - 15 * mm, "BeMyCa")
    c.setFillColor(SLATE4)
    c.setFont("Helvetica", 8)
    c.drawString(24 * mm, H - 21 * mm, "bemyca.cloud  ·  GST Filing, Simplified")

    # Hero block: top=H-27mm, bottom=H-66mm, h=39mm
    hx, hy = 20 * mm, H - 66 * mm
    hw, hh = W - 40 * mm, 39 * mm
    c.setFillColor(colors.HexColor("#0d1f0d"))
    c.roundRect(hx, hy, hw, hh, 8, fill=1, stroke=0)
    c.setFillColor(AMBER)
    c.roundRect(hx, hy, 4, hh, 4, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(hx + 8 * mm, hy + 27 * mm, "Upload your bills.")
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(hx + 8 * mm, hy + 18 * mm, "We handle your GST.")
    c.setFillColor(SLATE3)
    c.setFont("Helvetica", 8)
    c.drawString(hx + 8 * mm, hy + 11 * mm, "AI-powered invoice reading  ·  Automatic return computation  ·  No CA fees")
    c.setFillColor(SLATE5)
    c.setFont("Helvetica", 7)
    c.drawString(hx + 8 * mm, hy + 5 * mm, "GSTR-1  ·  GSTR-3B  ·  GSTR-9  ·  GSTR-2B Reconciliation  ·  ITC Ledger")

    # Stats row: top=H-72mm, bottom=H-98mm, h=26mm
    stats = [
        ("13",      "Features included"),
        ("Rs.999",  "Per month Pro"),
        ("~3 min",  "Avg filing time"),
        ("Rs.0",    "CA consultation fees"),
    ]
    sw  = (W - 40 * mm) / 4
    sx0 = 20 * mm
    sy  = H - 98 * mm
    sh  = 26 * mm
    for i, (val, lbl) in enumerate(stats):
        sx = sx0 + i * sw
        draw_card(c, sx, sy, sw - 3, sh)
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 15)
        c.drawCentredString(sx + (sw - 3) / 2, sy + 15.5 * mm, val)
        c.setFillColor(SLATE4)
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(sx + (sw - 3) / 2, sy + 8.5 * mm, lbl)

    # Section label: H-105mm
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(24 * mm, H - 105 * mm, "EVERYTHING IN PRO  —  AVAILABLE TODAY")
    c.setFillColor(BORDER)
    c.setLineWidth(0.5)
    c.line(24 * mm, H - 107.5 * mm, W - 24 * mm, H - 107.5 * mm)

    # Features 2-col: top of row-0 baseline = H-110mm, row_h=12.5mm
    feats = [
        ("AI Invoice Reader",           "Photo any bill — Claude extracts all fields automatically"),
        ("Sales Invoice Management",    "Add, edit, search invoices  ·  B2B / B2C / Export / Credit Note"),
        ("Purchase Invoice Mgmt",       "Inward invoices with RCM flag and GSTIN validation"),
        ("GSTR-1 Computation",          "Auto-categorises B2B, B2C, Exports; HSN/SAC summary"),
        ("GSTR-3B Computation",         "Net tax payable after ITC; section-wise breakdown"),
        ("GSTR-9 Annual Return",        "One-click aggregation of all 12 months; Table 4 breakdown"),
        ("GSTR-2B Reconciliation",      "Purchase vs supplier-filed: matched / mismatched / missing"),
        ("ITC Ledger",                  "12-month rolling ledger with running credit balance"),
        ("PDF Invoice Generation",      "Professional invoices with GSTIN, HSN, tax breakdown"),
        ("6-Month Trend Dashboard",     "Visual chart: tax liability, ITC, turnover trends"),
        ("Late Fee Calculator",         "Rs.50/day (capped Rs.10k) + 18% p.a. interest"),
        ("CSV Export",                  "One-click export of any invoice list"),
        ("Real-time GSTIN Validation",  "Format check on every form before portal rejection"),
    ]
    cw   = (W - 48 * mm) / 2
    rh   = 12.5 * mm
    top0 = H - 110 * mm
    for i, (name, desc) in enumerate(feats):
        col = i % 2
        row = i // 2
        fx  = 24 * mm + col * cw
        fy  = top0 - row * rh
        c.setFillColor(AMBER)
        c.circle(fx + 2.5 * mm, fy - 1.5 * mm, 1.8, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(fx + 6 * mm, fy, name)
        c.setFillColor(SLATE4)
        c.setFont("Helvetica", 6.5)
        c.drawString(fx + 6 * mm, fy - 5 * mm, desc)

    # CTA bar: bottom=H-210mm
    cb_y = H - 210 * mm
    c.setFillColor(AMBER)
    c.roundRect(W / 2 - 70 * mm, cb_y, 140 * mm, 12 * mm, 6, fill=1, stroke=0)
    c.setFillColor(BG)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(W / 2, cb_y + 4 * mm, "Start your FREE 1-month Pro trial  —  bemyca.cloud")


# ── PAGE 2: Feature detail cards ───────────────────────────────────────────────

def page2(c):
    draw_bg(c, 2)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 15)
    txt = "What's included in Pro"
    c.drawString(24 * mm, H - 16 * mm, txt)
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(24 * mm + c.stringWidth(txt, "Helvetica-Bold", 15) + 3, H - 16 * mm, " — available today")
    c.setFillColor(SLATE4)
    c.setFont("Helvetica", 7.5)
    c.drawString(24 * mm, H - 22 * mm, "13 features shipping now. No hidden paywalls within Pro.")

    features = [
        ("AI Invoice Reader",
         "Photograph any bill. Claude AI reads invoice no., GSTIN,",
         "HSN code, taxable value, IGST/CGST/SGST automatically."),
        ("Sales Invoice Management",
         "Add, edit, delete, search outward invoices. Categorise as",
         "B2B, B2C Large, B2C Small, Export, or Credit Note."),
        ("Purchase Invoice Management",
         "Inward invoices with RCM (Reverse Charge Mechanism) support.",
         "GSTIN validated on every entry before save."),
        ("GSTR-1 Computation",
         "Auto-categorises invoices into correct GSTR-1 sections.",
         "Table 12 HSN/SAC summary — ready for portal upload."),
        ("GSTR-3B Computation",
         "Computes net tax payable after ITC offset. Section-wise",
         "breakdown matches portal format exactly."),
        ("GSTR-9 Annual Return",
         "One-click aggregation of all 12 monthly returns. Table 4",
         "outward by type with month-wise filing status."),
        ("GSTR-2B Reconciliation",
         "Compares purchase register against supplier-filed data.",
         "Flags matched, mismatched, missing + IMS actions."),
        ("ITC Ledger (12-Month)",
         "Rolling ledger: ITC available, claimed, net cash paid,",
         "running credit balance — 12 months at a glance."),
        ("PDF Invoice Generation",
         "Generate professional invoices instantly. Includes GSTIN,",
         "HSN codes, full tax breakdown — downloadable."),
        ("6-Month Trend Dashboard",
         "Visual chart of tax liability, ITC claimed, and turnover.",
         "Spot seasonal patterns and cash flow trends."),
        ("Late Fee & Interest Calculator",
         "GSTR-1 and GSTR-3B fees (Rs.50/day, capped Rs.10,000).",
         "Plus 18% p.a. interest on delayed tax payments."),
        ("CSV Export",
         "One-click export of any invoice list as CSV.",
         "Sales or purchase data for your accountant."),
        ("Real-time GSTIN Validation",
         "Format-checks every GSTIN on every form. Catches errors",
         "before portal rejection — 15-digit, check digit, state code."),
    ]

    cols   = 2
    cw     = (W - 52 * mm) / 2
    card_h = 28 * mm
    gap_x  = 4 * mm
    gap_y  = 3 * mm
    # top of row-0 = H-28mm, so card bottom = H-28mm - card_h = H-56mm
    top0   = H - 28 * mm

    for i, (name, l1, l2) in enumerate(features):
        col = i % cols
        row = i // cols
        cx  = 24 * mm + col * (cw + gap_x)
        cy  = top0 - row * (card_h + gap_y) - card_h  # card bottom
        draw_card(c, cx, cy, cw, card_h, accent=AMBER)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(cx + 7 * mm, cy + card_h - 9 * mm, name)
        c.setFillColor(SLATE3)
        c.setFont("Helvetica", 6.5)
        c.drawString(cx + 7 * mm, cy + card_h - 15 * mm, l1)
        c.drawString(cx + 7 * mm, cy + card_h - 20 * mm, l2)


# ── PAGE 3: Comparison + Pricing ───────────────────────────────────────────────

def page3(c):
    draw_bg(c, 3)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(24 * mm, H - 16 * mm, "How BeMyCa compares")
    c.setFillColor(SLATE4)
    c.setFont("Helvetica", 7.5)
    c.drawString(24 * mm, H - 22 * mm, "Feature-for-feature. Rupee for Rupee.")

    # Comparison table ──────────────────────────────────────────────────────────
    headers = ["Feature", "BeMyCa Pro", "ClearTax", "Zoho Books", "Tally Prime", "Vyapar"]
    rows = [
        ["AI invoice photo reading",    "YES", "NO",       "NO",       "NO",  "NO"],
        ["GSTR-1 + 3B + 9",            "YES", "YES paid", "YES paid", "YES", "YES basic"],
        ["GSTR-2B reconciliation",      "YES", "YES paid", "NO",       "YES", "NO"],
        ["ITC ledger (12-month)",       "YES", "YES paid", "YES paid", "YES", "NO"],
        ["PDF invoice generation",      "YES", "NO",       "YES",      "NO",  "YES"],
        ["Late fee calculator",         "YES", "NO",       "NO",       "NO",  "NO"],
        ["Annual GSTR-9",               "YES", "YES paid", "NO",       "YES", "NO"],
        ["Direct portal filing (GSP)",  "Soon","YES",      "YES",      "YES", "NO"],
        ["Monthly price",               "Rs.999","Rs.1,249","Rs.749+","Rs.1,500","Rs.150+"],
    ]
    data    = [headers] + rows
    col_w   = [53 * mm, 25 * mm, 24 * mm, 26 * mm, 25 * mm, 22 * mm]
    row_h   = [8 * mm] + [7.5 * mm] * len(rows)

    tbl = Table(data, colWidths=col_w, rowHeights=row_h)
    style_cmds = [
        ("BACKGROUND",    (0, 0), (-1,  0), colors.HexColor("#182840")),
        ("TEXTCOLOR",     (0, 0), (-1,  0), AMBER),
        ("FONTNAME",      (0, 0), (-1,  0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1,  0), 7),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 7),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.HexColor("#1e293b"), colors.HexColor("#1a2232")]),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("ALIGN",         (0, 0), (0,  -1), "LEFT"),
        ("LEFTPADDING",   (0, 0), (0,  -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER),
    ]
    for r in range(1, len(data)):
        v = data[r][1]
        if v == "YES":
            style_cmds += [("TEXTCOLOR", (1, r), (1, r), GREEN),
                           ("FONTNAME",  (1, r), (1, r), "Helvetica-Bold")]
        elif v == "Soon":
            style_cmds += [("TEXTCOLOR", (1, r), (1, r), AMBER)]
        for col in range(2, 6):
            if data[r][col] == "NO":
                style_cmds += [("TEXTCOLOR", (col, r), (col, r), SLATE5)]
            elif data[r][col] in ("YES", "YES paid", "YES basic"):
                style_cmds += [("TEXTCOLOR", (col, r), (col, r), SLATE3)]

    tbl.setStyle(TableStyle(style_cmds))
    _tw, th = tbl.wrapOn(c, W, H)

    # Table top at H-27mm (just below header)
    tbl_top = H - 27 * mm
    tbl_bot = tbl_top - th          # pts from page bottom
    tbl.drawOn(c, 22 * mm, tbl_bot)

    # Pricing section ───────────────────────────────────────────────────────────
    gap_after_table = 7 * mm
    label_y   = tbl_bot - gap_after_table   # "Pricing" label baseline
    tier_h    = 47 * mm
    tier_top  = label_y - 5 * mm            # top of tier card area
    tier_bot  = tier_top - tier_h           # bottom of tier cards

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(24 * mm, label_y, "Pricing")

    tiers = [
        {
            "name":   "FREE TRIAL",
            "price":  "1 Month FREE",
            "sub":    "No credit card required",
            "accent": BLUE,
            "bg":     colors.HexColor("#0f1f3d"),
            "items":  ["Full Pro access", "All 13 features", "Expires after 30 days", "Upgrade anytime"],
        },
        {
            "name":   "PRO",
            "price":  "Rs.999 / month",
            "sub":    "or Rs.8,999/year  (save 25%)",
            "accent": AMBER,
            "bg":     colors.HexColor("#1a2a0a"),
            "items":  ["Everything in Free Trial", "Unlimited invoices", "Unlimited periods", "Priority support"],
        },
        {
            "name":   "ENTERPRISE",
            "price":  "Custom Pricing",
            "sub":    "For CAs managing 10+ clients",
            "accent": PURPLE,
            "bg":     colors.HexColor("#1a1030"),
            "items":  ["Multi-client dashboard", "Bulk filing", "Dedicated support", "Custom integrations"],
        },
    ]
    tier_w = (W - 52 * mm) / 3
    gap_x  = 2 * mm
    tx0    = 24 * mm

    for i, t in enumerate(tiers):
        tx = tx0 + i * (tier_w + gap_x)
        ty = tier_bot
        c.setFillColor(t["bg"])
        c.roundRect(tx, ty, tier_w, tier_h, 7, fill=1, stroke=0)
        c.setStrokeColor(t["accent"])
        c.setLineWidth(1)
        c.roundRect(tx, ty, tier_w, tier_h, 7, fill=0, stroke=1)
        c.setFillColor(t["accent"])
        c.roundRect(tx, ty + tier_h - 4, tier_w, 4, 3, fill=1, stroke=0)

        c.setFillColor(t["accent"])
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(tx + tier_w / 2, ty + tier_h - 11 * mm, t["name"])
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(tx + tier_w / 2, ty + tier_h - 18 * mm, t["price"])
        c.setFillColor(SLATE4)
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(tx + tier_w / 2, ty + tier_h - 23 * mm, t["sub"])
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.4)
        c.line(tx + 4 * mm, ty + tier_h - 26 * mm, tx + tier_w - 4 * mm, ty + tier_h - 26 * mm)
        for j, item in enumerate(t["items"]):
            iy = ty + tier_h - 31 * mm - j * 7
            c.setFillColor(t["accent"])
            c.circle(tx + 6 * mm, iy + 2, 2, fill=1, stroke=0)
            c.setFillColor(SLATE3)
            c.setFont("Helvetica", 6.5)
            c.drawString(tx + 10 * mm, iy, item)

    # Why not free ──────────────────────────────────────────────────────────────
    wf_h   = 22 * mm
    wf_bot = tier_bot - 6 * mm - wf_h
    c.setFillColor(colors.HexColor("#1c1208"))
    c.roundRect(24 * mm, wf_bot, W - 48 * mm, wf_h, 5, fill=1, stroke=0)
    c.setStrokeColor(AMBER_DIM)
    c.setLineWidth(0.8)
    c.roundRect(24 * mm, wf_bot, W - 48 * mm, wf_h, 5, fill=0, stroke=1)
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(28 * mm, wf_bot + wf_h - 7 * mm, "Why not free?")
    c.setFillColor(SLATE3)
    c.setFont("Helvetica", 7)
    c.drawString(28 * mm, wf_bot + wf_h - 13 * mm,
                 "Free tools cut corners. We invest in AI infrastructure, GSP API integrations,")
    c.drawString(28 * mm, wf_bot + wf_h - 19 * mm,
                 "and compliance updates. Rs.999/month is less than one CA consultation.")

    # Quote
    c.setFillColor(SLATE4)
    c.setFont("Helvetica", 7)
    c.drawString(24 * mm, wf_bot - 7 * mm,
                 '"ClearTax charges Rs.14,999/year and doesn\'t read your invoices.')
    c.drawString(24 * mm, wf_bot - 13 * mm,
                 ' Tally costs Rs.18,000 upfront. BeMyCa Pro: Rs.999/month, with AI, from day one."')


# ── PAGE 4: Roadmap + CTA ──────────────────────────────────────────────────────

def page4(c):
    draw_bg(c, 4)

    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(24 * mm, H - 16 * mm, "What's next  —  GSP API Integration")
    c.setFillColor(AMBER)
    c.setFont("Helvetica", 8)
    c.drawString(24 * mm, H - 22 * mm, "Pro roadmap  ·  Direct portal filing without manual re-entry")

    roadmap = [
        ("Direct GSTR-1 Filing",
         "Submit GSTR-1 directly to GST portal via GSP API — no manual copy-paste.",
         "Status: In development  ·  Requires GSP tie-up (IRIS Business / ClearTax)"),
        ("Direct GSTR-3B Filing",
         "File GSTR-3B with EVC/OTP authentication. Tax liability submitted in one flow.",
         "Status: Planned  ·  EVC integration after GSTR-1 filing ships"),
        ("Auto GSTR-2B Pull",
         "Automatically fetch GSTR-2B on the 14th each month — zero manual download.",
         "Status: Planned  ·  Available after GSP credentials provisioned"),
        ("Live GSTIN Verification",
         "Verify GSTIN against live GSTN database — catch deregistered suppliers instantly.",
         "Status: Planned  ·  GSP lookup API"),
        ("Tax Payment Initiation",
         "Generate challan and initiate NEFT/RTGS/Net Banking payment directly.",
         "Status: Roadmap  ·  Requires GSTN payment gateway integration"),
    ]

    rw      = W - 48 * mm
    rx      = 24 * mm
    rh      = 24 * mm
    gap     = 4 * mm
    top0    = H - 28 * mm   # top of first card

    for i, (name, desc, status) in enumerate(roadmap):
        cy = top0 - i * (rh + gap) - rh    # card bottom
        draw_card(c, rx, cy, rw, rh, accent=AMBER_DIM)
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(rx + 6 * mm, cy + rh - 10 * mm, str(i + 1))
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(rx + 15 * mm, cy + rh - 10 * mm, name)
        c.setFillColor(SLATE3)
        c.setFont("Helvetica", 7)
        c.drawString(rx + 15 * mm, cy + rh - 16 * mm, desc)
        c.setFillColor(SLATE5)
        c.setFont("Helvetica", 6.5)
        c.drawString(rx + 15 * mm, cy + rh - 21 * mm, status)

    # last card bottom
    last_bot = top0 - 4 * (rh + gap) - rh

    # CTA block
    cta_h   = 32 * mm
    cta_bot = last_bot - 10 * mm - cta_h
    c.setFillColor(colors.HexColor("#1a2a0a"))
    c.roundRect(20 * mm, cta_bot, W - 40 * mm, cta_h, 8, fill=1, stroke=0)
    c.setStrokeColor(AMBER)
    c.setLineWidth(1.5)
    c.roundRect(20 * mm, cta_bot, W - 40 * mm, cta_h, 8, fill=0, stroke=1)
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(W / 2, cta_bot + cta_h - 11 * mm, "Start your free 1-month Pro trial")
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(W / 2, cta_bot + cta_h - 20 * mm, "bemyca.cloud")
    c.setFillColor(SLATE4)
    c.setFont("Helvetica", 7.5)
    c.drawCentredString(W / 2, cta_bot + cta_h - 27 * mm,
                        "No credit card required  ·  All 13 Pro features  ·  Cancel anytime")

    # Footer
    footer_y = cta_bot - 10 * mm
    c.setFillColor(BORDER)
    c.setLineWidth(0.4)
    c.line(24 * mm, footer_y, W - 24 * mm, footer_y)
    c.setFillColor(SLATE5)
    c.setFont("Helvetica", 7)
    c.drawString(24 * mm, footer_y - 6 * mm,
                 "BeMyCa  ·  bemyca.cloud  ·  GST filing for Indian businesses")
    c.drawRightString(W - 24 * mm, footer_y - 6 * mm, "© 2025 BeMyCa. All rights reserved.")


# ── Build ──────────────────────────────────────────────────────────────────────

cv = canvas.Canvas(OUT, pagesize=A4)
page1(cv); cv.showPage()
page2(cv); cv.showPage()
page3(cv); cv.showPage()
page4(cv); cv.showPage()
cv.save()
print(f"Saved: {OUT}")
