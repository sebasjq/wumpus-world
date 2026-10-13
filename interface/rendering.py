'Interfaz gráfica: recursos, constantes y primitivas de renderizado.'

from functools import lru_cache
import json
import math
from pathlib import Path
import random
import re

import pygame

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
SETTINGS_FILE = ROOT / "settings.json"

MAPS = [
    ("board_4x4.json", "Mapa 4 x 4", "Ejemplo pequeño con un oro, un Wumpus y tres pozos."),
    ("board_16x16.json", "Mapa 16 x 16", "Cueva grande con 37 oros, nueve Wumpus y 11 pozos."),
    ("board_shoot_test.json", "Mapa de disparo", "Prueba de flecha: el oro comparte casilla con el Wumpus."),
    ("board_no_safe_path_test.json", "Mapa sin salida segura", "Prueba de retirada con peligros junto a la entrada."),
]

W, H = 1100, 720
SB_W = 340                 # ancho del panel lateral del juego
SX = W - 24 - SB_W         # x del panel lateral
CARD_W = (W - 150) // 2    # ancho de las tarjetas de dos columnas
SPEEDS = [("Lenta", 900), ("Normal", 450), ("Rápida", 180), ("Turbo", 60)]
DEFAULT_SETTINGS = {
    "speed": 1, "fullscreen": False, "notes": True, "coords": False,
    "music": True, "effects": True,
}

# --------------------------------------------------------------------------- #
# Paleta (tomada de la propuesta de interfaz)
# --------------------------------------------------------------------------- #
BG = (13, 15, 42)
PANEL = (27, 31, 80)
PANEL_2 = (37, 42, 104)
BORDER = (62, 72, 152)
BORDER_HI = (110, 124, 226)
PRIMARY = (251, 185, 40)
PRIMARY_INK = (46, 31, 6)
SECONDARY = (79, 97, 230)
TERTIARY = (50, 57, 112)
DANGER = (232, 56, 86)
SUCCESS = (30, 185, 140)
TEXT = (244, 245, 252)
MUTED = (160, 171, 217)
INK = (8, 10, 30)

BUTTON_COLORS = {
    "primary": (PRIMARY, PRIMARY_INK),
    "secondary": (SECONDARY, TEXT),
    "tertiary": (TERTIARY, TEXT),
    "danger": (DANGER, TEXT),
    "success": (SUCCESS, TEXT),
}

SENSES = [
    ("breeze", "Brisa", "breeze", (130, 200, 255)),
    ("stench", "Hedor", "stench", (120, 220, 130)),
    ("glitter", "Brillo", "glitter", (255, 214, 90)),
    ("bump", "Golpe", "bump", (255, 150, 110)),
    ("scream", "Grito", "scream", (200, 155, 255)),
]
PERCEPTION_SOUNDS = {
    "breeze": "breeze",
    "stench": "wumpus_growl",
    "glitter": "glitter",
    "bump": "bump",
    "scream": "scream",
}
DIR_NAMES = {"N": "Norte", "E": "Este", "S": "Sur", "W": "Oeste"}
DIR_VEC = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
DEATH_WORDS = ("dead", "death", "die", "lost", "fail", "wumpus", "pit", "muer", "perd",
               "eaten", "fell", "defeat")


# --------------------------------------------------------------------------- #
# Utilidades de color y fuentes
# --------------------------------------------------------------------------- #
def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def lighten(c, t=0.2):
    return mix(c, (255, 255, 255), t)


def darken(c, t=0.3):
    return mix(c, (0, 0, 0), t)


def _find_font(*names):
    for name in names:
        path = ASSETS / "fonts" / name
        if path.exists():
            return str(path)
    return None


@lru_cache(maxsize=None)
def font(size, bold=False, title=False):
    """Fuente del proyecto si está en assets/fonts; si no, una del sistema."""
    path = _find_font("LilitaOne-Regular.ttf") if title else (
        _find_font("Nunito-Bold.ttf", "Nunito-ExtraBold.ttf") if bold else
        _find_font("Nunito-SemiBold.ttf", "Nunito-Regular.ttf"))
    if path:
        return pygame.font.Font(path, size)
    return pygame.font.SysFont("trebuchetms,verdana,dejavusans,arial", size, bold=bold or title)


_TEXT_CACHE = {}


def _offsets(radius):
    return {(round(math.cos(a / 8 * math.pi) * radius), round(math.sin(a / 8 * math.pi) * radius))
            for a in range(16)}


def _text_img(value, size, color, bold, title, outline, outline_w):
    key = (value, size, color, bold, title, outline, outline_w)
    img = _TEXT_CACHE.get(key)
    if img is None:
        if len(_TEXT_CACHE) > 700:
            _TEXT_CACHE.clear()
        f = font(size, bold, title)
        base = f.render(value, True, color)
        if outline:
            w, h = base.get_size()
            img = pygame.Surface((w + outline_w * 2, h + outline_w * 2), pygame.SRCALPHA)
            edge = f.render(value, True, outline)
            for dx, dy in _offsets(outline_w):
                img.blit(edge, (outline_w + dx, outline_w + dy))
            img.blit(base, (outline_w, outline_w))
        else:
            img = base
        _TEXT_CACHE[key] = img
    return img


def draw_text(surface, value, pos, size=20, color=TEXT, bold=False, anchor="topleft",
              title=False, outline=None, outline_w=3):
    """Dibuja texto con ancla (topleft, center, midleft, midright...) y devuelve su rect."""
    value = str(value)
    img = _text_img(value, size, color, bold, title, outline, outline_w)
    rect = img.get_rect(**{anchor: pos})
    surface.blit(img, rect)
    return rect


def wrap(value, size, width, bold=False, title=False):
    f = font(size, bold, title)
    lines, current = [], ""
    for word in str(value).split():
        trial = (current + " " + word).strip()
        if f.size(trial)[0] <= width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def text_block(surface, value, pos, width, size=16, color=TEXT, bold=False,
               line_h=None, max_lines=None, center=False):
    line_h = line_h or int(size * 1.35)
    lines = wrap(value, size, width, bold)
    if max_lines:
        lines = lines[:max_lines]
    x, y = pos
    for i, line in enumerate(lines):
        if center:
            draw_text(surface, line, (x + width // 2, y + i * line_h), size, color, bold, "midtop")
        else:
            draw_text(surface, line, (x, y + i * line_h), size, color, bold)
    return len(lines) * line_h


# --------------------------------------------------------------------------- #
# Dibujo suavizado: se dibuja a escala k y se reduce
# --------------------------------------------------------------------------- #
def _ss(w, h, fn, k=3):
    surf = pygame.Surface((w * k, h * k), pygame.SRCALPHA)
    fn(surf, k)
    return pygame.transform.smoothscale(surf, (w, h))


@lru_cache(maxsize=256)
def panel_surf(w, h, fill, border, radius=16, shadow=True):
    """Panel redondeado con sombra suave. La superficie mide h + 8 de alto."""
    def draw(s, k):
        if shadow:
            pygame.draw.rect(s, (4, 5, 20, 150), (0, 7 * k, w * k, h * k), border_radius=radius * k)
        pygame.draw.rect(s, fill, (0, 0, w * k, h * k), border_radius=radius * k)
        pygame.draw.rect(s, mix(fill, (255, 255, 255), 0.07),
                         (6 * k, 3 * k, (w - 12) * k, 2 * k), border_radius=k)
        if border:
            pygame.draw.rect(s, border, (0, 0, w * k, h * k), 2 * k, border_radius=radius * k)
    return _ss(w, h + 8, draw)


@lru_cache(maxsize=256)
def button_surf(w, h, kind, state):
    """Botón con relieve. state: normal | hover | pressed | disabled."""
    base = BUTTON_COLORS.get(kind, BUTTON_COLORS["secondary"])[0]
    if state == "disabled":
        base = (62, 68, 100)
    elif state == "hover":
        base = lighten(base, 0.14)
    depth = darken(base, 0.42)
    radius = 16 if h >= 54 else 12
    top = 4 if state == "pressed" else 0

    def draw(s, k):
        pygame.draw.rect(s, (4, 5, 20, 160), (0, 8 * k, w * k, h * k), border_radius=radius * k)
        pygame.draw.rect(s, depth, (0, 6 * k, w * k, h * k), border_radius=radius * k)
        pygame.draw.rect(s, base, (0, top * k, w * k, h * k), border_radius=radius * k)
        pygame.draw.rect(s, lighten(base, 0.24),
                         (10 * k, (top + 4) * k, (w - 20) * k, 3 * k), border_radius=2 * k)
    return _ss(w, h + 8, draw)


@lru_cache(maxsize=32)
def glow(radius, color):
    surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(radius, 0, -2):
        alpha = int(70 * (1 - i / radius) ** 2)
        pygame.draw.circle(surf, (*color, alpha), (radius, radius), i)
    return surf


# --------------------------------------------------------------------------- #
# Iconos cargados desde assets (sin dibujadores vectoriales manuales)
# --------------------------------------------------------------------------- #
def _fit(img, size):
    w, h = img.get_size()
    scale = min(size / w, size / h)
    img = pygame.transform.smoothscale(img, (max(1, int(w * scale)), max(1, int(h * scale))))
    out = pygame.Surface((size, size), pygame.SRCALPHA)
    out.blit(img, img.get_rect(center=(size // 2, size // 2)))
    return out


@lru_cache(maxsize=None)
def icon(name, size, color=None):
    """Carga un icono PNG y lo adapta a un cuadrado de ``size`` px."""
    size = max(4, int(size))
    interface_icons = {
        "arrow": "Flecha_icon.png",
        "gold": "Oro_icon.png",
        "pit": "Pozo_icon.png",
        "wumpus": "Wumpus_icon.png",
        "chest": "Cofre_icon.png",
        "heart": "Corazon_icon.png",
    }
    help_icons = {
        "help_arrow": "Flecha_icon.png",
        "help_gold": "Oro_icon.png",
        "help_pit": "Pozo_icon.png",
        "help_wumpus": "Wumpus_icon.png",
    }
    if name in interface_icons:
        path = ASSETS / "images" / interface_icons[name]
    elif name in help_icons:
        path = ASSETS / "images" / help_icons[name]
    else:
        asset_name = name[5:] if name.startswith("menu_") else name
        asset_name = {"settings": "gear"}.get(asset_name, asset_name)
        path = ASSETS / "icons" / f"{asset_name}.png"
    if not path.exists() and name == "arrow_down":
        return pygame.transform.rotate(icon("arrow_up", size, color), 180)
    if not path.exists() and name == "arrow_right":
        return pygame.transform.rotate(icon("arrow_up", size, color), -90)
    if not path.exists() and name == "arrow_left":
        return pygame.transform.rotate(icon("arrow_up", size, color), 90)
    if not path.exists() and name == "turn_right":
        return pygame.transform.flip(icon("turn_left", size, color), True, False)
    if not path.exists():
        raise FileNotFoundError(f"No existe el icono requerido: {path}")
    img = pygame.image.load(str(path)).convert_alpha()
    if name not in interface_icons and name not in help_icons:
        img.fill(color or TEXT, special_flags=pygame.BLEND_RGB_MAX)
    return _fit(img, size)


# --------------------------------------------------------------------------- #
# Texturas procedurales (fondo de cueva, casillas, brújula)
# --------------------------------------------------------------------------- #
def find_image(name):
    for folder in (ASSETS / "images", ASSETS):
        if (folder / name).exists():
            return str(folder / name)
    return None


@lru_cache(maxsize=1)
def background():
    """Fondo.png ajustado a la ventana (cubre todo el lienzo y recorta el sobrante)."""
    surf = pygame.Surface((W, H))
    surf.fill(BG)
    path = find_image("Fondo.png")
    if path:
        img = pygame.image.load(path).convert()
        k = max(W / img.get_width(), H / img.get_height())
        img = pygame.transform.smoothscale(img, (round(img.get_width() * k), round(img.get_height() * k)))
        surf.blit(img, img.get_rect(center=(W // 2, H // 2)))
    return surf


@lru_cache(maxsize=4)
def logo(max_w, max_h):
    """Logo.png reducido para caber en max_w x max_h (nunca se agranda). None si no existe."""
    path = find_image("Logo.png")
    if not path:
        return None
    img = pygame.image.load(path).convert_alpha()
    k = min(max_w / img.get_width(), max_h / img.get_height(), 1)
    return pygame.transform.smoothscale(img, (max(1, round(img.get_width() * k)),
                                              max(1, round(img.get_height() * k))))


@lru_cache(maxsize=64)
def tile(side, known, variant):
    """Casilla de piedra. ``known`` = visitada (más clara)."""
    fill = (47, 55, 116) if known else (21, 24, 62)
    edge = (76, 88, 168) if known else (33, 38, 86)
    rnd = random.Random(variant * 977 + side)
    radius = max(4, side // 8)

    def draw(s, k):
        pygame.draw.rect(s, edge, (0, 0, side * k, side * k), border_radius=radius * k)
        pygame.draw.rect(s, fill, (2 * k, 2 * k, (side - 4) * k, (side - 4) * k),
                         border_radius=max(2, radius - 1) * k)
        pygame.draw.rect(s, mix(fill, (255, 255, 255), .1),
                         (5 * k, 3 * k, (side - 10) * k, 2 * k), border_radius=k)
        for _ in range(4 if side > 28 else 1):
            cx, cy = rnd.uniform(.2, .8) * side, rnd.uniform(.25, .8) * side
            r = rnd.uniform(.03, .07) * side
            col = mix(fill, (255, 255, 255), .12) if rnd.random() < .5 else darken(fill, .3)
            pygame.draw.polygon(s, col, [((cx + math.cos(a) * r * rnd.uniform(.7, 1.3)) * k,
                                          (cy + math.sin(a) * r * rnd.uniform(.7, 1.3)) * k)
                                         for a in (0, 1.3, 2.6, 3.9, 5.2)])
    return _ss(side, side, draw)


@lru_cache(maxsize=32)
def entrance_overlay(side):
    def draw(s, k):
        pygame.draw.rect(s, (*PRIMARY, 200), (2 * k, 2 * k, (side - 4) * k, (side - 4) * k),
                         max(2, k * side // 28), border_radius=max(3, side // 8) * k)
    return _ss(side, side, draw)


@lru_cache(maxsize=32)
def compass_surf(r, facing):
    size = r * 2 + 8

    def draw(s, k):
        c = (size * k // 2, size * k // 2)
        pygame.draw.circle(s, (4, 5, 20, 170), (c[0], c[1] + 3 * k), r * k + 2 * k)
        pygame.draw.circle(s, (20, 24, 66), c, r * k)
        pygame.draw.circle(s, BORDER, c, r * k, 3 * k)
        ang = math.radians({"N": 0, "E": 90, "S": 180, "W": 270}[facing])
        vx, vy = math.sin(ang), -math.cos(ang)
        length, width = r * k * .6, r * k * .17
        tip = (c[0] + vx * length, c[1] + vy * length)
        tail = (c[0] - vx * length, c[1] - vy * length)
        p1 = (c[0] - vy * width, c[1] + vx * width)
        p2 = (c[0] + vy * width, c[1] - vx * width)
        pygame.draw.polygon(s, DANGER, [tip, p1, p2])
        pygame.draw.polygon(s, (100, 140, 240), [tail, p1, p2])
        pygame.draw.circle(s, TEXT, c, max(2, int(r * k * .07)))
    img = _ss(size, size, draw)
    f = font(max(11, r // 3), True)
    for letter, (dx, dy) in (("N", (0, -1)), ("E", (1, 0)), ("S", (0, 1)), ("O", (-1, 0))):
        t = f.render(letter, True, PRIMARY if {"O": "W"}.get(letter, letter) == facing else MUTED)
        img.blit(t, t.get_rect(center=(size // 2 + dx * r * .78, size // 2 + dy * r * .78)))
    return img


@lru_cache(maxsize=16)
def map_dims(filename):
    """Obtiene las dimensiones de un mapa desde su nombre o su JSON."""
    match = re.search(r"(\d+)x(\d+)", filename)
    if match:
        return int(match.group(1)), int(match.group(2))
    try:
        data = json.loads((DATA / filename).read_text(encoding="utf-8"))
        for key in ("size", "board_size", "dimensions"):
            if key in data:
                value = data[key]
                return ((int(value[0]), int(value[1])) if isinstance(value, (list, tuple))
                        else (int(value), int(value)))
        if "width" in data and "height" in data:
            return int(data["width"]), int(data["height"])
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        pass
    return 4, 4


def norm_dir(value):
    """Convierte cualquier representación de dirección a N/E/S/W."""
    first = str(value).strip().upper()[:1]
    return {"N": "N", "U": "N", "E": "E", "R": "E", "S": "S", "D": "S",
            "W": "W", "O": "W", "L": "W"}.get(first, "N")
