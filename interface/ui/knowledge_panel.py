import pygame

from ..config import COLORS
from .theme import label


def draw_knowledge(surface, state, rect, font, small_font) -> None:
    pygame.draw.rect(surface, COLORS["parchment"], rect, border_radius=8)
    pygame.draw.rect(surface, COLORS["wood"], rect, 4, border_radius=8)
    surface.blit(label(font, "Conocimiento del agente"), (rect.x + 14, rect.y + 12))
    knowledge = state["knowledge"]
    rows = [
        ("Seguras", knowledge["safe_cells"], COLORS["safe"]),
        ("Peligro posible", knowledge["possible_pits"] + knowledge["possible_wumpus"], COLORS["danger"]),
        ("Desconocidas", [], COLORS["unknown"]),
    ]
    for index, (name, cells, color) in enumerate(rows):
        y = rect.y + 48 + index * 26
        pygame.draw.rect(surface, color, (rect.x + 14, y + 3, 16, 16))
        surface.blit(label(small_font, f"{name}: {len(cells)}"), (rect.x + 38, y))
