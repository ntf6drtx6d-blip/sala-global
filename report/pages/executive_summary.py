from reportlab.platypus import Paragraph, Spacer, Table, PageBreak
from ..styles import TITLE, BODY, BOLD

def build_summary(data):
    story = []

    story.append(Paragraph("Executive Summary", TITLE))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"{data['pass_count']} of {data['total']} devices meet requirement", BOLD))
    story.append(Spacer(1, 10))

    story.append(Paragraph(f"Required: {data['required']} hrs/day", BODY))
    story.append(Paragraph(f"Days with 0% battery depletion: {data['max_blackout']} days/year", BODY))

    story.append(Spacer(1, 12))

    table_data = [["Device", "Days", "Result"]]
    for d in data["devices"]:
        table_data.append([d["name"], str(d["days"]), d["status"]])

    table = Table(table_data)
    story.append(table)

    story.append(PageBreak())
    return story
