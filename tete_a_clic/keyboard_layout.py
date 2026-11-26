"""Disposition du clavier Tête-à-Clic (logique pure, testable) : touches, positions, majuscules.

Clavier AZERTY simplifié, à grandes touches, pensé pour le pointage par la tête :
4 rangées seulement, accents français en accès direct, et un mode « 123 ».
"""
from dataclasses import dataclass

VK_BACK, VK_TAB, VK_RETURN, VK_LEFT, VK_RIGHT = 0x08, 0x09, 0x0D, 0x25, 0x27

UNITS_WIDE = 11.5  # largeur d'une rangée, en touches


@dataclass(frozen=True)
class Key:
    label: str
    action: str  # "char", "vk", "shift", "mode", "move", "hide"
    value: object = None
    width: float = 1.0
    symbol: bool = False  # libellé en police de symboles


def _chars(text: str) -> list[Key]:
    return [Key(c, "char", c) for c in text]


BACK = Key("⌫", "vk", VK_BACK, 1.5, True)
ENTER = Key("Entrée", "vk", VK_RETURN, 1.5)
BOTTOM = [Key(",", "char", ","), Key(".", "char", "."), Key("Espace", "char", " ", 4.0),
          Key("←", "vk", VK_LEFT, symbol=True), Key("→", "vk", VK_RIGHT, symbol=True),
          Key("⇅", "move", symbol=True), Key("✕", "hide", symbol=True)]

LAYOUTS = {
    "abc": [
        _chars("azertyuiop") + [BACK],
        _chars("qsdfghjklm") + [ENTER],
        [Key("⇧", "shift", width=1.5, symbol=True)] + _chars("wxcvbnéèàç"),
        [Key("123", "mode", "123", 1.5)] + BOTTOM,
    ],
    "123": [
        _chars("1234567890") + [BACK],
        _chars("@#€%&-+=()") + [ENTER],
        [Key("Tab", "vk", VK_TAB, 1.5)] + _chars("'\"?!:;/_êù"),
        [Key("abc", "mode", "abc", 1.5)] + BOTTOM,
    ],
}


@dataclass(frozen=True)
class PlacedKey:
    key: Key
    rect: tuple[int, int, int, int]  # gauche, haut, droite, bas (pixels dans la fenêtre)


def place(mode: str, unit: int, row_h: int, gap: int, left: int, top: int) -> list[PlacedKey]:
    """Positionne les touches : chaque rangée occupe exactement UNITS_WIDE unités."""
    placed = []
    for r, row in enumerate(LAYOUTS[mode]):
        x = 0.0
        y0 = top + r * (row_h + gap)
        for key in row:
            x0 = left + round(x * unit)
            x1 = left + round((x + key.width) * unit) - gap
            placed.append(PlacedKey(key, (x0, y0, x1, y0 + row_h)))
            x += key.width
    return placed


def hit(placed: list[PlacedKey], x: float, y: float) -> PlacedKey | None:
    for p in placed:
        l, t, r, b = p.rect
        if l <= x < r and t <= y < b:
            return p
    return None


def shown_label(key: Key, shift: bool) -> str:
    return key.label.upper() if shift and key.action == "char" and len(key.label) == 1 else key.label


def typed_char(key: Key, shift: bool) -> str:
    return key.value.upper() if shift else key.value
