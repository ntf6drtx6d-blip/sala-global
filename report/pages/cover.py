from pathlib import Path

from reportlab.platypus import Image, PageBreak, Paragraph, Spacer, Table, TableStyle

from ..assets.maps import generate_static_map
from ..layout import HALF_WIDTH, card, header_row, page_footer, page_title, quiet_table, summary_strip, two_col
from ..styles import BODY, BODY_BOLD, SMALL, SMALL_BOLD, BORDER, SPACE_3

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


def _safe_img(path: Path, width: int, height: int):
    if path.exists():
        img = Image(str(path))
        img._restrictSize(width, height)
        return img
    return Paragraph("", BODY)


def build_cover(data):
    story = []

    sala_logo = _safe_img(ASSET_DIR / "sala_logo.png", 75, 34)
    jrc_logo = _safe_img(ASSET_DIR / "jrc_logo.jpg", 105, 34)
    topbar = Table(
        [[sala_logo, Paragraph("SALA Standardized Feasibility Study for Solar AGL", SMALL_BOLD), jrc_logo]],
        colWidths=[82, 328, 105],
    )
    topbar.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.7, BORDER),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(topbar)
    story.append(Spacer(1, 14))

    story.append(page_title("Solar Airfield Lighting Feasibility Study"))
    story.append(Spacer(1, SPACE_3))

    map_path = generate_static_map(data["lat"], data["lon"], width=700, height=380, zoom=9)
    map_img = Image(map_path)
    map_img._restrictSize(HALF_WIDTH - 20, 150)

    left = card(
        [
            Paragraph(data["airport_name"], BODY_BOLD),
            Spacer(1, 4),
            Paragraph(data["coordinates"], BODY),
            Spacer(1, 4),
            Paragraph(data["date"], BODY),
            Spacer(1, 10),
            summary_strip(data["cover_verdict"], data["overall_result_label"]),
        ],
        HALF_WIDTH,
        padding=14,
    )

    device_rows = [[d["name"], d["result_label"]] for d in data["devices"]]
    right = card(
        [
            Paragraph("Location and device result", SMALL_BOLD),
            Spacer(1, 8),
            map_img,
            Spacer(1, 8),
            quiet_table(device_rows, widths=[HALF_WIDTH * 0.68, HALF_WIDTH * 0.32], header=["Device", "Result"]),
        ],
        HALF_WIDTH,
        padding=14,
    )
    story.append(two_col(left, right))
    story.append(Spacer(1, 10))

    meta_rows = [
        ["Project / Airport", data["airport_name"]],
        ["Coordinates", data["coordinates"]],
        ["Required operating profile", data["required_operation"]],
        ["Generated with SALA by", data.get("generated_by", "")],
        ["Organization", data.get("generated_for_organization", "—")],
        ["Document ID", data["report_id"]],
    ]
    story.append(card([quiet_table(meta_rows, widths=[165, 330])], 515, padding=0))
    story.append(Spacer(1, 10))

    story.append(summary_strip(data["cover_statement"], data["overall_result_label"]))
    story.append(Spacer(1, 18))
    story.append(page_footer(data["footer_note"], "Page 1"))
    story.append(PageBreak())
    return story
