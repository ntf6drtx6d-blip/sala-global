import os
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth

from .theme import WHITE, LINE, TEXT, MUTED, NAVY


def draw_round_rect(c, x, y, w, h, r=14, fill_color=WHITE, stroke_color=LINE, stroke=1, fill=1, line_width=1):
    c.setLineWidth(line_width)
    c.setStrokeColor(stroke_color)
    c.setFillColor(fill_color)
    c.roundRect(x, y, w, h, r, stroke=stroke, fill=fill)


def draw_text(c, x, y, text, size=11, color=TEXT, font="Helvetica", max_width=None, leading=None):
    c.setFillColor(color)
    c.setFont(font, size)

    if max_width is None:
        c.drawString(x, y, str(text))
        return y

    if leading is None:
        leading = size * 1.35

    words = str(text).split()
    line = ""
    yy = y

    for word in words:
        candidate = (line + " " + word).strip()
        if stringWidth(candidate, font, size) <= max_width:
            line = candidate
        else:
            if line:
                c.drawString(x, yy, line)
                yy -= leading
            line = word

    if line:
        c.drawString(x, yy, line)

    return yy


def draw_title(c, x, y, text, size=28, color=NAVY, max_width=None, leading=None):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", size)

    if max_width is None:
        c.drawString(x, y, str(text))
        return y

    return draw_text(
        c,
        x,
        y,
        text,
        size=size,
        color=color,
        font="Helvetica-Bold",
        max_width=max_width,
        leading=leading or size * 1.08,
    )


def draw_small_caps(c, x, y, text, size=10, color=MUTED):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, str(text).upper())


def draw_label_value(c, x, y, label, value, label_w=110, value_size=10.8):
    c.setFont("Helvetica-Bold", 9.2)
    c.setFillColor(MUTED)
    c.drawString(x, y, str(label).upper())

    c.setFont("Helvetica", value_size)
    c.setFillColor(TEXT)
    c.drawString(x + label_w, y, str(value))


def draw_logo(c, path, x, y, w=None, h=None):
    if not path or not os.path.exists(path):
        return

    img = ImageReader(path)
    iw, ih = img.getSize()

    if w and not h:
        h = w * ih / iw
    elif h and not w:
        w = h * iw / ih
    elif not w and not h:
        w, h = iw, ih

    c.drawImage(img, x, y, width=w, height=h, mask="auto")
