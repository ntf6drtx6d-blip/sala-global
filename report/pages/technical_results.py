from reportlab.platypus import Paragraph, Spacer, Image, PageBreak
from ..layout import card, page_footer, page_title
from ..styles import CARD_TITLE, SMALL, PAGE_WIDTH, SPACE_3
from ..assets.charts import generate_blackout_chart, generate_profile_chart


def build_technical(data):
    story = [page_title("Technical Results"), Spacer(1, SPACE_3)]

    if data["show_blackout_chart"]:
        blackout_path = generate_blackout_chart(data["devices"])
        img = Image(blackout_path)
        img._restrictSize(495, 180)
        story.append(card([Paragraph("Days with 0% battery depletion", CARD_TITLE), Spacer(1, 6), img], PAGE_WIDTH))
        story.append(Spacer(1, 10))
    else:
        story.append(card([Paragraph("Days with 0% battery depletion", CARD_TITLE), Spacer(1, 4), Paragraph("No battery depletion is expected for any evaluated device.", SMALL)], PAGE_WIDTH))
        story.append(Spacer(1, 10))

    if data.get("show_profile_chart", True):
        profile_path = generate_profile_chart(data["devices"], data["required_hours"])
        pimg = Image(profile_path)
        pimg._restrictSize(495, 210)
        story.append(card([Paragraph("Annual operating profile", CARD_TITLE), Spacer(1, 6), pimg], PAGE_WIDTH))
    else:
        story.append(
            card(
                [
                    Paragraph("Annual operating profile", CARD_TITLE),
                    Spacer(1, 4),
                    Paragraph(
                        "The annual operating profile chart is omitted because blackout exposure is zero and battery reserve remains consistently high across the year.",
                        SMALL,
                    ),
                ],
                PAGE_WIDTH,
            )
        )

    story.append(Spacer(1, 16))
    story.append(page_footer(data["footer_note"], "Page 3"))
    story.append(PageBreak())
    return story
