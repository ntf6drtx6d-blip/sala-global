# report.py
import os, io
from datetime import datetime

from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm

# локальні імпорти
from utils import fmt_dec, build_map_image, add_round_corners_and_shadow

# графік
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

S4GA_NAVY = colors.HexColor("#000323")
S4GA_GOLD = colors.HexColor("#FFCB05")
SHADE_BG  = colors.HexColor("#F5F6F7")

MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

# ---------- PDF canvas з нумерацією ----------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()
    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_number(page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
    def _draw_page_number(self, page_count):
        page = self.getPageNumber()
        txt = f"{page} of {page_count}"
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.grey)
        w, _ = A4
        self.drawRightString(w - 15*mm, 10*mm, txt)

def hrule(width):
    t = Table([[""]], colWidths=[width], rowHeights=[2])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1), colors.HexColor("#E9EBEF"))]))
    return t

def _register_brand_heading_font():
    candidates = [
        "Montserrat-Bold.ttf",
        "fonts/Montserrat-Bold.ttf",
        os.path.expanduser("~/.fonts/Montserrat-Bold.ttf"),
        "/Library/Fonts/Montserrat-Bold.ttf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-Bold.ttf",
    ]
    for p in candidates:
        try:
            if os.path.exists(p):
                pdfmetrics.registerFont(TTFont("Montserrat-Bold", p))
                return "Montserrat-Bold"
        except Exception:
            pass
    return "Helvetica-Bold"

# ---------- плейсхолдер лише як останній шанс ----------
def build_map_placeholder(lat, lon, w=2000, h=1300):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGBA", (w, h), (240, 244, 247, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([8,8,w-8,h-8], outline=(210,215,220,255), width=2)
    txt = f"Map unavailable\nlat={lat:.4f}, lon={lon:.4f}"
    try:
        font = ImageFont.truetype("/Library/Fonts/Arial.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    tw, th, _, _ = d.multiline_textbbox((0,0), txt, font=font, align="center")
    d.multiline_text(((w-tw)//2, (h-th)//2), txt, fill=(90,90,95,255), font=font, align="center", spacing=6)
    bio = io.BytesIO()
    im.save(bio, "PNG"); bio.seek(0)
    return bio

# ---------- графік ----------
def build_plot(loc_label, required_hrs, sim_results):
    plt.figure(figsize=(10, 3.8), dpi=170)
    ax = plt.gca()
    ax.set_axisbelow(True)
    ax.grid(True, axis="y", alpha=0.22, zorder=1)

    for name, r in sim_results.items():
        ax.plot(MONTHS, r["hours"], marker="o", linewidth=2.4, markersize=5, label=name, zorder=3)

    ax.axhline(required_hrs, linestyle=(0, (6, 4)), linewidth=3.0, color="black", alpha=0.9,
               label=f"Required hrs ({fmt_dec(required_hrs)})", zorder=5, clip_on=False)

    ax.set_ylim(0, 24)
    ax.set_yticks(range(0, 25, 4))
    ax.set_ylabel("hrs/day")
    ax.set_title(f"Solar Autonomy (Guaranteed Operating Hours) – {loc_label}")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if len(sim_results) > 0:
        leg = ax.legend(loc="upper right", frameon=True, framealpha=0.95)
        leg.get_frame().set_linewidth(0.4)

    bio = io.BytesIO()
    plt.tight_layout()
    plt.savefig(bio, format="png", dpi=170)
    plt.close()
    bio.seek(0)
    return bio

# ---------- основний PDF ----------
def make_pdf(out_path, loc, required_hrs, results, overall, worst_name, worst_gap,
             header_tilt_text, airport_label, date_for_header, az_override):

    doc = SimpleDocTemplate(str(out_path), pagesize=A4,
                            leftMargin=14*mm, rightMargin=14*mm,
                            topMargin=10*mm, bottomMargin=12*mm)
    story = []

    brand_heading_font = _register_brand_heading_font()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="H1", fontName=brand_heading_font, fontSize=22, leading=26,
        alignment=TA_CENTER, textColor=S4GA_GOLD, spaceBefore=0, spaceAfter=0
    ))
    styles.add(ParagraphStyle(name="H2", fontSize=12, leading=14, textColor=colors.white))
    styles.add(ParagraphStyle(name="B", fontSize=10, leading=12))
    styles.add(ParagraphStyle(name="Small", fontSize=8, leading=10, textColor=colors.grey))
    styles.add(ParagraphStyle(name="Tiny", fontSize=7.5, leading=9, textColor=colors.grey))
    styles.add(ParagraphStyle(name="TH", fontSize=8.5, leading=10, alignment=TA_CENTER, wordWrap='LTR'))
    styles.add(ParagraphStyle(name="InfoWrap", fontSize=9, leading=11, wordWrap='LTR'))
    styles.add(ParagraphStyle(name="Note", fontSize=9, leading=12))

    # --- Header ---
    title = f"Solar Feasibility Study for {airport_label}" if airport_label else "Solar Feasibility Study – Off-grid PV System"
    hdr = Table([[Paragraph(title, styles["H1"])]], colWidths=[doc.width])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,0), S4GA_NAVY),
        ("ALIGN",(0,0),(0,0),"CENTER"),
        ("TOPPADDING",(0,0),(-1,-1),12),
        ("BOTTOMPADDING",(0,0),(-1,-1),12),
    ]))
    story += [hdr, Spacer(1,4*mm)]

    # --- Map + Info card ---
    try:
        if os.getenv("S4GA_DISABLE_MAP") == "1":
            raise RuntimeError("S4GA_DISABLE_MAP=1")
        raw_map = build_map_image(loc["lat"], loc["lon"], zoom=6, px_width=2000, px_height=1300, draw_pin=True)
        map_img_bytes = add_round_corners_and_shadow(raw_map, radius=14, shadow=10)
    except Exception as e:
        print(f"[WARN] Map placeholder used: {e}")
        map_img_bytes = build_map_placeholder(loc["lat"], loc["lon"], w=2000, h=1300)

    left_w  = doc.width * (1/3)
    left_h  = left_w * (3/5)
    left_flow = RLImage(map_img_bytes, width=left_w, height=left_h)

    method_text = (
        "PVGIS off-grid autonomy (tn=0), 24h flat load — using the European Commission’s PVGIS data, "
        "which combines 15+ years (2005–2020) of satellite-derived solar radiation (SARAH-2/SARAH-3) "
        "and reanalysis (ERA5, ERA5-Land)."
    )

    if len(results) == 1:
        only_name = next(iter(results))
        header_az_text = f"{int(round(results[only_name]['azim']))}°"
    elif len(results) > 1:
        az_set = {int(round(r['azim'])) for r in results.values()}
        header_az_text = f"{list(az_set)[0]}°" if len(az_set) == 1 else "varies (see table)"
    else:
        header_az_text = "–"

    info_data = [
        ["Location", f"{loc['label']}"],
        ["Coordinates", f"{fmt_dec(loc['lat'])}, {fmt_dec(loc['lon'])}"],
        ["Generated", date_for_header],
        ["Required hrs", f"{fmt_dec(required_hrs)} hrs/day"],
        ["Base tilt", header_tilt_text],
        ["Azimuth (mode)", f"{header_az_text} ({'Manual' if az_override is not None else 'Auto'})"],
        ["Method", Paragraph(method_text, styles["InfoWrap"])],
    ]
    info_tbl = Table(info_data, colWidths=[28*mm, doc.width*(2/3)-28*mm])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(0,-1), colors.HexColor("#F2F4F6")),
        ("BOX",(0,0),(-1,-1),0.25, colors.lightgrey),
        ("INNERGRID",(0,0),(-1,-1),0.25, colors.lightgrey),
        ("ALIGN",(0,0),(0,-1),"RIGHT"),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
        ("FONTSIZE",(0,0),(-1,-1),9),
        ("TOPPADDING",(0,0),(-1,-1),3),
        ("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("LEFTPADDING",(0,0),(-1,-1),6),
        ("RIGHTPADDING",(0,0),(-1,-1),6),
    ]))

    two_col = Table([[left_flow, info_tbl]], colWidths=[doc.width*(1/3), doc.width*(2/3)])
    two_col.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP")]))
    story += [two_col, Spacer(1,4*mm), hrule(doc.width), Spacer(1,3*mm)]

    # --- Explanation
    expl_para = Paragraph(
        "<b>Solar autonomy</b> = guaranteed daily hours without blackout. Panels recharge the battery; reserve covers cloudy days.",
        styles["Note"]
    )
    expl_box = Table([[expl_para]], colWidths=[doc.width])
    expl_box.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), SHADE_BG),
        ("BOX",(0,0),(-1,-1), 0.25, colors.lightgrey),
        ("LEFTPADDING",(0,0),(-1,-1),10),
        ("RIGHTPADDING",(0,0),(-1,-1),10),
        ("TOPPADDING",(0,0),(-1,-1),8),
        ("BOTTOMPADDING",(0,0),(-1,-1),8),
    ]))
    story += [expl_box, Spacer(1, 3*mm)]

    # --- Plot
    plot_img = build_plot(loc["label"], required_hrs, results)
    story += [RLImage(plot_img, width=doc.width, height=65*mm), Spacer(1,4*mm)]

    # --- PASS/FAIL banner
    failing = [name for name,r in results.items() if r["status"]=="FAIL"]
    left_label = Paragraph(f"OVERALL: {overall}", styles["H2"])
    right_txt = (f"Devices not meeting required hrs: {len(failing)} of {len(results)} — " + ", ".join(failing)) if failing else "All devices meet required hrs"
    ban = Table([[left_label, Paragraph(right_txt, styles["H2"])]],
                colWidths=[doc.width*0.32, doc.width*0.68])
    ban.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), colors.HexColor("#B00020") if overall=="FAIL" else colors.HexColor("#2E7D32")),
        ("TEXTCOLOR",(0,0),(-1, -1), colors.white),
        ("ALIGN",(0,0),(0,-1),"LEFT"),
        ("ALIGN",(1,0),(1,-1),"RIGHT"),
        ("TOPPADDING",(0,0),(-1,-1),6),
        ("BOTTOMPADDING",(0,0),(-1,-1),6),
        ("LEFTPADDING",(0,0),(-1,-1),10),
        ("RIGHTPADDING",(0,0),(-1,-1),10),
    ]))
    story += [ban, Spacer(1,3*mm)]

    # --- Summary table
    sum_hdr_labels = ["Device","Engine","PV","Battery","Tilt","Azimuth","Lowest-month difference (hrs)","Status","Fail months","Power consumption (W)"]
    sum_hdr = [Paragraph(t, styles["TH"]) for t in sum_hdr_labels]
    sum_rows = [sum_hdr]
    for name, r in results.items():
        fm_txt = "–" if not r["fail_months"] else ", ".join(r["fail_months"])
        fm_cell = Paragraph(fm_txt, styles["InfoWrap"])
        sum_rows.append([
            name, r["engine"], f"{r['pv']} W", f"{r['batt']} Wh", f"{r['tilt']}°", f"{int(round(r['azim']))}°",
            f"{fmt_dec(r['min_margin'])} hrs", r["status"], fm_cell, f"{fmt_dec(r['power'])}"
        ])

    weights = [16, 16, 8, 14, 7, 8, 17, 7, 17, 10]
    total_w = sum(weights)
    col_widths = [float(doc.width) * (w / total_w) for w in weights]

    sum_tbl = Table(sum_rows, colWidths=col_widths, repeatRows=1)
    sum_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#388E3C") if overall=="PASS" else colors.HexColor("#E53935")),
        ("TEXTCOLOR",(0,0),(-1,0), colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,0),9),
        ("TOPPADDING",(0,0),(-1,0),5),
        ("BOTTOMPADDING",(0,0),(-1,0),5),

        ("ALIGN",(2,1),(2,-1),"RIGHT"),
        ("ALIGN",(3,1),(3,-1),"RIGHT"),
        ("ALIGN",(4,1),(6,-1),"RIGHT"),
        ("ALIGN",(8,1),(8,-1),"LEFT"),
        ("ALIGN",(-1,1),(-1,-1),"RIGHT"),

        ("FONTSIZE",(0,1),(-1,-1),8.5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.whitesmoke, colors.white]),
        ("BOX",(0,0),(-1,-1),0.25, colors.lightgrey),
        ("INNERGRID",(0,0),(-1,-1),0.25, colors.lightgrey),
        ("LEFTPADDING",(0,0),(-1,-1),5),
        ("RIGHTPADDING",(0,0),(-1,-1),5),
    ]))
    story += [sum_tbl, Spacer(1,2*mm)]

    legend = Paragraph(
        "<b>Lowest-month difference (hrs)</b> = how many hours the weakest month is above/below the requirement (positive = surplus).",
        styles["Small"]
    )
    story += [legend, Spacer(1,4*mm)]

    # --- Monthly table
    ordered_names = list(results.keys())
    months_hdr_labels = ["Month", "Required (Hrs)"] + ordered_names
    months_hdr = [Paragraph(t, styles["TH"]) for t in months_hdr_labels]

    m_rows = [months_hdr]
    for i, m in enumerate(MONTHS):
        row = [m, fmt_dec(required_hrs)] + [fmt_dec(results[name]["hours"][i]) for name in ordered_names]
        m_rows.append(row)

    colW = [doc.width*(1/(len(months_hdr_labels)+0.5))]*(len(months_hdr_labels))
    m_tbl = Table(m_rows, colWidths=colW, repeatRows=1, splitByRow=1)
    m_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#eeeeee")),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("BOX",(0,0),(-1,-1),0.25, colors.lightgrey),
        ("INNERGRID",(0,0),(-1,-1),0.25, colors.lightgrey),
        ("FONTSIZE",(0,0),(-1,-1),8.3),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story += [m_tbl, Spacer(1,3*mm)]

    # --- footer
    foot = (
        f"Source & Methodology — Location: {loc['label']} • Data: PVGIS (SARAH-2/3, ERA5/ERA5-Land, 2005–2020) • "
        f"Model: off-grid autonomy (tn=0), 24h flat load • Evaluation: PASS/FAIL by lowest-month vs required hrs."
    )
    foot_tbl = Table([[Paragraph(foot, styles["Tiny"])]], colWidths=[doc.width])
    foot_tbl.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1), colors.whitesmoke),
        ("BOX",(0,0),(-1,-1),0.25, colors.lightgrey),
        ("TOPPADDING",(0,0),(-1,-1),3), ("BOTTOMPADDING",(0,0),(-1,-1),3),
        ("LEFTPADDING",(0,0),(-1,-1),6), ("RIGHTPADDING",(0,0),(-1,-1),6),
    ]))
    story += [foot_tbl]

    doc.build(story, canvasmaker=NumberedCanvas)
