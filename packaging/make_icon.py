"""Génère les icônes de Tête-à-Clic (assets/icon.png et assets/icon.ico).

Si une icône originale est déposée dans assets/ (icon-source.png), elle est utilisée telle
quelle. Sinon, l'icône est dessinée : une tête, et un curseur entouré de l'anneau du clic
par immobilité, sur le dégradé violet-bleu de l'application.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
S = 2048  # dessin en très haute résolution, puis réduction : bords lisses à toutes les tailles


def _gradient(size: int, top: tuple, bottom: tuple) -> Image.Image:
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for y in range(size):
        t = y / (size - 1)
        d.line([(0, y), (size, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def draw() -> Image.Image:
    k = S / 1024
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, S - 1, S - 1), radius=int(230 * k), fill=255)
    icon = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    icon.paste(_gradient(S, (139, 92, 255), (40, 110, 240)), (0, 0), mask)

    # Tête et épaules (silhouette blanche), à gauche.
    body = Image.new("L", (S, S), 0)
    b = ImageDraw.Draw(body)
    b.ellipse([v * k for v in (180, 250, 480, 550)], fill=255)  # tête
    b.ellipse([v * k for v in (60, 610, 600, 1200)], fill=255)  # épaules
    body = Image.composite(body, Image.new("L", (S, S), 0), mask)  # rognées par le carré arrondi
    icon.paste(Image.new("RGBA", (S, S), (255, 255, 255, 255)), (0, 0), body)

    d = ImageDraw.Draw(icon)
    tip = (610 * k, 300 * k)
    # Anneau du clic par immobilité, aux trois quarts rempli, autour de la pointe du curseur.
    r = 110 * k
    box = (tip[0] - r, tip[1] - r, tip[0] + r, tip[1] + r)
    d.ellipse(box, outline=(255, 255, 255, 120), width=int(28 * k))
    d.arc(box, -90, 180, fill=(52, 211, 153, 255), width=int(28 * k))
    # Curseur (flèche) blanc à contour sombre.
    arrow = [(0, 0), (0, 380), (95, 290), (160, 430), (225, 400), (162, 262), (290, 262)]
    pts = [(tip[0] + x * k, tip[1] + y * k) for x, y in arrow]
    d.line(pts + [pts[0], pts[1]], fill=(30, 20, 80, 255), width=int(44 * k), joint="curve")
    d.polygon(pts, fill=(255, 255, 255, 255))
    return icon


def main():
    ASSETS.mkdir(exist_ok=True)
    source = ASSETS / "icon-source.png"
    icon = Image.open(source).convert("RGBA") if source.exists() else draw()
    icon = icon.resize((1024, 1024), Image.LANCZOS)
    icon.save(ASSETS / "icon.png")
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    frames = [icon.resize((s, s), Image.LANCZOS) for s in sizes]
    frames[-1].save(ASSETS / "icon.ico", sizes=[(s, s) for s in sizes], append_images=frames[:-1])
    print("Icônes générées" + (" depuis icon-source.png" if source.exists() else " (dessin intégré)"))


if __name__ == "__main__":
    main()
