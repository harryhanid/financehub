import re
from PIL import Image, ImageDraw

# ── Exact source paths (company_select.html .wordmark-icon svg, viewBox 0 0 16 16) ──
PATH_1 = "M1.5 10.2c1.6-3.2 3.6-3.2 5 0s3.4 3.2 5 0s2.5-4 2.5-4"
PATH_2 = "M1.5 5.8c1.6-3.2 3.6-3.2 5 0s3.4 3.2 5 0"
VIEWBOX = 16.0

STROKE_1_WIDTH = 1.5   # SVG units, from stroke-width="1.5"
STROKE_2_WIDTH = 1.0   # from stroke-width="1"
STROKE_2_OPACITY = 0.55

FINAL_SIZE = 260        # px, final PNG size (10x a 26pt PDF placement)
SUPERSAMPLE = 4
CANVAS = FINAL_SIZE * SUPERSAMPLE
SCALE = CANVAS / VIEWBOX

CORNER_RADIUS_RATIO = 10 / 34  # from .wordmark-icon { width:34px; border-radius:10px }
CORNER_RADIUS = int(CANVAS * CORNER_RADIUS_RATIO)

COBALT = (91, 140, 255)   # #5B8CFF
CYAN   = (34, 211, 238)   # #22D3EE


def parse_path(path, scale):
    """Tiny parser for the subset of SVG path commands these two flow-line
    paths actually use: M (absolute moveto), c (relative cubic bezier,
    repeatable), s (relative smooth cubic bezier, repeatable). Returns a
    list of (x, y) points in canvas space, densely sampled along every
    cubic segment for a smooth polyline."""
    tokens = re.findall(r'[Mcs]|-?\d*\.?\d+', path)
    i = 0
    cmd = None
    cur = (0.0, 0.0)
    prev_cp2 = None
    points = []

    def cubic_points(p0, p1, p2, p3, n=24):
        pts = []
        for step in range(n + 1):
            t = step / n
            mt = 1 - t
            x = (mt**3) * p0[0] + 3 * (mt**2) * t * p1[0] + 3 * mt * (t**2) * p2[0] + (t**3) * p3[0]
            y = (mt**3) * p0[1] + 3 * (mt**2) * t * p1[1] + 3 * mt * (t**2) * p2[1] + (t**3) * p3[1]
            pts.append((x, y))
        return pts

    while i < len(tokens):
        tok = tokens[i]
        if tok in ('M', 'c', 's'):
            cmd = tok
            i += 1
            continue
        if cmd == 'M':
            x, y = float(tokens[i]), float(tokens[i + 1])
            cur = (x, y)
            points.append(cur)
            i += 2
            prev_cp2 = None
        elif cmd == 'c':
            dx1, dy1, dx2, dy2, dx, dy = (float(tokens[i + k]) for k in range(6))
            cp1 = (cur[0] + dx1, cur[1] + dy1)
            cp2 = (cur[0] + dx2, cur[1] + dy2)
            end = (cur[0] + dx, cur[1] + dy)
            points.extend(cubic_points(cur, cp1, cp2, end)[1:])
            prev_cp2 = cp2
            cur = end
            i += 6
        elif cmd == 's':
            dx2, dy2, dx, dy = (float(tokens[i + k]) for k in range(4))
            cp2 = (cur[0] + dx2, cur[1] + dy2)
            end = (cur[0] + dx, cur[1] + dy)
            cp1 = (2 * cur[0] - prev_cp2[0], 2 * cur[1] - prev_cp2[1]) if prev_cp2 else cur
            points.extend(cubic_points(cur, cp1, cp2, end)[1:])
            prev_cp2 = cp2
            cur = end
            i += 4
        else:
            i += 1

    return [(px * scale, py * scale) for px, py in points]


def rounded_mask(size, radius):
    mask = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def gradient_135(size, c1, c2):
    """Linear gradient top-left -> bottom-right (CSS 135deg)."""
    grad = Image.new('RGB', (size, size))
    px = grad.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * (size - 1))
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            px[x, y] = (r, g, b)
    return grad


def main():
    bg = gradient_135(CANVAS, COBALT, CYAN).convert('RGBA')
    mask = rounded_mask(CANVAS, CORNER_RADIUS)
    canvas = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    canvas.paste(bg, (0, 0), mask)

    line_layer = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(line_layer)

    pts1 = parse_path(PATH_1, SCALE)
    draw.line(pts1, fill=(255, 255, 255, 255), width=int(STROKE_1_WIDTH * SCALE), joint='curve')
    for p in (pts1[0], pts1[-1]):
        r = int(STROKE_1_WIDTH * SCALE / 2)
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(255, 255, 255, 255))

    pts2 = parse_path(PATH_2, SCALE)
    alpha2 = int(255 * STROKE_2_OPACITY)
    draw.line(pts2, fill=(255, 255, 255, alpha2), width=int(STROKE_2_WIDTH * SCALE), joint='curve')
    for p in (pts2[0], pts2[-1]):
        r = int(STROKE_2_WIDTH * SCALE / 2)
        draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=(255, 255, 255, alpha2))

    combined = Image.alpha_composite(canvas, line_layer)
    final = combined.resize((FINAL_SIZE, FINAL_SIZE), Image.LANCZOS)

    import os
    out_dir = os.path.join(os.path.dirname(__file__), "app", "static", "img")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "flow-mark.png")
    final.save(out_path)
    print("Saved", out_path, final.size)


if __name__ == "__main__":
    main()
