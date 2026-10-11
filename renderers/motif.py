"""Background motifs for the card renderers. Used on Sunday scripture days: --motif cross.

apply() inserts one quiet layer behind the type: a plain Latin cross in the palette's accent
colour, at low opacity, on the right of the safe area. It never enters the top or bottom safe
bands, and the type always sits above it.
"""
MOTIFS = ["none", "cross"]

def apply(html, motif, color, w, h, top, bot, right, opacity=0.13):
    if motif != "cross":
        return html
    ch = int((h - top - bot) * 0.62)
    cw = int(ch * 2 / 3)
    if cw > w * 0.5:
        cw = int(w * 0.5); ch = int(cw * 1.5)
    y = top + (h - top - bot - ch) // 2
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 300' width='%d' height='%d'>"
           "<rect x='88' y='0' width='24' height='300' fill='%s'/>"
           "<rect x='22' y='82' width='156' height='24' fill='%s'/></svg>" % (cw, ch, color, color))
    layer = ("<div style=\"position:absolute;z-index:1;pointer-events:none;top:%dpx;right:%dpx;"
             "width:%dpx;height:%dpx;opacity:%s\">%s</div>" % (y, right, cw, ch, opacity, svg))
    assert '<div class="card">' in html
    return html.replace('<div class="card">', '<div class="card">' + layer, 1)
