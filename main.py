# Republic of Sorvane — passport spread renderer.
# Stdlib-only: draws an invented passport's open spread (data page + visas
# page) into a pixel buffer and writes it as a PNG with zlib.
# Runs on Python 3.13 with no third-party packages, no network, no files.

import math
import os
import zlib

W = 1024
H = 1024


class Img:
    """RGB pixel buffer with alpha-blending puts."""

    def __init__(self, w, h, color):
        self.w = w
        self.h = h
        self.px = bytearray(color * (w * h))

    def put(self, x, y, r, g, b, a=255):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            if a >= 255:
                self.px[i] = r
                self.px[i + 1] = g
                self.px[i + 2] = b
            elif a > 0:
                ia = 255 - a
                self.px[i] = (self.px[i] * ia + r * a) // 255
                self.px[i + 1] = (self.px[i + 1] * ia + g * a) // 255
                self.px[i + 2] = (self.px[i + 2] * ia + b * a) // 255

    def fill_rect(self, x0, y0, x1, y1, color, a=255):
        x0 = max(0, int(x0)); y0 = max(0, int(y0))
        x1 = min(self.w, int(x1)); y1 = min(self.h, int(y1))
        if x1 <= x0 or y1 <= y0:
            return
        r, g, b = color
        if a >= 255:
            row = bytes(color) * (x1 - x0)
            for y in range(y0, y1):
                i = (y * self.w + x0) * 3
                self.px[i:i + len(row)] = row
        else:
            for y in range(y0, y1):
                for x in range(x0, x1):
                    self.put(x, y, r, g, b, a)


def stamp_disc(img, cx, cy, rad, color, a=255):
    r, g, b = color
    ir = int(rad)
    rr = rad * rad
    for dy in range(-ir, ir + 1):
        dx = int(math.sqrt(max(0.0, rr - dy * dy)))
        for x in range(int(cx) - dx, int(cx) + dx + 1):
            img.put(x, int(cy) + dy, r, g, b, a)


def line(img, x0, y0, x1, y1, color, wdt=1.0, a=255):
    dx = x1 - x0
    dy = y1 - y0
    steps = int(max(abs(dx), abs(dy))) + 1
    rad = max(0.4, wdt / 2.0)
    step = max(1, int(rad * 1.2))
    for i in range(0, steps + 1, step):
        t = i / steps if steps else 0.0
        stamp_disc(img, x0 + dx * t, y0 + dy * t, rad, color, a)
    stamp_disc(img, x1, y1, rad, color, a)


def polyline(img, pts, color, wdt=1.0, a=255, close=False):
    for i in range(len(pts) - 1):
        line(img, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], color, wdt, a)
    if close and len(pts) > 2:
        line(img, pts[-1][0], pts[-1][1], pts[0][0], pts[0][1], color, wdt, a)


def fill_polygon(img, pts, color, a=255):
    r, g, b = color
    ys = [p[1] for p in pts]
    y_lo = max(0, int(min(ys)))
    y_hi = min(img.h - 1, int(max(ys)))
    n = len(pts)
    for y in range(y_lo, y_hi + 1):
        yc = y + 0.5
        xs = []
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if (y0 <= yc < y1) or (y1 <= yc < y0):
                xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            xa = max(0, int(xs[i]))
            xb = min(img.w - 1, int(xs[i + 1]))
            for x in range(xa, xb + 1):
                img.put(x, y, r, g, b, a)


def fill_ellipse(img, cx, cy, rx, ry, color, a=255):
    r, g, b = color
    for dy in range(int(-ry), int(ry) + 1):
        t = dy / ry if ry else 0.0
        dx = rx * math.sqrt(max(0.0, 1.0 - t * t))
        y = int(cy + dy)
        for x in range(int(cx - dx), int(cx + dx) + 1):
            img.put(x, y, r, g, b, a)


def stroke_ellipse(img, cx, cy, rx, ry, color, wdt=1.0, a=255):
    steps = int(2 * math.pi * max(rx, ry) / 2) + 8
    pts = []
    for i in range(steps + 1):
        t = 2 * math.pi * i / steps
        pts.append((cx + rx * math.cos(t), cy + ry * math.sin(t)))
    polyline(img, pts, color, wdt, a)


def rect(img, x0, y0, x1, y1, color, wdt=1.0, a=255):
    line(img, x0, y0, x1, y0, color, wdt, a)
    line(img, x1, y0, x1, y1, color, wdt, a)
    line(img, x1, y1, x0, y1, color, wdt, a)
    line(img, x0, y1, x0, y0, color, wdt, a)


def rounded_rect(img, x0, y0, x1, y1, rad, color, wdt=1.0, a=255):
    line(img, x0 + rad, y0, x1 - rad, y0, color, wdt, a)
    line(img, x0 + rad, y1, x1 - rad, y1, color, wdt, a)
    line(img, x0, y0 + rad, x0, y1 - rad, color, wdt, a)
    line(img, x1, y0 + rad, x1, y1 - rad, color, wdt, a)
    for cx, cy, a0 in ((x0 + rad, y0 + rad, 180), (x1 - rad, y0 + rad, 270),
                       (x1 - rad, y1 - rad, 0), (x0 + rad, y1 - rad, 90)):
        pts = []
        for i in range(9):
            t = math.radians(a0 + i * 90 / 8)
            pts.append((cx + rad * math.cos(t), cy + rad * math.sin(t)))
        polyline(img, pts, color, wdt, a)


def bezier(img, p0, p1, p2, p3, color, wdt=1.0, a=255):
    pts = []
    steps = 40
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0]
        y = u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1]
        pts.append((x, y))
    polyline(img, pts, color, wdt, a)


def write_png(img, path):
    raw = bytearray()
    stride = img.w * 3
    for y in range(img.h):
        raw.append(0)
        raw += img.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = len(data).to_bytes(4, "big") + tag + data
        return out + (zlib.crc32(tag + data) & 0xFFFFFFFF).to_bytes(4, "big")

    ihdr = img.w.to_bytes(4, "big") + img.h.to_bytes(4, "big") + bytes([8, 2, 0, 0, 0])
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- font
# Geometric stroke font on a 10 x 14 grid (y down, baseline at 14).
# Each glyph is a list of polylines; each polyline is a list of (x, y).

GLYPHS = {
    "A": [[(0, 14), (5, 0), (10, 14)], [(2.4, 9), (7.6, 9)]],
    "B": [[(0, 0), (0, 14)], [(0, 0), (5.8, 0), (8.4, 2), (8.4, 5), (5.8, 7), (0, 7)],
          [(5.8, 7), (8.8, 9), (8.8, 12), (6.2, 14), (0, 14)]],
    "C": [[(9.2, 3.2), (6.2, 0.4), (3.2, 0.4), (0.6, 3.8), (0.6, 10.2), (3.2, 13.6), (6.2, 13.6), (9.2, 10.8)]],
    "D": [[(0, 0), (0, 14)], [(0, 0), (5.2, 0), (8.8, 3.8), (8.8, 10.2), (5.2, 14), (0, 14)]],
    "E": [[(9, 0), (0, 0), (0, 14), (9, 14)], [(0, 7), (6.4, 7)]],
    "F": [[(9, 0), (0, 0), (0, 14)], [(0, 7), (6.2, 7)]],
    "G": [[(9.2, 3.2), (6.2, 0.4), (3.2, 0.4), (0.6, 3.8), (0.6, 10.2), (3.2, 13.6), (6.6, 13.6), (9.4, 10.6), (9.4, 8.2), (6.2, 8.2)]],
    "H": [[(0, 0), (0, 14)], [(10, 0), (10, 14)], [(0, 7), (10, 7)]],
    "I": [[(5, 0), (5, 14)], [(2.2, 0), (7.8, 0)], [(2.2, 14), (7.8, 14)]],
    "J": [[(9, 0), (9, 10), (7.2, 13.4), (3.2, 13.6), (0.6, 11.2)]],
    "K": [[(0, 0), (0, 14)], [(9.2, 0), (1.2, 7.6)], [(3.6, 5.6), (9.6, 14)]],
    "L": [[(0, 0), (0, 14), (9, 14)]],
    "M": [[(0, 14), (0, 0), (5, 8), (10, 0), (10, 14)]],
    "N": [[(0, 14), (0, 0), (10, 14), (10, 0)]],
    "O": [[(5, 0), (8.4, 1.4), (9.8, 4.8), (9.8, 9.2), (8.4, 12.6), (5, 14), (1.6, 12.6), (0.2, 9.2), (0.2, 4.8), (1.6, 1.4), (5, 0)]],
    "P": [[(0, 14), (0, 0), (6, 0), (8.8, 2.4), (8.8, 5.2), (6, 7.6), (0, 7.6)]],
    "Q": [[(5, 0), (8.4, 1.4), (9.8, 4.8), (9.8, 9.2), (8.4, 12.6), (5, 14), (1.6, 12.6), (0.2, 9.2), (0.2, 4.8), (1.6, 1.4), (5, 0)],
          [(6.2, 10.2), (10.2, 14.6)]],
    "R": [[(0, 14), (0, 0), (6, 0), (8.8, 2.4), (8.8, 5.2), (6, 7.6), (0, 7.6)], [(5.4, 7.6), (9.6, 14)]],
    "S": [[(9, 2.6), (6.2, 0.3), (3, 0.5), (0.8, 3), (1.6, 6), (8.2, 8.4), (9, 11), (6.4, 13.8), (3, 13.8), (0.6, 11.4)]],
    "T": [[(0, 0), (10, 0)], [(5, 0), (5, 14)]],
    "U": [[(0, 0), (0, 9.8), (1.8, 13.2), (5, 14), (8.2, 13.2), (10, 9.8), (10, 0)]],
    "V": [[(0, 0), (5, 14), (10, 0)]],
    "W": [[(0, 0), (2.2, 14), (5, 4.5), (7.8, 14), (10, 0)]],
    "X": [[(0, 0), (10, 14)], [(10, 0), (0, 14)]],
    "Y": [[(0, 0), (5, 6.4)], [(10, 0), (5, 6.4), (5, 14)]],
    "Z": [[(0, 0), (10, 0), (0, 14), (10, 14)]],
    "0": [[(5, 0), (8, 1.4), (9.2, 4.8), (9.2, 9.2), (8, 12.6), (5, 14), (2, 12.6), (0.8, 9.2), (0.8, 4.8), (2, 1.4), (5, 0)]],
    "1": [[(3, 3.2), (6.2, 0), (6.2, 14)], [(3.2, 14), (9.2, 14)]],
    "2": [[(0.8, 3), (3, 0.5), (6.8, 0.5), (8.8, 3), (8.2, 6.6), (0.8, 14), (9.4, 14)]],
    "3": [[(0.8, 2.2), (3.6, 0.3), (6.8, 0.5), (8.8, 3.2), (6.2, 7)], [(6.2, 7), (8.8, 8.2), (8.8, 11.4), (6.4, 13.9), (3, 13.9), (0.8, 11.8)]],
    "4": [[(6.8, 14), (6.8, 0), (0, 10.2), (9.8, 10.2)]],
    "5": [[(9.2, 0), (1, 0), (1, 5.8), (6.4, 5.4), (8.8, 7.8), (8.4, 11.8), (5.8, 13.9), (1.6, 13.5), (0.6, 11)]],
    "6": [[(8.6, 2.2), (6, 0.3), (2.6, 2.8), (1, 7.8), (1, 10.8), (2.8, 13.7), (6.4, 13.8), (8.9, 11.2), (8.4, 8), (5.8, 6.4), (1.6, 7.4)]],
    "7": [[(0.4, 0), (9.6, 0), (4.4, 14)]],
    "8": [[(5, 7), (2.6, 5.6), (1, 2.6), (3, 0.3), (7, 0.3), (9, 2.6), (7.4, 5.6), (5, 7), (2.6, 8.4), (1, 11.4), (3, 13.8), (7, 13.8), (9, 11.4), (7.4, 8.4), (5, 7)]],
    "9": [[(1.4, 11.8), (4, 13.7), (7.4, 11.2), (9, 6.2), (9, 3.2), (7.2, 0.3), (3.6, 0.3), (0.9, 2.8), (1.6, 6), (4.2, 7.6), (8.4, 6.6)]],
    ".": [],
    ",": [[(5.6, 10.6), (4.6, 14.6)]],
    "-": [[(2, 7), (8, 7)]],
    "'": [[(5.2, 0), (4.6, 3.6)]],
    "/": [[(2, 14.6), (8, -0.6)]],
    "(": [[(7.2, 0), (4.2, 4), (4.2, 10), (7.2, 14)]],
    ")": [[(2.8, 0), (5.8, 4), (5.8, 10), (2.8, 14)]],
    ":": [],
    "<": [[(8.2, 2), (2, 7), (8.2, 12)]],
    ">": [[(1.8, 2), (8, 7), (1.8, 12)]],
    "+": [[(5, 3.4), (5, 10.6)], [(1.6, 7), (8.4, 7)]],
    "=": [[(2, 5), (8, 5)], [(2, 9.6), (8, 9.6)]],
    " ": [],
}


def text_size(text, h, spacing=0.0, mono=None):
    s = h / 14.0
    if mono:
        return len(text) * mono
    w = 0.0
    for ch in text:
        w += (6.5 if ch == " " else 10.0) * s + spacing
    return w - (spacing if text else 0.0)


def draw_text(img, x, y, text, h, color, wdt=None, spacing=0.0, align="left",
              mono=None, a=255):
    """Draw text with cap height h px; (x, y) is the top of the cap line."""
    s = h / 14.0
    if wdt is None:
        wdt = max(1.0, h * 0.115)
    total = text_size(text, h, spacing, mono)
    if align == "center":
        x -= total / 2.0
    elif align == "right":
        x -= total
    cx = x
    for ch in text.upper():
        if ch == ".":
            stamp_disc(img, cx + 5 * s, y + 13.2 * s, wdt * 0.62, color, a)
        elif ch == "·":
            stamp_disc(img, cx + 5 * s, y + 7 * s, wdt * 0.62, color, a)
        elif ch == ":":
            stamp_disc(img, cx + 5 * s, y + 4 * s, wdt * 0.62, color, a)
            stamp_disc(img, cx + 5 * s, y + 10.6 * s, wdt * 0.62, color, a)
        else:
            for pl in GLYPHS.get(ch, []):
                pts = [(cx + px * s, y + py * s) for (px, py) in pl]
                polyline(img, pts, color, wdt, a)
        if mono:
            cx += mono
        else:
            cx += (6.5 if ch == " " else 10.0) * s + spacing
    return total


def draw_dotted_text(img, x, y, text, h, color, align="left"):
    """Perforation-style text: dots along the glyph strokes."""
    s = h / 14.0
    total = text_size(text, h, 1.5)
    if align == "center":
        x -= total / 2.0
    elif align == "right":
        x -= total
    cx = x
    for ch in text.upper():
        for pl in GLYPHS.get(ch, []):
            for i in range(len(pl) - 1):
                x0, y0 = pl[i]
                x1, y1 = pl[i + 1]
                seg = math.hypot((x1 - x0) * s, (y1 - y0) * s)
                n = max(1, int(seg / (h * 0.30)))
                for k in range(n + 1):
                    t = k / n if n else 0
                    stamp_disc(img, cx + (x0 + (x1 - x0) * t) * s,
                               y + (y0 + (y1 - y0) * t) * s, h * 0.085, color)
        cx += (6.5 if ch == " " else 10.0) * s + 1.5


# ---------------------------------------------------------------- MRZ

def icao_value(ch):
    if ch.isdigit():
        return int(ch)
    if ch == "<":
        return 0
    return ord(ch) - 55  # A=10 .. Z=35


def icao_check(field):
    weights = (7, 3, 1)
    total = 0
    for i, ch in enumerate(field):
        total += icao_value(ch) * weights[i % 3]
    return str(total % 10)


DOC_NO = "S48291763"        # 9 chars, printed on the data page
SURNAME = "MAREN"
GIVEN = "JORIK TAL"
DOB_YYMMDD = "880504"       # 04 MAY 1988
EXP_YYMMDD = "330314"       # 14 MAR 2033
PERSONAL = "880504317<<<<<"  # 14 chars, digits echo the printed personal no.


def build_mrz():
    line2 = DOC_NO + icao_check(DOC_NO)
    line2 += "SVR"
    line2 += DOB_YYMMDD + icao_check(DOB_YYMMDD)
    line2 += "M"
    line2 += EXP_YYMMDD + icao_check(EXP_YYMMDD)
    line2 += PERSONAL + icao_check(PERSONAL)
    composite = line2[0:10] + line2[13:20] + line2[21:43]
    line2 += icao_check(composite)
    name = (SURNAME + "<<" + GIVEN.replace(" ", "<")).ljust(39, "<")
    line1 = "P<SVR" + name
    assert len(line1) == 44 and len(line2) == 44, (line1, line2)
    return line1, line2


# ---------------------------------------------------------------- art

PAPER = (244, 237, 219)
NAVY = (26, 40, 84)
INK = (32, 32, 38)
LABEL = (96, 104, 122)
RULE = (178, 168, 142)
BURG = (122, 30, 46)
GREEN = (28, 94, 60)
GOLD = (186, 138, 52)


def guilloche(img, x0, y0, x1, y1, phase=0.0):
    """Fine wavy security lines clipped to a page rectangle."""
    cols = [(226, 208, 188), (208, 218, 208), (220, 210, 198)]
    k = 0
    yy = y0 + 8
    while yy < y1 - 6:
        col = cols[k % 3]
        pts = []
        xx = x0 + 4
        while xx <= x1 - 4:
            pts.append((xx, yy + 3.2 * math.sin(xx * 0.021 + phase + k * 0.9)
                        + 1.4 * math.sin(xx * 0.006 + k * 2.1)))
            xx += 9
        polyline(img, pts, col, 0.8)
        yy += 13
        k += 1
    # rosette in a corner: overlapping circles
    for cx, cy, rr, col in ((x0 + 52, y1 - 58, 34, (224, 204, 196)),
                            (x1 - 52, y0 + 58, 30, (206, 216, 206))):
        for i in range(7):
            t = 2 * math.pi * i / 7
            stroke_ellipse(img, cx + 11 * math.cos(t), cy + 11 * math.sin(t),
                           rr * 0.62, rr * 0.62, col, 0.8)


def draw_emblem(img, cx, cy, r, a=255):
    """Circular emblem: lighthouse over waves, ring of stars."""
    stroke_ellipse(img, cx, cy, r, r, NAVY, 2.2, a)
    stroke_ellipse(img, cx, cy, r * 0.86, r * 0.86, NAVY, 1.1, a)
    for i in range(12):
        t = 2 * math.pi * i / 12
        stamp_disc(img, cx + r * 0.93 * math.cos(t), cy + r * 0.93 * math.sin(t),
                   r * 0.035, GOLD, a)
    # sun disc behind the lamp
    fill_ellipse(img, cx, cy - r * 0.30, r * 0.34, r * 0.34, (232, 190, 96), a)
    # light beams
    beam_l = [(cx - r * 0.10, cy - r * 0.34), (cx - r * 0.72, cy - r * 0.52),
              (cx - r * 0.72, cy - r * 0.16)]
    beam_r = [(cx + r * 0.10, cy - r * 0.34), (cx + r * 0.72, cy - r * 0.52),
              (cx + r * 0.72, cy - r * 0.16)]
    fill_polygon(img, beam_l, (238, 205, 120), a)
    fill_polygon(img, beam_r, (238, 205, 120), a)
    # lighthouse tower
    tw = r * 0.21
    tower = [(cx - tw, cy + r * 0.42), (cx - tw * 0.62, cy - r * 0.18),
             (cx + tw * 0.62, cy - r * 0.18), (cx + tw, cy + r * 0.42)]
    fill_polygon(img, tower, (250, 248, 240), a)
    for i, yy in enumerate((cy - r * 0.02, cy + r * 0.20)):
        band = [(cx - tw * (0.86 - i * 0.10), yy), (cx + tw * (0.86 - i * 0.10), yy),
                (cx + tw * (0.80 - i * 0.10), yy + r * 0.13), (cx - tw * (0.80 - i * 0.10), yy + r * 0.13)]
        fill_polygon(img, band, BURG, a)
    rect(img, cx - tw * 0.72, cy - r * 0.36, cx + tw * 0.72, cy - r * 0.16, NAVY, 1.4, a)
    stamp_disc(img, cx, cy - r * 0.26, r * 0.075, GOLD, a)
    # waves
    for j, wy in enumerate((cy + r * 0.52, cy + r * 0.66)):
        pts = []
        xx = cx - r * 0.62
        while xx <= cx + r * 0.62:
            pts.append((xx, wy + r * 0.05 * math.sin((xx - cx) * 0.09 + j * 1.7)))
            xx += 5
        polyline(img, pts, NAVY, 1.6, a)


def draw_portrait(img, cx, cy, w, alpha=255, backdrop=True):
    """Flat drawn portrait of the holder, centred at (cx, cy), w px wide."""
    h = w * 1.22
    x0, x1 = cx - w / 2, cx + w / 2
    y0, y1 = cy - h / 2, cy + h / 2
    if backdrop:
        for i in range(int(h)):
            t = i / h
            col = (int(198 + 18 * t), int(210 + 14 * t), int(222 + 10 * t))
            img.fill_rect(x0, y0 + i, x1, y0 + i + 1, col, alpha)
        for k in range(5):
            pts = []
            xx = x0 + 4
            while xx < x1 - 4:
                pts.append((xx, y0 + 16 + k * (h - 32) / 4 + 4 * math.sin(xx * 0.05 + k)))
                xx += 8
            polyline(img, pts, (176, 192, 208), 0.8, alpha)
    skin = (226, 178, 138)
    skin_sh = (206, 156, 116)
    hair = (70, 50, 34)
    # shoulders / jacket
    fill_polygon(img, [(x0 + w * 0.06, y1), (cx - w * 0.16, cy + h * 0.28),
                       (cx + w * 0.16, cy + h * 0.28), (x1 - w * 0.06, y1)],
                 (40, 50, 80), alpha)
    fill_polygon(img, [(cx - w * 0.16, cy + h * 0.28), (cx, cy + h * 0.44),
                       (cx + w * 0.16, cy + h * 0.28), (cx + w * 0.07, y1),
                       (cx - w * 0.07, y1)], (236, 234, 226), alpha)
    line(img, cx - w * 0.16, cy + h * 0.28, cx - w * 0.03, y1, (28, 36, 58), 1.4, alpha)
    line(img, cx + w * 0.16, cy + h * 0.28, cx + w * 0.03, y1, (28, 36, 58), 1.4, alpha)
    # neck
    img.fill_rect(cx - w * 0.09, cy + h * 0.16, cx + w * 0.09, cy + h * 0.32, skin_sh, alpha)
    # ears
    fill_ellipse(img, cx - w * 0.335, cy - h * 0.02, w * 0.055, h * 0.075, skin_sh, alpha)
    fill_ellipse(img, cx + w * 0.335, cy - h * 0.02, w * 0.055, h * 0.075, skin_sh, alpha)
    # head
    fill_ellipse(img, cx, cy - h * 0.06, w * 0.335, h * 0.335, skin, alpha)
    fill_ellipse(img, cx + w * 0.10, cy - h * 0.03, w * 0.24, h * 0.27, skin_sh,
                 alpha // 3 if alpha == 255 else alpha)
    fill_ellipse(img, cx, cy - h * 0.06, w * 0.335, h * 0.335, skin, alpha // 2 + 40 if alpha < 255 else 0)
    # hair: cap over the top of the head with a wavy hairline
    hair_pts = []
    for i in range(25):
        t = math.pi * (1 - i / 24)
        hair_pts.append((cx + w * 0.345 * math.cos(t), cy - h * 0.06 + h * 0.345 * math.sin(t) * -1))
    hair_pts += [(cx + w * 0.345, cy - h * 0.16), (cx + w * 0.20, cy - h * 0.235),
                 (cx + w * 0.05, cy - h * 0.20), (cx - w * 0.10, cy - h * 0.25),
                 (cx - w * 0.24, cy - h * 0.20), (cx - w * 0.345, cy - h * 0.13)]
    fill_polygon(img, hair_pts, hair, alpha)
    # brows and eyes
    for sgn in (-1, 1):
        ex = cx + sgn * w * 0.135
        ey = cy - h * 0.075
        line(img, ex - w * 0.075, ey - h * 0.055, ex + w * 0.075, ey - h * 0.068, hair, w * 0.028, alpha)
        fill_ellipse(img, ex, ey, w * 0.062, h * 0.030, (248, 246, 240), alpha)
        stamp_disc(img, ex, ey, w * 0.026, (38, 34, 30), alpha)
        line(img, ex - w * 0.062, ey - h * 0.028, ex + w * 0.062, ey - h * 0.028, skin_sh, 1.1, alpha)
    # nose and mouth
    line(img, cx + w * 0.012, cy - h * 0.03, cx - w * 0.018, cy + h * 0.075, skin_sh, 1.4, alpha)
    line(img, cx - w * 0.045, cy + h * 0.085, cx + w * 0.03, cy + h * 0.085, skin_sh, 1.2, alpha)
    bezier(img, (cx - w * 0.085, cy + h * 0.155), (cx - w * 0.03, cy + h * 0.185),
           (cx + w * 0.03, cy + h * 0.185), (cx + w * 0.085, cy + h * 0.15),
           (168, 104, 92), 1.8, alpha)
    # cheek shading
    fill_ellipse(img, cx - w * 0.19, cy + h * 0.06, w * 0.07, h * 0.045, (232, 160, 128), alpha // 2)


def draw_signature(img, x, y, scale=1.0, color=(30, 44, 96), a=255):
    """Flowing script squiggle: a tall J, name humps, and a flourish."""
    pts = []
    steps = 130
    for i in range(steps + 1):
        t = i / steps
        xx = x + t * 118 * scale
        env = math.sin(math.pi * min(1.0, t * 1.04))
        yy = y - 6 * scale * env * math.sin(t * 21.0) - 3 * scale * math.sin(t * 5.0)
        if t < 0.16:  # the tall J loop
            yy = y - 26 * scale * math.sin(math.pi * t / 0.16) + t * 30 * scale
        pts.append((xx, yy))
    polyline(img, pts, color, 1.9 * scale, a)
    bezier(img, (x - 4 * scale, y + 9 * scale), (x + 40 * scale, y + 16 * scale),
           (x + 84 * scale, y + 2 * scale), (x + 126 * scale, y + 8 * scale),
           color, 1.5 * scale, a)
    line(img, x + 66 * scale, y - 15 * scale, x + 78 * scale, y - 19 * scale, color, 1.6 * scale, a)


# ---------------------------------------------------------------- stamps

class Stamp:
    """Small RGB + mask buffer, blitted rotated with translucent ink."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.mask = bytearray(w * h)

    def put(self, x, y, r, g, b, a=255):
        x = int(x); y = int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            i = y * self.w + x
            self.px[i * 3] = r
            self.px[i * 3 + 1] = g
            self.px[i * 3 + 2] = b
            if a > self.mask[i]:
                self.mask[i] = a


def blit_rotated(img, st, cx, cy, angle_deg, alpha=215):
    ang = math.radians(angle_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    rad = int(math.hypot(st.w, st.h) / 2) + 2
    for dy in range(-rad, rad + 1):
        for dx in range(-rad, rad + 1):
            sx = dx * ca + dy * sa + st.w / 2
            sy = -dx * sa + dy * ca + st.h / 2
            ix, iy = int(sx), int(sy)
            if 0 <= ix < st.w and 0 <= iy < st.h:
                m = st.mask[iy * st.w + ix]
                if m:
                    i = (iy * st.w + ix) * 3
                    img.put(cx + dx, cy + dy, st.px[i], st.px[i + 1], st.px[i + 2],
                            m * alpha // 255)


def make_stamp(w, h, ink, lines, oval=False, sub=None):
    st = Stamp(w, h)
    if oval:
        stroke_ellipse(st, w / 2, h / 2, w / 2 - 4, h / 2 - 4, ink, 3.0)
        stroke_ellipse(st, w / 2, h / 2, w / 2 - 10, h / 2 - 10, ink, 1.2)
    else:
        rounded_rect(st, 4, 4, w - 4, h - 4, 12, ink, 3.0)
        rounded_rect(st, 10, 10, w - 10, h - 10, 9, ink, 1.2)
    n = len(lines)
    total_h = sum(lh for _, lh in lines)
    yy = (h - total_h) / 2
    for text, lh in lines:
        draw_text(st, w / 2, yy, text, lh * 0.72, ink, wdt=max(1.4, lh * 0.10),
                  align="center")
        yy += lh
    if sub:
        draw_text(st, w / 2, h - 24, sub, 9.5, ink, wdt=1.1, align="center")
    return st


# ---------------------------------------------------------------- pages

def field(img, x, y, w, label_en, label_sv, value, vsize=15.5):
    draw_text(img, x, y, label_en + " / " + label_sv, 9.0, LABEL, wdt=1.05, spacing=0.6)
    draw_text(img, x, y + 13, value, vsize, INK, wdt=vsize * 0.13)
    line(img, x, y + 13 + vsize + 7, x + w, y + 13 + vsize + 7, RULE, 0.9)


def data_page(img):
    x0, y0, x1, y1 = 36, 40, 500, 984
    img.fill_rect(x0, y0, x1, y1, PAPER)
    guilloche(img, x0, y0, x1, y1, phase=0.7)
    # ghost portrait first (under the fields, lower right)
    draw_portrait(img, 404, 756, 106, alpha=40, backdrop=False)
    draw_text(img, x0 + 232, y0 + 18, "REPUBLIC OF SORVANE", 24, NAVY,
              wdt=3.0, spacing=1.6, align="center")
    draw_text(img, x0 + 232, y0 + 52, "RESPUBLIKA SORVANE", 11.5, LABEL,
              wdt=1.2, spacing=3.2, align="center")
    line(img, x0 + 26, y0 + 76, x1 - 26, y0 + 76, NAVY, 1.8)
    line(img, x0 + 26, y0 + 80, x1 - 26, y0 + 80, NAVY, 0.8)
    draw_emblem(img, x0 + 232, y0 + 148, 47)
    draw_text(img, x0 + 232, y0 + 208, "PASSPORT", 26, NAVY, wdt=3.2,
              spacing=4.5, align="center")
    draw_text(img, x0 + 232, y0 + 240, "PASOS", 11, LABEL, wdt=1.2,
              spacing=5.0, align="center")
    # type / code / number row
    fy = y0 + 268
    field(img, x0 + 24, fy, 62, "TYPE", "TIP", "P", 16)
    field(img, x0 + 104, fy, 74, "CODE", "KOD", "SVR", 16)
    field(img, x0 + 196, fy, 240, "PASSPORT NO", "PASOS NOMER", DOC_NO, 16)
    # portrait
    px0, py0, px1, py1 = x0 + 24, y0 + 330, x0 + 160, y0 + 496
    draw_portrait(img, (px0 + px1) / 2, (py0 + py1) / 2, px1 - px0)
    rect(img, px0, py0, px1, py1, (120, 116, 100), 1.4)
    draw_signature(img, px0 + 10, py1 + 24, 0.85)
    draw_text(img, px0 + 2, py1 + 34, "SIGNATURE / NENSKRIFT", 8.0, LABEL, wdt=0.95)
    # fields right of the portrait
    fx = x0 + 182
    fw = x1 - fx - 22
    field(img, fx, y0 + 330, fw, "SURNAME", "FAMILINOM", SURNAME)
    field(img, fx, y0 + 386, fw, "GIVEN NAMES", "FORNOMI", GIVEN)
    field(img, fx, y0 + 442, fw, "NATIONALITY", "NASIONALITET", "SORVANIAN")
    # full-width fields
    wy = y0 + 556
    field(img, x0 + 24, wy, 200, "DATE OF BIRTH", "DATUM NASIT", "04 MAY 1988")
    field(img, x0 + 244, wy, 90, "SEX", "KON", "M")
    field(img, x0 + 24, wy + 56, 200, "PLACE OF BIRTH", "LOK NASIT", "VEL MORRA")
    field(img, x0 + 244, wy + 56, 190, "PERSONAL NO", "NOMER LOK", "880504 317")
    field(img, x0 + 24, wy + 112, 200, "DATE OF ISSUE", "DATUM DELIVR", "14 MAR 2023")
    field(img, x0 + 244, wy + 112, 190, "DATE OF EXPIRY", "DATUM FIN", "14 MAR 2033")
    field(img, x0 + 24, wy + 168, 300, "AUTHORITY", "OTORITET",
          "PASSPORT OFFICE · VEL MORRA")
    # machine-readable zone
    img.fill_rect(x0 + 14, y1 - 108, x1 - 14, y1 - 14, (238, 231, 205))
    line1, line2 = build_mrz()
    draw_text(img, x0 + 30, y1 - 92, line1, 15.5, (44, 42, 40), wdt=1.5, mono=9.62)
    draw_text(img, x0 + 30, y1 - 58, line2, 15.5, (44, 42, 40), wdt=1.5, mono=9.62)
    draw_dotted_text(img, x1 - 20, y1 - 30, DOC_NO, 10, (150, 142, 124), align="right")
    draw_text(img, x0 + 24, y1 - 128, "7", 12, LABEL, wdt=1.2)


def visas_page(img):
    x0, y0, x1, y1 = 524, 40, 988, 984
    img.fill_rect(x0, y0, x1, y1, PAPER)
    guilloche(img, x0, y0, x1, y1, phase=2.3)
    draw_emblem(img, (x0 + x1) / 2, 640, 120, a=16)
    draw_text(img, x0 + 232, y0 + 18, "VISAS", 23, NAVY, wdt=2.9, spacing=3.4,
              align="center")
    draw_text(img, x0 + 232, y0 + 50, "VIZE", 11, LABEL, wdt=1.2, spacing=5.0,
              align="center")
    line(img, x0 + 26, y0 + 72, x1 - 26, y0 + 72, NAVY, 1.6)
    draw_dotted_text(img, x0 + 24, y0 + 14, DOC_NO, 11, (150, 142, 124))
    # --- amber coast endorsement (the telling detail)
    bx0, by0, bx1, by1 = x0 + 30, y0 + 92, x1 - 30, y0 + 296
    rect(img, bx0, by0, bx1, by1, NAVY, 2.0)
    rect(img, bx0 + 5, by0 + 5, bx1 - 5, by1 - 5, NAVY, 0.8)
    draw_text(img, bx0 + 18, by0 + 16, "AMBER COAST ENDORSEMENT", 14.5, NAVY, wdt=1.9)
    draw_text(img, bx0 + 18, by0 + 38, "JANTARKUST ENDOS", 9.0, LABEL, wdt=1.0, spacing=1.4)
    body = [
        "The holder is entered on the Amber Coast",
        "register and must report to the harbour",
        "master at any Sorvanian port within 24",
        "hours of landfall, there to receive the",
        "amber tally stamp. Charts and tide",
        "tables carried are exempt from duty.",
    ]
    for i, ln in enumerate(body):
        draw_text(img, bx0 + 18, by0 + 62 + i * 17, ln, 11.0, INK, wdt=1.1)
    fee = make_stamp(156, 64, GREEN, [("AMBER TALLY", 15), ("FEE PAID · 12 LUMA", 11)])
    blit_rotated(img, fee, bx1 - 88, by1 - 36, -7, alpha=200)
    # --- Meridia visitor visa sticker
    vx0, vy0, vx1, vy1 = x0 + 34, y0 + 328, x0 + 268, y0 + 452
    for i in range(vy1 - vy0):
        t = i / (vy1 - vy0)
        img.fill_rect(vx0, vy0 + i, vx1, vy0 + i + 1,
                      (int(196 - 60 * t), int(178 - 30 * t), int(96 + 30 * t)))
    rounded_rect(img, vx0, vy0, vx1, vy1, 8, (90, 74, 30), 2.0)
    draw_text(img, vx0 + 16, vy0 + 14, "MERIDIA", 19, (52, 44, 20), wdt=2.4, spacing=2.0)
    draw_text(img, vx0 + 16, vy0 + 42, "VISITOR VISA · VIZA TURIST", 9.5, (70, 60, 30), wdt=1.1)
    draw_text(img, vx0 + 16, vy0 + 62, "VALID 90 DAYS FROM 10 JAN 2025", 10.5, (52, 44, 20), wdt=1.2)
    draw_text(img, vx0 + 16, vy0 + 80, "ENTRIES: MULTIPLE", 10.5, (52, 44, 20), wdt=1.2)
    draw_text(img, vx0 + 16, vy0 + 98, "NO M-4471", 10.5, (52, 44, 20), wdt=1.2)
    stroke_ellipse(img, vx1 - 34, vy0 + 30, 17, 17, (90, 74, 30), 1.4)
    stamp_disc(img, vx1 - 34, vy0 + 30, 3.2, (90, 74, 30))
    # --- stamps: one coherent itinerary, all after the 14 MAR 2023 issue
    dep_svr = make_stamp(212, 118, NAVY,
                         [("SORVANE", 19), ("VEL MORRA HARBOUR", 13),
                          ("DEPARTED", 15), ("28 MAY 2024", 16)], oval=True)
    blit_rotated(img, dep_svr, x1 - 128, y0 + 384, 5)
    arr_kh = make_stamp(218, 122, BURG,
                        [("KHALDEN", 19), ("BRASK PORT", 13),
                         ("ARRIVED", 15), ("28 MAY 2024", 16)])
    blit_rotated(img, arr_kh, x0 + 140, y0 + 552, -6)
    dep_kh = make_stamp(206, 116, BURG,
                        [("KHALDEN", 18), ("BRASK", 13),
                         ("DEPARTED", 14), ("09 JUN 2024", 16)])
    blit_rotated(img, dep_kh, x1 - 140, y0 + 572, 3)
    arr_svr = make_stamp(224, 124, GREEN,
                         [("SORVANE", 18), ("VEL MORRA", 13),
                          ("ARRIVED", 15), ("09 JUN 2024", 16)],
                        sub="AMBER TALLY ENTERED")
    blit_rotated(img, arr_svr, x0 + 150, y0 + 724, -3)
    arr_me = make_stamp(196, 108, NAVY,
                        [("MERIDIA", 17), ("AERIN", 12),
                         ("ARRIVED", 13), ("17 JAN 2025", 15)])
    blit_rotated(img, arr_me, x1 - 132, y0 + 740, 7)
    dep_me = make_stamp(196, 108, GREEN,
                        [("MERIDIA", 17), ("AERIN", 12),
                         ("DEPARTED", 13), ("25 JAN 2025", 15)])
    blit_rotated(img, dep_me, x0 + 250, y0 + 868, -8)
    draw_text(img, x1 - 24, y1 - 30, "8", 12, LABEL, wdt=1.2, align="right")


def render():
    img = Img(W, H, (66, 30, 38))
    # soft vignette on the cover showing around the spread
    for i in range(0, W, 4):
        t = abs(i - W / 2) / (W / 2)
        col = (int(74 - 14 * t), int(34 - 8 * t), int(42 - 8 * t))
        img.fill_rect(i, 0, i + 4, H, col)
    # page shadows, then the two pages
    img.fill_rect(42, 48, 506, 990, (30, 16, 20))
    img.fill_rect(530, 48, 994, 990, (30, 16, 20))
    data_page(img)
    visas_page(img)
    # gutter shadow between the pages
    for i in range(24):
        a = int(120 * (1 - i / 24))
        img.fill_rect(500 + i, 40, 501 + i, 984, (52, 40, 34), a)
    return img


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    img = render()
    write_png(img, os.path.join(out_dir, "entry.png"))


if __name__ == "__main__":
    main()
