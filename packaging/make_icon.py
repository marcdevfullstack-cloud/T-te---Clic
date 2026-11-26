"""Génère toutes les icônes de Tête-à-Clic à partir de l'icône officielle (assets/).

- assets/icon.png          : icône officielle détourée (coins transparents), 1024 px
- assets/icon-small.png    : emblème seul (profil + curseur), pour les petites tailles
- assets/icon.ico          : icône Windows multi-tailles (exe, installateur, raccourcis)
- tete_a_clic/ui/web/img/  : logo de l'interface (en-tête, écran de démarrage)

En petite taille (16 à 48 px), l'illustration et le nom deviennent illisibles : on n'y
garde que l'emblème du logo (le profil blanc et le curseur), sur un fond bleu.
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
WEB_IMG = ROOT / "tete_a_clic" / "ui" / "web" / "img"
SOURCE_NAMES = ("icon-source.png", "Tête-à-Clic _ contrôle par le regard.png")
EMBLEM_BOX = (0.064, 0.630, 0.302, 0.866)  # zone de l'emblème dans l'icône officielle (fractions)


def _source() -> Path:
    for name in SOURCE_NAMES:
        if (ASSETS / name).exists():
            return ASSETS / name
    raise FileNotFoundError(f"Icône officielle introuvable dans {ASSETS}")


def cut_out(img: Image.Image) -> Image.Image:
    """Rend transparents les coins noirs autour du carré arrondi (remplissage depuis les 4 coins)."""
    rgb = np.ascontiguousarray(np.asarray(img.convert("RGB")))
    h, w = rgb.shape[:2]
    flood = np.zeros((h + 2, w + 2), np.uint8)
    for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        cv2.floodFill(rgb.copy(), flood, corner, (0, 0, 0), (40, 40, 40), (40, 40, 40),
                      cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE | (255 << 8) | 8)
    mask = Image.fromarray(np.where(flood[1:-1, 1:-1] > 0, 0, 255).astype(np.uint8))
    mask = mask.filter(ImageFilter.GaussianBlur(1.2))  # bords adoucis
    out = Image.fromarray(rgb).convert("RGBA")
    out.putalpha(mask)
    return out.crop(mask.getbbox())


def _components(mask: np.ndarray, keep) -> np.ndarray:
    n, labels, stats, cent = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    out = np.zeros_like(mask, dtype=bool)
    for i in range(1, n):
        if keep(stats[i, cv2.CC_STAT_AREA], cent[i][0] / mask.shape[1], cent[i][1] / mask.shape[0]):
            out |= labels == i
    return out


def emblem(icon: Image.Image, size: int = 1024) -> Image.Image:
    """Profil blanc, curseur et traits orange extraits du logo, sur un carré arrondi bleu."""
    w, h = icon.size
    box = [int(v * s) for v, s in zip(EMBLEM_BOX, (w, h, w, h))]
    crop = np.asarray(icon.convert("RGB").crop(box)).astype(int)
    r, g, b = crop[..., 0], crop[..., 1], crop[..., 2]
    total = crop.shape[0] * crop.shape[1]
    # Blanc : le profil et le curseur (grandes formes) ; on écarte l'arc et le bout du « T ».
    white = _components((r > 200) & (g > 200) & (b > 200),
                        lambda a, cx, cy: a > total * 0.01 and 0.1 < cx < 0.95 and cy > 0.3)
    # Orange : les trois petits traits du « clic » ; on écarte le grand arc orange.
    orange = _components((r > 200) & (g > 110) & (g < 210) & (b < 90),
                         lambda a, cx, cy: a < total * 0.01 and 0.55 < cx < 0.95 and 0.2 < cy < 0.6)
    ys, xs = np.nonzero(white | orange)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    layer = np.zeros((*crop.shape[:2], 4), np.uint8)
    layer[white] = (255, 255, 255, 255)
    layer[orange] = (255, 165, 20, 255)
    shapes = Image.fromarray(layer[y0:y1, x0:x1]).filter(ImageFilter.SMOOTH)

    # Fond : carré arrondi au dégradé bleu du logo.
    plate = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / (size - 1)
        grad.putpixel((0, y), (round(30 + (12 - 30) * t), round(120 + (45 - 120) * t), round(245 + (160 - 245) * t)))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=size * 0.22, fill=255)
    plate.paste(grad.resize((size, size)), (0, 0), mask)
    inner = int(size * 0.78)
    scale = inner / max(shapes.size)
    shapes = shapes.resize((round(shapes.width * scale), round(shapes.height * scale)), Image.LANCZOS)
    plate.alpha_composite(shapes, ((size - shapes.width) // 2, (size - shapes.height) // 2))
    return plate


def main():
    source = _source()
    icon = cut_out(Image.open(source)).resize((1024, 1024), Image.LANCZOS)
    icon.save(ASSETS / "icon.png", optimize=True)
    small = emblem(icon)
    small.resize((256, 256), Image.LANCZOS).save(ASSETS / "icon-small.png", optimize=True)

    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    frames = [(small if s <= 48 else icon).resize((s, s), Image.LANCZOS) for s in sizes]
    frames[-1].save(ASSETS / "icon.ico", sizes=[(s, s) for s in sizes], append_images=frames[:-1])

    WEB_IMG.mkdir(parents=True, exist_ok=True)
    icon.resize((320, 320), Image.LANCZOS).save(WEB_IMG / "icon.png", optimize=True)
    small.resize((96, 96), Image.LANCZOS).save(WEB_IMG / "icon-small.png", optimize=True)
    print(f"Icônes générées depuis « {source.name} »")


if __name__ == "__main__":
    main()
