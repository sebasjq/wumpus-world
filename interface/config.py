from pathlib import Path

import pygame

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
DATA_ROOT = PROJECT_ROOT / "data"
ASSET_ROOT = ROOT / "assets"

SCREEN_SIZE = (900, 900)
FPS = 60
BOARD_AREA = pygame.Rect(50, 50, 800, 800)
PANEL_AREA = pygame.Rect(0, 0, 0, 0)
AUTO_DELAY = 0.55
MIN_AUTO_DELAY = 0.08
MAX_AUTO_DELAY = 2.0
ANIMATION_DURATION = 0.22
TITLE = "Mundo de Wumpus"

COLORS = {
    "background": (0, 0, 0),
    "wood": (93, 55, 30),
    "wood_light": (143, 91, 44),
    "parchment": (238, 216, 164),
    "parchment_dark": (191, 158, 103),
    "ink": (43, 30, 20),
    "gold": (231, 187, 47),
    "safe": (75, 151, 91),
    "danger": (178, 65, 48),
    "unknown": (92, 87, 78),
    "fog": (24, 25, 31),
    "white": (245, 240, 220),
}
