"""Genere l'icone .ico de Jarvis (cercle cyan style arc-reacteur sur fond sombre)."""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).parent.parent / "src" / "jarvis" / "assets" / "jarvis.ico"
SIZE = 256

BG = (5, 8, 13, 255)
CYAN = (0, 229, 255, 255)
CYAN_DIM = (8, 145, 168, 255)
DARK_RING = (10, 20, 28, 255)


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    center = size / 2
    r_outer = size * 0.48

    draw.ellipse(
        [center - r_outer, center - r_outer, center + r_outer, center + r_outer],
        fill=BG,
    )

    ring_width = max(2, size * 0.045)
    r1 = size * 0.44
    draw.ellipse(
        [center - r1, center - r1, center + r1, center + r1],
        outline=CYAN, width=int(ring_width),
    )

    r2 = size * 0.30
    draw.ellipse(
        [center - r2, center - r2, center + r2, center + r2],
        outline=CYAN_DIM, width=max(1, int(ring_width * 0.6)),
    )

    r3 = size * 0.10
    draw.ellipse(
        [center - r3, center - r3, center + r3, center + r3],
        fill=CYAN,
    )

    for angle_deg in (45, 135, 225, 315):
        import math
        rad = math.radians(angle_deg)
        x1 = center + r2 * math.cos(rad)
        y1 = center + r2 * math.sin(rad)
        x2 = center + r1 * math.cos(rad)
        y2 = center + r1 * math.sin(rad)
        draw.line([x1, y1, x2, y2], fill=CYAN, width=max(1, int(ring_width * 0.5)))

    return img


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    base = draw_icon(SIZE)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    base.save(OUT, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"Icone generee : {OUT}")


if __name__ == "__main__":
    main()
