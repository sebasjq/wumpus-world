"""Interfaz Pygame del Mundo de Wumpus (estilo cartoon minimalista de cueva).

La vista usa ``Game`` como única fuente de verdad. El modo manual llama a
``Game.act`` y el modo agente avanza con ``Game.step`` mediante un temporizador,
por lo que el bucle de Pygame nunca queda bloqueado.

Imágenes (junto a este archivo o en assets/; si faltan, se usan colores planos):

    Fondo.png                               fondo de todas las pantallas
    Logo.png                                logotipo del menú (y de la barra del juego si es apaisado)

Recursos opcionales:

    assets/fonts/LilitaOne-Regular.ttf      títulos y botones
    assets/fonts/Nunito-Regular.ttf         texto corrido
    assets/fonts/Nunito-Bold.ttf            texto corrido en negrita
    assets/icons/<nombre>.png               iconos PNG de la interfaz
    assets/sprites/<nombre>.png             explorer_N/E/S/W, wumpus, gold, pit, chest

Requiere pygame >= 2.0.
"""

from functools import lru_cache
from array import array
import json
import math
from pathlib import Path
import random
import re

import pygame

from logic.game import Game

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
    help_icons = {
        "help_arrow": "Flecha_icon.png",
        "help_gold": "Oro_icon.png",
        "help_pit": "Pozo_icon.png",
        "help_wumpus": "Wumpus_icon.png",
    }
    if name in help_icons:
        path = HERE / help_icons[name]
    elif name == "wumpus":
        path = HERE / "Logo.png"
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
    if name not in help_icons and name != "wumpus":
        img.fill(color or TEXT, special_flags=pygame.BLEND_RGB_MAX)
    return _fit(img, size)


# --------------------------------------------------------------------------- #
# Texturas procedurales (fondo de cueva, casillas, brújula)
# --------------------------------------------------------------------------- #
def find_image(name):
    for folder in (HERE, ASSETS):
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


def norm_dir(value):
    """Convierte cualquier representación de dirección a N/E/S/W."""
    first = str(value).strip().upper()[:1]
    return {"N": "N", "U": "N", "E": "E", "R": "E", "S": "S", "D": "S",
            "W": "W", "O": "W", "L": "W"}.get(first, "N")


class SoundManager:
    """Gestiona efectos sintetizados y música opcional de la interfaz."""

    SAMPLE_RATE = 44100
    MUSIC_FILES = {
        "pregame": ("Fondo1.mp3",),
        "game": ("Partida.mp3",),
    }
    CLICK_FILE = "Botón.mp3"

    def __init__(self, music_enabled=True, effects_enabled=True):
        self.music_enabled = music_enabled
        self.effects_enabled = effects_enabled
        self.sounds = {}
        self.music_mode = None
        self.music_index = -1
        self.mixer_ready = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.SAMPLE_RATE, size=-16, channels=1)
            self.mixer_ready = True
            self.sounds = {
                "click": self._load_sound(self.CLICK_FILE) or self._tone(920, 1120, .065),
                "turn": self._tone(230, 180, .09),
                "move": self._tone(180, 280, .11),
                "gold": self._tone(520, 1040, .22),
                "shoot": self._tone(640, 120, .28),
                "breeze": self._tone(300, 520, .32, harmonics=2),
                "stench": self._tone(115, 75, .4, harmonics=3),
                "glitter": self._tone(880, 1320, .18),
                "bump": self._tone(90, 55, .16, harmonics=3),
                "scream": self._tone(420, 120, .5, harmonics=4),
                "win": self._tone(660, 1320, .5, harmonics=2),
                "lose": self._tone(180, 60, .55, harmonics=3),
            }
        except pygame.error:
            self.sounds = {}

    @staticmethod
    def _load_sound(filename):
        path = ASSETS.parent / filename
        if not path.exists():
            return None
        try:
            return pygame.mixer.Sound(str(path))
        except pygame.error:
            return None

    def _music_path(self, mode, index):
        files = self.MUSIC_FILES[mode]
        path = ASSETS.parent / files[index]
        return path if path.exists() else None

    def play_music(self, mode):
        """Inicia la música del menú o de la partida, repitiéndola si hace falta."""
        if not self.mixer_ready or mode not in self.MUSIC_FILES:
            return
        self.music_mode = mode
        self.music_index = -1
        self._next_music()

    def _next_music(self):
        if not self.mixer_ready:
            return
        if not self.music_enabled or self.music_mode is None:
            pygame.mixer.music.stop()
            return
        files = self.MUSIC_FILES[self.music_mode]
        for _ in range(len(files)):
            self.music_index = (self.music_index + 1) % len(files)
            path = self._music_path(self.music_mode, self.music_index)
            if path:
                try:
                    pygame.mixer.music.load(str(path))
                    pygame.mixer.music.play()
                    return
                except pygame.error:
                    continue
        pygame.mixer.music.stop()

    def update(self):
        if (self.mixer_ready and self.music_enabled and self.music_mode
                and not pygame.mixer.music.get_busy()):
            self._next_music()

    def _tone(self, start, end, duration, harmonics=1):
        samples = int(self.SAMPLE_RATE * duration)
        audio = array("h")
        for i in range(samples):
            progress = i / max(1, samples - 1)
            frequency = start + (end - start) * progress
            envelope = min(1.0, i / (self.SAMPLE_RATE * .012))
            envelope *= min(1.0, (samples - i) / (self.SAMPLE_RATE * .035))
            value = sum(math.sin(2 * math.pi * frequency * harmonic * i / self.SAMPLE_RATE)
                        / harmonic for harmonic in range(1, harmonics + 1))
            audio.append(max(-32767, min(32767, int(value * 10500 * envelope / harmonics))))
        return pygame.mixer.Sound(buffer=audio.tobytes())

    def play(self, name):
        if self.effects_enabled and name in self.sounds:
            self.sounds[name].play()

    def set_music_enabled(self, enabled):
        self.music_enabled = enabled
        if not self.mixer_ready:
            return
        if enabled:
            if self.music_mode:
                self._next_music()
        else:
            pygame.mixer.music.stop()

    def set_effects_enabled(self, enabled):
        self.effects_enabled = enabled


@lru_cache(maxsize=16)
def map_dims(filename):
    match = re.search(r"(\d+)x(\d+)", filename)
    if match:
        return int(match.group(1)), int(match.group(2))
    try:
        data = json.loads((DATA / filename).read_text(encoding="utf-8"))
        for key in ("size", "board_size", "dimensions"):
            if key in data:
                v = data[key]
                return (int(v[0]), int(v[1])) if isinstance(v, (list, tuple)) else (int(v), int(v))
        if "width" in data and "height" in data:
            return int(data["width"]), int(data["height"])
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        pass
    return 4, 4


# --------------------------------------------------------------------------- #
# Widgets
# --------------------------------------------------------------------------- #
class Button:
    """Botón con icono opcional y estados normal, hover, pulsado y deshabilitado.

    ``kind='ghost'`` crea una zona clicable invisible (para tarjetas).
    """

    def __init__(self, rect, label, callback, kind="secondary", enabled=True, icon_name=None,
                 stack=False, size=20, native=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.kind = kind
        self.enabled = enabled
        self.icon_name = icon_name
        self.stack = stack
        self.size = size
        self.native = native

    def draw(self, surface, mouse, down, force_disabled=False):
        if self.kind == "ghost":
            return
        enabled = self.enabled and not force_disabled
        hover = enabled and self.rect.collidepoint(mouse)
        state = "disabled" if not enabled else "pressed" if hover and down else \
            "hover" if hover else "normal"
        w, h = self.rect.size
        surface.blit(button_surf(w, h, self.kind, state), self.rect.topleft)
        ink = BUTTON_COLORS.get(self.kind, BUTTON_COLORS["secondary"])[1]
        if not enabled:
            ink = (140, 148, 180)
        dy = 4 if state == "pressed" else 0
        cx, cy = self.rect.centerx, self.rect.centery + dy
        icon_color = None if self.native and enabled else ink
        if self.icon_name and self.stack:
            isz = int(h * .42)
            surface.blit(icon(self.icon_name, isz, icon_color), (cx - isz // 2, self.rect.y + dy + 6))
            draw_text(surface, self.label, (cx, self.rect.bottom - 8 + dy), self.size, ink,
                      anchor="midbottom", title=True)
        elif self.icon_name:
            isz = int(min(h * .56, 34))
            lw = font(self.size, False, True).size(self.label)[0] if self.label else 0
            total = isz + (12 + lw if self.label else 0)
            x0 = cx - total // 2
            surface.blit(icon(self.icon_name, isz, icon_color), (x0, cy - isz // 2))
            if self.label:
                draw_text(surface, self.label, (x0 + isz + 12, cy), self.size, ink,
                          anchor="midleft", title=True)
        else:
            draw_text(surface, self.label, (cx, cy), self.size, ink, anchor="center", title=True)

    def click(self, event):
        if self.enabled and event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.callback()
                return True
        return False


def chip(surface, pos, icon_name, label, color, size=14):
    """Etiqueta redondeada con icono. Devuelve su rect."""
    f = font(size, True)
    w = 14 + 22 + 8 + f.size(label)[0] + 14
    rect = pygame.Rect(pos[0], pos[1], w, 30)
    surface.blit(panel_surf(rect.w, rect.h, mix(color, PANEL, .78), color, 15, False), rect.topleft)
    surface.blit(icon(icon_name, 22), (rect.x + 10, rect.y + 4))
    draw_text(surface, label, (rect.x + 40, rect.centery), size, TEXT, True, "midleft")
    return rect


def keycap(surface, rect, label=None, icon_name=None):
    pygame.draw.rect(surface, INK, rect.move(0, 6), border_radius=12)
    pygame.draw.rect(surface, (62, 72, 150), rect, border_radius=12)
    face = rect.inflate(-8, -12).move(0, -2)
    pygame.draw.rect(surface, (92, 104, 200), face, border_radius=10)
    if icon_name:
        isz = int(rect.h * .5)
        surface.blit(icon(icon_name, isz), icon(icon_name, isz).get_rect(center=face.center))
    else:
        draw_text(surface, label, face.center, 22, TEXT, anchor="center", title=True)


# --------------------------------------------------------------------------- #
# Aplicación
# --------------------------------------------------------------------------- #
class App:
    """Controla navegación, renderizado e integración incremental con ``Game``."""

    HELP_PAGES = ["Tu misión", "Peligros", "Percepciones", "Controles", "Modalidades"]

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Wumpus World")
        flags = pygame.SCALED | pygame.RESIZABLE
        self.screen = pygame.display.set_mode((W, H), flags)
        self.clock = pygame.time.Clock()
        self.settings = self.load_settings()
        self.audio = SoundManager(self.settings["music"], self.settings["effects"])
        self.audio.play_music("pregame")
        if self.settings["fullscreen"]:
            self.apply_fullscreen()
        self.t = 0.0
        self.fade = 1.0
        self.mouse = (0, 0)
        self.state = "menu"
        self.mode = None
        self.map_index = 0
        self.game = None
        self.paused = False
        self.finished = False
        self.result_hidden = False
        self.auto_agent = True
        self.agent_timer = 0.0
        self.help_page = 0
        self.settings_from = "menu"
        self.settings_scroll = 0
        self.settings_max_scroll = 200
        self.error = ""
        self.message = "Explora la cueva y encuentra todo el oro."
        self.notes = {}
        self.max_arrows = 1
        self.max_lives = 0
        self.vis_pos = None
        self.hand_cursor = False
        self.buttons = []

    # ----------------------------------------------------------- ajustes --
    @staticmethod
    def load_settings():
        data = dict(DEFAULT_SETTINGS)
        try:
            data.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
        data["speed"] = max(0, min(len(SPEEDS) - 1, int(data.get("speed", 1))))
        if "sound" in data:
            data.setdefault("music", data["sound"])
            data.setdefault("effects", data["sound"])
        data["music"] = bool(data.get("music", True))
        data["effects"] = bool(data.get("effects", True))
        return data

    def save_settings(self):
        try:
            SETTINGS_FILE.write_text(json.dumps(self.settings, indent=2), encoding="utf-8")
        except OSError:
            pass

    def apply_fullscreen(self):
        try:
            if bool(pygame.display.get_surface().get_flags() & pygame.FULLSCREEN) != \
                    self.settings["fullscreen"]:
                pygame.display.toggle_fullscreen()
        except pygame.error:
            pass

    def toggle_setting(self, key):
        self.settings[key] = not self.settings[key]
        if key == "music":
            self.audio.set_music_enabled(self.settings[key])
        elif key == "effects":
            self.audio.set_effects_enabled(self.settings[key])
            if self.settings[key]:
                self.audio.play("click")
        if key == "fullscreen":
            self.apply_fullscreen()
        self.save_settings()

    def set_speed(self, index):
        self.settings["speed"] = max(0, min(len(SPEEDS) - 1, index))
        self.save_settings()

    # -------------------------------------------------------- navegación --
    def set_state(self, state):
        self.state = state
        self.buttons = []
        self.fade = 1.0
        self.error = ""

    def go_menu(self):
        self.paused = False
        self.finished = False
        self.set_state("menu")

    def show_help(self):
        self.help_page = 0
        self.set_state("help")

    def show_settings(self, origin):
        self.settings_from = origin
        self.settings_scroll = 0
        self.set_state("settings")

    def back_from_settings(self):
        self.set_state(self.settings_from)

    def back(self):
        """Acción de la tecla ESC en las pantallas de menú."""
        target = {"mode": "menu", "maps": "mode", "setup": "maps", "help": "menu"}
        if self.state in target:
            self.set_state(target[self.state])
        elif self.state == "settings":
            self.back_from_settings()

    # ------------------------------------------------------ bucle y juego --
    def run(self):
        """Ejecuta el bucle principal hasta que el usuario cierre la ventana."""
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            self.t += dt
            self.fade = max(0.0, self.fade - dt * 4.5)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    self.key(event)
                elif event.type == pygame.MOUSEWHEEL and self.state == "settings":
                    self.settings_scroll = max(0, min(self.settings_max_scroll,
                                                      self.settings_scroll - event.y * 38))
                elif event.type == pygame.MOUSEBUTTONUP:
                    for button in list(self.buttons):
                        if button.click(event):
                            self.audio.play("click")
                            break
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def update(self, dt):
        """Avanza al agente con un temporizador (sin bloquear el bucle)."""
        self.audio.update()
        if (self.state == "game" and self.mode == "agent" and self.auto_agent
                and not self.paused and not self.finished and self.game):
            self.agent_timer += dt
            if self.agent_timer >= SPEEDS[self.settings["speed"]][1] / 1000.0:
                self.agent_timer = 0.0
                self.agent_step()

    def key(self, event):
        if event.key == pygame.K_ESCAPE:
            if self.state == "game":
                if not self.finished:
                    self.paused = not self.paused
            else:
                self.back()
            return
        if self.state != "game" or self.paused or self.finished:
            return
        if self.mode == "manual":
            actions = {pygame.K_LEFT: "TURN_LEFT", pygame.K_RIGHT: "TURN_RIGHT",
                       pygame.K_UP: "FORWARD", pygame.K_g: "GRAB",
                       pygame.K_SPACE: "SHOOT", pygame.K_c: "CLIMB"}
            if event.key in actions:
                self.perform(actions[event.key])
        elif self.mode == "agent":
            if event.key == pygame.K_SPACE:
                self.auto_agent = not self.auto_agent
            elif event.key == pygame.K_n:
                self.agent_step()

    def perform(self, action):
        if self.game and not self.paused and not self.finished:
            self.event_message(self.game.act(action))

    def agent_step(self):
        if self.mode == "agent" and self.game and not self.paused and not self.finished:
            self.event_message(self.game.step())

    def event_message(self, state):
        action = state.get("last_action")
        labels = {"TURN_LEFT": "Giraste a la izquierda.", "TURN_RIGHT": "Giraste a la derecha.",
                  "FORWARD": "Avanzaste.", "GRAB": "Recogiste el oro.",
                  "SHOOT": "Disparaste una flecha.", "CLIMB": "Intentaste salir."}
        msg = labels.get(action, action or self.message)
        action_sounds = {
            "TURN_LEFT": "turn", "TURN_RIGHT": "turn", "FORWARD": "move",
            "GRAB": "gold", "SHOOT": "shoot",
        }
        if action in action_sounds:
            self.audio.play(action_sounds[action])
        perception = state.get("perception") or {}
        for key, _, _, _ in SENSES:
            if perception.get(key):
                self.audio.play(key)
        if perception.get("bump"):
            msg += " ¡Chocaste con un muro!"
        if perception.get("scream"):
            msg += " Se oyó un grito."
        self.message = msg
        if state["status"] != "running":
            self.finished = True
            self.result_hidden = False
            self.audio.play("win" if state["status"] == "success" else "lose")

    def start(self):
        try:
            self.game = Game(DATA / MAPS[self.map_index][0],
                             allow_risk=self.mode == "agent", arrows=1)
            state = self.game.get_state()
        except Exception as exc:  # el mapa puede faltar o estar mal formado
            self.error = f"No se pudo cargar el mapa: {exc}"
            return
        agent = state["agent"]
        self.paused = False
        self.finished = False
        self.result_hidden = False
        self.auto_agent = self.mode == "agent"
        self.agent_timer = 0.0
        self.notes = {}
        self.vis_pos = None
        self.max_arrows = max(1, agent.get("arrows", 1))
        self.max_lives = self.life_value(agent) or 0
        self.message = "Pedro empezará a explorar." if self.mode == "agent" else \
            "Usa las flechas del teclado o los botones."
        self.audio.play_music("game")
        self.set_state("game")

    @staticmethod
    def life_value(agent):
        for key in ("lives", "life", "health", "hp"):
            if key in agent and isinstance(agent[key], (int, float)):
                return int(agent[key])
        return None

    # ----------------------------------------------------------- dibujo --
    def add(self, rect, label, callback, kind="secondary", enabled=True, icon_name=None,
            stack=False, size=20, native=False):
        button = Button(rect, label, callback, kind, enabled, icon_name, stack, size, native)
        self.buttons.append(button)
        return button

    def hit(self, rect, callback):
        self.buttons.append(Button(rect, "", callback, "ghost"))

    def flush_buttons(self, disabled=False, clear=True):
        """Dibuja los botones acumulados.

        Antes de un modal se llama con ``clear=True``: los botones del HUD se pintan
        deshabilitados y se descartan para que no reciban clics. Al final del
        fotograma se llama con ``clear=False``: los botones siguen disponibles para
        el manejo de eventos del siguiente ciclo.
        """
        down = pygame.mouse.get_pressed()[0]
        for button in self.buttons:
            button.draw(self.screen, self.mouse, down, force_disabled=disabled)
        if clear:
            self.buttons = []

    def draw(self):
        self.buttons = []
        self.mouse = pygame.mouse.get_pos()
        self.screen.blit(background(), (0, 0))
        {"menu": self.draw_menu, "mode": self.draw_mode, "maps": self.draw_maps,
         "setup": self.draw_setup, "help": self.draw_help, "settings": self.draw_settings,
         "game": self.draw_game}[self.state]()
        self.update_cursor()
        self.flush_buttons(clear=False)
        if self.fade > 0:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((6, 7, 24, int(255 * self.fade)))
            self.screen.blit(veil, (0, 0))

    def update_cursor(self):
        over = any(b.enabled and b.rect.collidepoint(self.mouse) for b in self.buttons)
        if over == self.hand_cursor:
            return
        self.hand_cursor = over
        try:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if over else pygame.SYSTEM_CURSOR_ARROW)
        except (pygame.error, AttributeError, TypeError):
            pass

    def heading(self, title, subtitle="", icon_name="wumpus"):
        if icon_name == "logo":
            img = logo(150, 90)
            if img:
                self.screen.blit(img, (48, 20))
            else:
                self.screen.blit(icon("wumpus", 150), (48, 20))
        else:
            self.screen.blit(icon(icon_name, 150), (48, 6))
        draw_text(self.screen, title, (W // 2, 38), 44, TEXT, anchor="midtop", title=True,
                  outline=INK, outline_w=3)
        if subtitle:
            draw_text(self.screen, subtitle, (W // 2, 94), 17, MUTED, True, "midtop")

    def nav(self, back_cb, next_cb=None, next_label="Continuar", next_enabled=True,
            next_icon="arrow_right"):
        self.add((60, H - 86, 190, 56), "Volver", back_cb, "tertiary", icon_name="arrow_left")
        if next_cb:
            self.add((W - 290, H - 86, 230, 56), next_label, next_cb, "primary",
                     next_enabled, next_icon)

    def card(self, rect, selected, callback):
        hover = rect.collidepoint(self.mouse)
        fill = PANEL_2 if selected or hover else PANEL
        border = PRIMARY if selected else BORDER_HI if hover else BORDER
        self.screen.blit(panel_surf(rect.w, rect.h, fill, border, 22), rect.topleft)
        if selected:
            c = (rect.right - 30, rect.y + 30)
            pygame.draw.circle(self.screen, SUCCESS, c, 17)
            self.screen.blit(icon("check", 22, TEXT), (c[0] - 11, c[1] - 11))
        self.hit(rect, callback)

    # ------------------------------------------------------------- menú --
    def draw_menu(self):
        img = logo(460, 250)
        if img:
            self.screen.blit(img, img.get_rect(midtop=(W // 2, 20)))
        else:
            self.screen.blit(icon("wumpus", 128), (W // 2 - 64, 14))
            draw_text(self.screen, "WUMPUS", (W // 2, 196), 108, TEXT, anchor="center",
                      title=True, outline=INK, outline_w=7)
        bx = W // 2 - 160
        self.add((bx, 300, 320, 62), "Jugar", lambda: self.set_state("mode"), "primary",
                 icon_name="menu_play", size=26)
        self.add((bx, 376, 320, 62), "Configuración", lambda: self.show_settings("menu"),
                 icon_name="menu_settings", size=24)
        self.add((bx, 452, 320, 62), "Cómo jugar", self.show_help,
                 icon_name="menu_book", size=24)
        self.add((bx, 528, 320, 62), "Salir",
                 lambda: pygame.event.post(pygame.event.Event(pygame.QUIT)),
                 "danger", icon_name="menu_exit", size=24)

    # ------------------------------------------------- ayuda / tutorial --
    def draw_help(self):
        self.heading("Cómo jugar", f"Tutorial  ·  {self.help_page + 1} de {len(self.HELP_PAGES)}",
                     "logo")
        panel_rect = pygame.Rect(70, 130, W - 140, 466)
        self.screen.blit(panel_surf(panel_rect.w, panel_rect.h, PANEL, BORDER, 24), panel_rect.topleft)
        draw_text(self.screen, self.HELP_PAGES[self.help_page], (panel_rect.x + 40, panel_rect.y + 24),
                  38, PRIMARY, title=True)
        [self.help_mission, self.help_dangers, self.help_senses, self.help_controls,
         self.help_modes][self.help_page](panel_rect)
        for i in range(len(self.HELP_PAGES)):
            col = PRIMARY if i == self.help_page else BORDER
            pygame.draw.circle(self.screen, col, (W // 2 - 40 + i * 20, H - 58), 6)
        last = self.help_page == len(self.HELP_PAGES) - 1
        self.add((70, H - 86, 160, 56), "Menú", self.go_menu, "tertiary", icon_name="home")
        self.add((700, H - 86, 160, 56), "Anterior",
                 lambda: setattr(self, "help_page", self.help_page - 1), "tertiary",
                 self.help_page > 0, "arrow_left")
        if last:
            self.add((870, H - 86, 160, 56), "Entendido", self.go_menu, "primary",
                     icon_name="check")
        else:
            self.add((870, H - 86, 160, 56), "Siguiente",
                     lambda: setattr(self, "help_page", self.help_page + 1), "primary",
                     icon_name="arrow_right")

    def help_mission(self, box):
        side = 96
        x0, y0 = box.x + 50, box.y + 88
        for row in range(3):
            for col in range(4):
                known = (col, row) in ((0, 2), (3, 0))
                self.screen.blit(tile(side - 4, known, (row * 4 + col) % 4),
                                 (x0 + col * side, y0 + row * side))
        self.screen.blit(entrance_overlay(side - 4), (x0, y0 + 2 * side))
        self.screen.blit(icon("explorer_E", 78), (x0 + 9, y0 + 2 * side + 6))
        self.screen.blit(icon("help_gold", 62), (x0 + 3 * side + 16, y0 + 16))
        tx, tw = box.x + 500, box.w - 560
        text_block(self.screen, "Pedro entra en una cueva oscura donde no ve nada. Tu objetivo es "
                   "encontrar todo el oro y volver a la casilla de entrada para salir.",
                   (tx, box.y + 88), tw, 21, TEXT, line_h=30)
        for i, (ico, msg) in enumerate([
                ("glitter", "Las casillas que visitas se iluminan en el mapa."),
                ("compass", "Usa las percepciones para deducir dónde hay peligro."),
                ("exit", "Recoge el oro y pulsa C en la entrada para salir.")]):
            y = box.y + 215 + i * 56
            self.screen.blit(icon(ico, 38), (tx, y))
            text_block(self.screen, msg, (tx + 56, y + 4), tw - 56, 18, MUTED, True, max_lines=2)

    def help_dangers(self, box):
        cards = [("help_pit", "Pozo", "Si caes en un pozo, pierdes la partida. Se anuncia con una brisa."),
                 ("help_wumpus", "Wumpus", "Si entras en la casilla de un Wumpus vivo, te devora. Se anuncia con hedor."),
                 ("help_arrow", "Flecha", "Dispara en la dirección en la que miras para matar a un Wumpus. Tu munición es limitada.")]
        cw = (box.w - 80 - 40) // 3
        for i, (ico, title, desc) in enumerate(cards):
            r = pygame.Rect(box.x + 40 + i * (cw + 20), box.y + 82, cw, 350)
            self.screen.blit(panel_surf(r.w, r.h, PANEL_2, BORDER, 20), r.topleft)
            self.screen.blit(icon(ico, 118), (r.centerx - 59, r.y + 24))
            draw_text(self.screen, title, (r.centerx, r.y + 172), 30, TEXT, anchor="midtop", title=True)
            text_block(self.screen, desc, (r.x + 22, r.y + 224), r.w - 44, 17, MUTED, True, center=True)

    def help_senses(self, box):
        rows = [("breeze", "Brisa", "Hay un pozo en una casilla vecina."),
                ("stench", "Hedor", "Hay un Wumpus en una casilla vecina."),
                ("glitter", "Brillo", "Hay oro en tu casilla: pulsa G para recogerlo."),
                ("bump", "Golpe", "Has chocado contra un muro."),
                ("scream", "Grito", "Tu flecha ha matado a un Wumpus.")]
        for i, (ico, name, desc) in enumerate(rows):
            y = box.y + 90 + i * 68
            r = pygame.Rect(box.x + 40, y, box.w - 80, 62)
            self.screen.blit(panel_surf(r.w, r.h, PANEL_2, BORDER, 16, False), r.topleft)
            self.screen.blit(icon(ico, 44, SENSES[i][3]), (r.x + 18, r.y + 9))
            draw_text(self.screen, name, (r.x + 88, r.centery), 26, SENSES[i][3], anchor="midleft", title=True)
            draw_text(self.screen, desc, (r.x + 250, r.centery), 19, TEXT, True, "midleft")

    def help_controls(self, box):
        arrows = [("arrow_left", "Girar a la izquierda"), ("arrow_up", "Avanzar"),
                  ("arrow_right", "Girar a la derecha")]
        for i, (ico, cap) in enumerate(arrows):
            r = pygame.Rect(box.x + 120 + i * 280, box.y + 88, 72, 66)
            keycap(self.screen, r, icon_name=ico)
            text_block(self.screen, cap, (r.centerx - 100, r.bottom + 18), 200, 16, MUTED, True, center=True)
        keys = [("G", "Recoger el oro"), ("ESPACIO", "Disparar la flecha"),
                ("C", "Salir por la entrada"), ("ESC", "Pausar el juego")]
        for i, (label, cap) in enumerate(keys):
            r = pygame.Rect(box.x + 120 + (i % 2) * 440, box.y + 232 + (i // 2) * 78,
                            150 if len(label) > 2 else 72, 62)
            keycap(self.screen, r, label)
            draw_text(self.screen, cap, (r.right + 22, r.centery), 19, TEXT, True, "midleft")

    def help_modes(self, box):
        cards = [("explorer_S", "Explorador", ["Tú tomas cada decisión.", "Usa el teclado o los botones.",
                                               "Descubre la cueva paso a paso."]),
                 ("robot", "Observar al agente", ["Pedro deduce y actúa solo.", "Puedes pausar, ir paso a paso",
                                                  "y cambiar la velocidad."])]
        cw = (box.w - 80 - 30) // 2
        for i, (ico, title, lines) in enumerate(cards):
            r = pygame.Rect(box.x + 40 + i * (cw + 30), box.y + 100, cw, 300)
            self.screen.blit(panel_surf(r.w, r.h, PANEL_2, BORDER, 20), r.topleft)
            self.screen.blit(icon(ico, 96), (r.centerx - 48, r.y + 20))
            draw_text(self.screen, title, (r.centerx, r.y + 130), 30, TEXT, anchor="midtop", title=True)
            for j, line in enumerate(lines):
                draw_text(self.screen, line, (r.centerx, r.y + 186 + j * 30), 18, MUTED, True, "midtop")
        draw_text(self.screen, "Elegirás la modalidad cuando pulses Jugar en el menú principal.",
                  (box.x + 40, box.bottom - 52), 17, MUTED, True)

    # ------------------------------------------------- selección de partida --
    def draw_mode(self):
        self.heading("Elige tu modalidad", "Las dos modalidades usan el mismo mundo y las mismas reglas.")
        cards = [("manual", "explorer_S", "Explorador", "Toma cada decisión y descubre la cueva.",
                  "Teclado + botones"),
                 ("agent", "robot", "Observar al agente", "Pedro deduce, actúa y vuelve a la entrada.",
                  "Pausa, paso a paso y velocidad")]
        for i, (kind, ico, title, desc, hint) in enumerate(cards):
            r = pygame.Rect(60 + i * (CARD_W + 30), 170, CARD_W, 380)
            self.card(r, self.mode == kind, lambda k=kind: setattr(self, "mode", k))
            self.screen.blit(icon(ico, 180), (r.centerx - 90, r.y + 14))
            draw_text(self.screen, title, (r.centerx, r.y + 194), 34, TEXT, anchor="midtop", title=True)
            text_block(self.screen, desc, (r.x + 40, r.y + 250), r.w - 80, 19, MUTED, True, center=True)
            draw_text(self.screen, hint, (r.centerx, r.y + 320), 16, PRIMARY, True, "midtop")
        self.nav(lambda: self.set_state("menu"), lambda: self.set_state("maps"),
                 next_enabled=self.mode is not None)

    def draw_maps(self):
        self.heading("Selecciona el mapa", "Escoge cualquiera")
        for i, (filename, name, desc) in enumerate(MAPS):
            col, row = i % 2, i // 2
            r = pygame.Rect(60 + col * (CARD_W + 30), 180 + row * 215, CARD_W, 195)
            self.card(r, i == self.map_index, lambda index=i: setattr(self, "map_index", index))
            self.mini_board(pygame.Rect(r.x + 24, r.y + 28, 138, 138), *map_dims(filename))
            draw_text(self.screen, name, (r.x + 186, r.y + 28), 25, TEXT, title=True)
            text_block(self.screen, desc, (r.x + 186, r.y + 70), r.w - 186 - 28, 16, MUTED, True, max_lines=3)
            w, h = map_dims(filename)
            chip(self.screen, (r.x + 186, r.bottom - 54), "compass", f"{w} x {h}", BORDER_HI)
        self.nav(lambda: self.set_state("mode"), self.start, "Iniciar partida", True, "play")

    def mini_board(self, rect, cols, rows):
        cell = max(2, min(rect.w // cols, rect.h // rows))
        gap = 1 if cell > 7 else 0
        ox = rect.x + (rect.w - cell * cols) // 2
        oy = rect.y + (rect.h - cell * rows) // 2
        pygame.draw.rect(self.screen, INK, pygame.Rect(ox - 4, oy - 4, cell * cols + 8, cell * rows + 8),
                         border_radius=8)
        for r in range(rows):
            for c in range(cols):
                color = PRIMARY if (r, c) == (rows - 1, 0) else (46, 54, 114) if (r + c) % 2 else (38, 45, 98)
                pygame.draw.rect(self.screen, color,
                                 (ox + c * cell, oy + r * cell, cell - gap, cell - gap))

    def draw_setup(self):
        self.heading("Prepara la partida", "Revisa la selección antes de entrar en la cueva.")
        filename, name, desc = MAPS[self.map_index]
        left = pygame.Rect(60, 140, CARD_W, 300)
        right = pygame.Rect(60 + CARD_W + 30, 140, CARD_W, 300)
        for r in (left, right):
            self.screen.blit(panel_surf(r.w, r.h, PANEL, BORDER, 22), r.topleft)
        manual = self.mode == "manual"
        draw_text(self.screen, "MODALIDAD", (left.x + 30, left.y + 24), 15, MUTED, True)
        self.screen.blit(icon("explorer_S" if manual else "robot", 120), (left.x + 18, left.y + 58))
        draw_text(self.screen, "Explorador" if manual else "Observar al agente",
                  (left.x + 150, left.y + 92), 28, TEXT, title=True)
        text_block(self.screen, "Controlas a Pedro con el teclado o los botones." if manual else
                   "Pedro explora solo; tú puedes pausar o avanzar paso a paso.",
                   (left.x + 150, left.y + 134), left.w - 180, 16, MUTED, True, max_lines=3)
        draw_text(self.screen, "MAPA", (right.x + 30, right.y + 24), 15, MUTED, True)
        self.mini_board(pygame.Rect(right.x + 30, right.y + 64, 120, 120), *map_dims(filename))
        draw_text(self.screen, name, (right.x + 176, right.y + 82), 24, TEXT, title=True)
        text_block(self.screen, desc, (right.x + 176, right.y + 124), right.w - 206, 16, MUTED, True, max_lines=4)
        strip = pygame.Rect(60, 470, W - 120, 70)
        self.screen.blit(panel_surf(strip.w, strip.h, PANEL, BORDER, 18, False), strip.topleft)
        tip = ("Flechas: girar/avanzar  ·  G: recoger  ·  Espacio: disparar  ·  C: salir  ·  Esc: pausa"
               if manual else "Espacio: auto  ·  N: un paso  ·  Esc: pausa  ·  La velocidad se cambia en el panel")
        self.screen.blit(icon("gear", 30, MUTED), (strip.x + 24, strip.y + 20))
        draw_text(self.screen, tip, (strip.x + 72, strip.centery), 17, TEXT, True, "midleft")
        self.nav(lambda: self.set_state("maps"), self.start, "Iniciar partida", True, "play")
        if self.error:
            draw_text(self.screen, self.error, (W // 2, 580), 16, DANGER, True, "center")

    def draw_settings(self):
        self.heading("Configuración", "Los cambios se guardan automáticamente.")
        box = pygame.Rect(60, 138, W - 120, 470)
        self.screen.blit(panel_surf(box.w, box.h, PANEL, BORDER, 24), box.topleft)
        viewport = box.inflate(-24, -24)
        content_y = viewport.y + 18 - self.settings_scroll
        self.screen.set_clip(viewport)

        def section(title, y, icon_name):
            self.screen.blit(icon(icon_name, 26, PRIMARY), (viewport.x + 8, y))
            draw_text(self.screen, title, (viewport.x + 46, y + 3), 22, PRIMARY, title=True)
            pygame.draw.line(self.screen, BORDER, (viewport.x + 8, y + 36),
                             (viewport.right - 8, y + 36), 1)

        def setting_row(title, desc, y, key, icon_name):
            draw_text(self.screen, title, (viewport.x + 18, y), 21, TEXT, title=True)
            draw_text(self.screen, desc, (viewport.x + 18, y + 29), 14, MUTED, True)
            on = self.settings[key]
            rect = pygame.Rect(viewport.right - 158, y + 4, 132, 46)
            if viewport.contains(rect):
                self.add(rect, "Sí" if on else "No", lambda k=key: self.toggle_setting(k),
                         "success" if on else "tertiary",
                         icon_name="check" if on else "close", size=18)

        section("Audio", content_y, "play")
        setting_row("Música de fondo", "Canciones de menús y partida.", content_y + 52,
                    "music", "play")
        setting_row("Efectos de sonido", "Botones, acciones y percepciones.", content_y + 122,
                    "effects", "glitter")

        general_y = content_y + 212
        section("Interfaz", general_y, "gear")
        setting_row("Pantalla completa", "Alterna el modo de visualización.", general_y + 52,
                    "fullscreen", "gear")
        setting_row("Percepciones en el mapa", "Conserva brisa y hedor en casillas visitadas.",
                    general_y + 122, "notes", "compass")
        setting_row("Coordenadas del tablero", "Muestra filas y columnas alrededor del mapa.",
                    general_y + 192, "coords", "compass")

        speed_y = content_y + 452
        section("Agente", speed_y, "robot")
        draw_text(self.screen, "Velocidad de avance", (viewport.x + 18, speed_y + 52),
                  21, TEXT, title=True)
        draw_text(self.screen, "Tiempo entre pasos en la modalidad agente.",
                  (viewport.x + 18, speed_y + 81), 14, MUTED, True)
        for j, (label, _) in enumerate(SPEEDS):
            rect = pygame.Rect(viewport.x + 18 + j * 123, speed_y + 112, 112, 44)
            if viewport.contains(rect):
                self.add(rect, label, lambda idx=j: self.set_speed(idx),
                         "primary" if self.settings["speed"] == j else "tertiary", size=17)

        self.screen.set_clip(None)
        track = pygame.Rect(box.right - 14, viewport.y, 4, viewport.h)
        pygame.draw.rect(self.screen, TERTIARY, track, border_radius=2)
        thumb_h = max(48, int(viewport.h * viewport.h / (viewport.h + self.settings_max_scroll)))
        thumb_y = viewport.y + int((viewport.h - thumb_h) *
                                    self.settings_scroll / self.settings_max_scroll)
        pygame.draw.rect(self.screen, BORDER_HI, (track.x, thumb_y, track.w, thumb_h), border_radius=2)
        self.add((60, H - 86, 190, 56), "Volver", self.back_from_settings, "primary",
                 icon_name="arrow_left")

    # ------------------------------------------------------------ juego --
    def draw_game(self):
        state = self.game.get_state()
        self.update_notes(state)
        self.draw_topbar()
        self.draw_board(state)
        self.draw_sidebar(state)
        if self.finished and not self.result_hidden:
            self.flush_buttons(disabled=True)
            self.draw_result(state)
        elif self.finished:
            self.flush_buttons(disabled=True)
            self.draw_reveal_bar()
        elif self.paused:
            self.flush_buttons(disabled=True)
            self.draw_pause()

    def update_notes(self, state):
        pos = tuple(state["agent"]["position"])
        senses = {key for key, *_ in SENSES if (state.get("perception") or {}).get(key)}
        self.notes.setdefault(pos, set()).update(senses & {"breeze", "stench"})

    def draw_topbar(self):
        img = logo(150, 90)
        if img and img.get_width() >= 2 * img.get_height():
            self.screen.blit(img, (48, 20))
        else:
            draw_text(self.screen, "WUMPUS", (48, 20), 38, TEXT, anchor="topleft", title=True,
                      outline=INK, outline_w=3)
        manual = self.mode == "manual"
        r = chip(self.screen, (248, 25), "explorer_S" if manual else "robot",
                 "Explorador" if manual else "Agente", SECONDARY)
        chip(self.screen, (r.right + 12, 25), "compass", MAPS[self.map_index][1], BORDER_HI)
        self.add((W - 76, 14, 52, 52), "", lambda: setattr(self, "paused", True), "secondary",
                 icon_name="pause")

    def board_geometry(self, state):
        width, height = state["board_size"]
        area = pygame.Rect(24, 84, SX - 36, 612)
        side = max(10, min((area.w - 36) // width, (area.h - 36) // height, 140))
        rect = pygame.Rect(0, 0, side * width, side * height)
        rect.center = area.center
        return rect, side

    def draw_board(self, state):
        width, height = state["board_size"]
        rect, side = self.board_geometry(state)
        frame = rect.inflate(30, 30)
        self.screen.blit(panel_surf(frame.w, frame.h, (9, 11, 34), BORDER, 24), frame.topleft)
        visited = set(map(tuple, state["knowledge"]["visited"]))
        start = tuple(state["initial_position"])
        reveal = self.finished
        world = state["world"]
        pits = {tuple(p) for p in world["pits"]}
        gold = {tuple(p) for p in world["gold"]}
        wumpus = {tuple(p) for p in world["live_wumpus"]}
        show_notes = self.settings["notes"] and side >= 36
        layers = ((pits, "pit", .78), (gold, "gold", .62), (wumpus, "wumpus", .8))
        for y in range(1, height + 1):
            for x in range(1, width + 1):
                cx, cy = rect.x + (x - 1) * side, rect.bottom - y * side
                known = (x, y) in visited or (x, y) == start or reveal
                self.screen.blit(tile(side - 3, known, (x * 7 + y * 13) % 4), (cx + 1, cy + 1))
                if (x, y) == start:
                    self.screen.blit(entrance_overlay(side - 3), (cx + 1, cy + 1))
                if not known:
                    continue
                for cells, name, frac in layers:
                    if (x, y) in cells:
                        img = icon(name, int(side * frac))
                        self.screen.blit(img, img.get_rect(center=(cx + side // 2, cy + side // 2)))
                if show_notes and (x, y) in self.notes:
                    for n, key in enumerate(sorted(self.notes[(x, y)])):
                        small = icon(key, int(side * .28))
                        self.screen.blit(small, (cx + 5 + n * (small.get_width() + 1), cy + side - small.get_height() - 5))
        if state["status"] != "success":
            self.draw_explorer(state, rect, side)
        if self.settings["coords"] and side >= 24:
            for x in range(1, width + 1):
                draw_text(self.screen, x, (rect.x + (x - .5) * side, rect.bottom + 9), 12, MUTED, True, "center")
            for y in range(1, height + 1):
                draw_text(self.screen, y, (rect.x - 10, rect.bottom - (y - .5) * side), 12, MUTED, True, "center")

    def draw_explorer(self, state, rect, side):
        agent = state["agent"]
        x, y = agent["position"]
        target = (rect.x + (x - .5) * side, rect.bottom - (y - .5) * side)
        if self.vis_pos is None:
            self.vis_pos = list(target)
        else:
            k = min(1.0, 16 * (1 / 60))
            self.vis_pos[0] += (target[0] - self.vis_pos[0]) * k
            self.vis_pos[1] += (target[1] - self.vis_pos[1]) * k
        facing = norm_dir(agent["direction"])
        px, py = self.vis_pos
        py += math.sin(self.t * 5) * side * .02
        g = glow(int(side * .8), PRIMARY)
        self.screen.blit(g, g.get_rect(center=(px, py)))
        img = icon(f"explorer_{facing}", int(side * .88))
        self.screen.blit(img, img.get_rect(center=(px, py - side * .03)))
        if side >= 30:
            vx, vy = DIR_VEC[facing]
            tipx, tipy = px + vx * side * .45, py + vy * side * .45
            nx, ny = -vy, vx
            pygame.draw.polygon(self.screen, PRIMARY, [
                (tipx, tipy), (tipx - vx * side * .14 + nx * side * .1, tipy - vy * side * .14 + ny * side * .1),
                (tipx - vx * side * .14 - nx * side * .1, tipy - vy * side * .14 - ny * side * .1)])

    def stat_tile(self, rect, icon_name, label, value=None, extra=None):
        self.screen.blit(panel_surf(rect.w, rect.h, (20, 23, 64), None, 12, False), rect.topleft)
        self.screen.blit(icon(icon_name, 30), (rect.x + 10, rect.centery - 15))
        draw_text(self.screen, label, (rect.x + 50, rect.y + 6), 11, MUTED, True)
        if extra:
            extra(rect)
        else:
            draw_text(self.screen, value, (rect.x + 50, rect.y + 20), 20, TEXT, True)

    def draw_sidebar(self, state):
        agent = state["agent"]
        sx, sw = SX, SB_W
        # --- estadísticas ---
        lives = self.life_value(agent)
        world = state["world"]

        def arrows_extra(rect):
            n = agent["arrows"]
            shown = max(self.max_arrows, n)
            if shown > 6:
                draw_text(self.screen, f"x{n}", (rect.x + 50, rect.y + 20), 20, TEXT, True)
                return
            for i in range(shown):
                col = None if i < n else (70, 76, 120)
                self.screen.blit(icon("arrow", 20, col), (rect.x + 50 + i * 22, rect.y + 22))

        def hearts_extra(rect):
            for i in range(max(self.max_lives, lives or 0)):
                col = None if i < (lives or 0) else (70, 76, 120)
                self.screen.blit(icon("heart", 20, col), (rect.x + 50 + i * 22, rect.y + 22))

        tiles = [("gold", "ORO", f"{agent['collected_gold']}/{agent['total_gold']}", None),
                 ("backpack", "FLECHAS", None, arrows_extra),
                 ("pit", "POZOS", len(world["pits"]), None),
                 ("wumpus", "WUMPUS VIVOS", len(world["live_wumpus"]), None)]
        if lives is not None:
            tiles.append(("heart", "VIDA", None, hearts_extra))
        tiles.append(("glitter", "PUNTOS", agent["score"], None))
        rows = (len(tiles) + 1) // 2
        panel = pygame.Rect(sx, 84, sw, 24 + rows * 50 - 6)
        self.screen.blit(panel_surf(panel.w, panel.h, PANEL, BORDER, 18), panel.topleft)
        for i, (ico, label, value, extra) in enumerate(tiles):
            full = i == len(tiles) - 1 and len(tiles) % 2 == 1
            tw = panel.w - 24 if full else (panel.w - 32) // 2
            tx = panel.x + 12 + (0 if full else (i % 2) * (tw + 8))
            self.stat_tile(pygame.Rect(tx, panel.y + 12 + (i // 2) * 50, tw, 44), ico, label, value, extra)
        y = panel.bottom + 12
        # --- brújula ---
        facing = norm_dir(agent["direction"])
        comp = pygame.Rect(sx, y, sw, 90)
        self.screen.blit(panel_surf(comp.w, comp.h, PANEL, BORDER, 18), comp.topleft)
        img = compass_surf(38, facing)
        self.screen.blit(img, img.get_rect(center=(comp.x + 60, comp.centery)))
        px, py = agent["position"]
        draw_text(self.screen, "POSICIÓN", (comp.x + 126, comp.y + 16), 11, MUTED, True)
        draw_text(self.screen, f"({px}, {py})", (comp.x + 126, comp.y + 30), 22, TEXT, True)
        draw_text(self.screen, "MIRANDO AL", (comp.x + 250, comp.y + 16), 11, MUTED, True)
        draw_text(self.screen, DIR_NAMES[facing], (comp.x + 250, comp.y + 30), 22, PRIMARY, True)
        draw_text(self.screen, f"Modo: {'manual' if self.mode == 'manual' else 'agente'}",
                  (comp.x + 126, comp.y + 62), 14, MUTED, True)
        y = comp.bottom + 12
        # --- percepción ---
        p = state.get("perception") or {}
        active = [s for s in SENSES if p.get(s[0])]
        per = pygame.Rect(sx, y, sw, 76 if len(active) <= 3 else 110)
        self.screen.blit(panel_surf(per.w, per.h, PANEL, BORDER, 18), per.topleft)
        draw_text(self.screen, "PERCEPCIÓN", (per.x + 18, per.y + 10), 11, MUTED, True)
        if not active:
            draw_text(self.screen, "Sin señales: casilla tranquila.", (per.x + 18, per.y + 44), 16, MUTED, True)
        cx, cy = per.x + 14, per.y + 30
        for key, label, ico, color in active:
            if cx + 100 > per.right - 8:
                cx, cy = per.x + 14, cy + 34
            chip_rect = chip(self.screen, (cx, cy), ico, label, color)
            self.hit(chip_rect, lambda sound=key: self.audio.play(sound))
            cx = chip_rect.right + 8
        y = per.bottom + 12
        # --- mensaje ---
        msg = pygame.Rect(sx, y, sw, 52)
        self.screen.blit(panel_surf(msg.w, msg.h, (20, 23, 64), BORDER, 16, False), msg.topleft)
        text_block(self.screen, self.message, (msg.x + 18, msg.y + 6), msg.w - 36, 15, TEXT, True,
                   line_h=20, max_lines=2)
        y = msg.bottom + 12
        # --- acciones ---
        act = pygame.Rect(sx, y, sw, 696 - y)
        self.screen.blit(panel_surf(act.w, act.h, PANEL, BORDER, 18), act.topleft)
        if self.mode == "manual":
            bw = (act.w - 24 - 16) // 3
            items = [("Izquierda", "turn_left", "secondary", "TURN_LEFT", False),
                     ("Avanzar", "arrow_up", "secondary", "FORWARD", False),
                     ("Derecha", "turn_right", "secondary", "TURN_RIGHT", False),
                     ("Recoger", "gold", "primary", "GRAB", True),
                     ("Disparar", "arrow", "danger", "SHOOT", False),
                     ("Salir", "exit", "tertiary", "CLIMB", False)]
            bh = (act.h - 24 - 8) // 2
            for i, (label, ico, kind, action, native) in enumerate(items):
                self.add((act.x + 12 + (i % 3) * (bw + 8), act.y + 12 + (i // 3) * (bh + 8), bw, bh), label,
                         lambda a=action: self.perform(a), kind, icon_name=ico, stack=True, size=15,
                         native=native)
        else:
            bw = (act.w - 24 - 8) // 2
            bh = (act.h - 24 - 8) // 2 - 6
            running = self.auto_agent
            self.add((act.x + 12, act.y + 12, bw, bh), "Detener" if running else "Reanudar",
                     lambda: setattr(self, "auto_agent", not self.auto_agent),
                     "tertiary" if running else "primary", icon_name="pause" if running else "play",
                     stack=True, size=16)
            self.add((act.x + 20 + bw, act.y + 12, bw, bh), "Paso", self.agent_step, "secondary",
                     icon_name="arrow_right", stack=True, size=16)
            yy = act.y + 12 + bh + 8
            sp = self.settings["speed"]
            self.add((act.x + 12, yy, 52, 48), "", lambda: self.set_speed(sp - 1), "tertiary",
                     sp > 0, "minus")
            self.add((act.right - 64, yy, 52, 48), "", lambda: self.set_speed(sp + 1), "tertiary",
                     sp < len(SPEEDS) - 1, "plus")
            draw_text(self.screen, "VELOCIDAD", (act.centerx, yy + 2), 11, MUTED, True, "midtop")
            draw_text(self.screen, SPEEDS[sp][0], (act.centerx, yy + 28), 21, PRIMARY, anchor="center", title=True)

    # --------------------------------------------------------- modales --
    def dim(self, alpha=185):
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((4, 6, 22, alpha))
        self.screen.blit(veil, (0, 0))

    def draw_pause(self):
        self.dim()
        box = pygame.Rect(0, 0, 480, 470)
        box.center = (W // 2, H // 2)
        self.screen.blit(panel_surf(box.w, box.h, PANEL, BORDER, 26), box.topleft)
        draw_text(self.screen, "En pausa", (box.centerx, box.y + 62), 52, TEXT, anchor="center",
                  title=True, outline=INK, outline_w=4)
        bx, bw = box.x + 50, box.w - 100
        self.add((bx, box.y + 118, bw, 60), "Continuar", lambda: setattr(self, "paused", False),
                 "primary", icon_name="play", size=24)
        self.add((bx, box.y + 192, bw, 60), "Configuración", lambda: self.show_settings("game"),
                 icon_name="gear", size=22)
        self.add((bx, box.y + 266, bw, 60), "Reiniciar", self.start, "tertiary",
                 icon_name="retry", size=22)
        self.add((bx, box.y + 340, bw, 60), "Menú principal", self.go_menu, "tertiary",
                 icon_name="home", size=22)
        self.add((box.right - 58, box.y + 14, 40, 40), "", lambda: setattr(self, "paused", False),
                 "tertiary", icon_name="close")

    def outcome(self, state):
        status = str(state["status"]).lower()
        agent = state["agent"]
        if status == "success":
            return "win", "¡Ganaste!", "Has encontrado el tesoro y escapado de la cueva.", "chest"
        if any(word in status for word in DEATH_WORDS):
            if "pit" in status or "pozo" in status:
                reason = "Caíste en un pozo sin fondo…"
            elif "wumpus" in status:
                reason = "El Wumpus te ha comido…"
            else:
                reason = "Pedro no sobrevivió a la cueva…"
            return "lose", "¡Game Over!", reason, "wumpus"
        return "end", "Fin de la partida", \
            f"Saliste con {agent['collected_gold']} de {agent['total_gold']} oros.", "gold"

    def draw_result(self, state):
        kind, title, sub, ico = self.outcome(state)
        self.dim(200)
        box = pygame.Rect(0, 0, 540, 540)
        box.center = (W // 2, H // 2)
        self.screen.blit(panel_surf(box.w, box.h, PANEL, BORDER, 28), box.topleft)
        color = {"win": PRIMARY, "lose": DANGER, "end": TEXT}[kind]
        if kind == "win":
            for i in range(6):
                a = self.t * 1.2 + i * math.pi / 3
                r = 104 + 8 * math.sin(self.t * 3 + i)
                s = int(26 + 8 * math.sin(self.t * 4 + i * 2))
                self.screen.blit(icon("glitter", s), icon("glitter", s).get_rect(
                    center=(box.centerx + math.cos(a) * r, box.y + 112 + math.sin(a) * r * .62)))
        bob = math.sin(self.t * 2.4) * 4
        self.screen.blit(icon(ico, 144), (box.centerx - 72, box.y + 40 + bob))
        draw_text(self.screen, title, (box.centerx, box.y + 218), 52, color, anchor="center",
                  title=True, outline=INK, outline_w=4)
        text_block(self.screen, sub, (box.x + 50, box.y + 252), box.w - 100, 20, TEXT, True, center=True)
        agent = state["agent"]
        draw_text(self.screen, f"Oro {agent['collected_gold']}/{agent['total_gold']}   ·   Puntos {agent['score']}",
                  (box.centerx, box.y + 296), 17, MUTED, True, "center")
        bx, bw = box.x + 60, box.w - 120
        self.add((bx, box.y + 340, bw, 58), "Jugar de nuevo", self.start, "primary",
                 icon_name="retry", size=23)
        self.add((bx, box.y + 410, (bw - 12) // 2, 54), "Ver cueva",
                 lambda: setattr(self, "result_hidden", True), "secondary", icon_name="compass", size=19)
        self.add((bx + (bw - 12) // 2 + 12, box.y + 410, (bw - 12) // 2, 54), "Menú",
                 self.go_menu, "tertiary", icon_name="home", size=19)

    def draw_reveal_bar(self):
        bar = pygame.Rect(0, 0, 620, 74)
        bar.midbottom = (SX // 2, H - 10)
        self.screen.blit(panel_surf(bar.w, bar.h, PANEL, BORDER, 20), bar.topleft)
        draw_text(self.screen, "Cueva revelada", (bar.x + 26, bar.centery), 21, TEXT, anchor="midleft", title=True)
        self.add((bar.x + 230, bar.y + 10, 190, 54), "Ver resultado",
                 lambda: setattr(self, "result_hidden", False), "primary", icon_name="check", size=18)
        self.add((bar.x + 430, bar.y + 10, 170, 54), "Menú", self.go_menu, "tertiary",
                 icon_name="home", size=18)


def main():
    """Punto de entrada de la aplicación gráfica."""
    App().run()


if __name__ == "__main__":
    main()
