from reportlab.platypus import Paragraph, Spacer, Image
from ..styles import TITLE, BODY, SMALL, BOLD


def build_summary(data):
    story = []

    story.append(Paragraph("Feasibility Result", TITLE))
    story.append(Spacer(1, 20))

    story.append(Paragraph(f"Airport: {data['airport_name']}", BOLD))
    story.append(Paragraph(f"Coordinates: {data['coordinates']}", BODY))

    story.append(Spacer(1, 10))

    story.append(Paragraph(f"Daily requirement: {data['required_operation']}", BODY))
    story.append(Paragraph(f"Blackout risk: {data['worst_blackout_risk']}", BODY))

    story.append(Spacer(1, 20))

    if data["map_image_path"]:
        story.append(Image(data["map_image_path"], width=300, height=200))

    if data["monthly_chart_path"]:
        story.append(Image(data["monthly_chart_path"], width=400, height=200))

    if data["annual_profile_chart_path"]:
        story.append(Image(data["annual_profile_chart_path"], width=400, height=200))

    return story
