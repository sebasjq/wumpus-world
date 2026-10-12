import pygame

from .theme import draw_panel


class Panel:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)

    def draw(self, surface: pygame.Surface) -> None:
        draw_panel(surface, self.rect)
