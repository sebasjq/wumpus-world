import pygame

from ..config import COLORS


def draw_panel(surface: pygame.Surface, rect: pygame.Rect) -> None:
    pygame.draw.rect(surface, COLORS["parchment"], rect, border_radius=8)
    pygame.draw.rect(surface, COLORS["wood"], rect, 5, border_radius=8)


def label(font: pygame.font.Font, text: str, color=COLORS["ink"]) -> pygame.Surface:
    return font.render(text, True, color)
