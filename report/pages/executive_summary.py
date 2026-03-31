from reportlab.platypus import Paragraph, Spacer, Table, PageBreak
from ..styles import TITLE, BODY, BOLD

def build_summary(data):
    rows = [["Device", "Days", "Result"]]
    for d in data["devices"]:
        rows.append([d["name"], str(d["days"]), d["status"]])

    return [
        Paragraph("Executive Summary", TITLE),
        Spacer(1, 12),
        Paragraph(f"{data['pass_count']} of {data['total']} devices meet requirement", BOLD),
        Spacer(1, 10),
        Paragraph(f"Required: {data['required']} hrs/day", BODY),
        Paragraph(f"Days with 0% battery depletion: {data['max_blackout']} days/year", BODY),
        Spacer(1, 12),
        Table(rows),
        PageBreak()
    ]
